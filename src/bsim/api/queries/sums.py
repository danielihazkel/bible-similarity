"""Read-only SQL helpers of `api/routes/sums.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, count


def sums_lists(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every list, in the config's order."""
    return _dicts(conn.execute("SELECT * FROM sums_lists ORDER BY seq"))


def sums_items(conn: sqlite3.Connection, key: str) -> list[dict[str, Any]]:
    """A list's counts, in text order."""
    return _dicts(
        conn.execute("SELECT * FROM sums_items WHERE key = ? ORDER BY verse_id, tok_first", (key,))
    )


def sums_parallels_page(
    conn: sqlite3.Connection,
    across: bool,
    differ: bool,
    one_step: bool | None,
    book_id: int | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Aligned numbers of parallel verses, in canon order: across books, differing, one step
    apart or not, touching a book."""
    where, args = ["1"], []
    if across:
        where.append("a_book != b_book")
    if differ:
        where.append("same = 0")
    if one_step is not None:
        where.append("one_step = ?")
        args.append(int(one_step))
    if book_id is not None:
        where.append("(a_book = ? OR b_book = ?)")
        args += [book_id, book_id]
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM sums_parallels WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM sums_parallels WHERE {w} ORDER BY a, b, a_tok_first LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)
