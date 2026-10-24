"""Haftarot (DESIGN.md §16.69): each parasha's haftarah, where the systems rank it among the
chapters of the Prophets, the parasha's own first chapters, and the checks."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.haftarot import Haftarah, HaftarahChapter, HaftarotResponse
from bsim.api.routes._common import Conn, State

router = APIRouter()


@router.get("/haftarot", response_model=HaftarotResponse)
def haftarot(state: State, conn: Conn) -> dict[str, Any]:
    """Every parasha with its haftarah's ranks and its first chapters (404: the stage did not
    run)."""
    m = state.meta.get("haftarot")
    if not m:
        raise HTTPException(status_code=404, detail="the haftarot were not computed")
    rows = queries.haftarot(conn)
    lists = queries.haftarah_lists(conn)
    gold = {r["parasha"]: json.loads(r["chapters"]) for r in rows}
    units = queries.units_by_id(
        conn, [*gold, *{c for g in gold.values() for c in g}, *{r["chapter"] for r in lists}]
    )
    top: dict[str, list[HaftarahChapter]] = {}
    for r in lists:
        u = units.get(r["chapter"])
        if u is None:
            continue
        top.setdefault(r["parasha"], []).append(
            HaftarahChapter(rank=r["rank"], unit_id=r["chapter"], label_en=u["label_en"],
                            label_he=u["label_he"], lex_rank=r["lex_rank"],
                            sem_rank=r["sem_rank"], haftarah=bool(r["haftarah"]))  # fmt: skip
        )
    parashot = []
    for r in rows:
        u = units.get(r["parasha"])
        chapters = [c for c in gold[r["parasha"]] if c in units]
        parashot.append(
            Haftarah(
                parasha=r["parasha"],
                num=r["num"],
                label_en=u["label_en"] if u else r["name"],
                label_he=u["label_he"] if u else r["name"],
                theme=r["theme"],
                haft=r["haft"],
                seph=r["seph"],
                chapters=chapters,
                chapter_labels=[units[c]["label_en"] for c in chapters],
                chapter_labels_he=[units[c]["label_he"] for c in chapters],
                rank_lexical=r["rank_lexical"],
                rank_semantic=r["rank_semantic"],
                rank_fused=r["rank_fused"],
                pct=r["pct"],
                known=bool(r["known"]),
                top=top.get(r["parasha"], []),
            )
        )
    keep = ("candidates", "thematic", "claim_mode", "shuffles", "alpha", "list", "thematic_pct",
            "shuffled_pct", "p", "holds", "calendar_pct", "difference", "calendar_p",
            "calendar_holds", "modes", "known", "known_rank", "known_holds")  # fmt: skip
    return {**{k: m[k] for k in keep}, "parashot": parashot}
