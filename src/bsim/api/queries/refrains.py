"""Read-only SQL helpers of `api/routes/refrains.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from typing import Any

from bsim.api.queries.common import _dicts, _marks, count


def refrains_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    span: tuple[int, int] | None,
    strongest: bool,
    known: bool,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Refrains, strongest burst first; `span`: with a verse in it; `strongest`: only the
    strongest of each group sharing a verse; `known`: only those named in advance."""
    where, args = ["1 = 1"], []
    if book_id is not None:
        where.append("r.book_id = ?")
        args.append(book_id)
    if strongest:
        where.append("r.strongest = 1")
    if known:
        where.append("r.known IS NOT NULL")
    if span is not None:
        where.append(
            "EXISTS (SELECT 1 FROM refrain_verses v WHERE v.refrain_id = r.refrain_id"
            " AND v.verse_id BETWEEN ? AND ?)"
        )
        args += list(span)
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM refrains r WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM refrains r WHERE {w} ORDER BY r.refrain_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def refrain_verses(conn: sqlite3.Connection, ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    """refrain_id -> its verses in order, with the display span of the phrase."""
    if not ids:
        return {}
    cur = conn.execute(
        f"SELECT * FROM refrain_verses WHERE refrain_id IN ({_marks(len(ids))})"
        " ORDER BY refrain_id, verse_id",
        ids,
    )
    out: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in _dicts(cur):
        out[r["refrain_id"]].append(r)
    return out
