"""Response models of `api/routes/forms.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel, Verse, VerseLabel

FormsKind = Literal["genealogy", "itinerary", "census", "offering", "kings", "names", "other"]


class FormsKnownSaying(ApiModel):
    """A graded numerical saying named in advance and whether it is found (§16.45)."""

    name: str
    first: VerseLabel  # its first named verse
    n_verses: int  # verses named
    hits: int  # of them holding a graded pair
    found: bool  # at least half


class FormsKnownList(ApiModel):
    """A list named in advance and how much of it the lists found cover."""

    name: str
    first: VerseLabel
    last_verse: VerseLabel
    n_verses: int
    covered: int  # its verses inside a list found
    found: bool  # at least half


class FormsBook(ApiModel):
    book_id: int
    numbers: int  # number words
    free: int  # ... not part of a compound number
    sayings: int
    lists: int
    list_verses: int


class FormsResponse(ApiModel):
    meta: dict[str, Any]  # counts, steps, the chance and parallelism checks, the lists' detection
    known: list[FormsKnownSaying]
    known_lists: list[FormsKnownList]
    books: list[FormsBook]  # canon order, books with a number or a list


class FormsPair(ApiModel):
    a_tok: int | None  # display tokens of the two numbers
    b_tok: int | None
    a_value: int
    b_value: int


class FormsSaying(ApiModel):
    """A verse with a number and the next a few words on (שלשה … וארבעה)."""

    unit_id: str  # its chapter
    n_pairs: int
    steps: str  # e.g. "3 / 4"
    prob: float | None  # probability of parallel halves (§16.9)
    known: str | None  # the saying named in advance it is
    pairs: list[FormsPair]
    verse: Verse


class FormsSayingsResponse(ApiModel):
    book: int | None
    unit: str | None
    known: bool
    total: int
    offset: int
    limit: int
    items: list[FormsSaying]


class FormsList(ApiModel):
    """A run of verses shaped alike: a genealogy, an itinerary, a roll of names."""

    list_id: int
    book_id: int
    unit_id: str  # the chapter it starts in
    first: VerseLabel
    last_verse: VerseLabel
    n_verses: int  # first to last
    n_like: int  # list-like verses
    likeness: float  # mean best cosine of word shapes with a neighbour
    kind: FormsKind
    known: str | None  # the list named in advance it is part of
    verses: list[Verse]  # its first few verses (`serve.list_verses`)


class FormsListsResponse(ApiModel):
    book: int | None
    unit: str | None
    kind: str | None
    total: int
    offset: int
    limit: int
    items: list[FormsList]
