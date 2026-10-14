"""Response models of `api/routes/roots.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import (
    ApiModel,
    BookCount,
    ConcordanceHit,
    LemmaStat,
    UnitSummary,
    Verse,
)

RootPairKind = Literal["cognate", "other", "inf_abs"]


class RootBook(ApiModel):
    book_id: int
    words: int  # Hebrew words
    cognate: int  # a verb and a noun of one root side by side
    expected: float  # ... with the content words permuted within chapters
    inf_abs: int  # infinitive absolute + finite verb (מות יומת)


class RootKnown(ApiModel):
    """A Leitwort named in advance, ranked among its chapter's Leitworte both ways."""

    unit: UnitSummary
    root: str
    root_he: str
    lemma_rank: int | None  # best rank of any word of the family, counted by lemma
    root_rank: int | None  # rank of the family counted by root


class RootsResponse(ApiModel):
    meta: dict[str, Any]  # families, pairs per kind, tests (cognate, other), known_*, hidden
    known: list[RootKnown]
    books: list[RootBook]  # canon order


class RootPair(ApiModel):
    """Two words of one root side by side in a verse (DESIGN.md §16.38)."""

    pair_id: int
    verse_id: int
    label: str
    label_he: str
    kind: RootPairKind
    root: str
    root_he: str
    a: LemmaStat
    b: LemmaStat
    verse: Verse
    marks: dict[int, int]  # display token -> 0 (the first word) or 1


class RootPairsResponse(ApiModel):
    kind: RootPairKind | None
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[RootPair]


class HiddenRoot(ApiModel):
    """A chapter Leitwort that only shows when its words are counted as one root."""

    unit: UnitSummary
    rank: int
    root: str
    root_he: str
    count: int
    g2: float
    n_words: int  # Strong's numbers of the family in the chapter
    lemma_rank: int | None  # best rank of one of them counted by lemma
    lemmas: list[LemmaStat]  # the family's words


class HiddenRootsResponse(ApiModel):
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[HiddenRoot]


class RootFamily(ApiModel):
    """A root family and a page of the verses holding any of its words (`/root/{root}`)."""

    root: str
    root_he: str
    members: list[LemmaStat]  # commonest first
    links: dict[str, str]  # member lemma -> how Strong's derives it (from, feminine of, ...)
    n_verses: int
    by_book: list[BookCount]
    book: int | None
    total: int
    offset: int
    limit: int
    items: list[ConcordanceHit]
