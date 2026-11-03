"""This week's parasha (DESIGN.md §11.1): the weekly reading of a Shabbat, in Israel or abroad,
with each parasha's haftarah."""

from __future__ import annotations

import json
from datetime import date as Date
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.common import UnitSummary
from bsim.api.models.week import WeekHaftarah, WeekParasha, WeekResponse
from bsim.api.routes._common import Conn, State
from bsim.api.week import reading

router = APIRouter()


@router.get("/week", response_model=WeekResponse)
def week(
    state: State, conn: Conn, date: Date | None = None, israel: bool = False
) -> dict[str, Any]:
    """The weekly reading of the Shabbat on or after `date` (default: today, the server's)."""
    asked = date or Date.today()
    r = reading(asked, israel, int(state.cfg["week"]["ahead"]))
    units = queries.parasha_units(conn)
    if len(units) != 54:
        raise HTTPException(status_code=503, detail="the parasha units are not in this build")
    picked = [units[i] for i in r.portions]
    haft = (
        queries.haftarot_of(conn, [u["unit_id"] for u in picked])
        if state.present(conn, "haftarot")
        else {}
    )
    parashot = []
    for u in picked:
        h = haft.get(u["unit_id"])
        parashot.append(
            WeekParasha(
                unit=UnitSummary(**u),
                haftarah=WeekHaftarah(
                    haft=h["haft"],
                    seph=h["seph"],
                    theme=h["theme"],
                    chapters=json.loads(h["chapters"]),
                    rank_fused=h["rank_fused"],
                )  # fmt: skip
                if h
                else None,
            )
        )
    return {
        "date": asked.isoformat(),
        "israel": israel,
        "shabbat": r.shabbat.isoformat(),
        "hebrew_he": r.hebrew_he,
        "hebrew_en": r.hebrew_en,
        "festival": r.festival,
        "reading_shabbat": r.reading_shabbat.isoformat() if r.reading_shabbat else None,
        "parashot": parashot,
        "prev": (r.shabbat - timedelta(weeks=1)).isoformat(),
        "next": (r.shabbat + timedelta(weeks=1)).isoformat(),
    }
