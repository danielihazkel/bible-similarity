"""Response models of `api/routes/vocabulary.py` (DESIGN.md §10, §16.76)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, Verse

Section = Literal["Torah", "Prophets", "Writings"]


class VocabularyBook(ApiModel):
    book_id: int
    words: int  # counted words: Hebrew, not proper names
    lemmas: int
    new: int  # lemmas found in no book before it
    new_per_k: float
    expected: float  # new lemmas by Heaps' law, in canon order
    excess: float  # log((new + 1) / (expected + 1))
    novelty: float  # the mean excess over random book orders
    hapax: int
    hapax_per_k: float
    one_corpus: int
    end_words: int  # the canon's words and vocabulary at the book's end
    end_lemmas: int
    period: Literal["early", "late"] | None


class KnownRare(ApiModel):
    book: str  # OSIS
    book_id: int
    rank: int | None  # by hapax per 1,000 words
    at_most: int
    holds: bool


class VocabularyResponse(ApiModel):
    words: int
    lemmas: int
    hapax: int
    one_corpus: dict[str, int]  # lemmas found in one corpus only, by corpus
    heaps_k: float
    heaps_b: float
    late_novelty: float
    early_novelty: float
    difference: float
    late_p: float
    splits: int
    late_holds: bool
    known: list[KnownRare]
    known_holds: bool
    orders: int
    alpha: float
    books: list[VocabularyBook]  # canon order


class LemmaFirst(ApiModel):
    """A lemma's place in the vocabulary (`bsim vocabulary`), on its concordance."""

    first_verse: Verse  # its first occurrence, in canon order
    first_tok: int | None  # ... its display token
    n_books: int
    section: Section | None  # when found in one corpus only
    counted: bool  # Hebrew, not a proper name
    hapax: bool
