"""Response models of `api/routes/ketiv.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel, KqClass, Verse


class KqBook(ApiModel):
    book_id: int
    n: int
    words: int
    rate: float  # per 1,000 words
    vowel_letter: int
    ketiv_fuller: float | None  # share of vowel-letter pairs written fuller than read
    swap: int
    division: int
    other_cls: int
    form: int
    word: int


class KqLetter(ApiModel):
    pair: str  # two letters, sorted
    n: int
    expected: float
    ratio: float | None
    p: float
    q: float
    lookalike: bool


class KetivResponse(ApiModel):
    meta: dict[str, Any]  # pairs, classes, grammar, euphemisms, features, checks
    books: list[KqBook]
    letters: list[KqLetter]  # pairs with at least one swap


class KqPair(ApiModel):
    """One ketiv / qere (§16.30): what is written, what is read, and how they differ."""

    kq_id: int
    verse_id: int
    book_id: int
    label: str
    label_he: str
    ketiv: str
    qere: str
    cls: KqClass
    fuller: Literal["ketiv", "qere"] | None
    letters: str | None
    grammar: Literal["spelling", "form", "word"] | None
    features: list[str]
    euphemism: bool
    parallel: Literal["qere", "ketiv", "neither"] | None
    partner_vid: int | None
    partner_label: str | None
    partner_label_he: str | None
    partner_form: str | None
    verse: Verse
    display: list[int]  # display tokens of the read words


class KqPairsResponse(ApiModel):
    cls: KqClass | None
    grammar: str | None
    parallel: str | None
    euphemism: bool | None
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[KqPair]
