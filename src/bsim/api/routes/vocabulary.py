"""The vocabulary over the canon (DESIGN.md §16.76): each book's new lemmas against Heaps' law,
its rare words, and the checks."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models.vocabulary import KnownRare, VocabularyBook, VocabularyResponse
from bsim.api.routes._common import Conn, State, stage, stage_missing

router = APIRouter()

KEEP = ("words", "lemmas", "hapax", "one_corpus", "heaps_k", "heaps_b", "late_novelty",
        "early_novelty", "difference", "late_p", "splits", "late_holds", "known_holds", "orders",
        "alpha")  # fmt: skip


@router.get("/vocabulary", dependencies=[stage("vocabulary")], response_model=VocabularyResponse)
def vocabulary(state: State, conn: Conn) -> dict[str, Any]:
    """Every book's vocabulary in canon order, and the checks (503: the stage did not run)."""
    m = state.meta.get("vocabulary")
    if not m:
        raise stage_missing("vocabulary")
    return {
        **{k: m[k] for k in KEEP},
        "known": [KnownRare(**k) for k in m.get("known") or []],
        "books": [VocabularyBook(**r) for r in queries.vocabulary_books(conn)],
    }
