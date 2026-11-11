"""SQL helpers of `api/routes/mainline.py` (DESIGN.md §16.91)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, count


def mainline_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM mainline_books ORDER BY book_id"))


def mainline_pauses_page(
    conn: sqlite3.Connection,
    order: str,
    book_id: int | None,
    known: bool,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Pauses, the longest first or in canon order; `span`: touching these verses."""
    where, args = ["1 = 1"], []
    if book_id is not None:
        where.append("book_id = ?")
        args.append(book_id)
    if known:
        where.append("known = 1")
    if span is not None:
        where.append("first_vid <= ? AND last_vid >= ?")
        args += [span[1], span[0]]
    w = " AND ".join(where)
    by = "pause_id" if order == "longest" else "first_vid"
    total = count(conn, f"SELECT COUNT(*) FROM mainline_pauses WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM mainline_pauses WHERE {w} ORDER BY {by} LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def mainline_clauses_of(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    """The narrator clauses of these verses with their role (for the reader)."""
    try:
        cur = conn.execute(
            "SELECT verse_id, words, role FROM mainline_clauses WHERE verse_id BETWEEN ? AND ?",
            (first, last),
        )
    except sqlite3.OperationalError:  # a build without the table
        return []
    return _dicts(cur)
