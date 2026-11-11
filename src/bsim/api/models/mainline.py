"""The narrative main line and its pauses (DESIGN.md §16.91, D153)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, Page, Verse

MainlineOrder = Literal["longest", "canon"]


class MainlineClaim(ApiModel):
    excess: float  # background share among a paragraph's first clauses, less the rest's
    null_mean: float  # the same with the clause order shuffled within paragraphs
    p: float
    holds: bool
    paragraphs: int


class MainlineKnown(ApiModel):
    ref: str
    found: bool
    pause: int | None


class MainlineBook(ApiModel):
    book_id: int
    main: int
    background: int
    share: float | None  # main / (main + background)
    pauses: int


class MainlineResponse(ApiModel):
    clauses: int
    main: int
    background: int
    pauses: int
    min_run: int
    max_run: int
    opening: int
    claim: MainlineClaim
    shuffles: int
    alpha: float
    known: list[MainlineKnown]
    known_found: int
    books: list[MainlineBook]


class MainlinePause(ApiModel):
    pause_id: int
    unit_id: str
    book_id: int
    first_vid: int
    last_vid: int
    first_label: str
    last_label: str
    first_label_he: str
    last_label_he: str
    n_clauses: int
    types: list[str]  # BHSA clause types, in order
    known: bool
    verses: list[Verse]  # its verses, at most `serve.mainline.verses`


class MainlinePauses(Page[MainlinePause]):
    order: MainlineOrder
    book: int | None
