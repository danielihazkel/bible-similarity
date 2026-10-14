"""Read-only SQL helpers of `api/routes/ketiv.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, count


def kq_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM kq_books ORDER BY book_id"))


def kq_letters(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute("SELECT * FROM kq_letters WHERE n > 0 ORDER BY n DESC, pair")
    return [{**r, "lookalike": bool(r["lookalike"])} for r in _dicts(cur)]


def kq_pairs_page(
    conn: sqlite3.Connection,
    f: dict[str, Any],
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Ketiv / qere in reading order, filtered by `cls`, `grammar`, `parallel`, `euphemism`,
    `book_id` (keys of `f`, None = any) and a verse span."""
    where, args = ["1 = 1"], []
    for col in ("cls", "grammar", "parallel", "book_id"):
        if f.get(col) is not None:
            where.append(f"{col} = ?")
            args.append(f[col])
    if f.get("euphemism") is not None:
        where.append("euphemism = ?")
        args.append(int(f["euphemism"]))
    if span is not None:
        where.append("verse_id BETWEEN ? AND ?")
        args += list(span)
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM kq_pairs WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM kq_pairs WHERE {w} ORDER BY verse_id, pos LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)
