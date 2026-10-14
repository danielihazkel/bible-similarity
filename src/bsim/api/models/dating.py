"""Response models of `api/routes/dating.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel


class DatingChapter(ApiModel):
    """A chapter's Late Biblical Hebrew profile (DESIGN.md §16.24)."""

    unit_id: str
    book_id: int
    chapter: int
    n_words: int  # Hebrew words (Aramaic left out)
    role: Literal["early", "late", "scored"]  # training books are scored held out
    out_of_domain: bool  # poetry: the model is calibrated on prose
    score: float | None  # 0 = like Genesis–Kings, 1 = like the late books; None: too short
    features: dict[str, float]  # shrunk feature rates
    drivers: list[str]  # features pushing the score up most


class DatingBook(ApiModel):
    book_id: int
    role: Literal["early", "late", "scored"]
    out_of_domain: bool
    n_chapters: int
    score: float | None  # mean chapter score
    low: float | None  # 10th / 90th chapter percentiles
    high: float | None
    features: dict[str, float]  # the book's feature rates


class SynopticExample(ApiModel):
    """A Samuel–Kings passage and its Chronicles parallel, scored by models that saw neither."""

    early_first: int  # first verse id
    late_first: int
    early_label: str
    late_label: str
    early_label_he: str
    late_label_he: str
    early_score: float
    late_score: float


class DatingResponse(ApiModel):
    features: list[str]
    coefficients: dict[str, float]  # standardized logistic-regression weights
    held_out_auc: float | None  # leave-one-book-out over the training books
    held_out_auc_grammar: float | None  # ... without the late-word feature
    train_chapters: dict[str, int]
    synoptic: dict[str, Any]  # pairs, later, p, later_grammar, p_grammar
    synoptic_examples: list[SynopticExample]  # the largest gaps
    books: list[DatingBook]
