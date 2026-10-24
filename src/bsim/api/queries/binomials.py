"""Read-only SQL helpers of `api/routes/binomials.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts


def binomials(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every binomial, the commonest first."""
    return _dicts(conn.execute("SELECT * FROM binomials ORDER BY n DESC, pair"))


def binomial_occurrences(conn: sqlite3.Connection, pair: str) -> list[dict[str, Any]]:
    """A binomial's listed occurrences: its own order first, then the rarer, in text order."""
    return _dicts(
        conn.execute(
            "SELECT * FROM binomial_occurrences WHERE pair = ? ORDER BY own DESC, verse_id",
            (pair,),
        )
    )
