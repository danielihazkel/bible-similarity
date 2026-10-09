"""What is written against what is read (DESIGN.md §16.30): the summary, the letter swaps and
every ketiv / qere with the verse it stands in."""

from __future__ import annotations

import json
from typing import Any, Literal

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models import KetivResponse, KqBook, KqLetter, KqPair, KqPairsResponse
from bsim.api.routes._common import Conn, State, check_page, unit_span

router = APIRouter()

KqClassParam = Literal[
    "vowel_letter", "swap", "vowel_position", "metathesis", "division", "qere_only", "ketiv_only",
    "same_letters", "other",
]  # fmt: skip


@router.get("/ketiv", response_model=KetivResponse)
def ketiv(state: State, conn: Conn) -> dict[str, Any]:
    """Counts by class and grammar, the checks, the rate per book and the letter swaps."""
    return {
        "meta": state.meta.get("ketiv") or {},
        "books": [KqBook(**r) for r in queries.kq_books(conn)],
        "letters": [KqLetter(**r) for r in queries.kq_letters(conn)],
    }


@router.get("/ketiv/pairs", response_model=KqPairsResponse)
def ketiv_pairs(
    state: State,
    conn: Conn,
    cls: KqClassParam | None = None,
    grammar: Literal["spelling", "form", "word"] | None = None,
    parallel: Literal["qere", "ketiv", "neither"] | None = None,
    euphemism: bool | None = None,
    book: int | None = None,
    unit: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Every ketiv / qere in reading order with its verse, filtered; `unit`: those inside it."""
    check_page(state, limit, offset)
    f = {"cls": cls, "grammar": grammar, "parallel": parallel, "euphemism": euphemism}
    total, rows = queries.kq_pairs_page(
        conn, {**f, "book_id": book}, unit_span(conn, unit), limit, offset
    )
    verses = queries.verses_by_id(conn, [r["verse_id"] for r in rows])
    labels = queries.verse_labels(
        conn, [v for r in rows for v in (r["verse_id"], r["partner_vid"]) if v is not None]
    )
    display = queries.display_of_words(
        conn, [(r["verse_id"], r["pos"], r["n_qere"]) for r in rows if r["n_qere"]]
    )
    items = []
    for r in rows:
        p = r["partner_vid"]
        items.append(
            KqPair(
                **{k: r[k] for k in ("kq_id", "verse_id", "book_id", "ketiv", "qere", "cls")},
                **{k: r[k] for k in ("fuller", "letters", "grammar", "parallel", "partner_form")},
                label=labels[r["verse_id"]][0],
                label_he=labels[r["verse_id"]][1],
                features=json.loads(r["features"]),
                euphemism=bool(r["euphemism"]),
                partner_vid=p,
                partner_label=labels[p][0] if p is not None else None,
                partner_label_he=labels[p][1] if p is not None else None,
                verse=verses[r["verse_id"]],
                display=display.get((r["verse_id"], r["pos"]), []),
            )
        )
    return {
        **f,
        "book": book,
        "unit": unit,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
    }
