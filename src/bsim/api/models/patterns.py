"""Response models of `api/routes/patterns.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, Verse

PatternErrorCode = Literal[
    "empty", "expected_pattern", "unclosed", "bad_condition", "unknown_key", "bad_value",
    "unknown_value", "bad_gap", "too_many", "variable", "too_broad",
]  # fmt: skip


class PatternProblem(ApiModel):
    """Why a query could not run: what went wrong, where (a character offset) and on what."""

    code: PatternErrorCode
    at: int
    token: str


class PatternMatch(ApiModel):
    words: list[int]  # the matched words (OSHB word indexes), one per pattern
    tokens: list[int | None]  # their display tokens (None: not aligned)


class PatternVerse(ApiModel):
    verse_id: int
    label: str
    label_he: str
    unit_id: str  # its chapter
    text: str  # each match's words, " … " between them, " | " between matches
    matches: list[PatternMatch]
    verse: Verse


class PatternBook(ApiModel):
    book_id: int
    matches: int
    verses: int


class PatternResponse(ApiModel):
    q: str
    error: PatternProblem | None
    patterns: int  # word patterns in the query
    total: int  # verses with a match (the paged list)
    matches: int
    books: list[PatternBook]  # canon order
    offset: int
    limit: int
    items: list[PatternVerse]
