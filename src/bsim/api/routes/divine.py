"""The divine names across the canon (DESIGN.md §16.65): each chapter's names and mix, each
book's split where the mix changes, the two checks and the aligned names of the doubled psalms."""

from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.divine import (
    DivineBook,
    DivineChapter,
    DivinePairDetail,
    DivinePairsResponse,
    DivinePlace,
    DivineResponse,
)
from bsim.api.routes._common import Conn, State

router = APIRouter()


def _meta(state: State) -> dict[str, Any]:
    m = state.meta.get("divine")
    if not m:
        raise HTTPException(status_code=404, detail="the divine names were not computed")
    return m


def _num(v: Any) -> float | None:
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def _counts(row: dict[str, Any], names: list[str]) -> dict[str, int]:
    return {n: int(row[n]) for n in names if row.get(n)}


@router.get("/divine", response_model=DivineResponse)
def divine(state: State, conn: Conn) -> dict[str, Any]:
    """Every chapter's and book's names, the books' splits and the two checks (404: the stage
    did not run)."""
    m = _meta(state)
    names = m["names"]
    books = [
        DivineBook(
            book_id=b["book_id"],
            chapters=b["chapters"],
            words=b["words"],
            counts=_counts(b, names),
            share=_num(b["share"]),
            split=bool(b["split"]),
            cut1=b["cut1"],
            cut2=b["cut2"],
            shares=[_num(b[f"share{i}"]) for i in (1, 2, 3)] if b["split"] else [],
            gain=_num(b["gain"]),
            p=_num(b["p"]),
            q=_num(b["q"]),
        )
        for b in queries.divine_books(conn)
    ]
    chapters = [
        DivineChapter(
            unit_id=c["unit_id"],
            book_id=c["book_id"],
            chapter=c["chapter"],
            words=c["words"],
            counts=_counts(c, names),
            share=_num(c["share"]),
            part=c["part"],
        )
        for c in queries.divine_chapters(conn)
    ]
    return {
        **{k: m[k] for k in ("names", "measure", "totals", "alpha", "shuffles", "min_segment")},
        "elohistic": m["elohistic"],
        "doubled": m["doubled"],
        "books": books,
        "chapters": chapters,
    }


@router.get("/divine/pairs", response_model=DivinePairsResponse)
def divine_pairs(state: State, conn: Conn) -> dict[str, Any]:
    """The doubled passages of check 2, each with the places where a name stands on either side
    as the word alignment pairs them."""
    m = _meta(state)
    rows = queries.divine_pairs(conn)
    vids = {r[k] for r in rows for k in ("e_vid", "y_vid") if r[k] is not None}
    labels = queries.verse_labels(conn, vids)

    def label(v: int | None, lang: int) -> str | None:
        return labels[v][lang] if v is not None and v in labels else None

    places: dict[int, list[DivinePlace]] = {}
    for r in rows:
        places.setdefault(r["pair"], []).append(
            DivinePlace(
                kind=r["kind"],
                **{
                    f"{s}_{k}": v
                    for s in ("e", "y")
                    for k, v in (
                        ("vid", r[f"{s}_vid"]),
                        ("label", label(r[f"{s}_vid"], 0)),
                        ("label_he", label(r[f"{s}_vid"], 1)),
                        ("word", r[f"{s}_word"]),
                        ("name", r[f"{s}_name"]),
                    )
                },
            )
        )
    return {
        "pairs": [
            DivinePairDetail(**p, places=places.get(p["pair"], [])) for p in m["doubled"]["pairs"]
        ]
    }
