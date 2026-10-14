"""Read-only SQL helpers of `api/routes/mirrors.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, _span_book, count


def mirror_verses_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Full mirrors, lowest p first."""
    where: list[str] = ["1 = 1"]
    args: list[Any] = []
    _span_book(where, args, book_id, span)
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM mirror_verses WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM mirror_verses WHERE {w} ORDER BY p, n_pairs DESC, verse_id"
        " LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def mirror_clauses_page(
    conn: sqlite3.Connection,
    pair: str | None,
    mirrored: bool | None,
    poetic: bool | None,
    book_id: int | None,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Clause pairs in reading order."""
    where: list[str] = ["1 = 1"]
    args: list[Any] = []
    for col, val in (("pair", pair), ("mirrored", mirrored), ("poetic", poetic)):
        if val is not None:
            where.append(f"{col} = ?")
            args.append(int(val) if isinstance(val, bool) else val)
    _span_book(where, args, book_id, span)
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM mirror_clauses WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM mirror_clauses WHERE {w} ORDER BY verse_id, pair_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)
