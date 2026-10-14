"""Psalms (DESIGN.md §16.42): the form of each psalm against Gunkel's genres, and the turn of the
lament."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models.psalms import (
    Psalm,
    PsalmKnownTurn,
    PsalmsListResponse,
    PsalmsResponse,
    PsalmTurn,
    PsalmVerse,
)
from bsim.api.routes._common import Conn, State, check_page, unit_span, unprocessable

router = APIRouter()
FEATURES = (
    "first_singular", "first_plural", "second", "imperative", "imperative_plural", "question",
    "distress", "praise",
)  # fmt: skip


@router.get("/psalms", response_model=PsalmsResponse)
def psalms(state: State, conn: Conn) -> dict[str, Any]:
    """The genre test (clusters of the form against Gunkel's genres), the checks named in
    advance, the turns scholarship names and the laments' turns against the hymns'."""
    meta = state.meta.get("psalms") or {}
    rows = (meta.get("known_turns") or {}).get("rows") or []
    ids = [r[k] for r in rows for k in ("verse_id", "turn_vid") if r.get(k) is not None]
    labels = queries.verse_labels(conn, ids)
    known = []
    for r in rows:
        if r.get("verse_id") not in labels:
            continue
        t = r.get("turn_vid")
        known.append(
            PsalmKnownTurn(
                verse_id=r["verse_id"],
                label=labels[r["verse_id"]][0],
                label_he=labels[r["verse_id"]][1],
                turn_vid=t,
                turn_label=labels[t][0] if t in labels else None,
                turn_label_he=labels[t][1] if t in labels else None,
                **{k: r.get(k) for k in ("p", "found", "chance")},
            )
        )
    return {"meta": meta, "known": known}


@router.get("/psalms/list", response_model=PsalmsListResponse)
def psalm_list(
    state: State,
    conn: Conn,
    genre: str | None = None,
    cluster: int | None = None,
    turned: bool = False,
    unit: str | None = None,
    sort: str = "chapter",
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Psalms in order (or the clearest turn first) with their form, genre, cluster, turn and the
    mood of each verse; `turned`: only those whose turn is above chance at `psalms.alpha`."""
    check_page(state, limit, offset)
    if sort not in queries.PSALM_SORTS:
        raise unprocessable(f"sort must be one of {', '.join(queries.PSALM_SORTS)}")
    alpha = state.cfg["psalms"]["alpha"]
    total, rows = queries.psalms_page(
        conn, genre, cluster, alpha if turned else None, unit_span(conn, unit), sort, limit,
        offset,
    )  # fmt: skip
    verses = queries.psalm_verses(conn, [r["unit_id"] for r in rows])
    labels = queries.verse_labels(conn, [r["turn_vid"] for r in rows if r["turn_vid"] is not None])
    items = []
    for r in rows:
        t = r["turn_vid"]
        items.append(
            Psalm(
                unit_id=r["unit_id"],
                label=r["label_en"],
                label_he=r["label_he"],
                chapter=r["chapter"],
                genre=r["genre"],
                cluster=r["cluster"],
                words=r["words"],
                features={f: r[f] for f in FEATURES},
                turn=PsalmTurn(
                    verse_id=t, verse=r["turn_verse"], label=labels[t][0], label_he=labels[t][1],
                    stat=r["turn_stat"], p=r["turn_p"], before=r["before"], after=r["after"],
                ) if t is not None and t in labels else None,  # fmt: skip
                mood=[PsalmVerse(**{k: v[k] for k in ("verse", "words", "distress", "praise")})
                      for v in verses.get(r["unit_id"], [])],  # fmt: skip
            )
        )
    return {"genre": genre, "cluster": cluster, "turned": turned, "unit": unit, "sort": sort,
            "total": total, "offset": offset, "limit": limit, "items": items}  # fmt: skip
