"""Response models of `api/routes/witnesses.py` (DESIGN.md §10, §16.78)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, Page, Verse

WitnessKind = Literal["sp", "scroll"]
Op = Literal["same", "spelling", "form", "substitution", "omitted", "added", "moved"]


class OpCounts(ApiModel):
    """Positions that count, by op (a scroll's: its read words; `same` not always kept)."""

    spelling: int
    form: int
    substitution: int
    omitted: int  # in the MT only
    added: int  # in the witness only
    moved: int


class SamaritanTotals(OpCounts):
    verses: int
    words: int
    same: int


class ScrollTotals(OpCounts):
    scrolls: int
    verses: int
    words: int
    read: int  # words none of whose letters is reconstructed or uncertain
    same: int


class WitnessBook(OpCounts):
    kind: WitnessKind
    book_id: int
    verses: int
    words: int
    read: int
    pluses: int  # verses with a plus of `plus_min` read words or more


class ScrollRow(OpCounts):
    scroll: str  # the siglum, `1Qisaa`, `4Q51`
    book_id: int  # its first verse's book
    first_vid: int
    verses: int
    words: int
    read: int
    same: int
    pluses: int


class KnownReading(ApiModel):
    witness: str
    ref: str
    verse: Verse | None
    plus: int | None  # a plus of at least this many words
    reads: str | None  # a word it reads where the MT has another
    found: bool
    note: str | None  # in English, for the notes of the config (shown in the English interface)


class ChronologyKnown(ApiModel):
    event: str
    expected: int
    year: int | None
    holds: bool


class ChronologyRow(ApiModel):
    seq: int
    event: str  # chronology.events' id: `jared`, `jared.death`
    name: str | None  # the person, in Hebrew
    death: bool
    verse_id: int | None
    ref: str | None
    ref_he: str | None
    sp_value: int | None  # the Samaritan's number in that verse
    sp_year: int  # from Adam, in the Samaritan
    mt_year: int | None  # ... in the MT


class WitnessesResponse(ApiModel):
    samaritan: SamaritanTotals
    scrolls: ScrollTotals
    plus_min: int
    max_unc: int
    sp_pluses: int  # Torah verses with a Samaritan plus
    parallel_verses: int  # Torah verses with a parallel elsewhere in the Torah
    plus_in_parallel: float | None  # share of those with a plus
    plus_elsewhere: float | None
    ratio: float
    null_mean: float
    p: float
    shifts: int
    alpha: float
    holds: bool
    known: list[KnownReading]
    chronology_known: list[ChronologyKnown]
    known_holds: bool
    chronology: list[ChronologyRow]
    books: list[WitnessBook]
    scroll_rows: list[ScrollRow]


class WitnessPlus(ApiModel):
    witness: str
    verse: Verse
    plus: int
    variants: int


class WitnessPlusesResponse(Page[WitnessPlus]):
    kind: WitnessKind
    book: int | None


class WitnessWord(ApiModel):
    t: str  # letters, finals folded
    r: bool  # read: no letter reconstructed or uncertain
    op: Op | None
    mt: int | None  # the MT word's display token it is aligned to


class WitnessReading(ApiModel):
    witness: str
    n_words: int
    n_read: int
    plus: int
    variants: int
    words: list[WitnessWord]
    missing: list[int]  # the MT's display tokens this witness lacks (counted omissions)


class WitnessVerse(ApiModel):
    verse: Verse
    readings: list[WitnessReading]  # the Samaritan first, then the scrolls by siglum


class WitnessUnitResponse(Page[WitnessVerse]):
    unit_id: str
    witnesses: list[str]  # every witness of the unit's verses
