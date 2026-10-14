"""Read-only SQL helpers of `api/routes/citations.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, count


def citation_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM citation_books ORDER BY n DESC, book_id"))


def citations_page(
    conn: sqlite3.Connection,
    family: str | None,
    resolved: bool | None,
    book_id: int | None,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Citations in reading order; `span`: citing from it, or resolved and pointing into it."""
    where, args = ["1 = 1"], []
    if family is not None:
        where.append("family = ?")
        args.append(family)
    if resolved is not None:
        where.append("resolved = ?")
        args.append(int(resolved))
    if book_id is not None:
        where.append("book_id = ?")
        args.append(book_id)
    if span is not None:
        where.append(
            "(verse_id BETWEEN ? AND ? OR (resolved = 1 AND target_vid BETWEEN ? AND ?))"
        )
        args += [*span, *span]
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM citations WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM citations WHERE {w} ORDER BY verse_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)
