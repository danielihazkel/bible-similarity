"""The Masorah's counts on our text (DESIGN.md §16.55): the middle letter, words and verse of the
Torah and the other middles named, against ours; the verse totals of the Masorah's books and the
sections against ours, with the reason a book differs; every book counted in both texts."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models.common import VerseLabel
from bsim.api.models.masorah import MasorahBook, MasorahMiddle, MasorahResponse, MasorahTotal
from bsim.api.routes._common import Conn, State

router = APIRouter()


@router.get("/masorah", response_model=MasorahResponse)
def masorah(state: State, conn: Conn) -> dict[str, Any]:
    """The middles against ours, the totals against ours and every book's counts."""
    t = queries.masorah_tables(conn)
    verses = queries.verses_by_id(
        conn, [v for r in t["middles"] for v in (r["trad_vid"], r["mid_vid"])]
    )
    refs = [v for r in t["totals"] for v in (r["ref_first"], r["ref_last"]) if v is not None]
    labels = queries.verse_labels(conn, refs)

    def label(vid: int | None) -> VerseLabel | None:
        if vid is None or vid not in labels:
            return None
        return VerseLabel(verse_id=vid, label_en=labels[vid][0], label_he=labels[vid][1])

    return {
        "meta": state.meta.get("masorah") or {},
        "middles": [
            MasorahMiddle(
                trad_verse=verses[r["trad_vid"]],
                mid_verse=verses[r["mid_vid"]],
                **{k: v for k, v in r.items() if k not in ("trad_vid", "mid_vid", "ref")},
            )
            for r in t["middles"]
            if r["trad_vid"] in verses and r["mid_vid"] in verses
        ],
        "totals": [
            MasorahTotal(
                ref_first=label(r["ref_first"]),
                ref_last=label(r["ref_last"]),
                also=json.loads(r["also"]),
                **{k: v for k, v in r.items() if k not in ("ref", "ref_first", "ref_last", "also")},
            )
            for r in t["totals"]
        ],
        "books": [MasorahBook(**r) for r in t["books"]],
    }
