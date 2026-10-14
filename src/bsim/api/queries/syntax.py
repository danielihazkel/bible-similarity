"""Read-only SQL helpers of `api/routes/syntax.py` (DESIGN.md §9)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, dialogue_pairs


def syntax_phrases_of(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT * FROM syntax_phrases WHERE verse_id BETWEEN ? AND ? ORDER BY phrase",
        (first, last),
    )
    return _dicts(cur)


def surfaces(conn: sqlite3.Connection, first: int, last: int) -> dict[tuple[int, int], str]:
    cur = conn.execute(
        "SELECT verse_id, idx, surface FROM words WHERE verse_id BETWEEN ? AND ?", (first, last)
    )
    return {(v, i): s for v, i, s in cur}


def syntax_neighbors(conn: sqlite3.Connection, verse_id: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT tgt, score FROM syntax_neighbors WHERE verse_id = ? ORDER BY rank", (verse_id,)
    )
    return _dicts(cur)


def speech_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM speech_books ORDER BY book_id"))


def speech_chapters(conn: sqlite3.Connection, book_id: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT * FROM speech_chapters WHERE book_id = ? ORDER BY chapter", (book_id,)
    )
    return _dicts(cur)


def speakers(conn: sqlite3.Connection, book_id: int | None = None) -> list[dict[str, Any]]:
    """Speakers with their words, the most first (all books, or one)."""
    where, args = ("WHERE s.book_id = ?", (book_id,)) if book_id is not None else ("", ())
    cur = conn.execute(
        "SELECT s.book_id, s.lemma, s.n_words, s.n_explicit, COALESCE(g.he_lemma, s.lemma) AS he"
        f" FROM speakers s LEFT JOIN lemma_gloss g ON g.lemma = s.lemma {where}"
        " ORDER BY s.book_id, s.n_words DESC, s.lemma",
        args,
    )
    return _dicts(cur)


def voice_speakers(conn: sqlite3.Connection, key: str | None = None) -> list[dict[str, Any]]:
    """Profiled speakers, the most distinct first (all, or one), with their Hebrew form."""
    where, args = ("WHERE v.key = ?", (key,)) if key is not None else ("", ())
    cur = conn.execute(
        "SELECT v.*, g.he_lemma AS he FROM voice_speakers v"
        f" LEFT JOIN lemma_gloss g ON g.lemma = v.key {where} ORDER BY v.effect DESC, v.key",
        args,
    )
    return [{**r, "books": json.loads(r["books"])} for r in _dicts(cur)]


def voice_pairs(conn: sqlite3.Connection, key: str | None = None) -> list[dict[str, Any]]:
    """Delta between voices (all pairs, or those of one voice with it as `a`, nearest first)."""
    if key is None:
        return _dicts(conn.execute("SELECT a, b, delta FROM voice_pairs ORDER BY a, b"))
    cur = conn.execute(
        "SELECT a, b, delta FROM voice_pairs WHERE a = ?"
        " UNION ALL SELECT b AS a, a AS b, delta FROM voice_pairs WHERE b = ?"
        " ORDER BY delta",
        (key, key),
    )
    return _dicts(cur)


def voice_features(conn: sqlite3.Connection, key: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT side, rank, feature, label, rate, rate_ref, z FROM voice_features"
        " WHERE key = ? ORDER BY rank",
        (key,),
    )
    return _dicts(cur)


def speaker_lemmas(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT DISTINCT speaker FROM clauses WHERE speaker != ''")]


def speaker_chapters(
    conn: sqlite3.Connection, lemmas: list[str], limit: int
) -> list[dict[str, Any]]:
    """Chapters with the most speech clauses of these speaker lemmas."""
    marks = ",".join("?" * len(lemmas))
    cur = conn.execute(
        "SELECT v.book_id, v.chapter, COUNT(*) AS n_clauses FROM clauses c"
        f" JOIN verses v ON v.verse_id = c.verse_id WHERE c.speaker IN ({marks})"
        " AND c.txt LIKE '%Q' GROUP BY v.book_id, v.chapter"
        " ORDER BY n_clauses DESC, v.book_id, v.chapter LIMIT ?",
        (*lemmas, limit),
    )
    return _dicts(cur)


def dialogue_targets(conn: sqlite3.Connection, book_id: int) -> dict[str, list[dict[str, Any]]]:
    """speaker key -> whom they speak to in the book, the most quotations first."""
    out: dict[str, list[dict[str, Any]]] = {}
    for r in dialogue_pairs(conn, book_id):
        out.setdefault(r["speaker"], []).append(r)
    return out
