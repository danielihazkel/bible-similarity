"""BHSA clauses and phrases of a unit, verses built the same way, and who speaks where
(DESIGN.md §16.26)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models import (
    ClauseInfo,
    ClauseSegment,
    SpeakerInfo,
    SpeechBook,
    SpeechBookResponse,
    SpeechChapter,
    SpeechResponse,
    SyntaxNeighbor,
    UnitSummary,
    UnitSyntax,
    VerseSyntax,
)
from bsim.api.routes._common import Conn, State, unit_or_404, unprocessable
from bsim.data.lexicon import strong_key

router = APIRouter()
# a word in a conjunction phrase and another phrase (ויאמר: ו + the predicate) shows the other
MINOR = ("Conj",)
SHARES = ("narration", "speech", "discourse", "divine", "attributed", "n_words")


def segments(
    words: list[int], phrases: list[dict[str, Any]], surface: dict[int, str]
) -> list[ClauseSegment]:
    """A clause's words grouped into runs of the same phrase, in word order."""
    of_word: dict[int, dict[str, Any]] = {}
    for p in phrases:
        for w in p["words"]:
            if w not in of_word or of_word[w]["function"] in MINOR:
                of_word[w] = p
    out: list[ClauseSegment] = []
    last = None
    for w in words:
        p = of_word.get(w)
        key = p["phrase"] if p else None
        text = surface.get(w, "")
        if out and key == last:
            out[-1].text += " " + text
        else:
            out.append(
                ClauseSegment(
                    function=p["function"] if p else "", typ=p["typ"] if p else "", text=text
                )
            )
        last = key
    return out


def _divine(state: State, lemma: str | None) -> bool:
    return lemma is not None and strong_key(lemma) in state.cfg["syntax"]["divine"]


@router.get("/syntax/{unit_id}", response_model=UnitSyntax)
def unit_syntax(unit_id: str, state: State, conn: Conn) -> dict[str, Any]:
    """The unit's clauses with their phrases and speakers; for a verse, the verses built the same
    way (`syntax.system`)."""
    u = unit_or_404(conn, unit_id)
    first, last = u["start_verse_id"], u["end_verse_id"]
    if u["n_verses"] > state.cfg["serve"]["max_compare_verses"]:
        raise unprocessable(
            f"{unit_id} is longer than {state.cfg['serve']['max_compare_verses']} verses"
        )
    surf = queries.surfaces(conn, first, last)
    by_clause: dict[int, list[dict[str, Any]]] = {}
    for p in queries.syntax_phrases_of(conn, first, last):
        by_clause.setdefault(p["clause"], []).append({**p, "words": json.loads(p["words"])})
    by_verse: dict[int, list[ClauseInfo]] = {}
    for c in queries.clauses_of(conn, first, last):
        v = c["verse_id"]
        words = json.loads(c["words"])
        by_verse.setdefault(v, []).append(
            ClauseInfo(
                **{k: c[k] for k in ("typ", "kind", "txt", "rela", "speaker", "speaker_he")},
                speaker_source=c["speaker_source"],
                speech=c["txt"].endswith("Q"),
                divine=_divine(state, c["speaker"]),
                segments=segments(
                    words,
                    by_clause.get(c["clause"], []),
                    {i: surf[v, i] for i in words if (v, i) in surf},
                ),
            )
        )
    labels = queries.verses_by_id(conn, list(by_verse))
    verses = [
        VerseSyntax(verse_id=v, ref=labels[v]["ref"], ref_he=labels[v]["ref_he"], clauses=cl)
        for v, cl in sorted(by_verse.items())
    ]
    neighbors = []
    if u["unit_type"] == "verse":
        rows = queries.syntax_neighbors(conn, first)
        units = queries.units_by_id(conn, [f"v:{r['tgt']}" for r in rows])
        texts = queries.previews(
            conn, [r["tgt"] for r in rows], state.cfg["serve"]["preview_chars"]
        )
        neighbors = [
            SyntaxNeighbor(
                unit=UnitSummary(**units[f"v:{r['tgt']}"]),
                score=r["score"],
                preview=texts.get(r["tgt"], ""),
            )
            for r in rows
            if f"v:{r['tgt']}" in units
        ]
    return {"verses": verses, "neighbors": neighbors}


def _speakers(state: State, rows: list[dict[str, Any]]) -> list[SpeakerInfo]:
    return [
        SpeakerInfo(
            **{k: r[k] for k in ("lemma", "he", "n_words", "n_explicit")},
            divine=_divine(state, r["lemma"]),
        )
        for r in rows
    ]


@router.get("/speech", response_model=SpeechResponse)
def speech(state: State, conn: Conn) -> dict[str, Any]:
    """Narration, speech and its speakers per book."""
    top = state.cfg["syntax"]["speech_speakers"]
    by_book: dict[int, list[dict[str, Any]]] = {}
    for r in queries.speakers(conn):
        by_book.setdefault(r["book_id"], []).append(r)
    return {
        "meta": state.meta.get("syntax") or {},
        "books": [
            SpeechBook(
                book_id=b["book_id"],
                **{k: b[k] for k in SHARES},
                speakers=_speakers(state, by_book.get(b["book_id"], [])[:top]),
            )
            for b in queries.speech_books(conn)
        ],
    }


@router.get("/speech/book/{book_id}", response_model=SpeechBookResponse)
def speech_book(book_id: int, state: State, conn: Conn) -> dict[str, Any]:
    """A book's chapters and every speaker in it."""
    chapters = queries.speech_chapters(conn, book_id)
    if not chapters:
        raise HTTPException(status_code=404, detail=f"no speech data for book {book_id}")
    return {
        "book_id": book_id,
        "chapters": [
            SpeechChapter(unit_id=c["unit_id"], chapter=c["chapter"], **{k: c[k] for k in SHARES})
            for c in chapters
        ],
        "speakers": _speakers(state, queries.speakers(conn, book_id)),
    }
