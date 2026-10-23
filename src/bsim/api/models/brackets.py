"""Response models of `api/routes/brackets.py` (DESIGN.md §10, §16.67)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, Verse

BracketShow = Literal["all", "strong", "known"]
BracketOrder = Literal["canon", "strongest"]


class KnownBracket(ApiModel):
    a: str  # the first verse(s), as written in config
    b: str  # the repeat
    found: bool
    bracket: int | None
    insertion: float | None
    p: float | None
    beats: bool  # beats its random brackets at alpha


class BracketBook(ApiModel):
    book_id: int
    brackets: int
    strong: int  # p <= alpha, one by one


class BracketsResponse(ApiModel):
    candidates: int  # verse pairs aligned
    repetitions: int  # pairs whose clause aligns
    brackets: int  # after mutual best and room for the windows
    mean: float | None  # mean bracket score
    mean_null: float | None  # ... of random brackets of the same spans
    p: float
    draws: int
    window: int
    alpha: float
    holds: bool
    leads: int  # q <= alpha
    strong: int  # p <= alpha, one by one
    known: list[KnownBracket]
    known_found: int
    known_beat: int
    known_holds: bool
    books: list[BracketBook]  # canon order


class Bracket(ApiModel):
    bracket: int
    book_id: int
    a: Verse
    b: Verse
    a_disp: list[int]  # display tokens of the repeated clause
    b_disp: list[int]
    between: int
    unit_id: str  # the chapter of the first verse, for the reader
    score: float
    n_tokens: int
    lex: float
    sem: float
    insertion: float
    p: float
    q: float | None
    known: bool


class BracketsPage(ApiModel):
    show: BracketShow
    order: BracketOrder
    book: int | None
    total: int
    offset: int
    limit: int
    items: list[Bracket]
