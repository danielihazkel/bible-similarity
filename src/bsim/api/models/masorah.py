"""Response models of `api/routes/masorah.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel, Verse, VerseLabel

MasorahText = Literal["ketiv", "qere"]
MasorahReason = Literal["split", "decalogue", "absent", "untraced", "witnesses"]


class MasorahMiddle(ApiModel):
    """The tradition's middle of a span against ours, in one text (§16.55)."""

    claim: int  # its place in `masorah.middles`
    span: str  # a book, or Torah / Prophets / Writings
    unit: Literal["letter", "word", "verse"]
    text: MasorahText | None  # None for verses
    source: Literal["masorah", "talmud", "soferim"]
    holds: bool  # within `tolerance` units of ours
    trad_verse: Verse
    trad_tok: int | None  # display token of its word (-1: a written word MAM does not show)
    trad_word: str | None  # the word(s) as written in this text
    trad_letter: int | None  # which letter of the word, from 1
    mid_verse: Verse  # our middle's verse (of its first unit when n is even)
    mid_tok: int | None
    mid_word: str | None
    mid_letter: int | None
    n: int  # units in the span
    trad_pos: float
    mid_pos: float  # (n - 1) / 2: halfway between two units when n is even
    distance: float  # trad_pos - mid_pos
    verses_apart: int


class MasorahTotal(ApiModel):
    """A total of the tradition against ours: a book of the Masorah, a section or the whole."""

    scope: Literal["book", "section"]
    name: str | None  # a book group or a section; None: one of our books (`first_book`)
    first_book: int
    last_book: int
    unit: Literal["verses", "words", "letters"]
    text: MasorahText | None
    source: Literal["masorah", "talmud", "printed"]
    tradition: int
    ours: int
    diff: int  # ours - tradition
    book_sum: int | None  # sections: the Masorah's totals of its books, added
    reason: MasorahReason | None  # why ours differs
    ref_first: VerseLabel | None  # the verses the reason concerns
    ref_last: VerseLabel | None
    also: list[int]  # other totals the manuscripts give


class MasorahBook(ApiModel):
    book_id: int
    verses: int
    words_ketiv: int
    words_qere: int
    letters_ketiv: int
    letters_qere: int


class MasorahResponse(ApiModel):
    meta: dict[str, Any]  # tolerance, text, ketiv / qere applied, Torah and Bible counts, checks
    middles: list[MasorahMiddle]  # config order, written before read
    totals: list[MasorahTotal]  # books in canon order, then the sections
    books: list[MasorahBook]
