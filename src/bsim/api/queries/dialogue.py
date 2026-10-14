"""Read-only SQL helpers of `api/routes/dialogue.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, count


def dialogue_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Per book: quotations with a speaker and an addressee, pairs and exchanges."""
    cur = conn.execute(
        "SELECT p.book_id, SUM(p.n_quotes) AS n_quotes, COUNT(*) AS n_pairs,"
        " (SELECT COUNT(*) FROM dialogue_exchanges e WHERE e.book_id = p.book_id) AS n_exchanges"
        " FROM dialogue_pairs p GROUP BY p.book_id ORDER BY p.book_id"
    )
    return _dicts(cur)


def dialogue_exchanges_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    party: str | None,
    unequal: bool,
    limit: int,
    offset: int,
    span: tuple[int, int] | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """Exchanges in canon order: of a book, with a party, between unequal parties, touching a
    verse range."""
    where, args = ["1"], []
    if book_id is not None:
        where.append("e.book_id = ?")
        args.append(book_id)
    if party is not None:
        where.append("(e.a = ? OR e.b = ?)")
        args += [party, party]
    if unequal:
        where.append("e.a_rank != e.b_rank")
    if span is not None:
        where.append("e.verse_id <= ? AND e.last_verse_id >= ?")
        args += [span[1], span[0]]
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM dialogue_exchanges e WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM dialogue_exchanges e WHERE {w} ORDER BY e.verse_id, e.exchange"
        " LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)
