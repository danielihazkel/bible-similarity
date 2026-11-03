"""Response models of `api/routes/sums.py` (DESIGN.md §10, §16.75)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, Page, Verse

NumberUnit = Literal["count", "year", "month", "day"]


class SumsList(ApiModel):
    key: str  # sums.lists
    total: int  # the total the text states
    sum: int  # its items' counts added
    n_items: int
    adds_up: bool
    expected: bool  # the known answer
    holds: bool  # adds_up == expected
    total_verse: Verse
    total_tok_first: int | None
    total_tok_last: int | None
    first_verse: Verse  # the items' span
    last_verse: Verse


class SumsTest(ApiModel):
    numbers: int  # aligned numbers
    same: int
    tested: int  # differing, with a draw to compare
    one_step: int
    share: float | None
    expected: float | None  # the second number drawn from its book
    p: float


class KnownSumsParallel(ApiModel):
    a: Verse
    b: Verse
    a_value: int
    b_value: int
    found: bool
    one_step: bool | None  # None: not found, or the same
    expected: bool
    holds: bool


class SumsResponse(ApiModel):
    lists: list[SumsList]
    lists_adding_up: int
    lists_holds: bool
    min_value: int
    pairs: int  # parallel verse pairs from the three sources
    pairs_used: int  # ... sharing words, with numbers aligned
    numbers: int
    numbers_same: int
    numbers_differ: int
    across: SumsTest  # the claim: verses in different books
    every: SumsTest  # the first run's rule, described
    step_holds: bool
    known_parallels: list[KnownSumsParallel]
    known_holds: bool
    min_shared: int
    min_big: int
    shuffles: int
    alpha: float


class SumsItem(ApiModel):
    verse: Verse
    value: int
    tok_first: int | None
    tok_last: int | None


class SumsItemsResponse(ApiModel):
    key: str
    items: list[SumsItem]


class SumsParallel(ApiModel):
    a: Verse
    b: Verse
    unit: NumberUnit
    a_value: int
    b_value: int
    same: bool
    one_step: bool | None
    a_tok_first: int | None
    a_tok_last: int | None
    b_tok_first: int | None
    b_tok_last: int | None


class SumsParallelsResponse(Page[SumsParallel]):
    across: bool  # verses in different books only
    differ: bool  # differing numbers only
    one_step: bool | None
    book: int | None
