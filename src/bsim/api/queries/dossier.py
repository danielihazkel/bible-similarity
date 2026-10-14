"""Read-only SQL helpers of `api/routes/dossier.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3


def p_like_verses(conn: sqlite3.Connection, first: int, last: int) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM pentateuch_verses WHERE side = 'P' AND verse_id BETWEEN ? AND ?",
        (first, last),
    ).fetchone()[0]
