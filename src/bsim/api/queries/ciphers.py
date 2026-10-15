"""Read-only SQL helpers of `api/routes/ciphers.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, _marks, count


def cipher_chapters(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute("SELECT * FROM cipher_chapters ORDER BY cipher, p, book_id, unit_id")
    return _dicts(cur)


def cipher_hits_page(
    conn: sqlite3.Connection,
    cipher: str | None,
    book_id: int | None,
    span: tuple[int, int] | None,
    known: bool,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Names read through a swap, in canon order: of one swap, a book, a verse range, named."""
    where, args = ["1"], []
    if cipher is not None:
        where.append("cipher = ?")
        args.append(cipher)
    if book_id is not None:
        where.append("book_id = ?")
        args.append(book_id)
    if span is not None:
        where.append("verse_id BETWEEN ? AND ?")
        args += list(span)
    if known:
        where.append("known IS NOT NULL")
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM cipher_hits WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM cipher_hits WHERE {w} ORDER BY verse_id, first_tok, cipher"
        " LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def form_counts(conn: sqlite3.Connection, forms: list[str]) -> dict[str, int]:
    """Written form -> times it occurs (`gematria_forms`; empty without `bsim gematria`)."""
    if not forms:
        return {}
    cur = conn.execute(
        f"SELECT form, n_words FROM gematria_forms WHERE form IN ({_marks(len(forms))})", forms
    )
    return dict(cur.fetchall())
