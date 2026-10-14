"""Read-only SQL helpers of `api/routes/forms.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from typing import Any

from bsim.api.queries.common import _dicts, _marks, count


def forms_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT * FROM forms_books WHERE numbers > 0 OR lists > 0 ORDER BY book_id"
    )
    return _dicts(cur)


def forms_sayings_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    span: tuple[int, int] | None,
    known: bool,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Graded numerical sayings in canon order: of a book, in a verse range, named in advance."""
    where, args = ["1"], []
    if book_id is not None:
        where.append("book_id = ?")
        args.append(book_id)
    if span is not None:
        where.append("verse_id BETWEEN ? AND ?")
        args += list(span)
    if known:
        where.append("known IS NOT NULL")
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM forms_sayings WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM forms_sayings WHERE {w} ORDER BY verse_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def forms_pairs(conn: sqlite3.Connection, ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    """verse_id -> its graded pairs, in word order."""
    if not ids:
        return {}
    cur = conn.execute(
        f"SELECT * FROM forms_pairs WHERE verse_id IN ({_marks(len(ids))})"
        " ORDER BY verse_id, a_tok, b_tok",
        ids,
    )
    out: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in _dicts(cur):
        out[r["verse_id"]].append(r)
    return out


def forms_lists_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    span: tuple[int, int] | None,
    kind: str | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Lists in canon order: of a book, overlapping a verse range, of a kind."""
    where, args = ["1"], []
    if book_id is not None:
        where.append("book_id = ?")
        args.append(book_id)
    if span is not None:
        where.append("first_vid <= ? AND last_vid >= ?")
        args += [span[1], span[0]]
    if kind is not None:
        where.append("kind = ?")
        args.append(kind)
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM forms_lists WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM forms_lists WHERE {w} ORDER BY first_vid LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)
