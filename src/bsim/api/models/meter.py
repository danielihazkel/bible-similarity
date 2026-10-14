"""Response models of `api/routes/meter.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel, UnitSummary

MeterGroup = Literal["test", "control", "pool", "poetic", "prose"]


class MeterChapter(ApiModel):
    """A chapter's lines by the stresses of their two members (DESIGN.md §16.37)."""

    unit: UnitSummary
    group: MeterGroup  # test / control chapters, the poetry pool, poetic accents, the rest
    n_lines: int  # measured lines (`min_stresses`…`max_stresses`, both members stressed)
    fall: float  # share with the first member longer (3:2)
    rise: float  # ... shorter (2:3)
    net: float  # fall - rise
    share32: float  # share of 3:2 lines
    prob: float | None  # mean probability of parallel verse halves
    pct: float | None  # share of the pool chapters with a lower net fall


class MeterResponse(ApiModel):
    meta: dict[str, Any]  # lengths, the tests (test, test_poetic, named, grid), groups
    test_chapters: list[MeterChapter]
    control_chapters: list[MeterChapter]
    named_chapters: list[MeterChapter]  # chapters that name a lament (קינה)
    group: MeterGroup | None
    book: int | None
    total: int
    offset: int
    limit: int
    items: list[MeterChapter]  # highest net fall first


class MeterLine(ApiModel):
    first: int  # inclusive display-token span
    last: int
    stresses: int
    a: int | None  # stresses of the two members (None: the line does not split)
    b: int | None


class MeterVerse(ApiModel):
    verse_id: int
    lines: list[MeterLine]


class UnitMeter(ApiModel):
    unit_id: str
    min_stresses: int
    max_stresses: int
    chapter: MeterChapter | None  # the chapter the unit starts in
    verses: list[MeterVerse]
