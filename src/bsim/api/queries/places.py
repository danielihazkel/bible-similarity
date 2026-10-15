"""Read-only SQL helpers of `api/routes/places.py` (DESIGN.md §9)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, count

_COLS = (
    "p.place_id, p.he, p.kind, p.lat, p.lon, p.score, p.coord_source, p.runner_up,"
    " p.n_identifications, p.n_verses, p.first_vid, p.lemmas"
)


def _sites(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r | {"lemmas": json.loads(r["lemmas"])} for r in rows]


def places_list(
    conn: sqlite3.Connection,
    kind: str | None,
    book_id: int | None,
    span: tuple[int, int] | None,
) -> list[dict[str, Any]]:
    """Every site (of a kind), most named first; with a book or a verse span, only the sites named
    there, with `n_here`."""
    where, args = ["1"], []
    if kind is not None:
        where.append("p.kind = ?")
        args.append(kind)
    w = " AND ".join(where)
    if book_id is None and span is None:
        cur = conn.execute(
            f"SELECT {_COLS}, NULL AS n_here FROM places p WHERE {w}"
            " ORDER BY p.n_verses DESC, p.place_id",
            args,
        )
        return _sites(_dicts(cur))
    scope, sargs = [], []
    if book_id is not None:
        scope.append("v.book_id = ?")
        sargs.append(book_id)
    if span is not None:
        scope.append("m.verse_id BETWEEN ? AND ?")
        sargs += list(span)
    cur = conn.execute(
        f"SELECT {_COLS}, COUNT(DISTINCT m.verse_id) AS n_here FROM place_mentions m"
        " JOIN places p ON p.place_id = m.place_id JOIN verses v ON v.verse_id = m.verse_id"
        f" WHERE {w} AND {' AND '.join(scope)} GROUP BY p.place_id"
        " ORDER BY n_here DESC, p.n_verses DESC, p.place_id",
        [*args, *sargs],
    )
    return _sites(_dicts(cur))


def entity_sites(conn: sqlite3.Connection, lemma: str) -> list[dict[str, Any]]:
    """The sites a name is, with how many of its verses name each (`n_here`)."""
    cur = conn.execute(
        f"SELECT {_COLS}, COUNT(*) AS n_here FROM place_mentions m"
        " JOIN places p ON p.place_id = m.place_id WHERE m.lemma = ?"
        " GROUP BY p.place_id ORDER BY n_here DESC, p.place_id",
        (lemma,),
    )
    return _sites(_dicts(cur))


def name_kind(conn: sqlite3.Connection, lemma: str) -> str | None:
    row = conn.execute("SELECT kind FROM name_kinds WHERE lemma = ?", (lemma,)).fetchone()
    return row[0] if row else None


def place(conn: sqlite3.Connection, place_id: int) -> dict[str, Any] | None:
    cur = conn.execute(f"SELECT {_COLS}, NULL AS n_here FROM places p WHERE p.place_id = ?",
                       (place_id,))  # fmt: skip
    rows = _sites(_dicts(cur))
    return rows[0] if rows else None


def place_names(conn: sqlite3.Connection, place_id: int) -> list[dict[str, Any]]:
    """The names that are this place, with their Hebrew form and verses here."""
    cur = conn.execute(
        "SELECT m.lemma, COALESCE(e.he, m.lemma) AS he, COUNT(*) AS n_verses FROM place_mentions m"
        " LEFT JOIN entities e ON e.lemma = m.lemma WHERE m.place_id = ?"
        " GROUP BY m.lemma ORDER BY n_verses DESC, m.lemma",
        (place_id,),
    )
    return _dicts(cur)


def place_books(conn: sqlite3.Connection, place_id: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT v.book_id, COUNT(DISTINCT m.verse_id) AS n_verses FROM place_mentions m"
        " JOIN verses v ON v.verse_id = m.verse_id WHERE m.place_id = ?"
        " GROUP BY v.book_id ORDER BY v.book_id",
        (place_id,),
    )
    return _dicts(cur)


def place_partners(conn: sqlite3.Connection, place_id: int, limit: int) -> list[dict[str, Any]]:
    """Places named in the same verses, most shared verses first."""
    cur = conn.execute(
        "SELECT p.place_id, p.he, p.kind, COUNT(DISTINCT b.verse_id) AS n_verses"
        " FROM place_mentions a JOIN place_mentions b"
        " ON b.verse_id = a.verse_id AND b.place_id != a.place_id"
        " JOIN places p ON p.place_id = b.place_id WHERE a.place_id = ?"
        " GROUP BY p.place_id ORDER BY n_verses DESC, p.place_id LIMIT ?",
        (place_id, limit),
    )
    return _dicts(cur)


def place_verses_page(
    conn: sqlite3.Connection, place_id: int, limit: int, offset: int
) -> tuple[int, list[dict[str, Any]]]:
    """The verses naming a place (canon order) with the name lemmas there."""
    total = count(conn, "SELECT COUNT(DISTINCT verse_id) FROM place_mentions WHERE place_id = ?",
                  [place_id])  # fmt: skip
    cur = conn.execute(
        "SELECT verse_id, group_concat(lemma, ' ') AS lemmas FROM place_mentions"
        " WHERE place_id = ? GROUP BY verse_id ORDER BY verse_id LIMIT ? OFFSET ?",
        (place_id, limit, offset),
    )
    return total, _dicts(cur)


def place_tokens(
    conn: sqlite3.Connection, first: int, last: int
) -> list[dict[str, Any]]:
    """Place mentions in a verse span with the display tokens of their words."""
    cur = conn.execute(
        "SELECT m.verse_id, m.place_id, w.display_idx, w.content_lemmas, m.lemma"
        " FROM place_mentions m JOIN words w ON w.verse_id = m.verse_id"
        " WHERE m.verse_id BETWEEN ? AND ? AND w.display_idx IS NOT NULL"
        " AND (' ' || w.content_lemmas || ' ') LIKE ('% ' || m.lemma || ' %')"
        " ORDER BY m.verse_id, w.display_idx",
        (first, last),
    )
    return _dicts(cur)


def map_shapes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    order = "CASE layer WHEN 'land' THEN 0 WHEN 'lakes' THEN 1 ELSE 2 END"
    cur = conn.execute(f"SELECT layer, rings FROM map_shapes ORDER BY {order}, shape_id")
    return [{"layer": r["layer"], "rings": json.loads(r["rings"])} for r in _dicts(cur)]
