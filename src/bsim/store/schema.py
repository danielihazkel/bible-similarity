"""The column names of every results-DB table, read from `schema.sql` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")


def _columns() -> dict[str, list[str]]:
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(SCHEMA.read_text("utf-8"))
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        return {t: [r[1] for r in conn.execute(f"PRAGMA table_info({t})")] for t in names}
    finally:
        conn.close()


COLUMNS = _columns()  # table -> its columns in schema order
