"""Read-only SQL helpers of `api/routes/senses.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, count

SHIFT_COLS = (
    "lemma, n, groups, k, silhouette, use_excess, use_q, n_senses, sense_excess, sense_q, nmi,"
    " nmi_null"
)


def shifts_page(
    conn: sqlite3.Connection, by: str, max_q: float | None, limit: int, offset: int
) -> tuple[int, list[dict[str, Any]]]:
    """Lemmas by `{by}_excess` (sense | use), strongest first, at `{by}_q` ≤ `max_q`."""
    where, args = f"{by}_excess IS NOT NULL", []
    if max_q is not None:
        where += f" AND {by}_q <= ?"
        args.append(max_q)
    total = count(conn, f"SELECT COUNT(*) FROM lemma_shifts WHERE {where}", args)
    cur = conn.execute(
        f"SELECT {SHIFT_COLS} FROM lemma_shifts WHERE {where}"
        f" ORDER BY {by}_excess DESC, lemma LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def lemma_shift(conn: sqlite3.Connection, lemma: str) -> dict[str, Any] | None:
    rows = _dicts(conn.execute(f"SELECT {SHIFT_COLS} FROM lemma_shifts WHERE lemma = ?", (lemma,)))
    return rows[0] if rows else None


def lemma_senses(conn: sqlite3.Connection, lemma: str) -> list[dict[str, Any]]:
    """A lemma's clusters (by number) then SDBH meanings (most frequent first)."""
    cur = conn.execute(
        "SELECT kind, sense, n, groups, collocates, examples, domains FROM lemma_senses"
        " WHERE lemma = ? ORDER BY kind DESC, CASE kind WHEN 'use' THEN CAST(sense AS INTEGER)"
        " ELSE -n END, sense",
        (lemma,),
    )
    return _dicts(cur)
