"""Other witnesses (DESIGN.md §16.78): the Samaritan Pentateuch and the Dead Sea Scrolls against
the MT, word by word; the check, the known readings and the Samaritan chronology."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models.witnesses import (
    ChronologyKnown,
    ChronologyRow,
    KnownReading,
    SamaritanTotals,
    ScrollRow,
    ScrollTotals,
    WitnessBook,
    WitnessesResponse,
    WitnessKind,
    WitnessPlus,
    WitnessPlusesResponse,
    WitnessReading,
    WitnessUnitResponse,
    WitnessVerse,
)
from bsim.api.routes._common import (
    BookFilter,
    Conn,
    State,
    check_page,
    stage,
    stage_missing,
    unit_or_404,
)

router = APIRouter()

KEEP = ("plus_min", "max_unc", "sp_pluses", "parallel_verses", "plus_in_parallel",
        "plus_elsewhere", "ratio", "null_mean", "p", "shifts", "alpha", "holds",
        "known_holds")  # fmt: skip


def _meta(state: State) -> dict[str, Any]:
    m = state.meta.get("witnesses")
    if not m:
        raise stage_missing("witnesses")
    return m


@router.get("/witnesses", dependencies=[stage("witnesses")], response_model=WitnessesResponse)
def witnesses(state: State, conn: Conn) -> dict[str, Any]:
    """The totals, the check, the known readings, both chronologies, the books and the scrolls
    (503: the stage did not run)."""
    m = _meta(state)
    known = m.get("known") or []
    chron = queries.witnesses_chronology(conn)
    ids = [k["verse_id"] for k in known]
    ids += [c["verse_id"] for c in chron if c["verse_id"] is not None]
    verses = queries.verses_by_id(conn, ids)
    return {
        **{k: m[k] for k in KEEP},
        "samaritan": SamaritanTotals(**m["samaritan"]),
        "scrolls": ScrollTotals(**m["scrolls"]),
        "known": [
            KnownReading(
                **{k: x.get(k) for k in ("witness", "ref", "plus", "reads", "found", "note")},
                verse=verses.get(x["verse_id"]),
            )
            for x in known
        ],
        "chronology_known": [ChronologyKnown(**c) for c in m.get("chronology_known") or []],
        "chronology": [
            ChronologyRow(
                **c,
                ref=verses[c["verse_id"]]["ref"] if c["verse_id"] in verses else None,
                ref_he=verses[c["verse_id"]]["ref_he"] if c["verse_id"] in verses else None,
            )
            for c in chron
        ],
        "books": [WitnessBook(**b) for b in queries.witnesses_books(conn)],
        "scroll_rows": [ScrollRow(**s) for s in queries.witnesses_scrolls(conn)],
    }


@router.get(
    "/witnesses/pluses", dependencies=[stage("witnesses")], response_model=WitnessPlusesResponse
)
def witnesses_pluses(
    state: State,
    conn: Conn,
    kind: WitnessKind = "sp",
    book: BookFilter = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """The verses where a witness has the most words the MT lacks (the Samaritan or the
    scrolls), in a book or all."""
    check_page(state, limit, offset)
    m = _meta(state)
    total, rows = queries.witnesses_pluses_page(conn, kind, book, int(m["plus_min"]), limit,
                                                offset)  # fmt: skip
    verses = queries.verses_by_id(conn, [r["verse_id"] for r in rows])
    items = [
        WitnessPlus(
            witness=r["witness"],
            verse=verses[r["verse_id"]],
            plus=r["plus"],
            variants=r["variants"],
        )  # fmt: skip
        for r in rows
        if r["verse_id"] in verses
    ]
    return {"kind": kind, "book": book, "total": total, "offset": offset, "limit": limit,
            "items": items}  # fmt: skip


@router.get(
    "/witnesses/unit", dependencies=[stage("witnesses")], response_model=WitnessUnitResponse
)
def witnesses_unit(
    unit: str, state: State, conn: Conn, limit: int = 50, offset: int = 0
) -> dict[str, Any]:
    """Each verse of a unit with every witness's words aligned to it (404: unknown unit)."""
    check_page(state, limit, offset)
    _meta(state)
    u = unit_or_404(conn, unit)
    total, page, wits, rows = queries.witnesses_unit_page(
        conn, u["start_verse_id"], u["end_verse_id"], limit, offset
    )
    verses = queries.verses_by_id(conn, page)
    by: dict[int, list[WitnessReading]] = {}
    for r in rows:
        by.setdefault(r["verse_id"], []).append(WitnessReading(
            **{k: r[k] for k in ("witness", "n_words", "n_read", "plus", "variants", "words",
                                 "missing")},
        ))  # fmt: skip
    items = [WitnessVerse(verse=verses[v], readings=by.get(v, [])) for v in page if v in verses]
    return {"unit_id": u["unit_id"], "witnesses": wits, "total": total, "offset": offset,
            "limit": limit, "items": items}  # fmt: skip
