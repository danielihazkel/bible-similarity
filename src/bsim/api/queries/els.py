"""Read-only SQL helpers of `api/routes/els.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts


def els_tables(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    """The terms (per scope, as listed in config) and the controls' draws."""
    return {
        "terms": _dicts(conn.execute("SELECT * FROM els_terms ORDER BY scope, rowid")),
        "draws": _dicts(conn.execute("SELECT * FROM els_draws ORDER BY scope, control, draw")),
    }
