"""The text's own chronology (DESIGN.md §16.70): years from Adam with the verse of every number,
the kings of both kingdoms on one count, the synchronisms and Gen 5's numbers, and the checks."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.chronology import (
    ChronEvent,
    ChronKing,
    ChronologyResponse,
    ChronSync,
    Gen5Number,
    Life,
)
from bsim.api.routes._common import Conn, State

router = APIRouter()


@router.get("/chronology", response_model=ChronologyResponse)
def chronology(state: State, conn: Conn) -> dict[str, Any]:
    """Every date, reign and synchronism with its verse (404: the stage did not run)."""
    m = state.meta.get("chronology")
    if not m:
        raise HTTPException(status_code=404, detail="the chronology was not computed")
    events = queries.chronology_events(conn)
    kings = queries.chronology_kings(conn)
    syncs = queries.chronology_syncs(conn)
    numbers = queries.chronology_numbers(conn)
    verses = queries.verses_by_id(
        conn,
        [r["verse_id"] for rows in (events, kings, syncs, numbers) for r in rows
         if r["verse_id"] is not None],
    )  # fmt: skip
    born: dict[str, int] = {}
    died: dict[str, int] = {}
    names: dict[str, str] = {}
    for e in events:
        if not e["used"] or e["name"] is None:
            continue
        person, _, death = e["event"].partition(".")
        names[person] = e["name"]
        (died if death else born)[person] = e["year"]
    lives = [Life(person=p, name=names[p], born=y, died=died.get(p)) for p, y in born.items()]
    keep = ("conflicts", "known", "known_holds", "intervals", "agree", "rules", "rule_counts",
            "tolerance", "shuffles", "alpha", "expected", "p", "holds", "absolute", "division",
            "ends", "tradition", "digits", "digits_chapter", "digits_compare", "digits_ends",
            "digits_min")  # fmt: skip
    return {
        **{k: m[k] for k in keep},
        "events": [
            ChronEvent(**{**e, "verse": verses.get(e["verse_id"]), "used": bool(e["used"]),
                          "conflict": bool(e["conflict"])})  # fmt: skip
            for e in events
        ],
        "lives": lives,
        "kings": [ChronKing(**{**k, "verse": verses[k["verse_id"]], "short": bool(k["short"])})
                  for k in kings if k["verse_id"] in verses],  # fmt: skip
        "syncs": [
            ChronSync(**{**s, "verse": verses[s["verse_id"]],
                         "agrees": None if s["agrees"] is None else bool(s["agrees"])})  # fmt: skip
            for s in syncs
            if s["verse_id"] in verses
        ],
        "numbers": [Gen5Number(**{**n, "verse": verses[n["verse_id"]]}) for n in numbers
                    if n["verse_id"] in verses],  # fmt: skip
    }
