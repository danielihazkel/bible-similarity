"""Sefaria's links in the results DB (DESIGN.md §9): gold verse pairs, the gold flags of the
parallel sequences, a unit pair's link, and the discoveries (strong pairs Sefaria does not link).

`matches.link_level / link_type`: `verse` when a verse-level link joins a verse of the source to a
verse of the target, `unit` when only a passage-level link covers them (its ranges expanded to
verse pairs).
"""

from __future__ import annotations

import json
from collections.abc import Iterable

import numpy as np
import pandas as pd

from bsim.store.schema import COLUMNS


def _join_types(types: Iterable[str]) -> str:
    return ",".join(sorted({t for s in types for t in s.split(",") if t}))


def gold_verse_pairs(links: pd.DataFrame) -> pd.DataFrame:
    """`src, tgt, direct, types`: every gold-linked verse pair (both directions, as in
    `links.parquet`). Unit-level rows are expanded to their Cartesian verse pairs
    (`direct` False)."""
    parts = []
    for row in links.itertuples(index=False):
        src = np.arange(row.src_vid, row.src_end_vid + 1)
        tgt = np.arange(row.tgt_vid, row.tgt_end_vid + 1)
        s, t = np.meshgrid(src, tgt, indexing="ij")
        parts.append((s.ravel(), t.ravel(), row.level == "verse", row.connection_type))
    if not parts:
        return pd.DataFrame({"src": [], "tgt": [], "direct": [], "types": []})
    df = pd.DataFrame(
        {
            "src": np.concatenate([p[0] for p in parts]),
            "tgt": np.concatenate([p[1] for p in parts]),
            "direct": np.concatenate([np.full(len(p[0]), p[2]) for p in parts]),
            "types": np.concatenate([np.full(len(p[0]), p[3], dtype=object) for p in parts]),
        }
    )
    return (
        df.groupby(["src", "tgt"], sort=False)
        .agg(direct=("direct", "any"), types=("types", _join_types))
        .reset_index()
    )


def sequence_gold(sequences: pd.DataFrame, gold: pd.DataFrame) -> pd.DataFrame:
    """`pairs` JSON `[[a, b, w], ...]` -> `[[a, b, w, is_gold], ...]` plus `n_gold`, the aligned
    pairs that are gold links (either direction)."""
    linked = set(zip(gold.src.tolist(), gold.tgt.tolist(), strict=True))
    pairs, counts = [], []
    for p in sequences.pairs:
        rows = [[a, b, w, int((a, b) in linked or (b, a) in linked)] for a, b, w in json.loads(p)]
        pairs.append(json.dumps(rows))
        counts.append(sum(r[3] for r in rows))
    return sequences.assign(pairs=pairs, n_gold=counts)


def unit_links(
    pairs: pd.DataFrame, units: pd.DataFrame, members: pd.DataFrame, unit_type: str
) -> pd.DataFrame:
    """`src_id, tgt_id, link_level, link_type` of the units of `unit_type` joined by a gold verse
    pair (a pair inside one unit is dropped)."""
    ids = set(units.unit_id[units.unit_type == unit_type])
    m = members[members.unit_id.isin(ids)]
    of_verse = pd.Series(m.unit_id.to_numpy(), index=m.verse_id.to_numpy())
    df = pd.DataFrame(
        {
            "src_id": pairs.src.map(of_verse),
            "tgt_id": pairs.tgt.map(of_verse),
            "direct": pairs.direct,
            "types": pairs.types,
        }
    ).dropna(subset=["src_id", "tgt_id"])
    df = df[df.src_id != df.tgt_id]
    out = (
        df.groupby(["src_id", "tgt_id"], sort=False)
        .agg(direct=("direct", "any"), link_type=("types", _join_types))
        .reset_index()
    )
    out["link_level"] = np.where(out.direct, "verse", "unit")
    return out[["src_id", "tgt_id", "link_level", "link_type"]]


def discoveries(
    matches: pd.DataFrame, units: pd.DataFrame, max_rank: int, window: int
) -> pd.DataFrame:
    """Unordered pairs of one (unit_type, mode) list without a gold link where either unit has
    the other in its top-`max_rank` (`COLUMNS["discoveries"]`). Verse pairs within
    ±`window` verses of the same book are left out, as with the `neighbors` filter."""
    df = matches[(matches["rank"] <= max_rank) & matches.link_level.isna()]
    cols = COLUMNS["discoveries"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    info = units.set_index("unit_id")
    start, book = info.start_verse_id, info.book_id
    s_start, t_start = df.src_id.map(start).to_numpy(), df.tgt_id.map(start).to_numpy()
    forward = s_start < t_start
    tie = df.sem_score if df["mode"].iloc[0] == "fused" else df.score
    pairs = pd.DataFrame(
        {
            "a_id": np.where(forward, df.src_id, df.tgt_id),
            "b_id": np.where(forward, df.tgt_id, df.src_id),
            "score": df.score.to_numpy(),
            "tie": pd.to_numeric(tie, errors="coerce").fillna(df.score).to_numpy(),
            "rank_ab": np.where(forward, df["rank"], -1),
            "rank_ba": np.where(forward, -1, df["rank"]),
        }
    )
    out = (
        pairs.groupby(["a_id", "b_id"], sort=False)
        .agg(
            score=("score", "max"),
            tie=("tie", "max"),
            rank_ab=("rank_ab", "max"),
            rank_ba=("rank_ba", "max"),
        )
        .reset_index()
    )
    for col in ("rank_ab", "rank_ba"):
        out[col] = out[col].where(out[col] > 0).astype("Int32")
    out["a_book"] = out.a_id.map(book).to_numpy()
    out["b_book"] = out.b_id.map(book).to_numpy()
    if df.unit_type.iloc[0] == "verse":
        gap = (out.b_id.map(start) - out.a_id.map(start)).abs()
        out = out[~((out.a_book == out.b_book) & (gap <= window))]
    out["unit_type"] = df.unit_type.iloc[0]
    out["mode"] = df["mode"].iloc[0]
    return out.sort_values(["score", "tie"], ascending=False, kind="stable")[cols]
