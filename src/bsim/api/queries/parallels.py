"""Read-only SQL helpers of `api/routes/parallels.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, count

SEQUENCE_COLS = (
    "seq_id, a_start, a_end, b_start, b_end, direction, a_book, b_book, same_chapter, n_pairs,"
    " score, q, n_gold"
)


def book_spans(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """First and last verse id of every book, in canon order."""
    cur = conn.execute(
        "SELECT book_id, MIN(verse_id) AS start, MAX(verse_id) AS end FROM verses"
        " GROUP BY book_id ORDER BY book_id"
    )
    return _dicts(cur)


def sequences_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    cross_book: bool,
    hide_same_chapter: bool,
    max_q: float | None,
    min_pairs: int,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
    direction: str | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """Chains, strongest first; `span` = (first, last) verse id: chains touching it."""
    where, args = "n_pairs >= ?", [min_pairs]
    if direction is not None:
        where += " AND direction = ?"
        args.append(direction)
    if max_q is not None:
        where += " AND q <= ?"
        args.append(max_q)
    if book_id is not None:
        where += " AND (a_book = ? OR b_book = ?)"
        args += [book_id, book_id]
    if cross_book:
        where += " AND a_book != b_book"
    if hide_same_chapter:
        where += " AND same_chapter = 0"
    if span is not None:
        where += " AND ((a_start <= ? AND a_end >= ?) OR (b_start <= ? AND b_end >= ?))"
        args += [span[1], span[0], span[1], span[0]]
    total = count(conn, f"SELECT COUNT(*) FROM sequences WHERE {where}", args)
    cur = conn.execute(
        f"SELECT {SEQUENCE_COLS} FROM sequences WHERE {where}"
        " ORDER BY score DESC, seq_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def _change_filter(
    op: str | None, a_book: int | None, b_book: int | None, span: tuple[int, int] | None = None
) -> tuple[str, list[Any]]:
    """`op` None: every op; `span`: verse pairs with a side in these verses."""
    # a moved word has a row on each side: count the A side only
    if op is None:
        where, args = "(op != 'moved' OR a_idx IS NOT NULL)", []
    else:
        where, args = "op = ?" + (" AND a_idx IS NOT NULL" if op == "moved" else ""), [op]
    if a_book is not None:
        where += " AND a_book = ?"
        args.append(a_book)
    if b_book is not None:
        where += " AND b_book = ?"
        args.append(b_book)
    if span is not None:
        where += " AND (a BETWEEN ? AND ? OR b BETWEEN ? AND ?)"
        args += [*span, *span]
    return where, args


# spelling / form changes keep the lemma: they are grouped by the written forms instead
FORM_OPS = ("spelling", "form")


def _group_cols(op: str) -> tuple[str, str]:
    return ("a_form", "b_form") if op in FORM_OPS else ("a_key", "b_key")


def change_groups(
    conn: sqlite3.Connection,
    op: str,
    a_book: int | None,
    b_book: int | None,
    limit: int,
    offset: int,
    span: tuple[int, int] | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """(number of groups, groups) of `diff_changes` by word key (by written form for spelling /
    form changes), most frequent first; the non-grouping pair of columns is None."""
    where, args = _change_filter(op, a_book, b_book, span)
    ca, cb = _group_cols(op)
    total = count(
        conn,
        f"SELECT COUNT(*) FROM (SELECT 1 FROM diff_changes WHERE {where} GROUP BY {ca}, {cb})",
        args,
    )
    other = "NULL AS a_key, NULL AS b_key" if op in FORM_OPS else "NULL AS a_form, NULL AS b_form"
    cur = conn.execute(
        f"SELECT {ca}, {cb}, {other}, COUNT(*) AS count, COUNT(DISTINCT seq_id) AS n_sequences"
        f" FROM diff_changes WHERE {where} GROUP BY {ca}, {cb}"
        f" ORDER BY count DESC, n_sequences DESC, {ca}, {cb} LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def change_examples(
    conn: sqlite3.Connection,
    op: str,
    a_book: int | None,
    b_book: int | None,
    groups: list[tuple[str | None, str | None]],
    n: int,
    span: tuple[int, int] | None = None,
) -> dict[tuple[str | None, str | None], list[dict[str, Any]]]:
    """Up to `n` example verse pairs of each group (`groups`: values of its grouping columns),
    in one query."""
    out: dict[tuple[str | None, str | None], list[dict[str, Any]]] = {g: [] for g in groups}
    if not groups:
        return out
    where, args = _change_filter(op, a_book, b_book, span)
    ca, cb = _group_cols(op)
    values = ", ".join("(?, ?)" for _ in groups)
    cur = conn.execute(
        f"WITH g(ga, gb) AS (VALUES {values}),"
        f" d AS (SELECT DISTINCT g.ga, g.gb, c.seq_id, c.a, c.b FROM diff_changes c"
        f" JOIN g ON c.{ca} IS g.ga AND c.{cb} IS g.gb WHERE {where}),"
        " r AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY ga, gb ORDER BY seq_id, a, b) AS rn"
        " FROM d)"
        " SELECT ga, gb, seq_id, a, b FROM r WHERE rn <= ? ORDER BY ga, gb, rn",
        [*(v for g in groups for v in g), *args, n],
    )
    for ga, gb, seq_id, a, b in cur:
        out[(ga, gb)].append({"seq_id": seq_id, "a": a, "b": b})
    return out


def change_totals(
    conn: sqlite3.Connection,
    a_book: int | None,
    b_book: int | None,
    span: tuple[int, int] | None = None,
) -> dict[str, int]:
    """Changes per op under the book / verse filters (moved words counted once)."""
    where, args = _change_filter(None, a_book, b_book, span)
    cur = conn.execute(f"SELECT op, COUNT(*) FROM diff_changes WHERE {where} GROUP BY op", args)
    return dict(cur.fetchall())


def sequence(conn: sqlite3.Connection, seq_id: int) -> dict[str, Any] | None:
    cur = conn.execute(f"SELECT {SEQUENCE_COLS}, pairs FROM sequences WHERE seq_id = ?", (seq_id,))
    rows = _dicts(cur)
    return rows[0] if rows else None


def synopsis_chains(conn: sqlite3.Connection, max_q: float) -> list[dict[str, Any]]:
    """Same-order chains with q <= max_q, pairs still JSON, strongest first."""
    cur = conn.execute(
        "SELECT seq_id, a_book, b_book, direction, same_chapter, q, pairs FROM sequences"
        " WHERE direction = 'forward' AND q <= ? ORDER BY seq_id",
        (max_q,),
    )
    return _dicts(cur)


def rewrites_page(
    conn: sqlite3.Connection,
    a_book: int | None,
    b_book: int | None,
    op: str | None,
    max_q: float | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Systematic changes between book pairs, strongest (lowest q, highest G²) first."""
    where, args = "1 = 1", []
    for col, cmp, val in (
        ("a_book", "=", a_book),
        ("b_book", "=", b_book),
        ("op", "=", op),
        ("q", "<=", max_q),
    ):
        if val is not None:
            where += f" AND {col} {cmp} ?"
            args.append(val)
    total = count(conn, f"SELECT COUNT(*) FROM rewrites WHERE {where}", args)
    cur = conn.execute(
        f"SELECT * FROM rewrites WHERE {where} ORDER BY q, g2 DESC, a_book, b_book, a_key, b_key"
        " LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def rewrite_profiles(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(
        conn.execute("SELECT * FROM rewrite_profiles ORDER BY verse_pairs DESC, a_book, b_book")
    )


def typescenes_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    max_q: float | None,
    hide_textual: bool,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Pericope pairs, most significant first; `span`: a pericope overlapping these verses."""
    where, args = "1 = 1", []
    if book_id is not None:
        where += " AND (a_book = ? OR b_book = ?)"
        args += [book_id, book_id]
    if max_q is not None:
        where += " AND q <= ?"
        args.append(max_q)
    if hide_textual:
        where += " AND parallel_text = 0"
    if span is not None:
        inside = (
            "SELECT unit_id FROM units WHERE unit_type = 'pericope'"
            " AND start_verse_id <= ? AND end_verse_id >= ?"
        )
        where += f" AND (a_unit IN ({inside}) OR b_unit IN ({inside}))"
        args += [span[1], span[0], span[1], span[0]]
    total = count(conn, f"SELECT COUNT(*) FROM typescenes WHERE {where}", args)
    cur = conn.execute(
        f"SELECT * FROM typescenes WHERE {where} ORDER BY q, score DESC, a_unit, b_unit"
        " LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)
