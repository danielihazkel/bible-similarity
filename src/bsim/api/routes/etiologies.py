"""Names given in the text and the words that explain them (DESIGN.md §16.66): every naming
found by the formula, its best echo, its rank among the explanations, and the two checks."""

from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.etiologies import EtiologiesResponse, Naming
from bsim.api.routes._common import Conn, State

router = APIRouter()


def _num(v: Any) -> float | None:
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


@router.get("/etiologies", response_model=EtiologiesResponse)
def etiologies(state: State, conn: Conn) -> dict[str, Any]:
    """Every naming with its verse, its name and the word that echoes it (404: the stage did
    not run)."""
    m = state.meta.get("etiologies")
    if not m:
        raise HTTPException(status_code=404, detail="the naming etiologies were not computed")
    rows = queries.etiologies(conn)
    verses = queries.verses_by_id(conn, [r["verse_id"] for r in rows])
    namings = [
        Naming(
            naming=r["naming"],
            unit_id=f"c:{verses[r['verse_id']]['book_id']}:{verses[r['verse_id']]['chapter']}",
            verse=verses[r["verse_id"]],
            name=r["name"],
            kind=r["kind"],
            name_first=r["name_first"],
            name_last=r["name_last"],
            echo_word=r["echo_word"],
            echo_disp=r["echo_disp"],
            words=r["words"],
            score=r["score"],
            chance=_num(r["chance"]),
            rank_p=_num(r["rank_p"]),
            p=_num(r["p"]),
            q=_num(r["q"]),
            known=bool(r["known"]),
        )
        for r in rows
        if r["verse_id"] in verses
    ]
    keep = ("places", "explained", "mean_own", "mean_null", "p", "shuffles", "alpha", "holds",
            "leads", "known", "known_found", "known_echo", "known_rank", "known_share",
            "known_holds")  # fmt: skip
    return {"namings": namings, **{k: m[k] for k in keep}}
