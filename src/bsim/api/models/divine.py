"""Response models of `api/routes/divine.py` (DESIGN.md §10, §16.65)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel

DivineName = Literal[
    "yhwh", "elohim", "adonai", "el", "eloah", "shaddai", "yah", "elyon", "tsevaot"
]  # fmt: skip


class DivineChapter(ApiModel):
    unit_id: str
    book_id: int
    chapter: int
    words: int
    counts: dict[str, int]  # name -> words that are it (only names present)
    share: float | None  # the first name of the measure among the two (None: neither)
    part: int | None  # 1-3: its part of the book's split


class DivineBook(ApiModel):
    book_id: int
    chapters: int
    words: int
    counts: dict[str, int]
    share: float | None
    split: bool  # the book has enough names and chapters to be split
    cut1: int | None  # first chapter of the second part
    cut2: int | None  # first chapter of the third part
    shares: list[float | None]  # the three parts' shares (empty without a split)
    gain: float | None
    p: float | None
    q: float | None


class ElohisticCheck(ApiModel):
    book_id: int
    named: list[int]  # the part named in advance: first and last chapter
    tolerance: int
    first: int | None  # the middle part found
    last: int | None
    shares: list[float] | None
    gain: float | None
    p: float | None
    found: bool | None  # None: the book is not split here
    holds: bool


class DoubledPair(ApiModel):
    pair: int
    e: str  # the passage inside the named part (as written in config)
    y: str  # its double outside
    e_ward: int  # the first has the second name of the measure where the other has the first
    y_ward: int
    same: int
    other: int


class DoubledCheck(ApiModel):
    pairs: list[DoubledPair]
    missing: list[str]  # passages the corpus lacks
    e_ward: int
    y_ward: int
    p: float
    holds: bool


class DivineResponse(ApiModel):
    names: list[DivineName]  # in the config's order
    measure: list[DivineName]  # the two whose mix is measured
    totals: dict[str, int]
    alpha: float
    shuffles: int
    min_segment: int
    elohistic: ElohisticCheck
    doubled: DoubledCheck
    books: list[DivineBook]  # canon order
    chapters: list[DivineChapter]  # canon order


class DivinePlace(ApiModel):
    """One aligned place of a doubled passage with a name on either side."""

    kind: Literal["e_ward", "y_ward", "same", "other"]
    e_vid: int | None
    e_label: str | None
    e_label_he: str | None
    e_word: str | None
    e_name: DivineName | None
    y_vid: int | None
    y_label: str | None
    y_label_he: str | None
    y_word: str | None
    y_name: DivineName | None


class DivinePairDetail(DoubledPair):
    places: list[DivinePlace]  # where a name stands on either side, in text order


class DivinePairsResponse(ApiModel):
    pairs: list[DivinePairDetail]
