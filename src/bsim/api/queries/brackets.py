"""Read-only SQL helpers of `api/routes/brackets.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, count


def bracket_books(conn: sqlite3.Connection, alpha: float) -> list[dict[str, Any]]:
    """Per book: its brackets and those beyond chance one by one."""
    cur = conn.execute(
        "SELECT book_id, COUNT(*) AS brackets, SUM(p <= ?) AS strong FROM brackets"
        " GROUP BY book_id ORDER BY book_id",
        (alpha,),
    )
    return _dicts(cur)


def brackets_page(
    conn: sqlite3.Connection,
    show: str,
    order: str,
    book_id: int | None,
    alpha: float,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Brackets: all, beyond chance one by one (p), or named in advance; of one book; in canon
    order or the strongest first."""
    where, args = ["1"], []
    if show == "strong":
        where.append("p <= ?")
        args.append(alpha)
    elif show == "known":
        where.append("known = 1")
    if book_id is not None:
        where.append("book_id = ?")
        args.append(book_id)
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM brackets WHERE {w}", args)
    by = "a, b" if order == "canon" else "p, insertion DESC, a, b"
    cur = conn.execute(
        f"SELECT * FROM brackets WHERE {w} ORDER BY {by} LIMIT ? OFFSET ?", [*args, limit, offset]
    )
    return total, _dicts(cur)
