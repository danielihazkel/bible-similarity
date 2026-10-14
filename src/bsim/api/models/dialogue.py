"""Response models of `api/routes/dialogue.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any

from bsim.api.models.common import ApiModel, VerseLabel


class DialogueParty(ApiModel):
    key: str  # lemma, or `divine` (the divine names together)
    he: str | None  # None for `divine`
    rank: int  # 2 God, 1 a king, 0 anyone else


class DialogueBook(ApiModel):
    book_id: int
    n_quotes: int  # quotations with a speaker and an addressee
    n_pairs: int
    n_exchanges: int


class DialogueResponse(ApiModel):
    meta: dict[str, Any]  # counts, hand check, the three checks, sensitivity, opener, lengths
    books: list[DialogueBook]


class DialoguePair(ApiModel):
    speaker: DialogueParty
    addressee: DialogueParty
    n_quotes: int
    n_words: int
    n_reliable: int  # quotations whose addressee is explicit or a vocative


class DialogueBookResponse(ApiModel):
    book_id: int
    pairs: list[DialoguePair]  # the most quotations first


class DialogueExchange(ApiModel):
    exchange: int
    book_id: int
    unit_id: str  # the chapter it starts in
    first: VerseLabel
    last_verse: VerseLabel
    a: DialogueParty  # who opens
    b: DialogueParty
    turns: int
    a_turns: int
    a_words: int
    b_words: int
    last: str  # the key of who speaks last


class DialogueExchangesResponse(ApiModel):
    book: int | None
    party: str | None
    unequal: bool
    total: int
    offset: int
    limit: int
    items: list[DialogueExchange]
