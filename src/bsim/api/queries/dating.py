"""Read-only SQL helpers of `api/routes/dating.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts


def dating_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM dating_books ORDER BY book_id"))


def dating_chapters(conn: sqlite3.Connection, book_id: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT * FROM dating_chapters WHERE book_id = ? ORDER BY chapter", (book_id,)
    )
    return _dicts(cur)


def dating_chapter_of(conn: sqlite3.Connection, verse_id: int) -> dict[str, Any] | None:
    """The profile of the chapter holding a verse."""
    rows = _dicts(
        conn.execute(
            "SELECT d.* FROM dating_chapters d JOIN verses v"
            " ON v.book_id = d.book_id AND v.chapter = d.chapter WHERE v.verse_id = ?",
            (verse_id,),
        )
    )
    return rows[0] if rows else None
