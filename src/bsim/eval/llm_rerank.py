"""`bsim llm-rerank`: Claude judges the cross-encoder's negatives, as soft targets (DESIGN.md
§16.85, D141; series L4).

The cross-encoder (§16.3) learns from Sefaria's train links as positives and, as negatives, up to
`rerank.negatives_per_query` targets drawn from each anchor's own fused list that no gold links.
Some of those negatives are connections Sefaria never recorded, and the loss teaches the model to
score them low. This run draws `llm_rerank.sample` of the training negatives (the same draw
`train-rerank` makes, `train/rerank.py` `training_pairs`) and has Claude judge them with the
triage's prompt, schema and model. With `rerank.soft_labels: llm`, `train-rerank` trains on its
`p_real` as the target of each judged negative (and, with `rerank.llm_extra`, on the queue pairs
of `bsim llm-triage` / `bsim llm-train` as extra rows), a calibrated run's answers only.

Calibration, fixed before the run: `calibration.gold` dev Sefaria links against
`calibration.random` random dev pairs (its own seed), AUC ≥ `min_auc`. Every pair is between
train books (the negatives' rule), so dev and test stay clean.
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
from bsim.eval.llm_triage import VERDICTS, answer, calibration_set, request, verse_texts

OUT = "llm_rerank"
COLUMNS = {"verdict": None, "p_real": np.nan, "kind": None, "rationale": None}


def negative_sample(negatives: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """`a, b`: `n` of the training negatives (`a, b, label` rows with label 0), drawn with
    `seed` and kept in their order; the same undirected pair once."""
    neg = negatives[negatives.label == 0]
    key = np.minimum(neg.a, neg.b) * 10**6 + np.maximum(neg.a, neg.b)
    neg = neg[~key.duplicated()].reset_index(drop=True)
    rng = np.random.default_rng(seed)
    take = np.sort(rng.choice(len(neg), size=min(n, len(neg)), replace=False))
    return neg.iloc[take][["a", "b"]].reset_index(drop=True)


def build_items(cfg: dict[str, Any], log: Log) -> pd.DataFrame:
    """`set, custom_id, a, b, gold`: the calibration pairs, then the sampled negatives."""
    from bsim.train.rerank import Corpus, training_pairs

    lc, rc = cfg["llm_rerank"], cfg["rerank"]
    calib = calibration_set(cfg, lc["calibration"], lc["seed"])
    data = training_pairs(Corpus(cfg), rc["negatives_per_query"], cfg["seed"])
    neg = negative_sample(data, lc["sample"], lc["seed"]).assign(gold=None)
    log(
        f"calibration: {len(calib)} pairs; {len(neg)} of the cross-encoder's"
        f" {int((data.label == 0).sum())} training negatives"
    )
    calib = calib.assign(set="calibration", custom_id=[f"cal-{i}" for i in range(len(calib))])
    neg = neg.assign(set="negative", custom_id=[f"neg-{i}" for i in range(len(neg))])
    return pd.concat([calib, neg], ignore_index=True)[["set", "custom_id", "a", "b", "gold"]]


def run_llm_rerank(
    cfg: dict[str, Any],
    log: Log = print,
    dry_run: bool = False,
    client: Any = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    lc = cfg["llm_rerank"]
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
            f" {int((items.set == 'negative').sum())} negatives)"
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
    df[df.set == "negative"][cols].to_parquet(out / "judged.parquet", index=False)
    write_meta(out / "llm_rerank.meta.json", meta)
    mark_collected(out, got.state)
    c = meta["calibration"]
    log(
        f"calibration: AUC {c['auc']} (needs {c['min_auc']}: {'holds' if c['holds'] else 'fails'});"
        f" negatives: {meta['negatives']['verdicts']}; about ${meta['usage']['usd']:.2f}"
    )
    return meta


def summarise(df: pd.DataFrame, cfg: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    lc = cfg["llm_rerank"]
    c = df[(df.set == "calibration") & (df.status == "ok")]
    gold = c.gold.astype(bool).to_numpy()
    a = auc(gold, c.p_real.to_numpy(float))
    n = df[df.set == "negative"]

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
        "negatives": {"pairs": len(n), "ok": int((n.status == "ok").sum()), "verdicts": counts(n)},
        "usage": usage(df, lc),
        "config_hash": config_hash(cfg, "llm_rerank", "rerank", "seed"),
    }


def soft_targets(cfg: dict[str, Any]) -> tuple[dict[tuple[int, int], float], set[tuple[int, int]]]:
    """Undirected pair -> Claude's `p_real`, from this run and the queue runs (`llm-triage`,
    `llm-train`), each only when its calibration held; and the pairs of this run (the judged
    negatives), so the queue pairs can be told apart."""
    from bsim.eval.llm_train import judged_runs

    out: dict[tuple[int, int], float] = {}
    q = judged_runs(cfg)
    for a, b, p in zip(q.a, q.b, q.p_real, strict=True):
        out[(int(a), int(b))] = float(p)
    own: set[tuple[int, int]] = set()
    art = resolve_path(cfg, "artifacts") / OUT
    meta_path, rows = art / "llm_rerank.meta.json", art / "judged.parquet"
    held = meta_path.exists() and rows.exists()
    if held and json.loads(meta_path.read_text("utf-8"))["calibration"]["holds"]:
        df = pd.read_parquet(rows, columns=["a_id", "b_id", "status", "p_real"])
        df = df[df.status == "ok"]
        a = df.a_id.str.removeprefix("v:").astype(np.int64).to_numpy()
        b = df.b_id.str.removeprefix("v:").astype(np.int64).to_numpy()
        for x, y, p in zip(a, b, df.p_real, strict=True):
            key = (int(min(x, y)), int(max(x, y)))
            out[key] = float(p)
            own.add(key)
    return out, own


def apply_soft_labels(
    data: pd.DataFrame,
    targets: dict[tuple[int, int], float],
    own: set[tuple[int, int]],
    train_pair: Callable[[int, int], bool],
    extra: bool,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Each negative row (label 0) Claude judged takes its `p_real` as the target; positives
    keep 1. With `extra`, the judged queue pairs not already rows join as rows of their own
    (a, b, p_real), those `train_pair` accepts only."""
    data = data.copy()
    key = [(min(a, b), max(a, b)) for a, b in zip(data.a, data.b, strict=True)]
    soft = [(lab == 0) and (k in targets) for lab, k in zip(data.label, key, strict=True)]
    data.loc[soft, "label"] = [targets[k] for k, s in zip(key, soft, strict=True) if s]
    counts = {"soft_negatives": int(sum(soft)), "extra_rows": 0}
    if extra:
        have = set(key)
        rows = [
            (a, b, p)
            for (a, b), p in sorted(targets.items())
            if (a, b) not in own and (a, b) not in have and train_pair(a, b)
        ]
        if rows:
            data = pd.concat(
                [data, pd.DataFrame(rows, columns=["a", "b", "label"])], ignore_index=True
            )
        counts["extra_rows"] = len(rows)
    return data, counts
