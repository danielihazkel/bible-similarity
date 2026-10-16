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


_PAIR_ORDER = {
    "vector": "p.vector DESC, p.a, p.b",
    "domains": "p.domains DESC, p.vector DESC, p.a, p.b",
    "value": "p.value, p.vector DESC, p.a, p.b",
}


def gematria_pairs_page(
    conn: sqlite3.Connection,
    value: int | None,
    sort: str,
    same_letters: bool,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Pairs of lemmas of equal value (§16.59), with both lemmas' headwords."""
    where, args = ["1"], []
    if value is not None:
        where.append("p.value = ?")
        args.append(value)
    if not same_letters:
        where.append("p.same_letters = 0")
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM gematria_pairs p WHERE {w}", args)
    cur = conn.execute(
        "SELECT p.*, la.he AS a_he, la.n_words AS a_n, lb.he AS b_he, lb.n_words AS b_n"
        " FROM gematria_pairs p JOIN gematria_lemmas la ON la.lemma = p.a"
        f" JOIN gematria_lemmas lb ON lb.lemma = p.b WHERE {w}"
        f" ORDER BY {_PAIR_ORDER[sort]} LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def gematria_lemma_heads(conn: sqlite3.Connection, lemmas: list[str]) -> dict[str, dict[str, Any]]:
    """lemma -> its headword and occurrences (`gematria_lemmas`)."""
    if not lemmas:
        return {}
    marks = ",".join("?" * len(lemmas))
    cur = conn.execute(
        f"SELECT lemma, he, n_words FROM gematria_lemmas WHERE lemma IN ({marks})", lemmas
    )
    return {r["lemma"]: r for r in _dicts(cur)}
