"""Download the raw sources into data/raw and record them in manifest.json (DESIGN.md §1).

Layout under `paths.data_raw`:
    oshb/{osis}.xml                    OSHB WLC at a pinned commit
    sefaria/text/{Book}.json           Miqra according to the Masorah
    sefaria/schemas/{Book_Slug}.json   index schema (parasha `alts`)
    sefaria/links/linksN.csv           all Sefaria links (discovered by listing the bucket)
    lexicon/{file}                     SDBH (UBS, senses and domains) and OpenScriptures
                                       HebrewStrong.xml, each at a pinned commit (§16.22)

Idempotent: a file is skipped when it is already on disk and still matches its checksum
(GCS md5 for Sefaria files, the recorded sha256 for files from GitHub).
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bsim.config import resolve_path
from bsim.data.canon import BOOKS

MANIFEST = "manifest.json"
GROUPS = ("oshb", "text", "schemas", "links", "lexicon")
_CHUNK = 1 << 20
_TIMEOUT = 60


@dataclass(frozen=True)
class Target:
    group: str
    rel: str  # destination path relative to data_raw, POSIX style
    url: str
    md5: str | None = None  # base64 MD5 as reported by GCS
    size: int | None = None


def make_session() -> requests.Session:
    retry = Retry(total=5, backoff_factor=1.0, status_forcelist=(429, 500, 502, 503, 504))
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry, pool_maxsize=16))
    return session


# --- GCS helpers -------------------------------------------------------------------------


def _gcs_urls(cfg: dict[str, Any]) -> tuple[str, str]:
    bucket = cfg["sources"]["sefaria"]["bucket"]
    return (
        f"https://storage.googleapis.com/{bucket}",
        f"https://storage.googleapis.com/storage/v1/b/{bucket}/o",
    )


def _gcs_meta(session: requests.Session, api: str, name: str) -> dict[str, Any]:
    r = session.get(f"{api}/{quote(name, safe='')}", timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _gcs_list(session: requests.Session, api: str, prefix: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    params: dict[str, str] = {"prefix": prefix}
    while True:
        r = session.get(api, params=params, timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        items.extend(data.get("items", []))
        if "nextPageToken" not in data:
            return items
        params["pageToken"] = data["nextPageToken"]


def _gcs_target(group: str, rel: str, public: str, meta: dict[str, Any]) -> Target:
    return Target(
        group=group,
        rel=rel,
        url=f"{public}/{quote(meta['name'])}",
        md5=meta.get("md5Hash"),
        size=int(meta["size"]) if "size" in meta else None,
    )


# --- planning ----------------------------------------------------------------------------


def plan_targets(
    cfg: dict[str, Any], session: requests.Session, groups: Iterable[str] = GROUPS
) -> list[Target]:
    """Resolve every file to download (queries the GCS API for Sefaria checksums)."""
    groups = set(groups)
    src = cfg["sources"]
    public, api = _gcs_urls(cfg)
    targets: list[Target] = []

    if "oshb" in groups:
        oshb = src["oshb"]
        for b in BOOKS:
            url = oshb["raw_url"].format(commit=oshb["commit"], osis=b.osis)
            targets.append(Target("oshb", f"oshb/{b.osis}.xml", url))

    if "lexicon" in groups:
        for key in ("sdbh", "hebrew_lexicon"):
            s = src[key]
            for file in s["files"]:
                url = s["raw_url"].format(commit=s["commit"], file=file)
                targets.append(Target("lexicon", f"lexicon/{file}", url))

    sef = src["sefaria"]
    if "text" in groups:
        for b in BOOKS:
            name = sef["text_path"].format(
                section=b.section, book=b.sefaria, version=sef["text_version"]
            )
            meta = _gcs_meta(session, api, name)
            targets.append(_gcs_target("text", f"sefaria/text/{b.sefaria}.json", public, meta))

    if "schemas" in groups:
        for b in BOOKS:
            name = sef["schema_path"].format(slug=b.sefaria_slug)
            meta = _gcs_meta(session, api, name)
            rel = f"sefaria/schemas/{b.sefaria_slug}.json"
            targets.append(_gcs_target("schemas", rel, public, meta))

    if "links" in groups:
        pattern = re.compile(sef["links_regex"])
        metas = [
            m for m in _gcs_list(session, api, sef["links_prefix"]) if pattern.match(m["name"])
        ]
        if not metas:
            raise RuntimeError(f"No link files matched {sef['links_regex']!r} in the bucket")
        for meta in sorted(metas, key=lambda m: m["name"]):
            rel = f"sefaria/links/{Path(meta['name']).name}"
            targets.append(_gcs_target("links", rel, public, meta))

    return targets


# --- fetching ----------------------------------------------------------------------------


def _file_hashes(path: Path) -> tuple[str, str]:
    """Return (sha256 hex, md5 base64) of a file."""
    sha, md5 = hashlib.sha256(), hashlib.md5()
    with path.open("rb") as f:
        while chunk := f.read(_CHUNK):
            sha.update(chunk)
            md5.update(chunk)
    return sha.hexdigest(), base64.b64encode(md5.digest()).decode()


def _is_current(target: Target, path: Path, entry: dict[str, Any] | None) -> tuple[bool, str]:
    if not path.exists():
        return False, ""
    sha, md5 = _file_hashes(path)
    if target.md5 is not None:
        return md5 == target.md5, sha
    return entry is not None and entry.get("url") == target.url and entry.get("sha256") == sha, sha


def fetch(
    session: requests.Session, target: Target, raw_dir: Path, entry: dict[str, Any] | None
) -> tuple[str, dict[str, Any]]:
    """Download one target unless current. Returns (status, manifest entry)."""
    dest = raw_dir / target.rel
    current, sha = _is_current(target, dest, entry)
    if current:
        if entry and entry.get("url") == target.url and entry.get("sha256") == sha:
            return "skipped", entry
        return "skipped", _entry(target, sha, dest.stat().st_size)

    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    sha_h, md5_h, n = hashlib.sha256(), hashlib.md5(), 0
    with session.get(target.url, stream=True, timeout=_TIMEOUT) as r:
        r.raise_for_status()
        with part.open("wb") as f:
            for chunk in r.iter_content(_CHUNK):
                f.write(chunk)
                sha_h.update(chunk)
                md5_h.update(chunk)
                n += len(chunk)

    md5 = base64.b64encode(md5_h.digest()).decode()
    if target.md5 is not None and md5 != target.md5:
        part.unlink(missing_ok=True)
        raise OSError(f"MD5 mismatch for {target.rel}: got {md5}, expected {target.md5}")
    if target.size is not None and n != target.size:
        part.unlink(missing_ok=True)
        raise OSError(f"Size mismatch for {target.rel}: got {n}, expected {target.size}")
    part.replace(dest)
    return "downloaded", _entry(target, sha_h.hexdigest(), n)


def _entry(target: Target, sha256: str, size: int) -> dict[str, Any]:
    return {
        "group": target.group,
        "url": target.url,
        "sha256": sha256,
        "md5": target.md5,
        "bytes": size,
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


# --- manifest + driver -------------------------------------------------------------------


def load_manifest(raw_dir: Path) -> dict[str, Any]:
    path = raw_dir / MANIFEST
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"files": {}}


def save_manifest(raw_dir: Path, manifest: dict[str, Any]) -> None:
    path = raw_dir / MANIFEST
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True), "utf-8")
    tmp.replace(path)


def run_download(
    cfg: dict[str, Any],
    session: requests.Session | None = None,
    groups: Iterable[str] = GROUPS,
    workers: int = 8,
    raw_dir: Path | None = None,
    log=print,
) -> dict[str, Any]:
    """Download everything in `groups`; returns the updated manifest."""
    session = session or make_session()
    raw_dir = raw_dir or resolve_path(cfg, "data_raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(raw_dir)
    files: dict[str, Any] = manifest.setdefault("files", {})

    targets = plan_targets(cfg, session, groups)
    log(f"{len(targets)} files to check")

    counts = {"downloaded": 0, "skipped": 0}
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, session, t, raw_dir, files.get(t.rel)): t for t in targets}
        for fut in as_completed(futures):
            t = futures[fut]
            try:
                status, entry = fut.result()
            except Exception as e:  # noqa: BLE001 - collect and report all failures
                errors.append(f"{t.rel}: {e}")
                log(f"  FAILED     {t.rel}: {e}")
                continue
            files[t.rel] = entry
            counts[status] += 1
            if status == "downloaded":
                log(f"  downloaded {t.rel} ({entry['bytes'] / 1e6:.1f} MB)")

    manifest["oshb_commit"] = cfg["sources"]["oshb"]["commit"]
    manifest["sdbh_commit"] = cfg["sources"]["sdbh"]["commit"]
    manifest["hebrew_lexicon_commit"] = cfg["sources"]["hebrew_lexicon"]["commit"]
    manifest["sefaria_text_version"] = cfg["sources"]["sefaria"]["text_version"]
    manifest["updated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    save_manifest(raw_dir, manifest)

    log(f"done: {counts['downloaded']} downloaded, {counts['skipped']} up to date")
    if errors:
        raise RuntimeError(f"{len(errors)} downloads failed:\n" + "\n".join(errors))
    return manifest
