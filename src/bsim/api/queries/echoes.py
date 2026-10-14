"""Read-only SQL helpers of `api/routes/echoes.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, count


def echo_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(
        conn.execute(
            "SELECT * FROM echo_books ORDER BY cited + borrowed + language DESC,"
            " src_book, dst_book"
        )
    )


def echo_sources(conn: sqlite3.Connection, top: int) -> list[dict[str, Any]]:
    """The chapters other books draw on most: cited / borrowed first, then any layer."""
    cur = conn.execute(
        "SELECT * FROM echo_chapters WHERE lends > 0"
        " ORDER BY lends_explicit DESC, lends DESC, unit_id LIMIT ?",
        (top,),
    )
    return _dicts(cur)


_ECHO_ORDER = (
    "CASE basis WHEN 'cited' THEN 0 WHEN 'borrowed' THEN 1 WHEN 'conflict' THEN 2"
    " WHEN 'language' THEN 3 ELSE 4 END"
)


def echoes_page(
    conn: sqlite3.Connection,
    basis: str | None,
    directed: bool | None,
    backward: bool | None,
    book_id: int | None,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Cross-book chapter pairs, the strongest evidence first; `backward`: the echo is earlier in
    the canon than its source; `span`: either chapter overlapping these verses."""
    where, args = ["1 = 1"], []
    if basis is not None:
        where.append("basis = ?")
        args.append(basis)
    if directed is not None:
        where.append("direction != 0" if directed else "direction = 0")
    if backward is not None:
        where.append("direction < 0" if backward else "direction > 0")
    if book_id is not None:
        where.append("(a_book = ? OR b_book = ?)")
        args += [book_id, book_id]
    if span is not None:
        where.append("((a_start <= ? AND a_end >= ?) OR (b_start <= ? AND b_end >= ?))")
        args += [span[1], span[0], span[1], span[0]]
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM echo_edges WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM echo_edges WHERE {w} ORDER BY {_ECHO_ORDER}, weight DESC, edge_id"
        " LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)
