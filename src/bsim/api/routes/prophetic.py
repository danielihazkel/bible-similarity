"""The forms of prophetic speech (DESIGN.md §16.92, D154)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models.prophetic import PropheticResponse, ProphForm, ProphItems
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
    m = state.meta.get("prophetic")
    if not m:
        raise stage_missing("prophetic")
    return m


@router.get("/prophetic", dependencies=[stage("prophetic")], response_model=PropheticResponse)
def prophetic(state: State, conn: Conn) -> dict[str, Any]:
    """Each form's findings, by book, and the passages named in advance."""
    m = _meta(state)
    keep = ("counts", "items", "known", "known_found", "known_total", "known_holds", "known_cover",
            "known_overlap")  # fmt: skip
    return {**{k: m[k] for k in keep}, "books": queries.prophetic_books(conn)}


@router.get("/prophetic/items", dependencies=[stage("prophetic")], response_model=ProphItems)
def prophetic_items(
    state: State,
    conn: Conn,
    form: ProphForm | None = None,
    book: BookFilter = None,
    known: bool = False,
    unit: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """A page of findings in canon order, with their first verses and the words that mark them."""
    _meta(state)
    check_page(state, limit, offset)
    span = unit_span(conn, unit)
    total, rows = queries.prophetic_items_page(conn, form, book, known, span, limit, offset)
    cap = state.cfg["serve"]["prophetic"]["verses"]
    labels = queries.verse_labels(conn, [v for r in rows for v in (r["first_vid"], r["last_vid"])])

    def shown(r: dict[str, Any]) -> range:
        return range(r["first_vid"], min(r["last_vid"], r["first_vid"] + cap - 1) + 1)

    vids = sorted({v for r in rows for v in shown(r)})
    verses = queries.verses_by_id(conn, vids)
    marked: dict[tuple[int, str], list[int]] = {}
    if vids:
        display = queries.display_span(conn, vids[0], vids[-1])
        for w in queries.prophetic_words_of(conn, vids[0], vids[-1]):
            d = display.get((w["verse_id"], w["idx"]))
            if d is not None:
                marked.setdefault((w["verse_id"], w["form"]), []).append(d)
    items = []
    for r in rows:
        vs = [v for v in shown(r) if v in verses]
        f = r["form"]
        items.append({
            **{k: r[k] for k in ("item_id", "form", "unit_id", "book_id", "first_vid", "last_vid")},
            "first_label": labels[r["first_vid"]][0], "last_label": labels[r["last_vid"]][0],
            "first_label_he": labels[r["first_vid"]][1], "last_label_he": labels[r["last_vid"]][1],
            "detail": json.loads(r["detail"]), "known": bool(r["known"]),
            "verses": [verses[v] for v in vs],
            "marks": {str(v): sorted(set(marked[(v, f)])) for v in vs if (v, f) in marked},
        })  # fmt: skip
    return {"total": total, "offset": offset, "limit": limit, "items": items, "form": form,
            "book": book}  # fmt: skip
