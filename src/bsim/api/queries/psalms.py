"""Read-only SQL helpers of `api/routes/psalms.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, _marks, count

PSALM_SORTS = {
    "chapter": "p.chapter",
    "turn": "p.turn_p IS NULL, p.turn_p, p.turn_stat DESC, p.chapter",
}


def psalms_page(
    conn: sqlite3.Connection,
    genre: str | None,
    cluster: int | None,
    turned_at: float | None,
    span: tuple[int, int] | None,
    sort: str,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Psalms with their unit labels; `turned_at`: only those whose turn has p at most this;
    `span`: those overlapping it."""
    where, args = ["1 = 1"], []
    if genre is not None:
        where.append("p.genre = ?")
        args.append(genre)
    if cluster is not None:
        where.append("p.cluster = ?")
        args.append(cluster)
    if turned_at is not None:
        where.append("p.turn_p <= ?")
        args.append(turned_at)
    if span is not None:
        where.append("u.start_verse_id <= ? AND u.end_verse_id >= ?")
        args += [span[1], span[0]]
    w = " AND ".join(where)
    base = "FROM psalms p JOIN units u ON u.unit_id = p.unit_id"
    total = count(conn, f"SELECT COUNT(*) {base} WHERE {w}", args)
    cur = conn.execute(
        f"SELECT p.*, u.label_en, u.label_he {base} WHERE {w} ORDER BY {PSALM_SORTS[sort]}"
        " LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def psalm_verses(conn: sqlite3.Connection, unit_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    """unit_id -> its verses in order, with their words and distress / praise words."""
    if not unit_ids:
        return {}
    cur = conn.execute(
        f"SELECT * FROM psalm_verses WHERE unit_id IN ({_marks(len(unit_ids))})"
        " ORDER BY unit_id, verse_id",
        unit_ids,
    )
    out: dict[str, list[dict[str, Any]]] = {}
    for r in _dicts(cur):
        out.setdefault(r["unit_id"], []).append(r)
    return out
