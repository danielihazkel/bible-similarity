"""`bsim deploy-bundle`: what a public read-only server needs, and nothing personal (DESIGN.md
§10.3, docs/DEPLOY.md).

Writes `deploy.out` (default `bundle/`, gitignored), laid out as `configs/public.yaml` reads it:
- `artifacts/results.sqlite`: the results DB, copied with SQLite's backup API (a consistent copy
  even while `bsim serve` has it open). With `no_nc`, every table of `deploy.noncommercial` is
  emptied, not dropped, and its stages taken off the build's `stages_run`: the API then answers
  their pages as stages that did not run ("not computed in this build"), as it does for any
  optional stage. Then VACUUM.
- `artifacts/<meta.embeddings>`: the final system's verse vectors (unless `embeddings=False`),
  for /compare, the semantic structure basis and the ladders' cosines.
- `artifacts/eval/`: the files /eval reads (`deploy.eval_files`), less the non-commercial ones.
- `bundle.json`: what was copied, emptied and left out, with sizes.

Never copied: your labels and notebook (`paths.labels`), Claude's suggestions (`artifacts/llm`),
models, raw downloads.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bsim.config import PROJECT_ROOT, resolve_path

Log = Callable[[str], None]


def noncommercial(cfg: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    """(stages, tables, eval files) carrying CC BY-NC data, over every source of
    `deploy.noncommercial`."""
    groups = cfg["deploy"]["noncommercial"].values()
    return tuple([x for g in groups for x in g[k]] for k in ("stages", "tables", "eval_files"))


def run_deploy_bundle(
    cfg: dict[str, Any],
    out: Path | None = None,
    *,
    no_nc: bool = False,
    embeddings: bool = True,
    log: Log = print,
) -> dict[str, Any]:
    d = cfg["deploy"]
    out = out if out is not None else PROJECT_ROOT / d["out"]
    db, art = resolve_path(cfg, "db"), resolve_path(cfg, "artifacts")
    if not db.exists():
        raise RuntimeError(f"{db} missing; run `bsim build-db` first")
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"{out} is not empty; remove it or pass another --out")
    nc_stages, nc_tables, nc_files = noncommercial(cfg) if no_nc else ([], [], [])
    (out / "artifacts" / "eval").mkdir(parents=True, exist_ok=True)

    dest = out / "artifacts" / "results.sqlite"
    t0 = time.perf_counter()
    src = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
        meta = {k: json.loads(v) for k, v in dst.execute("SELECT key, value FROM meta")}
        present = {r[0] for r in dst.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        emptied = {}
        for t in nc_tables:
            if t in present:
                emptied[t] = dst.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                dst.execute(f"DELETE FROM {t}")
        # off the build's list of stages run, and their own meta entries: the API answers them as
        # stages that did not run (`routes._common.stage_ran`)
        if nc_stages and "stages_run" in meta:
            ran = [s for s in meta["stages_run"] if s not in nc_stages]
            dst.execute("UPDATE meta SET value = ? WHERE key = 'stages_run'", (json.dumps(ran),))
        for s in nc_stages:
            dst.execute("DELETE FROM meta WHERE key = ?", (s.replace("-", "_"),))
        dst.commit()
        if emptied:
            dst.execute("VACUUM")
    finally:
        src.close()
        dst.close()
    log(f"results DB: {dest.stat().st_size / 2**20:.0f} MB ({time.perf_counter() - t0:.0f} s)")
    if emptied:
        log(f"emptied {len(emptied)} non-commercial tables ({sum(emptied.values())} rows)")

    files: dict[str, int] = {"artifacts/results.sqlite": dest.stat().st_size}
    if embeddings:
        name = meta["embeddings"]
        target = out / "artifacts" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(art / name, target)
        files[f"artifacts/{name}"] = target.stat().st_size
    skipped = []
    for f in d["eval_files"]:
        path = art / "eval" / f
        if f in nc_files or not path.exists():
            skipped.append(f)
            continue
        shutil.copyfile(path, out / "artifacts" / "eval" / f)
        files[f"artifacts/eval/{f}"] = path.stat().st_size

    manifest = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "db_built_at": meta.get("built_at"),
        "noncommercial_removed": no_nc,
        "embeddings": embeddings,
        "stages_removed": nc_stages,
        "emptied_tables": emptied,
        "eval_files_left_out": skipped,
        "files": files,
    }
    (out / "bundle.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    total = sum(files.values()) / 2**20
    log(f"wrote {out} ({len(files)} files, {total:.0f} MB); serve it with configs/public.yaml")
    return manifest
