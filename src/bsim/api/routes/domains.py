"""Semantic domains: the SDBH domain tree, a domain concordance and a unit's themes
(DESIGN.md §16.22). Domain names are English data from SDBH; glosses are never served (D56)."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models import (
    BookCount,
    DomainHit,
    DomainInfo,
    DomainResponse,
    DomainShare,
    UnitDomains,
    UnitSummary,
)
from bsim.api.routes._common import Conn, State, check_page, unit_or_404
from bsim.store.db import ancestors

router = APIRouter()


@router.get("/domains", response_model=list[DomainInfo])
def domains(conn: Conn) -> list[dict[str, Any]]:
    """Every domain in tree order (by code), with its verse and word counts."""
    return queries.domains(conn)


@router.get("/domain/{code}", response_model=DomainResponse)
def domain(
    code: str,
    state: State,
    conn: Conn,
    book: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Concordance of a domain and its subdomains: the verses whose content words fall in it,
    with per-book counts, its path from the top and its subdomains."""
    by_code = {d["code"]: d for d in queries.domains(conn)}
    if code not in by_code:
        raise HTTPException(status_code=404, detail=f"unknown domain {code!r}")
    check_page(state, limit, offset)
    by_book = queries.domain_books(conn, code)
    total = sum(b["n_verses"] for b in by_book if book is None or b["book_id"] == book)
    page = queries.domain_page(conn, code, book, limit, offset)
    vids = [v for v, _ in page]
    verses = queries.verses_by_id(conn, vids)
    labels = queries.verse_labels(conn, vids)
    marks: dict[int, set[int]] = defaultdict(set)
    for w in queries.word_domains(conn, vids):
        if w["display_idx"] is not None and any(d.startswith(code) for d in w["domains"].split()):
            marks[w["verse_id"]].add(w["display_idx"])
    return {
        "domain": by_code[code],
        "path": [by_code[a] for a in reversed(ancestors(code)[1:]) if a in by_code],
        "children": [d for d in by_code.values() if d["parent"] == code],
        "by_book": [BookCount(**b) for b in by_book],
        "book": book,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            DomainHit(
                verse=verses[v],
                label_en=labels[v][0],
                label_he=labels[v][1],
                display_idxs=sorted(marks[v]),
                weight=round(w, 3),
            )
            for v, w in page
        ],
    }


def g2_over(k: float, n: float, p: float) -> float:
    """Dunning's G² of `k` of `n` word weights against a corpus share `p`, signed by the
    direction (negative when under-represented)."""
    if n <= 0 or p <= 0 or p >= 1:
        return 0.0
    e = n * p
    g = 2 * sum(
        o * math.log(o / x) for o, x in ((k, e), (n - k, n - e)) if o > 0 and x > 0
    )
    return g if k >= e else -g


@router.get("/unit-domains/{unit_id}", response_model=UnitDomains)
def unit_domains(unit_id: str, state: State, conn: Conn) -> dict[str, Any]:
    """What a unit is about: its domains (any level below the top) most over-represented
    against the whole corpus (G²), and its share of each second-level domain."""
    u = unit_or_404(conn, unit_id)
    sc = state.cfg["serve"]["domains"]
    by_code = {d["code"]: d for d in queries.domains(conn)}
    here: dict[str, float] = defaultdict(float)
    for code, w in queries.unit_domain_weights(conn, u["start_verse_id"], u["end_verse_id"]):
        for a in ancestors(code):
            here[a] += w
    corpus = sum(d["weight"] for d in by_code.values() if d["level"] == 1)
    total = sum(w for c, w in here.items() if len(c) == 3)

    def share(code: str) -> DomainShare:
        d, k = by_code[code], here[code]
        p = d["weight"] / corpus if corpus else 0.0
        return DomainShare(
            domain=d,
            weight=round(k, 3),
            expected=round(total * p, 3),
            lift=round(k / (total * p), 3) if total and p else 0.0,
            g2=round(g2_over(k, total, p), 3),
        )

    themes = [
        share(c)
        for c, k in here.items()
        if c in by_code and len(c) > 3 and k >= sc["min_weight"]
    ]
    themes = sorted((t for t in themes if t.g2 > 0), key=lambda t: (-t.g2, t.domain.code))
    broad = sorted(
        (share(c) for c in here if c in by_code and len(c) == 6),
        key=lambda t: (-t.weight, t.domain.code),
    )
    return {
        "unit": UnitSummary(**u),
        "total": round(total, 3),
        "themes": themes[: sc["top"]],
        "broad": broad,
    }
