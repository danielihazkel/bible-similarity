"""Read-only SQL helpers of `api/routes/core.py` (DESIGN.md §9)."""

from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from typing import Any

from bsim.api.queries.common import UNIT_COLS, VERSE_COLS, _dicts, _verse, count
from bsim.text.normalize import match_key


def units_of_type(
    conn: sqlite3.Connection, unit_type: str, book_id: int | None = None, chapter: int | None = None
) -> list[dict[str, Any]]:
    """Units of a type, optionally of one book, and of one chapter (by their first verse)."""
    sql, args = f"SELECT {UNIT_COLS} FROM units WHERE unit_type = ?", [unit_type]
    if book_id is not None:
        sql += " AND book_id = ?"
        args.append(book_id)
    if chapter is not None:
        sql += (
            " AND start_verse_id IN (SELECT verse_id FROM verses WHERE book_id = ? AND chapter = ?)"
        )
        args += [book_id, chapter]
    return _dicts(conn.execute(sql + " ORDER BY start_verse_id", args))


def verse_range(conn: sqlite3.Connection, start: int, end: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        f"SELECT {VERSE_COLS} FROM verses WHERE verse_id BETWEEN ? AND ? ORDER BY verse_id",
        (start, end),
    )
    return [_verse(r) for r in _dicts(cur)]


def neighbours(conn: sqlite3.Connection, u: dict[str, Any]) -> tuple[str | None, str | None]:
    """(previous, next) unit id of the same type, in canon order."""
    prev = conn.execute(
        "SELECT unit_id FROM units WHERE unit_type = ? AND start_verse_id < ?"
        " ORDER BY start_verse_id DESC LIMIT 1",
        (u["unit_type"], u["start_verse_id"]),
    ).fetchone()
    nxt = conn.execute(
        "SELECT unit_id FROM units WHERE unit_type = ? AND start_verse_id > ?"
        " ORDER BY start_verse_id LIMIT 1",
        (u["unit_type"], u["start_verse_id"]),
    ).fetchone()
    return (prev[0] if prev else None), (nxt[0] if nxt else None)


def verse_lemmas(rows: list[dict[str, Any]]) -> dict[int, list[str]]:
    """verse_id -> distinct content lemmas in word order, from `words()` rows."""
    out: dict[int, dict[str, None]] = defaultdict(dict)
    for w in rows:
        out[w["verse_id"]].update(dict.fromkeys(w["content_lemmas"].split()))
    return {v: list(lems) for v, lems in out.items()}


def discoveries(
    conn: sqlite3.Connection,
    unit_type: str,
    mode: str,
    book_id: int | None,
    cross_book: bool,
    limit: int,
    offset: int,
    unit_id: str | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """(total, page) of `discoveries` rows, strongest first; `unit_id`: the pairs it is in."""
    where, args = "unit_type = ? AND mode = ?", [unit_type, mode]
    if unit_id is not None:
        where += " AND (a_id = ? OR b_id = ?)"
        args += [unit_id, unit_id]
    if book_id is not None:
        where += " AND (a_book = ? OR b_book = ?)"
        args += [book_id, book_id]
    if cross_book:
        where += " AND a_book != b_book"
    total = count(conn, f"SELECT COUNT(*) FROM discoveries WHERE {where}", args)
    cur = conn.execute(
        "SELECT a_id, b_id, score, tie, rank_ab, rank_ba FROM discoveries"
        f" WHERE {where} ORDER BY score DESC, tie DESC, a_id, b_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


_LEMMA_INDEX: dict[str, list[tuple[str, str, str, int]]] = {}


_STRONG = re.compile(r"[Hh]?(\d+)([a-z]?)")


_PREFIXES = set("והבכלמש")


def form_keys(q: str) -> list[str]:
    """A Hebrew form's match key, then the key with one and with two prefix letters dropped
    (בראשית, והמלך), as long as each dropped letter is a prefix and two letters are left."""
    key = match_key(q)
    keys = []
    for drop in range(3):
        if len(key) - drop < 2 or (drop and key[drop - 1] not in _PREFIXES):
            break
        keys.append(key[drop:])
    return keys


def lemma_lookup(conn: sqlite3.Connection, q: str, limit: int) -> list[dict[str, Any]]:
    """Lemmas named by a Strong's number (`7965`, `H1350a`) or a Hebrew form (consonants, finals
    folded; one or two prefix letters dropped when the whole form matches nothing): exact matches
    first, then lemmas starting with it, the commonest first. The lemma list is read once per DB."""
    db = conn.execute("PRAGMA database_list").fetchone()[2]
    index = _LEMMA_INDEX.get(db)
    if index is None:
        rows = conn.execute("SELECT lemma, he_lemma, n_verses FROM lemma_gloss").fetchall()
        index = [(lem, he, match_key(he), n) for lem, he, n in rows]
        _LEMMA_INDEX[db] = index
    q = q.strip()
    strong = _STRONG.fullmatch(q)
    if strong:
        num, sense = strong.groups()
        exact = re.compile(rf"{num}{sense}")
        loose = re.compile(rf"{num}[a-z]?")
        ranked = [
            (0 if exact.fullmatch(lem) else 1, -n, lem, he)
            for lem, he, _, n in index
            if loose.fullmatch(lem)
        ]
    else:
        ranked = []
        # a form with prefixes (בראשית, והמלך): drop up to two prefix letters until one matches
        for k0 in form_keys(q):
            ranked = [
                (0 if k == k0 else 1, -n, lem, he) for lem, he, k, n in index if k.startswith(k0)
            ]
            if ranked:
                break
    ranked.sort()
    return [{"lemma": lem, "he_lemma": he, "n_verses": -n} for _, n, lem, he in ranked[:limit]]


def verse_at(conn: sqlite3.Connection, book_id: int, chapter: int, verse: int) -> int | None:
    row = conn.execute(
        "SELECT verse_id FROM verses WHERE book_id = ? AND chapter = ? AND verse = ?",
        (book_id, chapter, verse),
    ).fetchone()
    return row[0] if row else None


def lemma_books(conn: sqlite3.Connection, lemma: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT book_id, COUNT(*) AS n_verses FROM lemma_verses WHERE lemma = ?"
        " GROUP BY book_id ORDER BY book_id",
        (lemma,),
    )
    return _dicts(cur)


def lemma_page(
    conn: sqlite3.Connection, lemma: str, book_id: int | None, limit: int, offset: int
) -> list[int]:
    """Verse ids containing `lemma` (in one book, if given), canon order."""
    sql, args = "SELECT verse_id FROM lemma_verses WHERE lemma = ?", [lemma]
    if book_id is not None:
        sql += " AND book_id = ?"
        args.append(book_id)
    cur = conn.execute(sql + " ORDER BY verse_id LIMIT ? OFFSET ?", [*args, limit, offset])
    return [r[0] for r in cur.fetchall()]
