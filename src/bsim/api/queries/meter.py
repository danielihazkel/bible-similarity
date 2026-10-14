"""Read-only SQL helpers of `api/routes/meter.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from typing import Any

from bsim.api.queries.common import _dicts, count


def meter_chapters_page(
    conn: sqlite3.Connection,
    grp: str | None,
    book_id: int | None,
    min_lines: int,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Chapters with at least `min_lines` measured lines, highest net fall first."""
    where, args = ["n_lines >= ?"], [min_lines]
    for col, val in (("grp", grp), ("book_id", book_id)):
        if val is not None:
            where.append(f"{col} = ?")
            args.append(val)
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM meter_chapters WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM meter_chapters WHERE {w} ORDER BY net DESC, n_lines DESC, book_id, chapter"
        " LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def meter_chapters(
    conn: sqlite3.Connection, keys: Iterable[tuple[int, int]]
) -> list[dict[str, Any]]:
    """The rows of the given (book_id, chapter) keys, in their order (missing keys skipped)."""
    out = []
    for b, c in keys:
        cur = conn.execute("SELECT * FROM meter_chapters WHERE book_id = ? AND chapter = ?", (b, c))
        out += _dicts(cur)
    return out


def meter_lines(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    """Every line of the verses first..last, in order."""
    cur = conn.execute(
        "SELECT * FROM meter_lines WHERE verse_id BETWEEN ? AND ? ORDER BY verse_id, idx",
        (first, last),
    )
    return _dicts(cur)
