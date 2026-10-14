"""Response models of `api/routes/refrains.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any

from bsim.api.models.common import ApiModel, Verse


class RefrainVerse(ApiModel):
    verse_id: int
    label: str
    label_he: str
    first: int  # display tokens of the phrase, inclusive
    last: int


class Refrain(ApiModel):
    """A phrase that comes back inside a passage (DESIGN.md §16.40)."""

    refrain_id: int  # 1 = the strongest burst
    book_id: int
    k: int  # verses holding it
    n_tokens: int
    p: float  # burst: the chance of k verses in its span at the phrase's rate in the book
    q: float  # false discovery rate against verse orders shuffled within books
    cv: float  # coefficient of variation of the gaps between its verses
    regular_p: float | None  # random placements as even (None: too few to test)
    turn: float | None  # mean of each verse's sharper neighbouring gap score (§16.29)
    strongest: bool  # the strongest refrain of its group sharing a verse
    known: str | None  # the refrain named in advance that it is
    text: str  # its first occurrence, pointed
    lemmas: str
    occurrences: list[RefrainVerse]
    verses: list[Verse]  # the first few occurrences' verses (`serve.refrain_verses`)


class RefrainKnown(ApiModel):
    """A refrain scholarship names, fixed in advance, and the refrain found for it."""

    name: str
    first_vid: int
    label: str  # its first named verse
    label_he: str
    n_verses: int  # verses named
    refrain_id: int | None  # None: not found
    text: str | None
    k: int | None
    q: float | None


class RefrainBook(ApiModel):
    book_id: int
    refrains: int
    strongest: int


class RefrainsResponse(ApiModel):
    meta: dict[str, Any]  # detect, refrains, distinct, known_found, regular, turns, parameters
    known: list[RefrainKnown]
    books: list[RefrainBook]  # canon order


class RefrainsListResponse(ApiModel):
    book: int | None
    unit: str | None
    strongest: bool
    known: bool
    total: int
    offset: int
    limit: int
    items: list[Refrain]
