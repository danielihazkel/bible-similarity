"""Response models of `api/routes/phrases.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any

from bsim.api.models.common import ApiModel, GoldLink, UnitSummary, Verse


class PhrasePair(ApiModel):
    """A shared phrase: `a_display` / `b_display` = the display tokens of the matched words."""

    score: float
    n_tokens: int
    spread: int  # verses sharing this exact lemma sequence (2 = only this pair)
    a: UnitSummary
    b: UnitSummary
    a_verse: Verse
    b_verse: Verse
    a_display: list[int]
    b_display: list[int]
    link: GoldLink | None = None


class PhrasesResponse(ApiModel):
    book: int | None
    unit: str | None  # only phrases with a side in this unit
    cross_book: bool
    min_tokens: int
    max_spread: int | None
    total: int
    offset: int
    limit: int
    items: list[PhrasePair]


class AllusionLemma(ApiModel):
    lemma: str  # Strong's number
    form: str


class Allusion(ApiModel):
    """Two passages of a few verses sharing rare words (§16.32)."""

    allusion_id: int
    a_start: int
    a_end: int
    b_start: int
    b_end: int
    a_label: str
    a_label_he: str
    b_label: str
    b_label_he: str
    n_shared: int
    score: float
    q: float
    known: bool  # already a fused neighbour or a parallel sequence
    lemmas: list[AllusionLemma]
    a_verses: list[Verse]
    b_verses: list[Verse]
    a_marks: dict[int, list[int]]  # verse_id -> display tokens of the shared words
    b_marks: dict[int, list[int]]


class AllusionsResponse(ApiModel):
    meta: dict[str, Any]  # rare_lemmas, window, pairs, known, max_q, strong, best_new_q
    known: bool | None
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[Allusion]
