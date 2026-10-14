"""Unit lists aggregated from weighted verse pairs (DESIGN.md §16.50).

A unit pair (A, B) scores the sum of the weights of the verse pairs with one verse in A and the
other in B, either way round; pairs inside one unit, or with a verse outside the unit type, are
ignored. Each unit keeps its best `retrieval.k` targets with a score above 0, ties by target. The
phrase list (`phrase_list`: verse pairs sharing a phrase, weight the alignment score, §16.1) is
the third list fused for the unit types of `fusion.unit_phrases`; `bsim unit-exp` builds others
the same way.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from bsim.config import resolve_path
from bsim.retrieve.topk import Units
from bsim.retrieve.units import member_index

PHRASES = "phrases"  # the phrase list's system name in artifacts/topk/{unit type}/


def unit_of_verse(units: Units, n_verses: int) -> np.ndarray:
    """Verse id -> unit position (-1 outside every unit)."""
    verses, unit_of = member_index(units)
    out = np.full(max(n_verses, int(verses.max()) + 1), -1, np.int64)
    out[verses] = unit_of
    return out


def unit_scores(pairs: pd.DataFrame, unit_of: np.ndarray) -> pd.DataFrame:
    """`src, tgt, score` over unit positions from verse pairs `a, b, w`, summed either way round."""
    a, b = unit_of[pairs.a.to_numpy()], unit_of[pairs.b.to_numpy()]
    w = pairs.w.to_numpy(np.float64)
    keep = (a >= 0) & (b >= 0) & (a != b)
    a, b, w = a[keep], b[keep], w[keep]
    both = pd.DataFrame(
        {"src": np.concatenate([a, b]), "tgt": np.concatenate([b, a]), "score": np.tile(w, 2)}
    )
    return both.groupby(["src", "tgt"], as_index=False)["score"].sum()


def ranked(scores: pd.DataFrame, k: int) -> pd.DataFrame:
    """The best `k` per source with a score above 0, ties by target: `src, tgt, rank, score`."""
    m = scores[scores.score > 0].sort_values(
        ["src", "score", "tgt"], ascending=[True, False, True], kind="stable"
    )
    m = m.assign(rank=(m.groupby("src").cumcount() + 1).astype(np.int32))
    return m[m["rank"] <= k].reset_index(drop=True)[["src", "tgt", "rank", "score"]]


def phrase_pairs(cfg: dict[str, Any]) -> pd.DataFrame:
    """`a, b, w`: the verse pairs sharing a phrase, weight the alignment score."""
    path = resolve_path(cfg, "artifacts") / "phrases" / "verse.parquet"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim phrases` first")
    return pd.read_parquet(path, columns=["a", "b", "score"]).rename(columns={"score": "w"})


def phrase_list(cfg: dict[str, Any], units: Units) -> pd.DataFrame:
    """The phrase unit list (`src, tgt, rank, score` over unit positions)."""
    pairs = phrase_pairs(cfg)
    n = int(pairs[["a", "b"]].to_numpy().max(initial=0)) + 1
    return ranked(unit_scores(pairs, unit_of_verse(units, n)), cfg["retrieval"]["k"])
