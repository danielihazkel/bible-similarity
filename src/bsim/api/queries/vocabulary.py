"""Read-only SQL helpers of `api/routes/vocabulary.py` and the concordance (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts


def vocabulary_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every book's vocabulary, in canon order."""
    return _dicts(conn.execute("SELECT * FROM vocabulary_books ORDER BY book_id"))


def vocabulary_lemma(conn: sqlite3.Connection, lemma: str) -> dict[str, Any] | None:
    """A lemma's first occurrence and spread."""
    rows = _dicts(conn.execute("SELECT * FROM vocabulary_lemmas WHERE lemma = ?", (lemma,)))
    return rows[0] if rows else None
