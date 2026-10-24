"""Read-only SQL helpers of `api/routes/frameworks.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts


def frameworks_episodes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """The judges' episodes in book order."""
    return _dicts(conn.execute("SELECT * FROM frameworks_episodes ORDER BY seq"))


def frameworks_slots(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every episode's slots and where each is found."""
    return _dicts(conn.execute("SELECT * FROM frameworks_slots"))


def frameworks_kings(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """The kings in the order of their formulas."""
    return _dicts(conn.execute("SELECT * FROM frameworks_kings ORDER BY seq"))
