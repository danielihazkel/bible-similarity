"""Read-only SQL helpers of `api/routes/borrowing.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts


def borrowing_sequences(
    conn: sqlite3.Connection, seq_id: int | None = None
) -> list[dict[str, Any]]:
    where, args = ("WHERE seq_id = ?", (seq_id,)) if seq_id is not None else ("", ())
    return _dicts(conn.execute(f"SELECT * FROM borrowing_sequences {where} ORDER BY seq_id", args))


def borrowing_between(
    conn: sqlite3.Connection, a: tuple[int, int], b: tuple[int, int]
) -> list[dict[str, Any]]:
    """Sequences with one side inside verse range `a` and the other inside `b` (either way)."""
    cur = conn.execute(
        "SELECT * FROM borrowing_sequences WHERE"
        " (a_start <= ? AND a_end >= ? AND b_start <= ? AND b_end >= ?)"
        " OR (a_start <= ? AND a_end >= ? AND b_start <= ? AND b_end >= ?) ORDER BY seq_id",
        (a[1], a[0], b[1], b[0], b[1], b[0], a[1], a[0]),
    )
    return _dicts(cur)


def borrowing_touching(conn: sqlite3.Connection, span: tuple[int, int]) -> list[dict[str, Any]]:
    """Scored parallels with either side overlapping verse range `span`."""
    cur = conn.execute(
        "SELECT * FROM borrowing_sequences WHERE (a_start <= ? AND a_end >= ?)"
        " OR (b_start <= ? AND b_end >= ?) ORDER BY seq_id",
        (span[1], span[0], span[1], span[0]),
    )
    return _dicts(cur)


def borrowing_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(
        conn.execute("SELECT * FROM borrowing_books ORDER BY n_pairs DESC, a_book, b_book")
    )
