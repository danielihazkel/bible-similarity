"""Read-only SQL helpers of `api/routes/retold.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, _marks, count


def retold_page(
    conn: sqlite3.Connection,
    group: str | None,
    book_id: int | None,
    known: bool,
    order: str,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Retellings of one group, one book or named in advance; in canon order, or the most or the
    least changed first."""
    where, args = ["1"], []
    if group is not None:
        where.append("grp = ?")
        args.append(group)
    if book_id is not None:
        where.append("book_id = ?")
        args.append(book_id)
    if known:
        where.append("known = 1")
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM retold_pairs WHERE {w}", args)
    by = {"canon": "later_first, src_first", "most": "rate DESC, later_first",
          "least": "rate, later_first"}[order]  # fmt: skip
    cur = conn.execute(
        f"SELECT * FROM retold_pairs WHERE {w} ORDER BY {by} LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def retold_marks(conn: sqlite3.Connection, pairs: list[int]) -> list[dict[str, Any]]:
    """The changed words of these pairs: pair, side, verse, display token, op."""
    if not pairs:
        return []
    cur = conn.execute(
        f"SELECT * FROM retold_marks WHERE pair IN ({_marks(len(pairs))})"
        " ORDER BY pair, side, verse_id, display_idx",
        pairs,
    )
    return _dicts(cur)
