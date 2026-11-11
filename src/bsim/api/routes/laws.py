"""The law codes side by side (DESIGN.md §16.93, D155)."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.laws import (
    LawCode,
    LawForm,
    LawList,
    LawPairOrder,
    LawPairs,
    LawsResponse,
    LawSynopsis,
)
from bsim.api.routes._common import Conn, State, check_page, stage, stage_missing, unit_span

router = APIRouter()

OPS = ("same", "spelling", "form", "substitution", "omitted", "added", "moved")


def _meta(state: State) -> dict[str, Any]:
    m = state.meta.get("laws")
    if not m:
        raise stage_missing("laws")
    return m


def _laws(conn: sqlite3.Connection, ids: list[int]) -> dict[int, dict[str, Any]]:
    """Laws with their labels and the count of their matched pairs."""
    rows = queries.laws_by_id(conn, ids)
    ends = [v for r in rows.values() for v in (r["first_vid"], r["last_vid"])]
    labels = queries.verse_labels(conn, ends)
    out = {}
    for i, r in rows.items():
        out[i] = {
            **{k: r[k] for k in ("law_id", "code", "unit_id", "book_id", "first_vid", "last_vid",
                                 "n_verses", "form", "address", "pairs")},
            "casuistic": bool(r["casuistic"]), "apodictic": bool(r["apodictic"]),
            "first_label": labels[r["first_vid"]][0], "last_label": labels[r["last_vid"]][0],
            "first_label_he": labels[r["first_vid"]][1], "last_label_he": labels[r["last_vid"]][1],
        }  # fmt: skip
    return out


def _span(labels: dict[int, tuple[str, str]], a: int, b: int, he: int) -> str:
    return labels[a][he] if a == b else f"{labels[a][he]} – {labels[b][he]}"


def _pairs(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    laws = _laws(conn, sorted({x for r in rows for x in (r["a"], r["b"])}))
    ends = [r[k] for r in rows for k in ("a_first", "a_last", "b_first", "b_last")]
    labels = queries.verse_labels(conn, ends)
    return [
        {
            **{
                k: r[k]
                for k in (
                    "pair_id",
                    "links",
                    "score",
                    "a_first",
                    "a_last",
                    "b_first",
                    "b_last",
                    "kept",
                    "known",
                )
            },
            "a": laws[r["a"]],
            "b": laws[r["b"]],
            "a_span": _span(labels, r["a_first"], r["a_last"], 0),
            "b_span": _span(labels, r["b_first"], r["b_last"], 0),
            "a_span_he": _span(labels, r["a_first"], r["a_last"], 1),
            "b_span_he": _span(labels, r["b_first"], r["b_last"], 1),
            "ops": {o: r[o] for o in OPS},
        }  # fmt: skip
        for r in rows
    ]


@router.get("/laws", dependencies=[stage("laws")], response_model=LawsResponse)
def laws(state: State, conn: Conn) -> dict[str, Any]:
    """Each code's laws by form and address, the matched pairs, the pairs named in advance."""
    m = _meta(state)
    keep = ("laws", "pairs", "linked", "top_k", "min_links", "forms", "known", "known_found",
            "known_total", "known_holds", "known_strict", "kept_mean")  # fmt: skip
    return {**{k: m[k] for k in keep}, "codes": queries.law_codes(conn)}


@router.get("/laws/list", dependencies=[stage("laws")], response_model=LawList)
def law_list(
    state: State,
    conn: Conn,
    code: LawCode | None = None,
    form: LawForm | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """A page of laws in canon order, with their form and address."""
    _meta(state)
    check_page(state, limit, offset)
    total, ids = queries.laws_page(conn, code, form, limit, offset)
    rows = _laws(conn, ids)
    return {"total": total, "offset": offset, "limit": limit, "items": [rows[i] for i in ids],
            "code": code, "form": form}  # fmt: skip


@router.get("/laws/pairs", dependencies=[stage("laws")], response_model=LawPairs)
def law_pairs(
    state: State,
    conn: Conn,
    order: LawPairOrder = "score",
    code: LawCode | None = None,
    known: bool = False,
    law: int | None = None,
    unit: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """A page of matched pairs: the strongest first or in canon order."""
    _meta(state)
    check_page(state, limit, offset)
    span = unit_span(conn, unit)
    total, rows = queries.law_pairs_page(conn, order, code, known, law, span, limit, offset)
    return {"total": total, "offset": offset, "limit": limit, "items": _pairs(conn, rows),
            "order": order, "code": code}  # fmt: skip


@router.get("/laws/pair/{pair_id}", dependencies=[stage("laws")], response_model=LawSynopsis)
def law_pair(pair_id: int, state: State, conn: Conn) -> dict[str, Any]:
    """One matched pair side by side: the aligned span of each law, its words marked."""
    _meta(state)
    row = queries.law_pair(conn, pair_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no law pair {pair_id}")
    cap = state.cfg["serve"]["laws"]["max_verses"]
    marks: dict[tuple[str, int], dict[str, str]] = {}
    for mk in queries.law_marks(conn, pair_id):
        marks.setdefault((mk["side"], mk["verse_id"]), {})[str(mk["display_idx"])] = mk["op"]
    sides = {}
    for side in ("a", "b"):
        first, last = row[f"{side}_first"], row[f"{side}_last"]
        vids = list(range(first, min(last, first + cap - 1) + 1))
        verses = queries.verses_by_id(conn, vids)
        sides[side] = [
            {"verse": verses[v], "marks": marks.get((side, v), {})} for v in vids if v in verses
        ]
    return {"pair": _pairs(conn, [row])[0], **sides}
