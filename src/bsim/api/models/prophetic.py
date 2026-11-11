"""The forms of prophetic speech (DESIGN.md §16.92, D154)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, Page, Verse

ProphForm = Literal["messenger", "woe", "nations", "lawsuit", "call"]


class ProphKnownRef(ApiModel):
    ref: str
    found: bool
    cover: float  # the share of its verses the form's findings cover
    item: int | None


class ProphKnown(ApiModel):
    refs: list[ProphKnownRef]
    found: int
    holds: bool


class ProphBook(ApiModel):
    book_id: int
    counts: dict[str, int]  # form -> findings


class PropheticResponse(ApiModel):
    counts: dict[str, int]  # form -> findings
    items: int
    known: dict[str, ProphKnown]  # form -> its passages named in advance
    known_found: int
    known_total: int
    known_holds: bool
    known_cover: float
    known_overlap: list[str]  # forms whose passages count as found on any overlap
    books: list[ProphBook]


class ProphName(ApiModel):
    lemma: str
    he: str  # Strong's headword
    n: int


class ProphDetail(ApiModel):
    kind: Literal["thus", "oracle"] | None = None  # messenger: כה אמר | נאם
    next: str | None = None  # woe: the lemma after הוי
    names: list[ProphName] | None = None  # nations: the nations named, the most named first
    heading: bool | None = None  # nations: headed משא + a name
    paragraphs: int | None = None
    dispute: bool | None = None  # lawsuit: ריב within the window
    witnesses: bool | None = None  # lawsuit: heaven and earth, mountains or hills
    objection: bool | None = None  # call
    reassurance: bool | None = None


class ProphItem(ApiModel):
    item_id: int
    form: ProphForm
    unit_id: str
    book_id: int
    first_vid: int
    last_vid: int
    first_label: str
    last_label: str
    first_label_he: str
    last_label_he: str
    detail: ProphDetail
    known: bool
    verses: list[Verse]  # its first verses, at most `serve.prophetic.verses`
    marks: dict[str, list[int]]  # verse_id -> the display tokens that mark the form


class ProphItems(Page[ProphItem]):
    form: ProphForm | None
    book: int | None
