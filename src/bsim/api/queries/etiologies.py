"""Read-only SQL helpers of `api/routes/etiologies.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts


def etiologies(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every naming, in canon order."""
    return _dicts(conn.execute("SELECT * FROM etiologies ORDER BY naming"))


def etiology_tokens(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    """The namings in a verse span: the name's and its echo's display tokens."""
    cur = conn.execute(
        "SELECT naming, verse_id, name, name_first, name_last, echo_word, echo_disp, score, q"
        " FROM etiologies WHERE verse_id BETWEEN ? AND ? ORDER BY naming",
        (first, last),
    )
    return _dicts(cur)
