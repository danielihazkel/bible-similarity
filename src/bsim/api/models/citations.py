"""Response models of `api/routes/citations.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel, Verse

CitationFamily = Literal["written", "word", "command"]


class CitationBook(ApiModel):
    book_id: int  # citing
    target_book: int  # cited
    n: int


class CitationsResponse(ApiModel):
    meta: dict[str, Any]  # citations, resolved, families, gold, word_lag_median, book_pairs
    books: list[CitationBook]


class CitationCandidate(ApiModel):
    verse_id: int
    label: str
    label_he: str
    score: float


class Citation(ApiModel):
    """A verse with a formula of reference and its best source (§16.31)."""

    cite_id: int
    family: CitationFamily
    verse_id: int
    book_id: int
    label: str
    label_he: str
    formula: str
    verse: Verse
    target: Verse | None
    target_label: str | None
    target_label_he: str | None
    score: float | None
    pct: float | None
    resolved: bool
    candidates: list[CitationCandidate]  # the best first, the source itself included
    gold_rank: int | None  # a named source's rank among the candidates (None: not named / missed)
    named: bool  # scholarship names a source for this citation


class CitationListResponse(ApiModel):
    family: CitationFamily | None
    resolved: bool | None
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[Citation]
