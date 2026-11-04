"""Read-only SQL helpers of `api/routes/reception.py` (DESIGN.md §9, §16.77)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts

CORPORA = ("mishnah", "tosefta", "bavli", "yerushalmi")
_ORDER = "CASE corpus " + " ".join(f"WHEN '{c}' THEN {i}" for i, c in enumerate(CORPORA)) + " END"


def reception_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM reception_books ORDER BY book_id"))


def reception_chapters(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM reception_chapters ORDER BY book_id, chapter"))


def reception_verses_page(
    conn: sqlite3.Connection, corpus: str | None, book: int | None, limit: int, offset: int
) -> tuple[int, list[dict[str, Any]]]:
    """The verses cited, most first (by `corpus` or in all), then in canon order."""
    col = corpus if corpus in CORPORA else "total"
    where = f"r.{col} > 0" + (" AND v.book_id = ?" if book is not None else "")
    args: tuple[Any, ...] = (book,) if book is not None else ()
    base = f"FROM reception_verses r JOIN verses v USING (verse_id) WHERE {where}"
    total = int(conn.execute(f"SELECT COUNT(*) {base}", args).fetchone()[0])
    rows = _dicts(
        conn.execute(
            f"SELECT r.* {base} ORDER BY r.{col} DESC, r.verse_id LIMIT ? OFFSET ?",
            (*args, limit, offset),
        )
    )
    return total, rows


def reception_counts(conn: sqlite3.Connection, first: int, last: int) -> dict[str, int]:
    """Citations of the verses first..last, by corpus, and their total."""
    cols = ", ".join(f"COALESCE(SUM({c}), 0)" for c in (*CORPORA, "total"))
    row = conn.execute(
        f"SELECT {cols} FROM reception_verses WHERE verse_id BETWEEN ? AND ?", (first, last)
    ).fetchone()
    return dict(zip((*CORPORA, "total"), (int(x) for x in row), strict=True))


def reception_verse_counts(
    conn: sqlite3.Connection, first: int, last: int
) -> dict[int, dict[str, int]]:
    """verse_id -> its citations by corpus, for the verses cited among first..last."""
    rows = _dicts(
        conn.execute("SELECT * FROM reception_verses WHERE verse_id BETWEEN ? AND ?", (first, last))
    )
    return {r["verse_id"]: {c: r[c] for c in (*CORPORA, "total")} for r in rows}


def reception_citations_page(
    conn: sqlite3.Connection, first: int, last: int, corpus: str | None, limit: int, offset: int
) -> tuple[int, list[dict[str, Any]]]:
    """The citations of the verses first..last, in verse order, then by corpus and passage."""
    where = "verse_id BETWEEN ? AND ?" + (" AND corpus = ?" if corpus else "")
    args: tuple[Any, ...] = (first, last, corpus) if corpus else (first, last)
    total = int(
        conn.execute(f"SELECT COUNT(*) FROM reception_citations WHERE {where}", args).fetchone()[0]
    )
    rows = _dicts(
        conn.execute(
            f"SELECT * FROM reception_citations WHERE {where}"
            f" ORDER BY verse_id, {_ORDER}, rowid LIMIT ? OFFSET ?",
            (*args, limit, offset),
        )
    )
    return total, rows
