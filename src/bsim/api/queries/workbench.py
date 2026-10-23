"""Read-only SQL helpers of `api/routes/workbench.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from bsim.api.queries.common import _marks


def value_labels(conn: sqlite3.Connection, feature: str, keys: Iterable[str]) -> dict[str, str]:
    """The Hebrew headword of lemmas and roots, the name of domains; nothing for the others."""
    keys = list(dict.fromkeys(keys))
    if not keys:
        return {}
    sql = {
        "lemma": "SELECT lemma, he_lemma FROM lemma_gloss WHERE lemma IN ({})",
        "root": "SELECT root, MIN(root_he) FROM lemma_roots WHERE root IN ({}) GROUP BY root",
        "domain": "SELECT code, label_en FROM domains WHERE code IN ({})",
    }.get(feature)
    if sql is None:
        return {}
    return dict(conn.execute(sql.format(_marks(len(keys))), keys).fetchall())


def book_sections(conn: sqlite3.Connection) -> dict[int, str]:
    return dict(conn.execute("SELECT book_id, section FROM books").fetchall())
