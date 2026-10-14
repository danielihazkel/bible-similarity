"""Read-only SQL helpers of `api/routes/segments.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, count


def segment_books(conn: sqlite3.Connection, book_id: int | None = None) -> list[dict[str, Any]]:
    sql, args = "SELECT * FROM segment_books", []
    if book_id is not None:
        sql, args = sql + " WHERE book_id = ?", [book_id]
    return _dicts(conn.execute(sql + " ORDER BY book_id, ref", args))


def segment_gaps_page(
    conn: sqlite3.Connection,
    kind: str | None,
    book_id: int | None,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Flagged gaps (`kind`, or any kind): turns sharpest first, cuts and quiet breaks most
    cohesive first; `span`: gaps at or inside these verses (the unit's opening gap included),
    in reading order."""
    where, args = "kind IS NOT NULL", []
    if kind is not None:
        where, args = "kind = ?", [kind]
    if book_id is not None:
        where += " AND book_id = ?"
        args.append(book_id)
    if span is not None:
        where += " AND verse_id BETWEEN ? AND ?"
        args += list(span)
    order = (
        "verse_id"
        if span is not None or kind is None
        else "score DESC, verse_id"
        if kind == "turn"
        else "score, verse_id"
    )
    total = count(conn, f"SELECT COUNT(*) FROM segment_gaps WHERE {where}", args)
    cur = conn.execute(
        f"SELECT * FROM segment_gaps WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def segment_curve(conn: sqlite3.Connection, book_id: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT g.verse_id, v.chapter, v.verse, g.score, g.mam, g.oshb, g.chapter AS chapter_start,"
        " g.seam, g.kind FROM segment_gaps g JOIN verses v ON v.verse_id = g.verse_id"
        " WHERE g.book_id = ? ORDER BY g.verse_id",
        (book_id,),
    )
    return _dicts(cur)
