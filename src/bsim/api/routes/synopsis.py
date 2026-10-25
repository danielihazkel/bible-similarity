"""Parallel sequences chained into synopses of three or more witnesses (DESIGN.md §16.74)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api import synopsis as syn
from bsim.api.app import ServeState
from bsim.api.models.synopsis import (
    SynopsesResponse,
    SynopsisCell,
    SynopsisColumn,
    SynopsisDetail,
    SynopsisSummary,
)
from bsim.api.routes._common import Conn, State, span_label, unprocessable
from bsim.api.routes.parallels import OP_RANK, diff_marks

router = APIRouter()


def _synopses(state: ServeState, conn: sqlite3.Connection) -> list[syn.Synopsis]:
    cached = state.synopsis_cache.get("all")
    if cached is None:
        sc = state.cfg["serve"]["synopsis"]
        rows = queries.synopsis_chains(conn, sc["max_q"])
        for r in rows:
            r["pairs"] = json.loads(r["pairs"])
        chains = syn.chains_of(rows, sc["max_q"], sc["same_chapter"])
        cached = syn.synopses(chains, sc["join"], sc["min_chains"])
        state.synopsis_cache.put("all", cached)
    return cached


def _summaries(conn: sqlite3.Connection, items: list[syn.Synopsis]) -> list[SynopsisSummary]:
    ends = [v for s in items for col in s.columns for p in col for v in (p.start, p.end)]
    labels = queries.verse_labels(conn, ends)

    def label(col: list[syn.Passage], lang: int) -> str:
        """The column's passages, the book named once: "Psalms 105:1–15 + 96:2–12"."""
        first, *rest = (span_label(labels, p.start, p.end, lang) for p in col)
        out = [first]
        for other in rest:
            common = 0
            while common < min(len(first), len(other)) and first[common] == other[common]:
                common += 1
            out.append(other[first.rfind(" ", 0, common) + 1 :])
        return " + ".join(out)

    return [
        SynopsisSummary(
            syn_id=s.syn_id,
            seq_ids=s.seq_ids,
            columns=[
                SynopsisColumn(book_id=col[0].book, label=label(col, 0), label_he=label(col, 1))
                for col in s.columns
            ],
            n_rows=len(s.rows),
            n_aligned=sum(1 for r in s.rows if sum(v is not None for v in r) > 1),
            breaks=s.breaks,
            dropped=s.dropped,
        )
        for s in items
    ]


@router.get("/synopses", response_model=SynopsesResponse)
def synopses(state: State, conn: Conn) -> dict[str, Any]:
    """Every synopsis, in order of its strongest chain."""
    return {
        "max_q": state.cfg["serve"]["synopsis"]["max_q"],
        "items": _summaries(conn, _synopses(state, conn)),
    }


@router.get("/synopses/{syn_id}", response_model=SynopsisDetail)
def synopsis(syn_id: int, state: State, conn: Conn, base: int = 0) -> dict[str, Any]:
    """One synopsis row by row, every column's verse marked against the `base` column's (cached)."""
    found = [s for s in _synopses(state, conn) if s.syn_id == syn_id]
    if not found:
        raise HTTPException(status_code=404, detail=f"unknown synopsis {syn_id}")
    s = found[0]
    if not 0 <= base < len(s.columns):
        raise unprocessable(f"base must be a column, 0 to {len(s.columns) - 1}")
    key = (syn_id, base)
    cached = state.synopsis_cache.get(key)
    if cached is None:
        cached = _detail(s, base, state, conn)
        state.synopsis_cache.put(key, cached)
    return cached


def _detail(
    s: syn.Synopsis, base: int, state: ServeState, conn: sqlite3.Connection
) -> dict[str, Any]:
    min_shared = state.cfg["diffs"]["min_shared"]
    rows: list[list[SynopsisCell]] = []
    for verses, flags in zip(s.rows, s.reordered, strict=True):
        cells = [SynopsisCell(verse=v, reordered=f) for v, f in zip(verses, flags, strict=True)]
        b = verses[base]
        for k, v in enumerate(verses):
            if b is None or v is None or k == base:
                continue
            bm, vm, _, shared = diff_marks(state, conn, b, v)
            cells[k].marks = vm
            cells[k].loose = shared < min_shared
            own = cells[base].marks
            for di, op in bm.items():
                if di not in own or OP_RANK[op] < OP_RANK[own[di]]:
                    own[di] = op
        rows.append(cells)
    vids = [v for r in s.rows for v in r if v is not None]
    return {
        "synopsis": _summaries(conn, [s])[0],
        "base": base,
        "rows": rows,
        "verses": queries.verses_by_id(conn, vids),
    }
