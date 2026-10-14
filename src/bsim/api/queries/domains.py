"""Read-only SQL helpers of `api/routes/domains.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts


def domain_tree(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT code, level, parent, label_en, n_verses, weight FROM domains ORDER BY code"
    )
    return _dicts(cur)


def _domain_range(code: str) -> tuple[str, str]:
    """A domain and its subdomains: the codes it prefixes (codes are digits; `~` sorts after)."""
    return code, code + "~"


def domain_books(conn: sqlite3.Connection, code: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT v.book_id, COUNT(DISTINCT d.verse_id) AS n_verses FROM domain_verses d"
        " JOIN verses v ON v.verse_id = d.verse_id WHERE d.code >= ? AND d.code < ?"
        " GROUP BY v.book_id ORDER BY v.book_id",
        _domain_range(code),
    )
    return _dicts(cur)


def domain_page(
    conn: sqlite3.Connection, code: str, book_id: int | None, limit: int, offset: int
) -> list[tuple[int, float]]:
    """(verse id, summed weight) of the verses in a domain (in one book, if given), canon order."""
    sql = (
        "SELECT d.verse_id, SUM(d.weight) FROM domain_verses d"
        + (" JOIN verses v ON v.verse_id = d.verse_id" if book_id is not None else "")
        + " WHERE d.code >= ? AND d.code < ?"
    )
    args: list[Any] = list(_domain_range(code))
    if book_id is not None:
        sql += " AND v.book_id = ?"
        args.append(book_id)
    sql += " GROUP BY d.verse_id ORDER BY d.verse_id LIMIT ? OFFSET ?"
    return [(r[0], r[1]) for r in conn.execute(sql, [*args, limit, offset]).fetchall()]


def unit_domain_weights(conn: sqlite3.Connection, first: int, last: int) -> list[tuple[str, float]]:
    cur = conn.execute(
        "SELECT code, SUM(weight) FROM domain_verses WHERE verse_id BETWEEN ? AND ? GROUP BY code",
        (first, last),
    )
    return [(r[0], r[1]) for r in cur.fetchall()]
