"""SQL helpers of `api/routes/prophetic.py` (DESIGN.md §16.92)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, count


def prophetic_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    out: dict[int, dict[str, int]] = {}
    for b, f, n in conn.execute("SELECT book_id, form, n FROM prophetic_books ORDER BY book_id"):
        out.setdefault(b, {})[f] = n
    return [{"book_id": b, "counts": c} for b, c in out.items()]


def prophetic_items_page(
    conn: sqlite3.Connection,
    form: str | None,
    book_id: int | None,
    known: bool,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Findings in canon order; `span`: touching these verses."""
    where, args = ["1 = 1"], []
    if form is not None:
        where.append("form = ?")
        args.append(form)
    if book_id is not None:
        where.append("book_id = ?")
        args.append(book_id)
    if known:
        where.append("known = 1")
    if span is not None:
        where.append("first_vid <= ? AND last_vid >= ?")
        args += [span[1], span[0]]
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM prophetic_items WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM prophetic_items WHERE {w} ORDER BY first_vid, item_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def prophetic_words_of(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    """The words that mark a form in these verses (for the reader and the list)."""
    try:
        cur = conn.execute(
            "SELECT verse_id, idx, form FROM prophetic_words WHERE verse_id BETWEEN ? AND ?",
            (first, last),
        )
    except sqlite3.OperationalError:  # a build without the table
        return []
    return _dicts(cur)
