"""Read-only SQL helpers of `api/routes/chronology.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts


def chronology_events(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every dated event in the order of the config."""
    return _dicts(conn.execute("SELECT * FROM chronology_events ORDER BY seq"))


def chronology_kings(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """The kings of Judah, then of Israel, each in order."""
    return _dicts(conn.execute("SELECT * FROM chronology_kings ORDER BY kingdom = 'israel', seq"))


def chronology_syncs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """The synchronisms in the text's order."""
    return _dicts(conn.execute("SELECT * FROM chronology_syncs ORDER BY seq"))


def chronology_numbers(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Gen 5's year numbers in order."""
    return _dicts(conn.execute("SELECT * FROM chronology_numbers ORDER BY verse_id, tok_first"))
