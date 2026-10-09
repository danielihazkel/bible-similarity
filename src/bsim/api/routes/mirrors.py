"""Chiasm at the small scale (DESIGN.md §16.33): the word- and clause-order tests, the full
mirrors and the clause pairs, each with its verse and the words marked."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models import (
    MirrorClause,
    MirrorClausesResponse,
    MirrorsResponse,
    MirrorVerse,
    MirrorVersesResponse,
)
from bsim.api.routes._common import Conn, State, check_page, unit_span

router = APIRouter()


@router.get("/mirrors", response_model=MirrorsResponse)
def mirrors(state: State) -> dict[str, Any]:
    """The tests: repeated words in mirrored or parallel order, clause constituents by genre."""
    return {"meta": state.meta.get("mirrors") or {}}


@router.get("/mirrors/verses", response_model=MirrorVersesResponse)
def mirror_verses(
    state: State,
    conn: Conn,
    book: int | None = None,
    unit: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Verses whose twice-used lemmas all nest (A B C … C B A), lowest p first."""
    check_page(state, limit, offset)
    total, rows = queries.mirror_verses_page(conn, book, unit_span(conn, unit), limit, offset)
    verses = queries.verses_by_id(conn, [r["verse_id"] for r in rows])
    labels = queries.verse_labels(conn, [r["verse_id"] for r in rows])
    items = []
    for r in rows:
        lemmas, idxs = json.loads(r["lemmas"]), json.loads(r["idxs"])
        disp = queries.display_map(conn, r["verse_id"])
        # depth of nesting: the outermost pair is 0
        order = list(dict.fromkeys(lemmas))
        marks = {
            disp[i]: order.index(lem) for lem, i in zip(lemmas, idxs, strict=True) if i in disp
        }
        items.append(
            MirrorVerse(
                **{k: r[k] for k in ("verse_id", "n_pairs", "n_words", "p", "q")},
                label=labels[r["verse_id"]][0],
                label_he=labels[r["verse_id"]][1],
                poetic=bool(r["poetic"]),
                verse=verses[r["verse_id"]],
                marks=marks,
            )
        )
    return {"book": book, "unit": unit, "total": total, "offset": offset, "limit": limit,
            "items": items}  # fmt: skip


@router.get("/mirrors/clauses", response_model=MirrorClausesResponse)
def mirror_clauses(
    state: State,
    conn: Conn,
    pair: str | None = None,
    mirrored: bool | None = None,
    poetic: bool | None = None,
    book: int | None = None,
    unit: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Consecutive clauses with the same two constituents, in reading order."""
    check_page(state, limit, offset)
    total, rows = queries.mirror_clauses_page(
        conn, pair, mirrored, poetic, book, unit_span(conn, unit), limit, offset
    )
    verses = queries.verses_by_id(conn, [r["verse_id"] for r in rows])
    labels = queries.verse_labels(conn, [r["verse_id"] for r in rows])
    items = []
    for r in rows:
        disp = queries.display_map(conn, r["verse_id"])
        marks: dict[int, int] = {}
        for side in ("a_words", "b_words"):
            for fn, idxs in json.loads(r[side]).items():
                for i in idxs:
                    if i in disp:
                        marks[disp[i]] = 0 if fn == r["first"] else 1
        items.append(
            MirrorClause(
                **{k: r[k] for k in ("pair_id", "verse_id", "pair", "first", "second")},
                label=labels[r["verse_id"]][0],
                label_he=labels[r["verse_id"]][1],
                poetic=bool(r["poetic"]),
                mirrored=bool(r["mirrored"]),
                verse=verses[r["verse_id"]],
                marks=marks,
            )
        )
    return {
        "pair": pair,
        "mirrored": mirrored,
        "poetic": poetic,
        "book": book,
        "unit": unit,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
    }
