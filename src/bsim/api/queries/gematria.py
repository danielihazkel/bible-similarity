"""Read-only SQL helpers of `api/routes/gematria.py` (DESIGN.md §9).

`system` is always one of `text.gematria.SYSTEMS` (checked by the route), so it can name a column.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, count

_ORDER = {"forms": "n_words DESC, form", "lemmas": "n_words DESC, lemma", "verses": "verse_id"}


def gematria_counts(conn: sqlite3.Connection, system: str, value: int) -> dict[str, int]:
    """Word forms (and their words), lemmas and verses of one value."""
    forms, words = conn.execute(
        f"SELECT COUNT(*), COALESCE(SUM(n_words), 0) FROM gematria_forms WHERE {system} = ?",
        [value],
    ).fetchone()
    return {
        "forms": forms,
        "words": words,
        "lemmas": count(conn, f"SELECT COUNT(*) FROM gematria_lemmas WHERE {system} = ?", [value]),
        "verses": count(conn, f"SELECT COUNT(*) FROM gematria_verses WHERE {system} = ?", [value]),
    }


def gematria_page(
    conn: sqlite3.Connection,
    table: str,
    system: str,
    value: int,
    limit: int,
    offset: int,
    book_id: int | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """One page of `gematria_{table}` (forms, lemmas, verses) with this value."""
    where, args = [f"{system} = ?"], [value]
    if book_id is not None:
        where.append("book_id = ?")
        args.append(book_id)
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM gematria_{table} WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM gematria_{table} WHERE {w} ORDER BY {_ORDER[table]} LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)
