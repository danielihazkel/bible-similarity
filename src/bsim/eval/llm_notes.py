"""`bsim llm-notes`: Claude's reading of the strongest parallels, shown as notes beside them
(DESIGN.md §16.88, D144; series L7).

The viewer shows a verse pair with its scores and shared words; what connects the two is left to
the reader. Every Claude run of series L reads verse pairs with the same prompt and a Hebrew
rationale (§16.81): the triage, the judged pool, the queue's training pairs, the reranker's
negatives. This run adds the strongest fused verse discoveries not yet read
(`llm_notes.pairs`: pairs ranked first both ways, then first one way, then by their semantic
score), with a calibration of its own fixed before the run.

`read_notes` gathers every run whose calibration held into one note per pair (this run's first,
then the pool's, the training pairs', the reranker's and the triage's, the triage only when its
rationale is in Hebrew). A note is a suggestion: its verdict, `p_real`, kind and a rationale shown
only through `clean_rationale` (D134). Notes are personal (`serve.personal`) and stay out of the
deploy bundle.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path, write_meta
from bsim.eval.llm_batch import (
    Collected,
    Log,
    auc,
    clean_rationale,
    ensure_columns,
    mark_collected,
    run_batch,
    usage,
)
from bsim.eval.llm_triage import VERDICTS, answer, calibration_set, request, verse_texts

OUT = "llm_notes"
# run folder, meta file, rows file, the rows' pair columns (ids "v:N" or ints); first wins
RUNS = (
    (OUT, "llm_notes.meta.json", "notes.parquet", ("a_id", "b_id")),
    ("llm_pool", "llm_pool.meta.json", "judged.parquet", ("a", "b")),
    ("llm_train", "llm_train.meta.json", "judged.parquet", ("a_id", "b_id")),
    ("llm_rerank", "llm_rerank.meta.json", "judged.parquet", ("a_id", "b_id")),
    ("llm", "llm_triage.meta.json", "triage.parquet", ("a_id", "b_id")),
)


def _vid(x: Any) -> int:
    return int(str(x).removeprefix("v:"))


def run_files(cfg: dict[str, Any]) -> list[Path]:
    art = resolve_path(cfg, "artifacts")
    return [p for d, m, r, _ in RUNS for p in (art / d / m, art / d / r)]


def read_notes(cfg: dict[str, Any]) -> tuple[dict[str, Any], dict[tuple[int, int], dict]]:
    """The runs used (name -> model, AUC, pairs) and undirected verse pair -> note."""
    art = resolve_path(cfg, "artifacts")
    runs: dict[str, Any] = {}
    notes: dict[tuple[int, int], dict] = {}
    for d, meta_file, rows_file, (ca, cb) in RUNS:
        mp, rp = art / d / meta_file, art / d / rows_file
        if not (mp.exists() and rp.exists()):
            continue
        meta = json.loads(mp.read_text("utf-8"))
        if not meta["calibration"]["holds"] or meta.get("rationale", "hebrew") != "hebrew":
            continue
        df = pd.read_parquet(
            rp, columns=[ca, cb, "status", "verdict", "p_real", "kind", "rationale"]
        )
        df = df[df.status == "ok"]
        runs[d] = {"model": meta["model"], "auc": meta["calibration"]["auc"], "pairs": len(df)}
        for a, b, v, p, k, r in zip(df[ca], df[cb], df.verdict, df.p_real, df.kind, df.rationale,
                                    strict=True):  # fmt: skip
            key = (min(_vid(a), _vid(b)), max(_vid(a), _vid(b)))
            if key not in notes:
                notes[key] = {"verdict": v, "p_real": float(p), "kind": k,
                              "rationale": clean_rationale(r), "run": d}  # fmt: skip
    return runs, notes


def strongest(conn: Any, n: int, skip: set[tuple[int, int]]) -> pd.DataFrame:
    """`a, b`: the `n` strongest fused verse discoveries not in `skip`: ranked first both ways,
    then first one way, then by the semantic score (`tie`)."""
    df = pd.read_sql_query(
        "SELECT a_id, b_id, rank_ab, rank_ba, tie FROM discoveries"
        " WHERE unit_type = 'verse' AND mode = 'fused'",
        conn,
    )
    df["both"] = (df.rank_ab == 1) & (df.rank_ba == 1)
    df["one"] = (df.rank_ab == 1) | (df.rank_ba == 1)
    df = df.sort_values(["both", "one", "tie"], ascending=[False, False, False], kind="stable")
    a = df.a_id.map(_vid).to_numpy()
    b = df.b_id.map(_vid).to_numpy()
    keep = [(min(x, y), max(x, y)) not in skip for x, y in zip(a, b, strict=True)]
    out = pd.DataFrame({"a": a, "b": b})[keep].head(n)
    return out.reset_index(drop=True)


def build_items(cfg: dict[str, Any], log: Log) -> pd.DataFrame:
    from bsim.store.db import connect_readonly

    lc = cfg["llm_notes"]
    calib = calibration_set(cfg, lc["calibration"], lc["seed"])
    _, done = read_notes(cfg)
    conn = connect_readonly(resolve_path(cfg, "db"))
    try:
        top = strongest(conn, lc["pairs"], set(done))
    finally:
        conn.close()
    log(f"calibration: {len(calib)} pairs; {len(top)} strongest discoveries ({len(done)} already"
        " read by another run left out)")  # fmt: skip
    calib = calib.assign(set="calibration", custom_id=[f"cal-{i}" for i in range(len(calib))])
    top = top.assign(set="note", gold=None, custom_id=[f"note-{i}" for i in range(len(top))])
    cols = ["set", "custom_id", "a", "b", "gold"]
    return pd.concat([calib[cols], top[cols]], ignore_index=True)


def run_llm_notes(
    cfg: dict[str, Any],
    log: Log = print,
    dry_run: bool = False,
    client: Any = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    lc = cfg["llm_notes"]
    out = resolve_path(cfg, "artifacts") / OUT

    def prepare() -> tuple[pd.DataFrame, list[dict]]:
        items = build_items(cfg, log)
        texts = verse_texts(cfg)
        reqs = [
            request(cid, texts[a], texts[b], lc)
            for cid, a, b in zip(items.custom_id, items.a, items.b, strict=True)
        ]
        return items, reqs

    got = run_batch(
        out, lc, prepare, answer(lc["rationale_chars"]), log=log, dry_run=dry_run,
        client=client, sleep=sleep, items_file="pairs.parquet",
    )  # fmt: skip
    if not isinstance(got, Collected):
        return got
    df = ensure_columns(
        got.df, {"verdict": None, "p_real": np.nan, "kind": None, "rationale": None}
    )
    c = df[(df.set == "calibration") & (df.status == "ok")]
    gold = c.gold.astype(bool).to_numpy()
    a = auc(gold, c.p_real.to_numpy(float))
    notes = df[df.set == "note"].copy()
    meta = {
        "model": got.state["model"],
        "rationale": lc["rationale"],
        "batch_id": got.state["batch_id"],
        "submitted_at": got.state["created_at"],
        "collected_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": {str(k): int(v) for k, v in df.status.value_counts().items()},
        "calibration": {
            "gold": int(gold.sum()),
            "random": int((~gold).sum()),
            "auc": a,
            "min_auc": lc["calibration"]["min_auc"],
            "holds": a is not None and a >= lc["calibration"]["min_auc"],
        },
        "notes": {v: int((notes.verdict == v).sum()) for v in VERDICTS},
        "usage": usage(df, lc),
        "config_hash": config_hash(cfg, "llm_notes"),
    }
    notes["a_id"] = "v:" + notes.a.astype(str)
    notes["b_id"] = "v:" + notes.b.astype(str)
    cols = ["a_id", "b_id", "status", "verdict", "p_real", "kind", "rationale", "input_tokens",
            "output_tokens"]  # fmt: skip
    notes[cols].to_parquet(out / "notes.parquet", index=False)
    write_meta(out / "llm_notes.meta.json", meta)
    mark_collected(out, got.state)
    log(f"calibration AUC {a}; notes {meta['notes']}; about ${meta['usage']['usd']:.2f}")
    return meta
