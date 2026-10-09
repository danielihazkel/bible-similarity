"""Verses that say they quote or fulfil another (DESIGN.md §16.31): the summary, the book graph
and every citation with its source and the candidates."""

from __future__ import annotations

import json
from typing import Any, Literal

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models import (
    Citation,
    CitationBook,
    CitationCandidate,
    CitationListResponse,
    CitationsResponse,
)
from bsim.api.routes._common import Conn, State, check_page, unit_span

router = APIRouter()


@router.get("/citations", response_model=CitationsResponse)
def citations(state: State, conn: Conn) -> dict[str, Any]:
    """Counts by family against random verses, the gold check and the book graph."""
    return {
        "meta": state.meta.get("citations") or {},
        "books": [CitationBook(**r) for r in queries.citation_books(conn)],
    }


@router.get("/citations/list", response_model=CitationListResponse)
def citation_list(
    state: State,
    conn: Conn,
    family: Literal["written", "word", "command"] | None = None,
    resolved: bool | None = None,
    book: int | None = None,
    unit: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Citations in reading order with their source; `unit`: citing from it or resolved into it."""
    check_page(state, limit, offset)
    total, rows = queries.citations_page(
        conn, family, resolved, book, unit_span(conn, unit), limit, offset
    )
    cands = {r["cite_id"]: json.loads(r["candidates"]) for r in rows}
    vids = {r["verse_id"] for r in rows} | {
        r["target_vid"] for r in rows if r["target_vid"] is not None
    }
    verses = queries.verses_by_id(conn, vids)
    labels = queries.verse_labels(conn, vids | {c for cs in cands.values() for c, _ in cs})
    items = []
    for r in rows:
        t = r["target_vid"]
        items.append(
            Citation(
                **{k: r[k] for k in ("cite_id", "family", "verse_id", "book_id", "formula")},
                **{k: r[k] for k in ("score", "pct", "gold_rank")},
                label=labels[r["verse_id"]][0],
                label_he=labels[r["verse_id"]][1],
                verse=verses[r["verse_id"]],
                target=verses.get(t) if t is not None else None,
                target_label=labels[t][0] if t is not None else None,
                target_label_he=labels[t][1] if t is not None else None,
                resolved=bool(r["resolved"]),
                candidates=[
                    CitationCandidate(
                        verse_id=c, label=labels[c][0], label_he=labels[c][1], score=s
                    )
                    for c, s in cands[r["cite_id"]]
                ],
                named=r["gold"] is not None,
            )
        )
    return {
        "family": family,
        "resolved": resolved,
        "book": book,
        "unit": unit,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
    }
