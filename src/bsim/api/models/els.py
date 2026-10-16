"""Response models of `api/routes/els.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel, VerseLabel

ElsControlKey = Literal["letters", "verses", "blocks"]


class ElsControl(ApiModel):
    """A control's values of R (the mean log ratio of hits to expected) against the text's."""

    n: int
    mean: float
    q05: float
    q95: float
    p: float  # the share of the control's values at least the text's R
    values: list[float]  # each draw's (or block's) R


class ElsBlock(ApiModel):
    block: int
    label_en: str  # the verses it spans
    label_he: str
    first_vid: int
    r: float


class ElsTerm(ApiModel):
    term: str
    length: int
    forward: int
    backward: int
    hits: int
    expected: float  # under a shuffle of the scope's letters, exactly
    log_ratio: float
    letters_mean: float
    letters_q05: float
    letters_q95: float
    letters_p: float
    verses_mean: float
    blocks_log_ratio: float | None


class ElsScope(ApiModel):
    key: str  # `els.scopes`: torah | genesis
    label_en: str
    label_he: str
    letters: int
    verses: int
    hits: int
    expected: float
    r: float
    holds: bool  # no control has p <= alpha
    controls: dict[ElsControlKey, ElsControl]
    blocks: list[ElsBlock]
    terms: list[ElsTerm]


class ElsKnown(ApiModel):
    verse: VerseLabel
    term: str
    skip: int
    found: bool
    offset: int | None  # the letter of the verse it starts at, from 0
    in_torah: int  # occurrences of the term at that skip in the Torah, forwards
    expected: float  # ... under a shuffle of its letters


class ElsResponse(ApiModel):
    meta: dict[str, Any]  # text, skips, shuffles, alpha, smooth, terms, holds
    scopes: list[ElsScope]
    known: list[ElsKnown]
