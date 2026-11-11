"""SQL helpers of `api/routes/laws.py` (DESIGN.md §16.93)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, count


def law_codes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM law_codes"))


def laws_by_id(conn: sqlite3.Connection, ids: list[int]) -> dict[int, dict[str, Any]]:
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    cur = conn.execute(
        f"SELECT l.*, (SELECT COUNT(*) FROM law_pairs p WHERE p.a = l.law_id OR p.b = l.law_id)"
        f" AS pairs FROM laws l WHERE l.law_id IN ({marks})",
        ids,
    )
    return {r["law_id"]: r for r in _dicts(cur)}


def laws_page(
    conn: sqlite3.Connection, code: str | None, form: str | None, limit: int, offset: int
) -> tuple[int, list[int]]:
    """Law ids in canon order."""
    where, args = ["1 = 1"], []
    if code is not None:
        where.append("code = ?")
        args.append(code)
    if form is not None:
        where.append("form = ?")
        args.append(form)
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM laws WHERE {w}", args)
    cur = conn.execute(
        f"SELECT law_id FROM laws WHERE {w} ORDER BY law_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, [r[0] for r in cur]


def law_pairs_page(
    conn: sqlite3.Connection,
    order: str,
    code: str | None,
    known: bool,
    law: int | None,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Matched pairs, the strongest first or in canon order; `span`: either side touching it."""
    where, args = ["1 = 1"], []
    if code is not None:
        where.append("(code_a = ? OR code_b = ?)")
        args += [code, code]
    if known:
        where.append("known IS NOT NULL")
    if law is not None:
        where.append("(a = ? OR b = ?)")
        args += [law, law]
    if span is not None:
        where.append("((a_first <= ? AND a_last >= ?) OR (b_first <= ? AND b_last >= ?))")
        args += [span[1], span[0], span[1], span[0]]
    w = " AND ".join(where)
    by = "score DESC, pair_id" if order == "score" else "a_first, b_first, pair_id"
    total = count(conn, f"SELECT COUNT(*) FROM law_pairs WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM law_pairs WHERE {w} ORDER BY {by} LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def law_pair(conn: sqlite3.Connection, pair_id: int) -> dict[str, Any] | None:
    rows = _dicts(conn.execute("SELECT * FROM law_pairs WHERE pair_id = ?", (pair_id,)))
    return rows[0] if rows else None


def law_marks(conn: sqlite3.Connection, pair_id: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT side, verse_id, display_idx, op FROM law_marks WHERE pair_id = ?", (pair_id,)
    )
    return _dicts(cur)


def law_pairs_touching(conn: sqlite3.Connection, span: tuple[int, int]) -> int:
    """Matched pairs with a law touching these verses (the dossier)."""
    try:
        return count(
            conn,
            "SELECT COUNT(*) FROM law_pairs p JOIN laws a ON a.law_id = p.a"
            " JOIN laws b ON b.law_id = p.b WHERE (a.first_vid <= ? AND a.last_vid >= ?)"
            " OR (b.first_vid <= ? AND b.last_vid >= ?)",
            [span[1], span[0], span[1], span[0]],
        )
    except sqlite3.OperationalError:  # a build without the tables
        return 0
