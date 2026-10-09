"""Shared phrases (DESIGN.md §16.1) and rare words shared over a few verses (§16.32)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import APIRouter, Response

from bsim.api import queries
from bsim.api.models import (
    Allusion,
    AllusionLemma,
    AllusionsResponse,
    PhrasePair,
    PhrasesResponse,
    UnitSummary,
)
from bsim.api.routes._common import (
    Conn,
    State,
    check_min,
    check_page,
    gold_link,
    unit_span,
    verse_or_404,
)

router = APIRouter()


@router.get("/allusions", response_model=AllusionsResponse)
def allusions(
    state: State,
    conn: Conn,
    known: bool | None = None,
    book: int | None = None,
    unit: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Passages sharing rare words over a few verses (DESIGN.md §16.32), strongest first, with
    both passages and the shared words marked; `known`: already found as a parallel."""
    check_page(state, limit, offset)
    total, rows = queries.allusions_page(conn, known, book, unit_span(conn, unit), limit, offset)
    ends = [v for r in rows for v in (r["a_start"], r["a_end"], r["b_start"], r["b_end"])]
    labels = queries.verse_labels(conn, ends)

    def span(first: int, last: int, lang: int) -> str:
        return f"{labels[first][lang]} – {labels[last][lang]}"

    items = []
    for r in rows:
        a = list(range(r["a_start"], r["a_end"] + 1))
        b = list(range(r["b_start"], r["b_end"] + 1))
        lemmas = json.loads(r["lemmas"])
        keys = {lem for lem, _ in lemmas}
        verses = queries.verses_by_id(conn, a + b)
        items.append(
            Allusion(
                **{k: r[k] for k in ("allusion_id", "a_start", "a_end", "b_start", "b_end")},
                **{k: r[k] for k in ("n_shared", "score", "q")},
                a_label=span(a[0], a[-1], 0),
                a_label_he=span(a[0], a[-1], 1),
                b_label=span(b[0], b[-1], 0),
                b_label_he=span(b[0], b[-1], 1),
                known=bool(r["known"]),
                lemmas=[AllusionLemma(lemma=lem, form=f) for lem, f in lemmas],
                a_verses=[verses[v] for v in a],
                b_verses=[verses[v] for v in b],
                a_marks=queries.lemma_marks(conn, a, keys),
                b_marks=queries.lemma_marks(conn, b, keys),
            )
        )
    return {
        "meta": state.meta.get("allusions") or {},
        "known": known,
        "book": book,
        "unit": unit,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
    }


def _phrase_pairs(
    conn: sqlite3.Connection, rows: list[dict[str, Any]], first: int | None = None
) -> list[PhrasePair]:
    """Phrase rows -> response items; `first` puts that verse on the `a` side."""
    flipped = [
        r
        if first is None or r["a"] == first
        else {**r, "a": r["b"], "b": r["a"], "a_words": r["b_words"], "b_words": r["a_words"]}
        for r in rows
    ]
    vids = [v for r in flipped for v in (r["a"], r["b"])]
    verses = queries.verses_by_id(conn, vids)
    units_ = queries.units_by_id(conn, [f"v:{v}" for v in vids])
    display: dict[tuple[int, int], int] = {
        (w["verse_id"], w["idx"]): w["display_idx"]
        for w in queries.words(conn, vids)
        if w["display_idx"] is not None
    }
    links = queries.verse_links(conn, [(r["a"], r["b"]) for r in flipped])

    def shown(vid: int, idxs: str) -> list[int]:
        return sorted({display[(vid, i)] for i in json.loads(idxs) if (vid, i) in display})

    return [
        PhrasePair(
            score=r["score"],
            n_tokens=r["n_tokens"],
            spread=r["spread"],
            a=UnitSummary(**units_[f"v:{r['a']}"]),
            b=UnitSummary(**units_[f"v:{r['b']}"]),
            a_verse=verses[r["a"]],
            b_verse=verses[r["b"]],
            a_display=shown(r["a"], r["a_words"]),
            b_display=shown(r["b"], r["b_words"]),
            link=gold_link(*links[(r["a"], r["b"])]) if (r["a"], r["b"]) in links else None,
        )
        for r in flipped
    ]


@router.get("/phrases/{verse_id}", response_model=list[PhrasePair])
def phrases_of(
    verse_id: int, state: State, conn: Conn, response: Response, limit: int = 50, offset: int = 0
) -> list[PhrasePair]:
    """The verses sharing an aligned phrase with this one, strongest first (this verse on the
    `a` side; at most `limit`, ≤ `serve.max_page`). `X-Total-Count` has the number of all."""
    verse_or_404(state, verse_id)
    check_page(state, limit, offset)
    rows = queries.phrases_of(conn, verse_id)
    response.headers["X-Total-Count"] = str(len(rows))
    return _phrase_pairs(conn, rows[offset : offset + limit], first=verse_id)


@router.get("/phrases", response_model=PhrasesResponse)
def phrases(
    state: State,
    conn: Conn,
    book: int | None = None,
    cross_book: bool = False,
    min_tokens: int = 3,
    max_spread: int | None = None,
    unit: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """The strongest shared phrases in the corpus (`max_spread`: hide recurring idioms;
    `unit`: phrases with a side in that unit's verses)."""
    check_page(state, limit, offset)
    check_min(min_tokens, "min_tokens")
    total, rows = queries.phrases_page(
        conn, book, cross_book, min_tokens, max_spread, limit, offset, unit_span(conn, unit)
    )
    return {
        "book": book,
        "unit": unit,
        "cross_book": cross_book,
        "min_tokens": min_tokens,
        "max_spread": max_spread,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": _phrase_pairs(conn, rows),
    }


# when several OSHB words share one display token, the more telling change is shown
