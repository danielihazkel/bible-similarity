"""The law codes side by side (DESIGN.md §16.93, D155)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, Page, Verse

LawCode = Literal["covenant", "ritual", "holiness", "deuteronomic", "priestly"]
LawForm = Literal["casuistic", "apodictic", "other"]
LawPairOrder = Literal["score", "canon"]
DiffOpName = Literal["spelling", "form", "substitution", "omitted", "added", "moved"]


class LawCodeRow(ApiModel):
    code: LawCode
    laws: int
    verses: int
    casuistic: int
    apodictic: int
    other: int
    v2ms: int  # laws addressed mostly in the 2ms
    v2mp: int
    v3: int
    mixed: int


class LawKnownMember(ApiModel):
    a: str
    b: str
    found: bool
    strict: bool  # the aligned verses themselves touch both passages
    pairs: list[int]  # law_pairs.pair_id joining the two


class LawKnown(ApiModel):
    group: str
    members: list[LawKnownMember]
    found: int
    of: int


class LawsResponse(ApiModel):
    laws: int
    pairs: int
    linked: int  # law pairs with any link
    top_k: int
    min_links: int
    forms: dict[str, int]
    known: list[LawKnown]
    known_found: int
    known_total: int
    known_holds: bool
    known_strict: int  # member pairs found by the aligned verses themselves
    kept_mean: float | None
    codes: list[LawCodeRow]


class Law(ApiModel):
    law_id: int
    code: LawCode
    unit_id: str
    book_id: int
    first_vid: int
    last_vid: int
    first_label: str
    last_label: str
    first_label_he: str
    last_label_he: str
    n_verses: int
    form: LawForm
    casuistic: bool
    apodictic: bool
    address: Literal["2ms", "2mp", "3", "mixed"] | None
    pairs: int  # matched pairs it is in


class LawList(Page[Law]):
    code: LawCode | None
    form: LawForm | None


class LawPair(ApiModel):
    pair_id: int
    a: Law
    b: Law
    links: int
    score: float
    a_first: int
    a_last: int
    b_first: int
    b_last: int
    a_span: str  # the aligned span's references
    b_span: str
    a_span_he: str
    b_span_he: str
    ops: dict[str, int]  # same, spelling, form, substitution, omitted, added, moved
    kept: float
    known: str | None


class LawPairs(Page[LawPair]):
    order: LawPairOrder
    code: LawCode | None


class LawSideVerse(ApiModel):
    verse: Verse
    marks: dict[str, DiffOpName]  # display token -> its change


class LawSynopsis(ApiModel):
    pair: LawPair
    a: list[LawSideVerse]  # the aligned span of each side, at most `serve.laws.max_verses`
    b: list[LawSideVerse]
