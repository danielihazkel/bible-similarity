"""Read-only SQL helpers of `api/routes/poetics.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import WORDPLAY_COLS, _dicts, _marks, count

PARALLEL_COLS = (
    "verse_id, n_cola, cola, pauses, cos, shared, shape, balance, prob, clauses, next_prob,"
    " relation, relation_pairs"
)


def parallelism_verses(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        f"SELECT {PARALLEL_COLS} FROM parallelism WHERE verse_id BETWEEN ? AND ? ORDER BY verse_id",
        (first, last),
    )
    return _dicts(cur)


def parallelism_units(
    conn: sqlite3.Connection,
    unit_type: str,
    book_id: int | None,
    skip_books: list[int],
    parallel_at: float,
    min_verses: int,
    limit: int,
    offset: int,
    sort: str = "prob",
    min_parallel: int = 0,
) -> tuple[int, list[dict[str, Any]]]:
    """Units ranked by the mean parallelism probability of their scored verses, or
    (`sort="antithetic"`) by the share of their parallel verses typed antithetic; units need
    `min_parallel` parallel verses."""
    where, args = "u.unit_type = ?", [unit_type]
    if book_id is not None:
        where += " AND u.book_id = ?"
        args.append(book_id)
    if skip_books:
        where += f" AND u.book_id NOT IN ({_marks(len(skip_books))})"
        args += skip_books
    inner = (
        "SELECT u.unit_id, AVG(p.prob) AS mean_prob, COUNT(p.prob) AS n_scored,"
        " AVG(CASE WHEN p.prob IS NULL THEN NULL WHEN p.prob >= ? THEN 1.0 ELSE 0.0 END)"
        " AS share_parallel, MIN(u.start_verse_id) AS start,"
        " SUM(CASE WHEN p.prob >= ? THEN 1 ELSE 0 END) AS n_parallel,"
        " AVG(CASE WHEN p.prob >= ? AND p.relation IS NOT NULL"
        " THEN p.relation = 'antithetic' END) AS share_antithetic"
        " FROM units u JOIN parallelism p"
        " ON p.verse_id BETWEEN u.start_verse_id AND u.end_verse_id"
        f" WHERE {where} GROUP BY u.unit_id HAVING COUNT(p.prob) >= ? AND n_parallel >= ?"
    )
    iargs = [parallel_at, parallel_at, parallel_at, *args, min_verses, min_parallel]
    total = count(conn, f"SELECT COUNT(*) FROM ({inner})", iargs)
    order = (
        "COALESCE(share_antithetic, -1) DESC, n_parallel DESC, start"
        if sort == "antithetic"
        else "mean_prob DESC, start"
    )
    cur = conn.execute(f"{inner} ORDER BY {order} LIMIT ? OFFSET ?", [*iargs, limit, offset])
    return total, _dicts(cur)


def parallelism_books(conn: sqlite3.Connection, parallel_at: float) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT v.book_id, AVG(p.prob) AS mean_prob, COUNT(p.prob) AS n_scored,"
        " AVG(CASE WHEN p.prob IS NULL THEN NULL WHEN p.prob >= ? THEN 1.0 ELSE 0.0 END)"
        " AS share_parallel"
        " FROM parallelism p JOIN verses v ON v.verse_id = p.verse_id"
        " GROUP BY v.book_id ORDER BY v.book_id",
        (parallel_at,),
    )
    return _dicts(cur)


def wordplay_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    kind: str | None,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Sound-alike pairs, strongest first; `span` = (first, last) verse id the pair touches."""
    where, args = "1 = 1", []
    if book_id is not None:
        where += " AND w.book_id = ?"
        args.append(book_id)
    if kind is not None:
        where += " AND w.kind = ?"
        args.append(kind)
    if span is not None:
        where += " AND w.b_vid >= ? AND w.a_vid <= ?"
        args += [span[0], span[1]]
    total = count(conn, f"SELECT COUNT(*) FROM wordplay w WHERE {where}", args)
    cur = conn.execute(
        f"SELECT {WORDPLAY_COLS} FROM wordplay w"
        " LEFT JOIN words wa ON wa.verse_id = w.a_vid AND wa.idx = w.a_idx"
        " LEFT JOIN words wb ON wb.verse_id = w.b_vid AND wb.idx = w.b_idx"
        f" WHERE {where} ORDER BY w.score DESC, w.a_vid, w.a_idx LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


STRUCTURE_SORT = {
    "semantic_chiasm": "semantic_chiasm_pct DESC, semantic_chiasm_z DESC",
    "lexical_chiasm": "lexical_chiasm_pct DESC, lexical_chiasm_z DESC",
    "semantic_inclusio": "semantic_inclusio_pct DESC, semantic_inclusio DESC",
    "lexical_inclusio": "lexical_inclusio_pct DESC, lexical_inclusio DESC",
}


def structure_page(
    conn: sqlite3.Connection, unit_type: str, by: str, min_verses: int, limit: int, offset: int
) -> tuple[int, list[dict[str, Any]]]:
    """Units ranked by one structure score (units without that score left out)."""
    score = by + "_pct"
    where = f"unit_type = ? AND n_verses >= ? AND {score} IS NOT NULL"
    args: list[Any] = [unit_type, min_verses]
    total = count(conn, f"SELECT COUNT(*) FROM structure WHERE {where}", args)
    cur = conn.execute(
        f"SELECT * FROM structure WHERE {where} ORDER BY {STRUCTURE_SORT[by]}, unit_id"
        " LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def acrostics_page(
    conn: sqlite3.Connection, max_q: float | None, book_id: int | None, limit: int, offset: int
) -> tuple[int, list[dict[str, Any]]]:
    """Chapters by their best alphabetic chain: lowest q, then highest score."""
    where, args = "1 = 1", []
    if max_q is not None:
        where += " AND q <= ?"
        args.append(max_q)
    if book_id is not None:
        where += " AND book_id = ?"
        args.append(book_id)
    total = count(conn, f"SELECT COUNT(*) FROM acrostics WHERE {where}", args)
    cur = conn.execute(
        f"SELECT * FROM acrostics WHERE {where} ORDER BY q, score DESC, unit_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def acrostic(conn: sqlite3.Connection, unit_id: str) -> dict[str, Any] | None:
    rows = _dicts(conn.execute("SELECT * FROM acrostics WHERE unit_id = ?", (unit_id,)))
    return rows[0] if rows else None


def word_pairs_page(
    conn: sqlite3.Connection, max_q: float | None, lemma: str | None, limit: int, offset: int
) -> tuple[int, list[dict[str, Any]]]:
    """Fixed word pairs of parallel lines, most significant first; `lemma`: pairs with it."""
    where, args = "1 = 1", []
    if max_q is not None:
        where += " AND q <= ?"
        args.append(max_q)
    if lemma is not None:
        where += " AND (a_lemma = ? OR b_lemma = ?)"
        args += [lemma, lemma]
    total = count(conn, f"SELECT COUNT(*) FROM word_pairs WHERE {where}", args)
    cur = conn.execute(
        f"SELECT * FROM word_pairs WHERE {where} ORDER BY q, g2 DESC, a_lemma, b_lemma"
        " LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def alliteration_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    unit_span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Cola by their alliteration p (lowest first)."""
    where, args = "1 = 1", []
    if book_id is not None:
        where += " AND book_id = ?"
        args.append(book_id)
    if unit_span is not None:
        where += " AND verse_id BETWEEN ? AND ?"
        args += list(unit_span)
    total = count(conn, f"SELECT COUNT(*) FROM alliteration WHERE {where}", args)
    cur = conn.execute(
        f"SELECT * FROM alliteration WHERE {where} ORDER BY p, verse_id, colon LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def rhymes_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    max_q: float | None,
    limit: int,
    offset: int,
    span: tuple[int, int] | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """Rhyme runs, most significant first; `span`: runs overlapping these verses."""
    where, args = "1 = 1", []
    if span is not None:
        where += " AND start_vid <= ? AND end_vid >= ?"
        args += [span[1], span[0]]
    if book_id is not None:
        where += " AND book_id = ?"
        args.append(book_id)
    if max_q is not None:
        where += " AND q <= ?"
        args.append(max_q)
    total = count(conn, f"SELECT COUNT(*) FROM rhymes WHERE {where}", args)
    cur = conn.execute(
        f"SELECT * FROM rhymes WHERE {where} ORDER BY q, n_cola DESC, start_vid LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)
