"""Who speaks to whom (DESIGN.md §16.44): the addressees' checks, who speaks to whom in a book,
and the exchanges between two parties."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models import (
    DialogueBook,
    DialogueBookResponse,
    DialogueExchange,
    DialogueExchangesResponse,
    DialoguePair,
    DialogueParty,
    DialogueResponse,
    VerseLabel,
)
from bsim.api.routes._common import Conn, State, check_page, unprocessable
from bsim.data.lexicon import strong_key

router = APIRouter()
DIVINE = "divine"


def _parties(
    state: State, conn: sqlite3.Connection, keys: list[str]
) -> dict[str, DialogueParty]:
    """key -> party with its Hebrew form and rank (2 God, 1 a king, 0 anyone else)."""
    kings = {strong_key(k) for k in state.cfg["dialogue"]["kings"]}
    he = queries.gloss(conn, [k for k in keys if k != DIVINE])
    return {
        k: DialogueParty(
            key=k,
            he=None if k == DIVINE else he.get(k, k),
            rank=2 if k == DIVINE else 1 if strong_key(k) in kings else 0,
        )
        for k in set(keys)
    }


@router.get("/dialogue", response_model=DialogueResponse)
def dialogue(state: State, conn: Conn) -> dict[str, Any]:
    """The addressees found and checked by hand, the three checks fixed in advance, and per book
    how much speech has an addressee."""
    return {
        "meta": state.meta.get("dialogue") or {},
        "books": [DialogueBook(**r) for r in queries.dialogue_books(conn)],
    }


@router.get("/dialogue/book/{book_id}", response_model=DialogueBookResponse)
def dialogue_book(book_id: int, state: State, conn: Conn) -> dict[str, Any]:
    """Who speaks to whom in a book: speaker -> addressee pairs, the most quotations first (empty
    for a book without addressed speech)."""
    rows = queries.dialogue_pairs(conn, book_id)
    parties = _parties(state, conn, [k for r in rows for k in (r["speaker"], r["addressee"])])
    return {
        "book_id": book_id,
        "pairs": [
            DialoguePair(
                speaker=parties[r["speaker"]],
                addressee=parties[r["addressee"]],
                **{k: r[k] for k in ("n_quotes", "n_words", "n_reliable")},
            )
            for r in rows
        ],
    }


@router.get("/dialogue/exchanges", response_model=DialogueExchangesResponse)
def dialogue_exchanges(
    state: State,
    conn: Conn,
    book: int | None = None,
    party: str | None = None,
    unequal: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Exchanges in canon order: runs of narrated turns between two parties (`party`: one of them,
    a lemma or `divine`; `unequal`: God or a king with someone of lower rank)."""
    check_page(state, limit, offset)
    if party is not None and not party:
        raise unprocessable("party must not be empty")
    total, rows = queries.dialogue_exchanges_page(conn, book, party, unequal, limit, offset)
    return {
        "book": book,
        "party": party,
        "unequal": unequal,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": exchange_items(state, conn, rows),
    }


def exchange_items(
    state: State, conn: sqlite3.Connection, rows: list[dict[str, Any]]
) -> list[DialogueExchange]:
    parties = _parties(state, conn, [k for r in rows for k in (r["a"], r["b"])])
    labels = queries.verse_labels(
        conn, [v for r in rows for v in (r["verse_id"], r["last_verse_id"])]
    )

    def label(v: int) -> VerseLabel:
        en, he = labels.get(v, (str(v), str(v)))
        return VerseLabel(verse_id=v, label_en=en, label_he=he)

    return [
        DialogueExchange(
            unit_id=f"c:{r['book_id']}:{r['chapter']}",
            first=label(r["verse_id"]),
            last_verse=label(r["last_verse_id"]),
            a=parties[r["a"]],
            b=parties[r["b"]],
            **{k: r[k] for k in ("exchange", "book_id", "turns", "a_turns", "a_words", "b_words",
                                 "last")},
        )  # fmt: skip
        for r in rows
    ]
