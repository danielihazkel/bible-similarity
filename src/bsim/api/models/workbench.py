"""Response models of `api/routes/workbench.py` (DESIGN.md §10, §16.64)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel
from bsim.api.models.patterns import PatternProblem

WorkbenchFeature = Literal[
    "lemma", "root", "domain", "pos", "stem", "form", "person", "function", "clause"
]  # fmt: skip
WorkbenchWithin = Literal["corpus", "book", "chapter"]
SetErrorCode = Literal[
    "empty", "too_long", "bad_item", "unknown_kind", "unknown_book", "bad_range", "unknown_unit",
    "unknown_collection", "pattern", "no_words", "filter_in_check",
]  # fmt: skip


class SetProblem(ApiModel):
    """Why a set could not be read: which set (`a`, `b` or the check's `set`), which item (its
    index among the `;`-separated items) and on what; a pattern item's own problem in `pattern`."""

    set: Literal["a", "b", "set"]
    code: SetErrorCode
    item: int
    token: str
    pattern: PatternProblem | None


class SetSummary(ApiModel):
    spec: str  # as read, whitespace collapsed; "" for B = every other word
    verses: int
    words: int
    books: list[int]  # canon order
    filtered: bool  # an only: filter keeps part of the verses' words


class WorkbenchExample(ApiModel):
    verse_id: int
    label: str
    label_he: str


class ContrastRow(ApiModel):
    key: str  # the value: Strong's number (lemma, root), domain code, or a feature value
    label: str | None  # Hebrew headword (lemma, root) or domain name; None for the others
    a: float  # words in A with it (a domain's words split over k domains count 1/k)
    b: float
    rate_a: float  # per 1,000 words of A that have the feature
    rate_b: float
    log_ratio: float  # log2(rate A / rate B), half a word added to each side
    g2: float
    p: float
    q: float  # Benjamini–Hochberg over every value tested
    examples: list[WorkbenchExample]  # verses of its side that hold it, canon order


class ContrastResponse(ApiModel):
    feature: WorkbenchFeature
    error: SetProblem | None
    a: SetSummary | None
    b: SetSummary | None
    overlap: int  # words in both sets, counted for A only
    total_a: float  # words of A that have the feature
    total_b: float
    tested: int  # values with at least `min_count` words over A and B
    min_count: int
    alpha: float
    significant_a: int  # values commoner in A at q ≤ alpha
    significant_b: int
    over_a: list[ContrastRow]  # commoner in A, by G²
    over_b: list[ContrastRow]


class CheckBook(ApiModel):
    book_id: int
    matches: int  # in the set's verses of the book
    words: int


class CheckResponse(ApiModel):
    q: str
    within: WorkbenchWithin
    draws: int
    error: SetProblem | None
    pattern_error: PatternProblem | None  # the query's own problem
    set: SetSummary | None
    testable: bool  # some group holds verses of the set and others
    matches: int  # pattern matches starting in the set's verses
    words: int
    rate: float  # per 1,000 words
    rest_matches: int  # in the other verses of the groups the set touches
    rest_words: int
    rest_rate: float
    null_mean: float  # the rate over the shuffles
    null_low: float  # 2.5 % and 97.5 % of the shuffled rates
    null_high: float
    p_high: float  # the set denser than its shuffles (one-sided, +1 corrected)
    p_low: float  # sparser
    groups: int  # groups (books, chapters, the corpus) holding verses of the set and others
    fixed_verses: int  # set verses in groups wholly inside the set, the same in every draw
    books: list[CheckBook]
