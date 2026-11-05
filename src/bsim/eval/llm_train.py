"""`bsim llm-train`: Claude judges more of the label queue, as training pairs (DESIGN.md §16.84,
D140; series L2).

The label queue (§16.79) holds about 79,000 pairs between train-split books, and the owner's
labels do not yet reach `labels.min_train`. The triage (§16.81) judged the first 500 as
suggestions; this run judges the next `llm_train.pairs` with the same prompt, schema and model,
so that the encoder can train on them as an extra source (`extra_pairs: [llm]`,
`train/pairs.py`): a pair called real with `p_real` ≥ `llm_train.min_p` is a positive, one
called not a hard negative. They are never labels: they live in `artifacts/llm_train/` and the
labels file is not touched.

Calibration, fixed before the run, as the triage's: `calibration.gold` dev Sefaria links against
`calibration.random` random dev pairs (its own seed); the source is refused unless it holds.
Every pair is between two train books, so the dev and test golds stay clean.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path, write_meta
from bsim.eval.llm_batch import (
    Collected,
    Log,
    auc,
    ensure_columns,
    mark_collected,
    run_batch,
    usage,
)
from bsim.eval.llm_triage import (
    VERDICTS,
    answer,
    calibration_set,
    queue_pairs,
    read_triage,
    request,
    verse_texts,
)

OUT = "llm_train"
COLUMNS = {"verdict": None, "p_real": np.nan, "kind": None, "rationale": None}


def build_items(cfg: dict[str, Any], log: Log) -> pd.DataFrame:
    """`set, custom_id, a, b, gold`: the calibration pairs, then the queue's next pairs (those
    the triage already judged left out)."""
    lc = cfg["llm_train"]
    calib = calibration_set(cfg, lc["calibration"], lc["seed"])
    _, done = read_triage(cfg)
    seen: set[tuple[int, int]] = set()
    if done is not None:
        v = lambda s: int(s.removeprefix("v:"))  # noqa: E731
        seen = {
            (min(v(a), v(b)), max(v(a), v(b))) for a, b in zip(done.a_id, done.b_id, strict=True)
        }
    queue = queue_pairs(cfg, lc["pairs"] + len(seen))
    keep = [(min(a, b), max(a, b)) not in seen for a, b in zip(queue.a, queue.b, strict=True)]
    train = queue[keep].head(lc["pairs"]).reset_index(drop=True).assign(gold=None)
    log(
        f"calibration: {len(calib)} pairs; {len(train)} queue pairs"
        f" ({len(seen)} judged by the triage left out)"
    )
    calib = calib.assign(set="calibration", custom_id=[f"cal-{i}" for i in range(len(calib))])
    train = train.assign(set="train", custom_id=[f"trn-{i}" for i in range(len(train))])
    return pd.concat([calib, train], ignore_index=True)[["set", "custom_id", "a", "b", "gold"]]


def run_llm_train(
    cfg: dict[str, Any],
    log: Log = print,
    dry_run: bool = False,
    client: Any = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    lc = cfg["llm_train"]
    out = resolve_path(cfg, "artifacts") / OUT

    def prepare() -> tuple[pd.DataFrame, list[dict]]:
        items = build_items(cfg, log)
        texts = verse_texts(cfg)
        reqs = [
            request(cid, texts[a], texts[b], lc)
            for cid, a, b in zip(items.custom_id, items.a, items.b, strict=True)
        ]
        return items, reqs

    def describe(items: pd.DataFrame) -> str:
        return (
            f"{len(items)} requests ({int((items.set == 'calibration').sum())} calibration,"
            f" {int((items.set == 'train').sum())} queue)"
        )

    got = run_batch(
        out, lc, prepare, answer(lc["rationale_chars"]), log=log, dry_run=dry_run,
        client=client, sleep=sleep, items_file="pairs.parquet", describe=describe,
    )  # fmt: skip
    if not isinstance(got, Collected):
        return got
    df = ensure_columns(got.df, dict(COLUMNS))
    meta = summarise(df, cfg, got.state)
    df["a_id"] = "v:" + df.a.astype(str)
    df["b_id"] = "v:" + df.b.astype(str)
    cols = ["set", "custom_id", "a_id", "b_id", "gold", "status", "verdict", "p_real", "kind",
            "rationale", "input_tokens", "output_tokens"]  # fmt: skip
    df[df.set == "calibration"][cols].to_parquet(out / "calibration.parquet", index=False)
    df[df.set == "train"][cols].to_parquet(out / "judged.parquet", index=False)
    write_meta(out / "llm_train.meta.json", meta)
    mark_collected(out, got.state)
    c = meta["calibration"]
    log(
        f"calibration: AUC {c['auc']} (needs {c['min_auc']}: {'holds' if c['holds'] else 'fails'});"
        f" queue: {meta['train']['verdicts']}; about ${meta['usage']['usd']:.2f}"
    )
    return meta


def summarise(df: pd.DataFrame, cfg: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    lc = cfg["llm_train"]
    c = df[(df.set == "calibration") & (df.status == "ok")]
    gold = c.gold.astype(bool).to_numpy()
    a = auc(gold, c.p_real.to_numpy(float))
    t = df[df.set == "train"]

    def counts(x: pd.DataFrame) -> dict[str, int]:
        return {v: int((x.verdict == v).sum()) for v in VERDICTS}

    return {
        "model": state["model"],
        "batch_id": state["batch_id"],
        "submitted_at": state["created_at"],
        "collected_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": {str(k): int(v) for k, v in df.status.value_counts().items()},
        "calibration": {
            "split": lc["calibration"]["split"],
            "gold": int(gold.sum()),
            "random": int((~gold).sum()),
            "auc": a,
            "min_auc": lc["calibration"]["min_auc"],
            "holds": a is not None and a >= lc["calibration"]["min_auc"],
            "gold_verdicts": counts(c[gold]),
            "random_verdicts": counts(c[~gold]),
        },
        "train": {"pairs": len(t), "ok": int((t.status == "ok").sum()), "verdicts": counts(t)},
        "usage": usage(df, lc),
        "config_hash": config_hash(cfg, "llm_train"),
    }


def judged_runs(cfg: dict[str, Any]) -> pd.DataFrame:
    """`a, b, verdict, p_real`: the answered pairs of the triage and of this run, each only when
    its calibration held (a pair judged twice keeps this run's answer). Empty when none did."""
    art = resolve_path(cfg, "artifacts")
    frames = []
    for name, meta_file, rows_file in (
        ("llm", "llm_triage.meta.json", "triage.parquet"),
        (OUT, "llm_train.meta.json", "judged.parquet"),
    ):
        meta_path, rows_path = art / name / meta_file, art / name / rows_file
        if not (meta_path.exists() and rows_path.exists()):
            continue
        if not json.loads(meta_path.read_text("utf-8"))["calibration"]["holds"]:
            continue
        df = pd.read_parquet(rows_path, columns=["a_id", "b_id", "status", "verdict", "p_real"])
        frames.append(df[df.status == "ok"])
    if not frames:
        return pd.DataFrame({"a": [], "b": [], "verdict": [], "p_real": []})
    df = pd.concat(frames, ignore_index=True)
    a = df.a_id.str.removeprefix("v:").astype(np.int64).to_numpy()
    b = df.b_id.str.removeprefix("v:").astype(np.int64).to_numpy()
    df = pd.DataFrame(
        {"a": np.minimum(a, b), "b": np.maximum(a, b), "verdict": df.verdict, "p_real": df.p_real}
    )
    return df.drop_duplicates(["a", "b"], keep="last").reset_index(drop=True)
