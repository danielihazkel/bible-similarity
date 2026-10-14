"""Response models of `api/routes/borrowing.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel


class SignCheck(ApiModel):
    agree: int  # sequences a sign points the accepted way
    n: int  # sequences it voted on
    p: float | None  # two-sided sign test
    unclear: int | None = None  # held-out check: sequences left undecided


class BorrowingSequence(ApiModel):
    """Which side of a cross-book parallel looks like the borrower (DESIGN.md §16.27). A is the
    side earlier in the canon; a sign > 0 says B looks later."""

    seq_id: int
    a_book: int
    b_book: int
    a_first: int
    b_first: int
    a_label: str
    b_label: str
    a_label_he: str
    b_label_he: str
    n_pairs: int
    language: float
    spelling: float | None
    smoothing: float | None
    expansion: float | None
    n_spelling: int
    n_substitution: int
    known: Literal["a_to_b", "b_to_a"] | None
    votes: int
    n_votes: int
    direction: Literal["a_to_b", "b_to_a", "unclear"]


class BorrowingBookPair(ApiModel):
    a_book: int
    b_book: int
    sequences: int
    n_pairs: int
    votes: int
    a_to_b: int
    b_to_a: int
    known: Literal["a_to_b", "b_to_a"] | None
    direction: Literal["a_to_b", "b_to_a", "unclear"]
    items: list[BorrowingSequence]


class BorrowingResponse(ApiModel):
    unit: str | None  # only the parallels touching this unit
    checks: dict[str, SignCheck]  # each sign and all four on the accepted directions
    used_signs: list[str]  # the signs that vote
    held_out: SignCheck | None  # signs chosen without each book pair, scored on it
    books: list[BorrowingBookPair]  # the most parallel verses first
