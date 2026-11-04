"""Rabbinic reception (DESIGN.md §16.77): where the Mishnah, the Tosefta and the two Talmuds cite
the Bible, per book, chapter and verse, and the checks."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models.reception import (
    Corpus,
    KnownCitation,
    ReceptionBook,
    ReceptionChapter,
    ReceptionCitation,
    ReceptionCitationsResponse,
    ReceptionCounts,
    ReceptionResponse,
    ReceptionVerse,
    ReceptionVersesResponse,
)
from bsim.api.routes._common import (
    BookFilter,
    Conn,
    State,
    check_page,
    stage,
    stage_missing,
    unit_or_404,
)

router = APIRouter()

KEEP = ("citations", "verses_cited", "by_corpus", "passages", "dropped_long", "legal_verses",
        "narrative_verses", "ratios", "law_p", "law_holds", "gap", "gap_p", "gap_holds",
        "known_holds", "max_span", "shifts", "alpha")  # fmt: skip
COUNTS = ("mishnah", "tosefta", "bavli", "yerushalmi", "total")


@router.get("/reception", dependencies=[stage("reception")], response_model=ReceptionResponse)
def reception(state: State, conn: Conn) -> dict[str, Any]:
    """The citations per book and chapter, and the checks (503: the stage did not run)."""
    m = state.meta.get("reception")
    if not m:
        raise stage_missing("reception")
    known = m.get("known") or []
    verses = queries.verses_by_id(conn, [k["verse_id"] for k in known])
    return {
        **{k: m[k] for k in KEEP},
        "known": [
            KnownCitation(
                cite=k["cite"], ref=k["ref"], verse=verses.get(k["verse_id"]), found=k["found"]
            )
            for k in known
        ],
        "books": [ReceptionBook(**r) for r in queries.reception_books(conn)],
        "chapters": [ReceptionChapter(**r) for r in queries.reception_chapters(conn)],
    }


@router.get(
    "/reception/verses", dependencies=[stage("reception")], response_model=ReceptionVersesResponse
)
def reception_verses(
    state: State,
    conn: Conn,
    corpus: Corpus | None = None,
    book: BookFilter = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """The verses most cited (by one corpus, or all), in a book or the whole canon."""
    check_page(state, limit, offset)
    total, rows = queries.reception_verses_page(conn, corpus, book, limit, offset)
    verses = queries.verses_by_id(conn, [r["verse_id"] for r in rows])
    items = [
        ReceptionVerse(verse=verses[r["verse_id"]], **{k: r[k] for k in COUNTS})
        for r in rows
        if r["verse_id"] in verses
    ]
    return {"corpus": corpus, "book": book, "total": total, "offset": offset, "limit": limit,
            "items": items}  # fmt: skip


@router.get(
    "/reception/citations",
    dependencies=[stage("reception")],
    response_model=ReceptionCitationsResponse,
)
def reception_citations(
    unit: str,
    state: State,
    conn: Conn,
    corpus: Corpus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """The rabbinic passages citing a unit's verses, verse by verse (404: unknown unit)."""
    check_page(state, limit, offset)
    u = unit_or_404(conn, unit)
    first, last = u["start_verse_id"], u["end_verse_id"]
    total, rows = queries.reception_citations_page(conn, first, last, corpus, limit, offset)
    verses = queries.verses_by_id(conn, [r["verse_id"] for r in rows])
    items = [
        ReceptionCitation(
            **{k: r[k] for k in ("corpus", "title", "cite", "cite_he", "url", "verse_id")},
            ref=verses[r["verse_id"]]["ref"],
            ref_he=verses[r["verse_id"]]["ref_he"],
        )
        for r in rows
        if r["verse_id"] in verses
    ]
    return {
        "unit_id": u["unit_id"],
        "corpus": corpus,
        "counts": ReceptionCounts(**queries.reception_counts(conn, first, last)),
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
    }
