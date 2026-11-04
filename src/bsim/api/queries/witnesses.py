"""Read-only SQL helpers of `api/routes/witnesses.py` (DESIGN.md §9, §16.78)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts

SP = "sp"
_ORDER = "CASE witness WHEN 'sp' THEN 0 ELSE 1 END, witness"


def witnesses_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM witnesses_books ORDER BY kind, book_id"))


def witnesses_scrolls(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM witnesses_scrolls ORDER BY read DESC, scroll"))


def witnesses_chronology(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = _dicts(conn.execute("SELECT * FROM witnesses_chronology ORDER BY seq"))
    return [r | {"death": bool(r["death"])} for r in rows]


def witnesses_pluses_page(
    conn: sqlite3.Connection, kind: str, book: int | None, min_plus: int, limit: int, offset: int
) -> tuple[int, list[dict[str, Any]]]:
    """The verses with a plus of `min_plus` read words or more, the largest first."""
    side = "witness = 'sp'" if kind == SP else "witness <> 'sp'"
    where = f"{side} AND plus >= ?" + (" AND book_id = ?" if book is not None else "")
    args: tuple[Any, ...] = (min_plus, book) if book is not None else (min_plus,)
    total = int(conn.execute(f"SELECT COUNT(*) FROM witnesses_verses WHERE {where}", args)
                .fetchone()[0])  # fmt: skip
    rows = _dicts(conn.execute(
        f"SELECT witness, verse_id, plus, variants FROM witnesses_verses WHERE {where}"
        " ORDER BY plus DESC, verse_id, witness LIMIT ? OFFSET ?", (*args, limit, offset),
    ))  # fmt: skip
    return total, rows


def witnesses_unit_page(
    conn: sqlite3.Connection, first: int, last: int, limit: int, offset: int
) -> tuple[int, list[int], list[str], list[dict[str, Any]]]:
    """(verses with a witness among first..last, a page of their verse_ids, every witness of
    them, the readings of the page's verses with the MT tokens each lacks)."""
    vids = [r[0] for r in conn.execute(
        "SELECT DISTINCT verse_id FROM witnesses_verses WHERE verse_id BETWEEN ? AND ?"
        " ORDER BY verse_id", (first, last),
    )]  # fmt: skip
    wits = [r[0] for r in conn.execute(
        f"SELECT DISTINCT witness FROM witnesses_verses WHERE verse_id BETWEEN ? AND ?"
        f" ORDER BY {_ORDER}", (first, last),
    )]  # fmt: skip
    page = vids[offset : offset + limit]
    if not page:
        return len(vids), [], wits, []
    marks = ",".join("?" * len(page))
    rows = _dicts(conn.execute(
        f"SELECT * FROM witnesses_verses WHERE verse_id IN ({marks}) ORDER BY verse_id, {_ORDER}",
        page,
    ))  # fmt: skip
    missing: dict[tuple[str, int], list[int]] = {}
    for w, v, t in conn.execute(
        f"SELECT witness, verse_id, mt_tok FROM witnesses_changes WHERE op = 'omitted'"
        f" AND mt_tok IS NOT NULL AND verse_id IN ({marks})", page,
    ):  # fmt: skip
        missing.setdefault((w, v), []).append(int(t))
    for r in rows:
        r["words"] = json.loads(r["words"])
        r["missing"] = sorted(missing.get((r["witness"], r["verse_id"]), []))
    return len(vids), page, wits, rows


def witnesses_verse_counts(conn: sqlite3.Connection, first: int, last: int
                           ) -> dict[int, dict[str, int]]:  # fmt: skip
    """verse_id -> {sp: the Samaritan's variants, scrolls: scrolls with the verse, scroll_variants:
    their variants} for the verses with a witness among first..last."""
    out: dict[int, dict[str, int]] = {}
    for v, w, n in conn.execute(
        "SELECT verse_id, witness, variants FROM witnesses_verses WHERE verse_id BETWEEN ? AND ?",
        (first, last),
    ):
        c = out.setdefault(int(v), {})
        if w == SP:
            c["sp"] = int(n)
        else:
            c["scrolls"] = c.get("scrolls", 0) + 1
            c["scroll_variants"] = c.get("scroll_variants", 0) + int(n)
    return out
