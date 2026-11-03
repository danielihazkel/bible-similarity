"""Read-only SQL helpers of `api/routes/haftarot.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts


def haftarot(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every parasha with its haftarah and the haftarah's ranks, in order."""
    return _dicts(conn.execute("SELECT * FROM haftarot ORDER BY num"))


def haftarah_lists(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Each parasha's first chapters of the Prophets (fused), in rank order."""
    return _dicts(conn.execute("SELECT * FROM haftarah_lists ORDER BY parasha, rank"))


def haftarot_of(conn: sqlite3.Connection, parashot: list[str]) -> dict[str, dict[str, Any]]:
    """The haftarah rows of some parashot, by parasha."""
    if not parashot:
        return {}
    marks = ",".join("?" * len(parashot))
    rows = _dicts(conn.execute(f"SELECT * FROM haftarot WHERE parasha IN ({marks})", parashot))
    return {r["parasha"]: r for r in rows}
