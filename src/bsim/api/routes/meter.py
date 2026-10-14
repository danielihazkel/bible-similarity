"""Stresses per line and the falling lament line (DESIGN.md §16.37): the tests, chapters ranked by
net fall, and the lines of one unit."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models.common import UnitSummary
from bsim.api.models.meter import (
    MeterChapter,
    MeterGroup,
    MeterLine,
    MeterResponse,
    MeterVerse,
    UnitMeter,
)
from bsim.api.routes._common import Conn, State, check_page, unit_or_404

router = APIRouter()


def _chapters(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> list[MeterChapter]:
    units = queries.units_by_id(conn, [f"c:{r['book_id']}:{r['chapter']}" for r in rows])
    return [
        MeterChapter(
            unit=UnitSummary(**units[f"c:{r['book_id']}:{r['chapter']}"]),
            group=r["grp"],
            **{k: r[k] for k in ("n_lines", "fall", "rise", "net", "share32", "prob", "pct")},
        )
        for r in rows
    ]


def _keyed(conn: sqlite3.Connection, entries: list[dict[str, Any]] | None) -> list[MeterChapter]:
    keys = [(e["book_id"], e["chapter"]) for e in entries or []]
    return _chapters(conn, queries.meter_chapters(conn, keys))


@router.get("/meter", response_model=MeterResponse)
def meter(
    state: State,
    conn: Conn,
    group: MeterGroup | None = None,
    book: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """The falling-line tests and the chapters with enough measured lines, highest net fall
    first."""
    check_page(state, limit, offset)
    meta = state.meta.get("meter") or {}
    total, rows = queries.meter_chapters_page(
        conn, group, book, meta.get("min_lines") or 1, limit, offset
    )
    named = meta.get("named") or {}
    return {
        "meta": {**meta, "named": {k: v for k, v in named.items() if k != "chapters"}},
        "test_chapters": _keyed(conn, meta.get("test_chapters")),
        "control_chapters": _keyed(conn, meta.get("control")),
        "named_chapters": _keyed(conn, named.get("chapters")),
        "group": group,
        "book": book,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": _chapters(conn, rows),
    }


@router.get("/meter/{unit_id}", response_model=UnitMeter)
def unit_meter(unit_id: str, state: State, conn: Conn) -> dict[str, Any]:
    """Every line of the unit's verses with its stresses, and the chapter it starts in (no lines
    without `bsim meter`)."""
    u = unit_or_404(conn, unit_id)
    meta = state.meta.get("meter") or {}
    by_verse: dict[int, list[MeterLine]] = {}
    for r in queries.meter_lines(conn, u["start_verse_id"], u["end_verse_id"]):
        by_verse.setdefault(r["verse_id"], []).append(
            MeterLine(**{k: r[k] for k in ("first", "last", "stresses", "a", "b")})
        )
    first = queries.verses_by_id(conn, [u["start_verse_id"]])[u["start_verse_id"]]
    chapter = _chapters(conn, queries.meter_chapters(conn, [(first["book_id"], first["chapter"])]))
    return {
        "unit_id": unit_id,
        "min_stresses": meta.get("min_stresses") or 0,
        "max_stresses": meta.get("max_stresses") or 0,
        "chapter": chapter[0] if chapter else None,
        "verses": [MeterVerse(verse_id=v, lines=ls) for v, ls in by_verse.items()],
    }
