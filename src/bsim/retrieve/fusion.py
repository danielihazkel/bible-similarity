"""`bsim fuse`: weighted Reciprocal Rank Fusion of the final lexical and semantic lists (§5.3).

`fused(t) = w_lex / (rrf_k + rank_lex(t)) + w_sem / (rrf_k + rank_sem(t))` over the two stored
top-k lists of a unit (a list missing `t` contributes 0); the best `retrieval.k` are kept, ties
ordered by target position. The lists fused per unit type are `final_lists`: verse =
`final_systems.lexical` + `final_systems.semantic`; chapter / pericope / parasha =
`final_systems.unit_lexical` + `{semantic}_{unit_aggregation}`.

Writes `artifacts/topk/{type}/{final_systems.fused}.parquet` with `lex_score, lex_rank, sem_score,
sem_rank` (nullable) next to the usual columns. `bsim fuse --tune` scores `fusion.w_lex_grid` on
dev in memory (verse + unit levels with gold) and writes `artifacts/eval/fusion_tuning.json`;
the chosen weight goes into the config by hand.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.retrieve.topk import Units, load_units, read_topk, verse_ids, write_topk

Log = Callable[[str], None]

BREAKDOWN = ("score", "lex_score", "lex_rank", "sem_score", "sem_rank")


def final_lists(cfg: dict[str, Any], unit_type: str) -> tuple[str, str]:
    """(lexical system, semantic system) whose files hold a unit type's final lists."""
    fs = cfg["final_systems"]
    if unit_type == "verse":
        return fs["lexical"], fs["semantic"]
    return fs["unit_lexical"], f"{fs['semantic']}_{fs['unit_aggregation']}"


def final_systems(cfg: dict[str, Any], unit_type: str) -> dict[str, str]:
    """mode -> system file name of a unit type (the systems that go into the DB)."""
    lex, sem = final_lists(cfg, unit_type)
    fs = cfg["final_systems"]
    structural = fs["structural"] if unit_type == "verse" else fs["unit_structural"]
    return {"lexical": lex, "semantic": sem, "fused": fs["fused"], "structural": structural}


def rrf(
    lex: pd.DataFrame,
    sem: pd.DataFrame,
    w_lex: float,
    w_sem: float,
    rrf_k: int,
    k: int,
) -> pd.DataFrame:
    """Fuse two ranked frames (integer `src`, `tgt`, `rank`, `score`).

    Returns `src, tgt, rank, score, lex_score, lex_rank, sem_score, sem_rank`, the top `k` per
    `src`, sorted by src then rank.
    """
    cols = ["src", "tgt", "rank", "score"]
    left = lex[cols].rename(columns={"rank": "lex_rank", "score": "lex_score"})
    right = sem[cols].rename(columns={"rank": "sem_rank", "score": "sem_score"})
    m = left.merge(right, on=["src", "tgt"], how="outer")
    m["score"] = (w_lex / (rrf_k + m.lex_rank)).fillna(0.0) + (w_sem / (rrf_k + m.sem_rank)).fillna(
        0.0
    )
    m = m.sort_values(["src", "score", "tgt"], ascending=[True, False, True], kind="stable")
    m["rank"] = m.groupby("src").cumcount() + 1
    m = m[m["rank"] <= k].reset_index(drop=True)
    return pd.DataFrame(
        {
            "src": m.src.astype(np.int64),
            "tgt": m.tgt.astype(np.int64),
            "rank": m["rank"].astype(np.int32),
            "score": m.score.astype(np.float32),
            "lex_score": m.lex_score.astype(np.float32),
            "lex_rank": m.lex_rank.astype("Int32"),
            "sem_score": m.sem_score.astype(np.float32),
            "sem_rank": m.sem_rank.astype("Int32"),
        }
    )


def to_topk_frame(fused: pd.DataFrame, unit_type: str, units: Units | None) -> pd.DataFrame:
    """Integer positions -> the top-k Parquet schema (+ the score breakdown)."""
    to_id = verse_ids if units is None else (lambda pos: units.ids[pos])
    return pd.DataFrame(
        {
            "unit_type": unit_type,
            "src_id": to_id(fused.src.to_numpy()),
            "rank": fused["rank"],
            "tgt_id": to_id(fused.tgt.to_numpy()),
            **{c: fused[c] for c in BREAKDOWN},
        }
    )


def load_lists(
    cfg: dict[str, Any], unit_type: str
) -> tuple[pd.DataFrame, pd.DataFrame, Units | None]:
    """The final lexical and semantic frames of a unit type with integer positions."""
    topk_dir = resolve_path(cfg, "artifacts") / "topk" / unit_type
    units = None if unit_type == "verse" else load_units(cfg, unit_type)
    positions = None if units is None else units.position()
    frames = []
    for name in final_lists(cfg, unit_type):
        path = topk_dir / f"{name}.parquet"
        if not path.exists():
            cmd = "topk" if unit_type == "verse" else "units"
            raise RuntimeError(f"{path} missing; run `bsim {cmd}` for {name!r} first")
        frames.append(read_topk(path, positions))
    return frames[0], frames[1], units


def run_fuse(cfg: dict[str, Any], log: Log = print) -> None:
    fu, k = cfg["fusion"], cfg["retrieval"]["k"]
    name = cfg["final_systems"]["fused"]
    log(f"RRF w_lex={fu['w_lex']} w_sem={fu['w_sem']} rrf_k={fu['rrf_k']}, top-{k}")
    for unit_type in cfg["units"]["types"]:
        lex, sem, units = load_lists(cfg, unit_type)
        fused = rrf(lex, sem, fu["w_lex"], fu["w_sem"], fu["rrf_k"], k)
        lex_name, sem_name = final_lists(cfg, unit_type)
        meta = {
            "kind": "fused",
            "lexical": lex_name,
            "semantic": sem_name,
            "w_lex": fu["w_lex"],
            "w_sem": fu["w_sem"],
            "rrf_k": fu["rrf_k"],
            "config_hash": config_hash(cfg, "retrieval", "fusion", "final_systems"),
            "k": int(k),
        }
        path = write_topk(cfg, unit_type, name, to_topk_frame(fused, unit_type, units), meta)
        both = int((fused.lex_rank.notna() & fused.sem_rank.notna()).sum())
        log(f"  {unit_type}: {lex_name} + {sem_name} -> {path} ({len(fused)} rows, {both} in both)")


def run_fuse_tune(cfg: dict[str, Any], log: Log = print) -> dict[str, Any]:
    """Score `fusion.w_lex_grid` on dev for every unit type with dev gold."""
    from bsim.data.report import md_table
    from bsim.eval.report import EvalContext

    fu, k, split = cfg["fusion"], cfg["retrieval"]["k"], "dev"
    key = f"ndcg@{cfg['eval']['rank_k']}"
    ctx = EvalContext.load(cfg, split)
    results: dict[str, dict[str, dict[str, float]]] = {}
    for unit_type in cfg["units"]["types"]:
        gold = ctx.gold(unit_type)
        if not gold:
            log(f"  {unit_type}: no {split} gold, skipped")
            continue
        lex, sem, _ = load_lists(cfg, unit_type)
        lex_name, sem_name = final_lists(cfg, unit_type)
        rows = {
            f"lexical ({lex_name})": ctx.score(unit_type, lex),
            f"semantic ({sem_name})": ctx.score(unit_type, sem),
        }
        for w in fu["w_lex_grid"]:
            fused = rrf(lex, sem, w, fu["w_sem"], fu["rrf_k"], k)
            rows[f"w_lex={w}"] = ctx.score(unit_type, fused)
        results[unit_type] = rows
        log(f"\n### {unit_type} ({split}, w_sem={fu['w_sem']})")
        log(
            md_table(
                ["run", "recall@10", "recall@50", key],
                [
                    [r, f"{m['recall@10']:.3f}", f"{m['recall@50']:.3f}", f"{m[key]:.3f}"]
                    for r, m in rows.items()
                ],
            )
        )
    verse = {w: results["verse"][f"w_lex={w}"][key] for w in fu["w_lex_grid"] if "verse" in results}
    best = max(verse, key=lambda w: (verse[w], -abs(w - 1))) if verse else None
    out = {
        "split": split,
        "metric": key,
        "w_sem": fu["w_sem"],
        "rrf_k": fu["rrf_k"],
        "best_w_lex_verse": best,
        "results": results,
        "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    path = resolve_path(cfg, "artifacts") / "eval" / "fusion_tuning.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    log(f"\nbest w_lex on verse {key}: {best} (config has {fu['w_lex']}); wrote {path}")
    return out
