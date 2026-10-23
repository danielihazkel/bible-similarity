"""Resumptive repetition (DESIGN.md §16.67): clauses repeated after a block, how much the block
interrupts its surroundings against random brackets of the same span, and the two checks."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.brackets import (
    Bracket,
    BracketBook,
    BracketOrder,
    BracketShow,
    BracketsPage,
    BracketsResponse,
)
from bsim.api.routes._common import Conn, State, check_page

router = APIRouter()


def _meta(state: State) -> dict[str, Any]:
    m = state.meta.get("brackets")
    if not m:
        raise HTTPException(status_code=404, detail="the resumptive repetitions were not computed")
    return m


@router.get("/brackets", response_model=BracketsResponse)
def brackets(state: State, conn: Conn) -> dict[str, Any]:
    """The checks and the brackets of each book (404: the stage did not run)."""
    m = _meta(state)
    books = [BracketBook(**{k: int(r[k] or 0) for k in ("book_id", "brackets", "strong")})
             for r in queries.bracket_books(conn, m["alpha"])]  # fmt: skip
    keep = ("candidates", "repetitions", "brackets", "mean", "mean_null", "p", "draws", "window",
            "alpha", "holds", "leads", "known", "known_found", "known_beat",
            "known_holds")  # fmt: skip
    return {**{k: m[k] for k in keep}, "strong": sum(b.strong for b in books), "books": books}


@router.get("/brackets/items", response_model=BracketsPage)
def bracket_items(
    state: State,
    conn: Conn,
    show: BracketShow = "all",
    order: BracketOrder = "canon",
    book: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """A page of brackets, each with its two verses and the repeated clause marked."""
    m = _meta(state)
    check_page(state, limit, offset)
    total, rows = queries.brackets_page(conn, show, order, book, m["alpha"], limit, offset)
    verses = queries.verses_by_id(conn, [v for r in rows for v in (r["a"], r["b"])])
    items = [
        Bracket(
            a=verses[r["a"]],
            b=verses[r["b"]],
            a_disp=json.loads(r["a_disp"]),
            b_disp=json.loads(r["b_disp"]),
            unit_id=f"c:{verses[r['a']]['book_id']}:{verses[r['a']]['chapter']}",
            between=r["n_between"],
            known=bool(r["known"]),
            **{k: r[k] for k in ("bracket", "book_id", "score", "n_tokens", "lex",
                                 "sem", "insertion", "p", "q")},  # fmt: skip
        )
        for r in rows
    ]
    return {"show": show, "order": order, "book": book, "total": total, "offset": offset,
            "limit": limit, "items": items}  # fmt: skip
