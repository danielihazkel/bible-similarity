"""Where the text turns and where it is divided (DESIGN.md §16.29): the tests, the lists of
unmarked turns, chapters cut through cohesive text and quiet breaks, and a book's curve."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models import (
    SegmentBook,
    SegmentCurve,
    SegmentGap,
    SegmentGapsResponse,
    SegmentPoint,
    SegmentsResponse,
)
from bsim.api.routes._common import Conn, State, check_page, unit_span

router = APIRouter()


@router.get("/segments", response_model=SegmentsResponse)
def segments(state: State, conn: Conn) -> dict[str, Any]:
    """The divisions against the text's cohesion: tests, contrasts and per-book agreement."""
    return {
        "meta": state.meta.get("segments") or {},
        "books": [SegmentBook(**r) for r in queries.segment_books(conn)],
    }


@router.get("/segments/gaps", response_model=SegmentGapsResponse)
def segment_gaps(
    state: State,
    conn: Conn,
    kind: Literal["turn", "cut", "quiet"] | None = None,
    book: int | None = None,
    unit: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Unmarked turns (sharpest first), chapter starts and paragraph breaks inside cohesive
    text (most cohesive first); `unit`: those at or inside that unit, in reading order."""
    check_page(state, limit, offset)
    total, rows = queries.segment_gaps_page(conn, kind, book, unit_span(conn, unit), limit, offset)
    vids = [v for r in rows for v in (r["verse_id"] - 1, r["verse_id"])]
    verses = queries.verses_by_id(conn, vids)
    labels = queries.verse_labels(conn, [r["verse_id"] for r in rows])
    return {
        "kind": kind,
        "book": book,
        "unit": unit,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            SegmentGap(
                **{k: r[k] for k in ("verse_id", "book_id", "score", "lex", "sem", "mam", "oshb")},
                label=labels[r["verse_id"]][0],
                label_he=labels[r["verse_id"]][1],
                chapter=bool(r["chapter"]),
                seam=bool(r["seam"]),
                kind=r["kind"],
                verses=[verses[r["verse_id"] - 1], verses[r["verse_id"]]],
            )
            for r in rows
        ],
    }


@router.get("/segments/book/{book_id}", response_model=SegmentCurve)
def segment_curve(book_id: int, conn: Conn) -> dict[str, Any]:
    """Every gap of one book with its score and divisions, and the book's agreement rows."""
    points = queries.segment_curve(conn, book_id)
    if (
        not points
        and not conn.execute("SELECT 1 FROM books WHERE book_id = ?", (book_id,)).fetchone()
    ):
        raise HTTPException(status_code=404, detail=f"unknown book {book_id}")
    return {
        "book_id": book_id,
        "points": [
            SegmentPoint(
                **{**p, "chapter_start": bool(p["chapter_start"]), "seam": bool(p["seam"])}
            )
            for p in points
        ],
        "agreement": [SegmentBook(**r) for r in queries.segment_books(conn, book_id)],
    }
