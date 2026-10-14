"""Pattern search (DESIGN.md §16.46): a query over the words' lemmas, roots, morphology and
syntax, matched inside each verse; the verses found, with each match's words marked."""

from __future__ import annotations

from typing import Any

import numpy as np
from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models.patterns import PatternBook, PatternMatch, PatternResponse, PatternVerse
from bsim.api.patterns import PatternError, normalize, parse
from bsim.api.routes._common import Conn, State, check_page, unit_span

router = APIRouter()


@router.get("/patterns", response_model=PatternResponse)
def patterns(
    state: State,
    conn: Conn,
    q: str = "",
    book: int | None = None,
    unit: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Verses where the query matches, in canon order (`book`, `unit`: only there), with the
    matches per book. A query that cannot run returns `error` and no verses."""
    check_page(state, limit, offset)
    pc = state.cfg["serve"]["patterns"]
    span = unit_span(conn, unit)
    query = normalize(q)
    empty = {"q": query, "patterns": 0, "total": 0, "matches": 0, "books": [], "offset": offset,
             "limit": limit, "items": []}  # fmt: skip
    table = state.word_table()
    try:
        terms = parse(query, pc["max_patterns"], table.max_words)
        rows = state.pattern_cache.get(query)
        if rows is None:
            rows = table.match(terms, pc["max_matches"])
            state.pattern_cache.put(query, rows)
    except PatternError as e:
        return {**empty, "error": e.as_dict()}
    verse = table.verse[rows[:, 0]] if len(rows) else np.empty(0, dtype=np.int32)
    keep = np.ones(len(rows), dtype=bool)
    books = state.verse_books
    if book is not None:
        keep &= books[verse] == book
    if span is not None:
        keep &= (verse >= span[0]) & (verse <= span[1])
    rows, verse = rows[keep], verse[keep]
    vids, first = np.unique(verse, return_index=True)
    by_book = []
    if len(vids):
        vb = books[vids]
        mb = books[verse]
        for b in np.unique(vb):
            by_book.append(PatternBook(book_id=int(b), matches=int((mb == b).sum()),
                                       verses=int((vb == b).sum())))  # fmt: skip
    page = vids[offset : offset + limit]
    texts = queries.verses_by_id(conn, [int(v) for v in page])
    labels = queries.verse_labels(conn, [int(v) for v in page])
    ends = np.append(first[1:], len(rows))
    items = []
    for k, v in enumerate(page, start=offset):
        ms = rows[first[k] : ends[k]]
        matches = [
            PatternMatch(
                words=[int(table.idx[i]) for i in m],
                tokens=[int(table.display[i]) if table.display[i] >= 0 else None for i in m],
            )
            for m in ms
        ]
        t = texts[int(v)]
        en, he = labels.get(int(v), (t["ref"], t["ref"]))
        items.append(
            PatternVerse(
                verse_id=int(v),
                label=en,
                label_he=he,
                unit_id=f"c:{t['book_id']}:{t['chapter']}",
                text=" | ".join(" … ".join(table.surfaces[i] for i in m) for m in ms),
                matches=matches,
                verse=t,
            )
        )
    return {**empty, "error": None, "patterns": len(terms), "total": int(len(vids)),
            "matches": int(len(rows)), "books": by_book, "items": items}  # fmt: skip
