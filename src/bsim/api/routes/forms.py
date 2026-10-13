"""Graded numerical sayings and lists (DESIGN.md §16.45): the checks, the sayings and lists named in
advance, and the sayings and lists found."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models import (
    FormsBook,
    FormsKnownList,
    FormsKnownSaying,
    FormsList,
    FormsListsResponse,
    FormsPair,
    FormsResponse,
    FormsSaying,
    FormsSayingsResponse,
    VerseLabel,
)
from bsim.api.routes._common import Conn, State, check_page, unit_span

router = APIRouter()


def _labeller(conn: sqlite3.Connection, ids: list[int]) -> Any:
    labels = queries.verse_labels(conn, ids)

    def label(v: int) -> VerseLabel:
        en, he = labels.get(v, (str(v), str(v)))
        return VerseLabel(verse_id=v, label_en=en, label_he=he)

    return label


@router.get("/forms", response_model=FormsResponse)
def forms(state: State, conn: Conn) -> dict[str, Any]:
    """The graded pairs against chance and against parallel lines, the sayings named in advance,
    the lists against shuffled verse orders and the lists named in advance, per book."""
    meta = state.meta.get("forms") or {}
    known = meta.get("known") or []
    lists = meta.get("lists") or {}
    known_lists = lists.get("known") or []
    label = _labeller(
        conn,
        [k["verses"][0] for k in known if k.get("verses")]
        + [v for k in known_lists for v in (k["first_vid"], k["last_vid"])],
    )
    return {
        "meta": {**{k: v for k, v in meta.items() if k not in ("known", "lists")},
                 "lists": {k: v for k, v in lists.items() if k != "known"}},  # fmt: skip
        "known": [
            FormsKnownSaying(
                name=k["name"],
                first=label(k["verses"][0]),
                n_verses=len(k["verses"]),
                hits=len(k.get("hits") or []),
                found=bool(k.get("found")),
            )
            for k in known
            if k.get("verses")
        ],
        "known_lists": [
            FormsKnownList(
                name=k["name"],
                first=label(k["first_vid"]),
                last_verse=label(k["last_vid"]),
                n_verses=k["last_vid"] - k["first_vid"] + 1,
                covered=k["covered"],
                found=bool(k["found"]),
            )
            for k in known_lists
        ],
        "books": [FormsBook(**b) for b in queries.forms_books(conn)],
    }


@router.get("/forms/sayings", response_model=FormsSayingsResponse)
def forms_sayings(
    state: State,
    conn: Conn,
    book: int | None = None,
    unit: str | None = None,
    known: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Verses holding a graded pair, in canon order, with the two numbers marked."""
    check_page(state, limit, offset)
    total, rows = queries.forms_sayings_page(conn, book, unit_span(conn, unit), known, limit,
                                             offset)  # fmt: skip
    ids = [r["verse_id"] for r in rows]
    pairs = queries.forms_pairs(conn, ids)
    verses = queries.verses_by_id(conn, ids)
    items = [
        FormsSaying(
            unit_id=f"c:{verses[r['verse_id']]['book_id']}:{verses[r['verse_id']]['chapter']}",
            pairs=[FormsPair(**{k: p[k] for k in ("a_tok", "b_tok", "a_value", "b_value")})
                   for p in pairs.get(r["verse_id"], [])],  # fmt: skip
            verse=verses[r["verse_id"]],
            **{k: r[k] for k in ("n_pairs", "steps", "prob", "known")},
        )
        for r in rows
    ]
    return {"book": book, "unit": unit, "known": known, "total": total, "offset": offset,
            "limit": limit, "items": items}  # fmt: skip


@router.get("/forms/lists", response_model=FormsListsResponse)
def forms_lists(
    state: State,
    conn: Conn,
    book: int | None = None,
    unit: str | None = None,
    kind: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Runs of verses shaped alike, in canon order, with their first few verses."""
    check_page(state, limit, offset)
    total, rows = queries.forms_lists_page(conn, book, unit_span(conn, unit), kind or None, limit,
                                           offset)  # fmt: skip
    label = _labeller(conn, [v for r in rows for v in (r["first_vid"], r["last_vid"])])
    shown = state.cfg["serve"]["list_verses"]
    head = {r["list_id"]: range(r["first_vid"], min(r["last_vid"], r["first_vid"] + shown - 1) + 1)
            for r in rows}  # fmt: skip
    verses = queries.verses_by_id(conn, [v for vs in head.values() for v in vs])
    items = []
    for r in rows:
        first = verses[r["first_vid"]]
        items.append(
            FormsList(
                unit_id=f"c:{first['book_id']}:{first['chapter']}",
                first=label(r["first_vid"]),
                last_verse=label(r["last_vid"]),
                n_verses=r["last_vid"] - r["first_vid"] + 1,
                verses=[verses[v] for v in head[r["list_id"]]],
                **{k: r[k] for k in ("list_id", "book_id", "n_like", "likeness", "kind", "known")},
            )
        )
    return {"book": book, "unit": unit, "kind": kind or None, "total": total, "offset": offset,
            "limit": limit, "items": items}  # fmt: skip
