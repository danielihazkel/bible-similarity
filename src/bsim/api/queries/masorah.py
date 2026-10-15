"""Read-only SQL helpers of `api/routes/masorah.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts


def masorah_tables(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    """The middles (config order, written before read), totals (as written) and books."""
    return {
        "middles": _dicts(conn.execute("SELECT * FROM masorah_middles ORDER BY claim, text")),
        "totals": _dicts(conn.execute("SELECT * FROM masorah_totals ORDER BY rowid")),
        "books": _dicts(conn.execute("SELECT * FROM masorah_books ORDER BY book_id")),
    }
