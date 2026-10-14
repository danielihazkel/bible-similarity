"""Read-only SQL helpers of `api/routes/roots.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, _marks, _span_book, count


def root_pairs_page(
    conn: sqlite3.Connection,
    kind: str | None,
    book_id: int | None,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Words of one root side by side, in canon order."""
    where: list[str] = ["1 = 1"]
    args: list[Any] = []
    if kind is not None:
        where.append("kind = ?")
        args.append(kind)
    _span_book(where, args, book_id, span)
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM root_pairs WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM root_pairs WHERE {w} ORDER BY verse_id, a_idx LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def hidden_roots_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    unit_ids: list[str] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Chapter Leitworte that only show when counted by root, strongest first."""
    where, args = ["l.hidden = 1"], []
    if book_id is not None:
        where.append("u.book_id = ?")
        args.append(book_id)
    if unit_ids is not None:
        where.append(f"l.unit_id IN ({_marks(len(unit_ids))})" if unit_ids else "0")
        args += unit_ids
    w = " AND ".join(where)
    join = "FROM root_leitworte l JOIN units u ON u.unit_id = l.unit_id"
    total = count(conn, f"SELECT COUNT(*) {join} WHERE {w}", args)
    cur = conn.execute(
        f"SELECT l.* {join} WHERE {w} ORDER BY l.g2 DESC, l.unit_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def lemmas_books(conn: sqlite3.Connection, lemmas: list[str]) -> list[dict[str, Any]]:
    """Verses containing any of `lemmas`, per book."""
    cur = conn.execute(
        "SELECT book_id, COUNT(DISTINCT verse_id) AS n_verses FROM lemma_verses"
        f" WHERE lemma IN ({_marks(len(lemmas))}) GROUP BY book_id ORDER BY book_id",
        lemmas,
    )
    return _dicts(cur)


def lemmas_page(
    conn: sqlite3.Connection, lemmas: list[str], book_id: int | None, limit: int, offset: int
) -> list[int]:
    """Verse ids containing any of `lemmas` (in one book, if given), canon order."""
    sql = f"SELECT DISTINCT verse_id FROM lemma_verses WHERE lemma IN ({_marks(len(lemmas))})"
    args: list[Any] = list(lemmas)
    if book_id is not None:
        sql += " AND book_id = ?"
        args.append(book_id)
    cur = conn.execute(sql + " ORDER BY verse_id LIMIT ? OFFSET ?", [*args, limit, offset])
    return [r[0] for r in cur.fetchall()]
