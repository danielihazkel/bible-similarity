"""Atbash and albam (DESIGN.md §16.54): the checks against random letter swaps, the cases named in
advance, the chapters and the names read through each swap, and any text in both swaps."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models.ciphers import (
    CipherChapter,
    CipherForm,
    CipherHit,
    CipherHitsResponse,
    CipherKnown,
    CipherName,
    CiphersResponse,
    CipherValueResponse,
)
from bsim.api.models.common import VerseLabel
from bsim.api.routes._common import Conn, State, check_page, unit_span, unprocessable
from bsim.api.routes.gematria import MAX_TEXT
from bsim.text.ciphers import CIPHERS, apply
from bsim.text.gematria import letters

router = APIRouter()


@router.get("/ciphers/value", response_model=CipherValueResponse)
def cipher_value(text: str, conn: Conn) -> dict[str, Any]:
    """Any Hebrew text in atbash and in albam, and how often each result is written in the Bible."""
    if len(text) > MAX_TEXT:
        raise unprocessable(f"text must be at most {MAX_TEXT} characters")
    if not letters(text):
        raise unprocessable("text has no Hebrew letters")
    forms = {c: apply(text, c) for c in CIPHERS}
    n = queries.form_counts(conn, [f for f in forms.values() if " " not in f])
    return {"text": text, **{c: CipherForm(form=f, n_words=n.get(f, 0)) for c, f in forms.items()}}


@router.get("/ciphers", response_model=CiphersResponse)
def ciphers(state: State, conn: Conn) -> dict[str, Any]:
    """The checks against random pairings of the letters, the cases named in advance and the
    chapters with a name read through a swap."""
    meta = state.meta.get("ciphers") or {}
    known = meta.get("known") or []
    rows = queries.cipher_chapters(conn)
    units = queries.units_by_id(conn, [r["unit_id"] for r in rows])
    labels = queries.verse_labels(conn, [k["verse_id"] for k in known])
    return {
        "meta": {k: v for k, v in meta.items() if k != "known"},
        "known": [
            CipherKnown(
                verse=VerseLabel(verse_id=k["verse_id"], label_en=labels[k["verse_id"]][0],
                                 label_he=labels[k["verse_id"]][1]),  # fmt: skip
                **{f: k[f] for f in ("cipher", "text", "name", "found")},
            )
            for k in known
            if k["verse_id"] in labels
        ],
        "chapters": [
            CipherChapter(
                label_en=units[r["unit_id"]]["label_en"],
                label_he=units[r["unit_id"]]["label_he"],
                **{f: r[f] for f in ("cipher", "unit_id", "hits", "expected", "p", "q")},
            )
            for r in rows
            if r["unit_id"] in units
        ],
    }


@router.get("/ciphers/hits", response_model=CipherHitsResponse)
def cipher_hits(
    state: State,
    conn: Conn,
    cipher: CipherName | None = None,
    book: int | None = None,
    unit: str | None = None,
    known: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """The names read through a swap, in canon order, with the words that hide them."""
    check_page(state, limit, offset)
    total, rows = queries.cipher_hits_page(conn, cipher, book, unit_span(conn, unit), known,
                                           limit, offset)  # fmt: skip
    verses = queries.verses_by_id(conn, [r["verse_id"] for r in rows])
    items = [
        CipherHit(
            unit_id=f"c:{verses[r['verse_id']]['book_id']}:{verses[r['verse_id']]['chapter']}",
            verse=verses[r["verse_id"]],
            **{f: r[f] for f in ("hit_id", "cipher", "first_tok", "last_tok", "span", "reads",
                                 "name_lemma", "known")},  # fmt: skip
        )
        for r in rows
    ]
    return {"cipher": cipher, "book": book, "unit": unit, "known": known, "total": total,
            "offset": offset, "limit": limit, "items": items}  # fmt: skip
