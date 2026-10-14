"""Read-only SQL helpers of `api/routes/reader.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from typing import Any

from bsim.api.queries.common import WORDPLAY_COLS, _dicts, _marks


def display_span(conn: sqlite3.Connection, first: int, last: int) -> dict[tuple[int, int], int]:
    """(verse_id, word idx) -> display token over a verse range (aligned words only)."""
    cur = conn.execute(
        "SELECT verse_id, idx, display_idx FROM words WHERE verse_id BETWEEN ? AND ?"
        " AND display_idx IS NOT NULL",
        (first, last),
    )
    return {(int(v), int(i)): int(d) for v, i, d in cur}


def phrases_touching(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    """Phrase rows with either side in a verse range."""
    cur = conn.execute(
        "SELECT a, b, a_words, b_words FROM phrases"
        " WHERE a BETWEEN ? AND ? OR b BETWEEN ? AND ?",
        (first, last, first, last),
    )
    return _dicts(cur)


def wordplay_touching(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    """Sound-alike pairs with either word in a verse range, with their display tokens."""
    cur = conn.execute(
        f"SELECT {WORDPLAY_COLS} FROM wordplay w"
        " LEFT JOIN words wa ON wa.verse_id = w.a_vid AND wa.idx = w.a_idx"
        " LEFT JOIN words wb ON wb.verse_id = w.b_vid AND wb.idx = w.b_idx"
        " WHERE w.a_vid BETWEEN ? AND ? OR w.b_vid BETWEEN ? AND ? ORDER BY w.q, w.a_vid",
        (first, last, first, last),
    )
    return _dicts(cur)


def gaps_in(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    """The gaps before the verses of a range that are flagged or a MAM paragraph break."""
    cur = conn.execute(
        "SELECT verse_id, score, kind, mam, chapter FROM segment_gaps"
        " WHERE verse_id BETWEEN ? AND ? AND (kind IS NOT NULL OR mam IS NOT NULL)",
        (first, last),
    )
    return _dicts(cur)


def kq_in(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT verse_id, pos, n_qere, ketiv, qere, cls FROM kq_pairs"
        " WHERE verse_id BETWEEN ? AND ? ORDER BY verse_id, pos",
        (first, last),
    )
    return _dicts(cur)


def entity_lemmas(conn: sqlite3.Connection, lemmas: Iterable[str]) -> set[str]:
    """The lemmas among `lemmas` that are names of people or places (§16.11)."""
    lemmas = sorted(set(lemmas))
    if not lemmas:
        return set()
    cur = conn.execute(
        f"SELECT lemma FROM entities WHERE lemma IN ({_marks(len(lemmas))})", lemmas
    )
    return {r[0] for r in cur}


def pentateuch_verses(conn: sqlite3.Connection, first: int, last: int) -> dict[int, dict[str, Any]]:
    cur = conn.execute(
        "SELECT verse_id, side, prob, reference FROM pentateuch_verses"
        " WHERE verse_id BETWEEN ? AND ?",
        (first, last),
    )
    return {r["verse_id"]: r for r in _dicts(cur)}


def refrains_in(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    """Every refrain verse in a range with its refrain: `verse_id, first, last, refrain_id, k,
    text, known, strongest`, strongest refrain first."""
    cur = conn.execute(
        "SELECT v.verse_id, v.first, v.last, r.refrain_id, r.k, r.text, r.known, r.strongest"
        " FROM refrain_verses v JOIN refrains r ON r.refrain_id = v.refrain_id"
        " WHERE v.verse_id BETWEEN ? AND ? ORDER BY r.refrain_id, v.verse_id",
        (first, last),
    )
    return _dicts(cur)
