"""Read-only SQL helpers of `api/routes/places.py` (DESIGN.md §9)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts

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
