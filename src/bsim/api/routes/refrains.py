"""Refrains (DESIGN.md §16.40): the tests, the refrains named in advance, and the refrains with
their verses."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models import (
    Refrain,
    RefrainBook,
    RefrainKnown,
    RefrainsListResponse,
    RefrainsResponse,
    RefrainVerse,
)
from bsim.api.routes._common import Conn, State, check_page, unit_span

router = APIRouter()


@router.get("/refrains", response_model=RefrainsResponse)
def refrains(state: State, conn: Conn) -> dict[str, Any]:
    """The detection against shuffled verse orders, the spacing and turn tests, the refrains
    named in advance and the refrains per book."""
    meta = state.meta.get("refrains") or {}
    known = meta.get("known") or []
    labels = queries.verse_labels(conn, [k["verses"][0] for k in known if k.get("verses")])
    books = queries._dicts(
        conn.execute(
            "SELECT book_id, COUNT(*) AS refrains, SUM(strongest) AS strongest FROM refrains"
            " GROUP BY book_id ORDER BY book_id"
        )
    )
    return {
        "meta": {k: v for k, v in meta.items() if k != "known"},
        "known": [
            RefrainKnown(
                name=k["name"],
                first_vid=k["verses"][0],
                label=labels[k["verses"][0]][0],
                label_he=labels[k["verses"][0]][1],
                n_verses=len(k["verses"]),
                **{f: k.get(f) for f in ("refrain_id", "text", "k", "q")},
            )
            for k in known
            if k.get("verses") and k["verses"][0] in labels
        ],
        "books": [RefrainBook(**b) for b in books],
    }


@router.get("/refrains/list", response_model=RefrainsListResponse)
def refrain_list(
    state: State,
    conn: Conn,
    book: int | None = None,
    unit: str | None = None,
    strongest: bool = True,
    known: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Refrains, strongest burst first, with every verse holding them (the phrase marked)."""
    check_page(state, limit, offset)
    total, rows = queries.refrains_page(
        conn, book, unit_span(conn, unit), strongest, known, limit, offset
    )
    occ = queries.refrain_verses(conn, [r["refrain_id"] for r in rows])
    shown = state.cfg["serve"]["refrain_verses"]
    vids = [o["verse_id"] for os in occ.values() for o in os]
    labels = queries.verse_labels(conn, vids)
    verses = queries.verses_by_id(conn, [o["verse_id"] for os in occ.values() for o in os[:shown]])
    items = []
    for r in rows:
        os = occ.get(r["refrain_id"], [])
        items.append(
            Refrain(
                **{k: r[k] for k in ("refrain_id", "book_id", "k", "n_tokens", "p", "q", "cv")},
                **{k: r[k] for k in ("regular_p", "turn", "known", "text", "lemmas")},
                strongest=bool(r["strongest"]),
                occurrences=[
                    RefrainVerse(
                        verse_id=o["verse_id"],
                        label=labels[o["verse_id"]][0],
                        label_he=labels[o["verse_id"]][1],
                        first=o["first"],
                        last=o["last"],
                    )
                    for o in os
                ],
                verses=[verses[o["verse_id"]] for o in os[:shown]],
            )
        )
    return {"book": book, "unit": unit, "strongest": strongest, "known": known, "total": total,
            "offset": offset, "limit": limit, "items": items}  # fmt: skip
