"""A lemma's senses and uses across the canon (DESIGN.md §16.23): the lemmas whose dictionary
senses or contextual uses differ most between corpus groups, and one lemma's breakdown."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.app import ServeState
from bsim.api.models import (
    LemmaForm,
    LemmaSense,
    LemmaSensesResponse,
    LemmaShift,
    SenseExample,
    ShiftsResponse,
)
from bsim.api.routes._common import Conn, State, check_page, unprocessable

router = APIRouter()


def _group_order(state: ServeState) -> list[str]:
    return list((state.meta.get("senses") or {}).get("groups") or {})


def _shift(r: dict[str, Any], he: dict[str, str]) -> LemmaShift:
    return LemmaShift(
        **{k: r[k] for k in LemmaShift.model_fields if k in r and k not in ("groups", "he_lemma")},
        he_lemma=he.get(r["lemma"], r["lemma"]),
        groups=json.loads(r["groups"]),
    )


@router.get("/shifts", response_model=ShiftsResponse)
def shifts(
    state: State,
    conn: Conn,
    by: str = "sense",
    max_q: float | None = 0.05,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Lemmas ranked by how much their dictionary senses (`by=sense`) or contextual uses
    (`by=use`) depend on the corpus group (MI above its shuffled mean), at q ≤ `max_q`."""
    if by not in ("sense", "use"):
        raise unprocessable(f"by must be sense or use, not {by!r}")
    if max_q is not None and not 0 < max_q <= 1:
        raise unprocessable("max_q must be in (0, 1]")
    check_page(state, limit, offset)
    total, rows = queries.shifts_page(conn, by, max_q, limit, offset)
    he = queries.gloss(conn, (r["lemma"] for r in rows))
    meta = state.meta.get("senses") or {}
    return {
        "by": by,
        "max_q": max_q,
        "group_order": _group_order(state),
        "nmi_mean": meta.get("nmi_mean"),
        "nmi_null_mean": meta.get("nmi_null_mean"),
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [_shift(r, he) for r in rows],
    }


@router.get("/lemma/{lemma}/senses", response_model=LemmaSensesResponse)
def lemma_senses(lemma: str, state: State, conn: Conn) -> dict[str, Any]:
    """One lemma's SDBH meanings and contextual-use clusters by corpus group, with Hebrew
    collocates and example occurrences; empty when the lemma was not compared."""
    row = queries.lemma_shift(conn, lemma)
    senses = queries.lemma_senses(conn, lemma)
    examples = {
        (s["kind"], s["sense"]): [tuple(e) for e in json.loads(s["examples"])] for s in senses
    }
    vids = sorted({v for ex in examples.values() for v, _ in ex})
    verses = queries.verses_by_id(conn, vids)
    labels = queries.verse_labels(conn, vids)
    display = {(w["verse_id"], w["idx"]): w["display_idx"] for w in queries.words(conn, vids)}
    cols = {s["sense"]: json.loads(s["collocates"]) for s in senses}
    he = queries.gloss(conn, [lemma, *(c for cs in cols.values() for c in cs)])

    def sense(s: dict[str, Any]) -> LemmaSense:
        return LemmaSense(
            kind=s["kind"],
            sense=s["sense"],
            n=s["n"],
            groups=json.loads(s["groups"]),
            collocates=[LemmaForm(lemma=c, he_lemma=he.get(c, c)) for c in cols[s["sense"]]],
            examples=[
                SenseExample(
                    verse=verses[v],
                    label_en=labels[v][0],
                    label_he=labels[v][1],
                    display_idx=display.get((v, i)),
                )
                for v, i in examples[(s["kind"], s["sense"])]
            ],
            domains=json.loads(s["domains"]),
        )

    return {
        "lemma": lemma,
        "he_lemma": he.get(lemma, lemma),
        "group_order": _group_order(state),
        "shift": _shift(row, he) if row else None,
        "uses": [sense(s) for s in senses if s["kind"] == "use"],
        "senses": [sense(s) for s in senses if s["kind"] == "sdbh"],
    }
