"""Fixed word pairs (DESIGN.md §16.72): every binomial with its order, its words' lengths and its
turns by period, a binomial's occurrences, and the checks."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.binomials import (
    Binomial,
    BinomialOccurrence,
    BinomialOccurrencesResponse,
    BinomialsResponse,
)
from bsim.api.routes._common import Conn, State

router = APIRouter()


@router.get("/binomials", response_model=BinomialsResponse)
def binomials(state: State, conn: Conn) -> dict[str, Any]:
    """Every binomial, the commonest first (404: the stage did not run)."""
    m = state.meta.get("binomials")
    if not m:
        raise HTTPException(status_code=404, detail="the binomials were not computed")
    keep = ("pairs", "binomials", "min_pairs", "both_ways", "letters", "syllables",
            "short_holds", "rate_early", "rate_late", "n_early", "n_late", "difference",
            "expected", "late_p", "late_holds", "without_known", "known", "known_late",
            "known_holds", "examples", "shuffles", "alpha")  # fmt: skip
    return {**{k: m[k] for k in keep}, "items": [Binomial(**r) for r in queries.binomials(conn)]}


@router.get("/binomials/occurrences", response_model=BinomialOccurrencesResponse)
def binomial_occurrences(pair: str, state: State, conn: Conn) -> dict[str, Any]:
    """A binomial's listed occurrences, its own order first (404: no such binomial)."""
    if not state.meta.get("binomials"):
        raise HTTPException(status_code=404, detail="the binomials were not computed")
    rows = queries.binomial_occurrences(conn, pair)
    if not rows:
        raise HTTPException(status_code=404, detail=f"no binomial {pair!r}")
    verses = queries.verses_by_id(conn, [r["verse_id"] for r in rows])
    return {
        "pair": pair,
        "items": [
            BinomialOccurrence(verse=verses[r["verse_id"]], own=bool(r["own"]), a_tok=r["a_tok"],
                               b_tok=r["b_tok"])  # fmt: skip
            for r in rows
            if r["verse_id"] in verses
        ],
    }
