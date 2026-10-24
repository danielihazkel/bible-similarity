"""Response models of `api/routes/binomials.py` (DESIGN.md §10, §16.72)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, Verse


class Binomial(ApiModel):
    pair: str  # the two lemmas, sorted, joined by +
    first: str  # the lemma first in its own (commoner) order
    second: str
    first_form: str  # consonantal
    second_form: str
    kind: Literal["noun", "name", "adjective"]
    n: int
    n_own: int
    fixed: float
    first_letters: float
    second_letters: float
    first_syll: float
    second_syll: float
    n_early: int
    rev_early: int
    n_late: int
    rev_late: int


class ShorterFirst(ApiModel):
    differ: int  # binomials whose words differ in length
    shorter_first: int
    share: float | None
    p: float


class RarerWithout(ApiModel):
    difference: float
    p: float
    rate_early: float | None
    rate_late: float | None


class KnownBinomial(ApiModel):
    first: str
    second: str
    n: int
    share: float | None  # in the expected order
    fixed: float
    holds: bool


class KnownLate(ApiModel):
    first: str
    second: str
    n_early: int
    share_early: float | None  # of the pair's occurrences in that order
    n_late: int
    share_late: float | None
    holds: bool


class BinomialsResponse(ApiModel):
    pairs: int  # every pair found
    binomials: int
    min_pairs: int
    both_ways: int
    letters: ShorterFirst
    syllables: ShorterFirst
    short_holds: bool
    rate_early: float | None  # the rarer order's share in the early books
    rate_late: float | None
    n_early: int
    n_late: int
    difference: float
    expected: float
    late_p: float
    late_holds: bool
    without_known: RarerWithout  # described: without the known pair
    known: list[KnownBinomial]
    known_late: KnownLate
    known_holds: bool
    examples: int  # occurrences listed per order
    shuffles: int
    alpha: float
    items: list[Binomial]


class BinomialOccurrence(ApiModel):
    verse: Verse
    own: bool
    a_tok: int | None
    b_tok: int | None


class BinomialOccurrencesResponse(ApiModel):
    pair: str
    items: list[BinomialOccurrence]
