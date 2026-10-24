"""Response models of `api/routes/chronology.py` (DESIGN.md §10, §16.70)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, Verse

Kingdom = Literal["judah", "israel"]


class ChronEvent(ApiModel):
    seq: int  # the order of `chronology.events`
    event: str  # a person's id (birth), `<id>.death`, or an event (flood, exodus, ...)
    name: str | None  # the person's name in Hebrew
    from_event: str | None  # counted from (None: Adam, year 0)
    verse: Verse | None  # whose number is added
    value: int | None
    sign: int  # 1 added, -1 taken away
    year: int  # from Adam
    used: bool  # the event's first way; else a check
    conflict: bool  # a check giving another year
    tok_first: int | None
    tok_last: int | None


class Life(ApiModel):
    person: str
    name: str
    born: int
    died: int | None


class ChronKing(ApiModel):
    king: str
    name: str  # Hebrew
    kingdom: Kingdom
    seq: int
    verse: Verse  # the regnal formula's first verse
    reign: int  # years (0 when short)
    short: bool  # days or months
    start: int  # year 1, counted from the division
    am: int  # from Adam


class ChronSync(ApiModel):
    seq: int
    king: str
    of: str
    verse: Verse
    year: int  # in year N of `of`
    t_judah: int
    t_israel: int
    agrees: bool | None  # the interval since the one before (None: the first)


class KnownDate(ApiModel):
    event: str
    year: int | None
    expected: int
    holds: bool


class Gen5Number(ApiModel):
    verse: Verse
    value: int
    tok_first: int | None
    tok_last: int | None


class Digits(ApiModel):
    n: int
    hits: int
    share: float
    rest_n: int
    rest_share: float
    p: float
    uniform: float
    uniform_p: float
    compare_n: int
    compare_share: float | None
    by_digit: dict[str, int]
    rest_by_digit: dict[str, int]
    holds: bool


class ChronologyResponse(ApiModel):
    events: list[ChronEvent]
    lives: list[Life]  # the people with a birth year, in order
    kings: list[ChronKing]
    syncs: list[ChronSync]
    numbers: list[Gen5Number]
    conflicts: int
    known: list[KnownDate]
    known_holds: bool
    intervals: int
    agree: int
    rules: dict[str, str]  # kingdom -> accession | non-accession
    rule_counts: dict[str, int]  # "judah/israel" rules -> agreeing intervals
    tolerance: int
    shuffles: int
    alpha: float
    expected: float
    p: float
    holds: bool
    absolute: int  # synchronisms whose two counts agree outright
    division: int
    ends: dict[str, int]
    tradition: dict[str, int]
    digits: Digits
    digits_chapter: str
    digits_compare: str
    digits_ends: list[int]
    digits_min: int
