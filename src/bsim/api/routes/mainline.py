"""The narrative main line and where a story pauses (DESIGN.md §16.91, D153)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models.mainline import MainlineOrder, MainlinePauses, MainlineResponse
from bsim.api.routes._common import (
    BookFilter,
    Conn,
    State,
    check_page,
    stage,
    stage_missing,
    unit_span,
)

router = APIRouter()


def _meta(state: State) -> dict[str, Any]:
    m = state.meta.get("mainline")
    if not m:
        raise stage_missing("mainline")
    return m


@router.get("/mainline", dependencies=[stage("mainline")], response_model=MainlineResponse)
def mainline(state: State, conn: Conn) -> dict[str, Any]:
    """The narrator's clauses on and off the main line, by book; the claim and the known pauses."""
    m = _meta(state)
    keep = ("clauses", "main", "background", "pauses", "min_run", "opening", "claim", "shuffles",
            "alpha", "known", "known_found")  # fmt: skip
    return {
        **{k: m[k] for k in keep},
        "max_run": state.cfg["mainline"]["max_run"],
        "books": queries.mainline_books(conn),
    }


@router.get("/mainline/pauses", dependencies=[stage("mainline")], response_model=MainlinePauses)
def mainline_pauses(
    state: State,
    conn: Conn,
    order: MainlineOrder = "longest",
    book: BookFilter = None,
    known: bool = False,
    unit: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """A page of pauses: background clauses between two wayyiqtols, with their verses."""
    _meta(state)
    check_page(state, limit, offset)
    span = unit_span(conn, unit)
    total, rows = queries.mainline_pauses_page(conn, order, book, known, span, limit, offset)
    cap = state.cfg["serve"]["mainline"]["verses"]
    ends = [v for r in rows for v in (r["first_vid"], r["last_vid"])]
    labels = queries.verse_labels(conn, ends)

    def shown(r: dict[str, Any]) -> range:
        return range(r["first_vid"], min(r["last_vid"], r["first_vid"] + cap - 1) + 1)

    verses = queries.verses_by_id(conn, [v for r in rows for v in shown(r)])
    items = []
    for r in rows:
        vids = shown(r)
        items.append({
            **{k: r[k] for k in ("pause_id", "unit_id", "book_id", "first_vid", "last_vid",
                                 "n_clauses")},
            "first_label": labels[r["first_vid"]][0], "last_label": labels[r["last_vid"]][0],
            "first_label_he": labels[r["first_vid"]][1], "last_label_he": labels[r["last_vid"]][1],
            "types": json.loads(r["types"]), "known": bool(r["known"]),
            "verses": [verses[v] for v in vids if v in verses],
        })  # fmt: skip
    return {"total": total, "offset": offset, "limit": limit, "items": items, "order": order,
            "book": book}  # fmt: skip
