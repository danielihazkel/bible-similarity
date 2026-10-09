"""Offline tests for the downloader, using a fake HTTP session."""

import base64
import hashlib
import json
from urllib.parse import quote

import pytest

from bsim.config import load_config
from bsim.data.download import Target, fetch, load_manifest, plan_targets, run_download

PUBLIC = "https://storage.googleapis.com/sefaria-export"
API = "https://storage.googleapis.com/storage/v1/b/sefaria-export/o"


def b64md5(data: bytes) -> str:
    return base64.b64encode(hashlib.md5(data).digest()).decode()


class FakeResponse:
    def __init__(self, body: bytes = b"", payload=None, status: int = 200):
        self.body, self.payload, self.status_code = body, payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise OSError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload

    def iter_content(self, size):
        for i in range(0, len(self.body), size):
            yield self.body[i : i + size]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeSession:
    """Serves GCS metadata/listing JSON and file bodies from in-memory dicts."""

    def __init__(self, gcs_files: dict[str, bytes], other: dict[str, bytes]):
        self.gcs_files, self.other = gcs_files, other
        self.downloads: list[str] = []

    def _meta(self, name):
        body = self.gcs_files[name]
        return {"name": name, "size": str(len(body)), "md5Hash": b64md5(body)}

    def get(self, url, params=None, stream=False, timeout=None):
        if url == API:
            names = [n for n in self.gcs_files if n.startswith(params["prefix"])]
            return FakeResponse(payload={"items": [self._meta(n) for n in names]})
        if url.startswith(API + "/"):
            name = url[len(API) + 1 :].replace("%2F", "/").replace("%20", " ")
            if name not in self.gcs_files:
                return FakeResponse(status=404)
            return FakeResponse(payload=self._meta(name))
        self.downloads.append(url)
        for name, body in self.gcs_files.items():
            if url == f"{PUBLIC}/{quote(name)}":
                return FakeResponse(body=body)
        if url in self.other:
            return FakeResponse(body=self.other[url])
        return FakeResponse(status=404)


@pytest.fixture
def cfg():
    return load_config()


@pytest.fixture
def session(cfg):
    from bsim.data.canon import BOOKS

    sef = cfg["sources"]["sefaria"]
    gcs: dict[str, bytes] = {}
    for b in BOOKS:
        text = sef["text_path"].format(
            section=b.section, book=b.sefaria, version=sef["text_version"]
        )
        gcs[text] = json.dumps({"title": b.sefaria}).encode()
        gcs[sef["schema_path"].format(slug=b.sefaria_slug)] = b"{}"
    gcs["links/links0.csv"] = b"Citation 1,Citation 2\n"
    gcs["links/links1.csv"] = b"Citation 1,Citation 2\n"
    gcs["links/links_by_book.csv"] = b"ignored"  # must not match links_regex
    oshb = cfg["sources"]["oshb"]
    other = {
        oshb["raw_url"].format(commit=oshb["commit"], osis=b.osis): f"<osis {b.osis}/>".encode()
        for b in BOOKS
    }
    for key in ("sdbh", "hebrew_lexicon", "bhsa", "etcbc_parallels"):
        s = cfg["sources"][key]
        for file in s["files"]:
            other[s["raw_url"].format(commit=s["commit"], file=file)] = file.encode()
    return FakeSession(gcs, other)


def test_plan_targets(cfg, session):
    targets = plan_targets(cfg, session)
    by_group = {
        g: [t for t in targets if t.group == g]
        for g in ("oshb", "text", "schemas", "links", "lexicon", "syntax", "parallels")
    }
    assert {t.rel for t in by_group["syntax"]} >= {"bhsa/otype.tf", "bhsa/oslots.tf"}
    assert not any("gloss" in t.rel for t in by_group["syntax"])  # D5
    assert [t.rel for t in by_group["parallels"]] == ["etcbc_parallels/crossref.tf"]
    assert len(by_group["oshb"]) == len(by_group["text"]) == len(by_group["schemas"]) == 39
    assert [t.rel for t in by_group["links"]] == [
        "sefaria/links/links0.csv",
        "sefaria/links/links1.csv",
    ]
    assert all(t.md5 for t in by_group["text"])
    assert {t.rel for t in by_group["lexicon"]} == {
        "lexicon/UBSHebrewDic-v0.9.3-en.JSON",
        "lexicon/UBSHebrewDicLexicalDomains-v0.9.3-en.JSON",
        "lexicon/HebrewStrong.xml",
    }
    assert "Song_of_Songs.json" in {t.rel.rsplit("/", 1)[1] for t in by_group["schemas"]}


def test_run_download_is_idempotent(cfg, session, tmp_path):
    m1 = run_download(cfg, session, raw_dir=tmp_path, log=lambda *_: None)
    assert len(m1["files"]) == 39 * 3 + 2 + 3 + len(cfg["sources"]["bhsa"]["files"]) + 1
    assert (tmp_path / "oshb" / "Gen.xml").read_bytes() == b"<osis Gen/>"
    assert (tmp_path / "sefaria" / "text" / "Song of Songs.json").exists()
    assert load_manifest(tmp_path)["oshb_commit"] == cfg["sources"]["oshb"]["commit"]

    n_before = len(session.downloads)
    run_download(cfg, session, raw_dir=tmp_path, log=lambda *_: None)
    assert len(session.downloads) == n_before  # nothing re-downloaded


def test_changed_file_is_redownloaded(cfg, session, tmp_path):
    run_download(cfg, session, groups=["links", "oshb"], raw_dir=tmp_path, log=lambda *_: None)
    (tmp_path / "sefaria" / "links" / "links0.csv").write_bytes(b"corrupted")
    (tmp_path / "oshb" / "Ruth.xml").write_bytes(b"corrupted")
    n_before = len(session.downloads)
    run_download(cfg, session, groups=["links", "oshb"], raw_dir=tmp_path, log=lambda *_: None)
    assert len(session.downloads) == n_before + 2
    assert (tmp_path / "oshb" / "Ruth.xml").read_bytes() == b"<osis Ruth/>"


def test_md5_mismatch_rejected(session, tmp_path):
    session.other["https://example.org/f"] = b"actual"
    target = Target("links", "x/f.csv", "https://example.org/f", md5=b64md5(b"expected"))
    with pytest.raises(OSError, match="MD5 mismatch"):
        fetch(session, target, tmp_path, None)
    assert not (tmp_path / "x" / "f.csv").exists()
    assert not (tmp_path / "x" / "f.csv.part").exists()
