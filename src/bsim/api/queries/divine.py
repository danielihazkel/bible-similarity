"""Read-only SQL helpers of `api/routes/divine.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts


def divine_chapters(conn: sqlite3.Connection, book_id: int | None = None) -> list[dict[str, Any]]:
    """Every chapter's counts of the names, in canon order (one book's with `book_id`)."""
    where, args = ("WHERE book_id = ?", (book_id,)) if book_id is not None else ("", ())
    cur = conn.execute(f"SELECT * FROM divine_chapters {where} ORDER BY book_id, chapter", args)
    return _dicts(cur)


def divine_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM divine_books ORDER BY book_id"))


def divine_pairs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """The aligned places of the doubled psalms, in pair and alignment order."""
    return _dicts(conn.execute("SELECT * FROM divine_pairs ORDER BY pair, rowid"))


def divine_tokens(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    """The names in a verse span with their display tokens."""
    cur = conn.execute(
        "SELECT d.verse_id, w.display_idx, d.name FROM divine_words d"
        " JOIN words w ON w.verse_id = d.verse_id AND w.idx = d.idx"
        " WHERE d.verse_id BETWEEN ? AND ? AND w.display_idx IS NOT NULL"
        " ORDER BY d.verse_id, w.display_idx",
        (first, last),
    )
    return _dicts(cur)


def divine_counts(conn: sqlite3.Connection, first: int, last: int) -> dict[str, int]:
    """Each name's words in a verse span, the commonest first."""
    cur = conn.execute(
        "SELECT name, COUNT(*) FROM divine_words WHERE verse_id BETWEEN ? AND ?"
        " GROUP BY name ORDER BY COUNT(*) DESC, name",
        (first, last),
    )
    return dict(cur.fetchall())
