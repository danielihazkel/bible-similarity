"""Read-only SQL helpers of `api/routes/phrases.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, _marks, count

PHRASE_COLS = "a, b, score, n_tokens, a_words, b_words, spread"


def phrases_of(conn: sqlite3.Connection, verse_id: int) -> list[dict[str, Any]]:
    """Phrase rows involving `verse_id`, strongest first."""
    cur = conn.execute(
        f"SELECT {PHRASE_COLS} FROM phrases WHERE a = ? OR b = ? ORDER BY score DESC, a, b",
        (verse_id, verse_id),
    )
    return _dicts(cur)


def phrases_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    cross_book: bool,
    min_tokens: int,
    max_spread: int | None,
    limit: int,
    offset: int,
    span: tuple[int, int] | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """Shared phrases, strongest first; `span` = (first, last) verse id one side lies in."""
    where, args = "n_tokens >= ?", [min_tokens]
    if span is not None:
        where += " AND (a BETWEEN ? AND ? OR b BETWEEN ? AND ?)"
        args += [*span, *span]
    if max_spread is not None:
        where += " AND spread <= ?"
        args.append(max_spread)
    if book_id is not None:
        where += " AND (a_book = ? OR b_book = ?)"
        args += [book_id, book_id]
    if cross_book:
        where += " AND a_book != b_book"
    total = count(conn, f"SELECT COUNT(*) FROM phrases WHERE {where}", args)
    cur = conn.execute(
        f"SELECT {PHRASE_COLS} FROM phrases WHERE {where}"
        " ORDER BY score DESC, a, b LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def allusions_page(
    conn: sqlite3.Connection,
    known: bool | None,
    book_id: int | None,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Allusion leads, strongest first; `span`: either side overlapping these verses."""
    where, args = ["1 = 1"], []
    if known is not None:
        where.append("known = ?")
        args.append(int(known))
    if book_id is not None:
        where.append("(a_book = ? OR b_book = ?)")
        args += [book_id, book_id]
    if span is not None:
        where.append("((a_start <= ? AND a_end >= ?) OR (b_start <= ? AND b_end >= ?))")
        args += [span[1], span[0], span[1], span[0]]
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM allusions WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM allusions WHERE {w} ORDER BY score DESC, allusion_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def lemma_marks(
    conn: sqlite3.Connection, vids: list[int], lemmas: set[str]
) -> dict[int, list[int]]:
    """verse_id -> display tokens of its words carrying one of `lemmas` (Strong's numbers, any
    sense letter)."""
    out: dict[int, list[int]] = {v: [] for v in vids}
    if not vids or not lemmas:
        return out
    cur = conn.execute(
        f"SELECT verse_id, display_idx, content_lemmas FROM words WHERE verse_id IN"
        f" ({_marks(len(vids))}) AND display_idx IS NOT NULL",
        vids,
    )
    for v, d, cl in cur:
        if any(c.rstrip("abcdefghijklmnopqrstuvwxyz") in lemmas for c in (cl or "").split()):
            out[v].append(d)
    return {v: sorted(set(ds)) for v, ds in out.items()}
