"""Response models shared by several routes: base model, units, verses (DESIGN.md §10)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

UnitType = Literal["verse", "chapter", "pericope", "parasha"]
Exclude = Literal["neighbors", "chapter", "book", "known"]  # /similar filters


class ApiModel(BaseModel):
    """Base of every response model: a field with a default is still always present in the
    response, so the OpenAPI schema (the viewer's generated types) marks it required."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class Book(ApiModel):
    book_id: int
    name: str
    he_name: str
    osis: str
    section: str
    n_chapters: int


class UnitSummary(ApiModel):
    unit_id: str
    unit_type: UnitType
    label_en: str
    label_he: str
    book_id: int
    start_verse_id: int
    end_verse_id: int
    n_verses: int
    marker: str | None = None


class Verse(ApiModel):
    verse_id: int
    book_id: int
    chapter: int
    verse: int
    ref: str
    ref_he: str
    text_display: str
    display_tokens: list[str]
    ketiv_note: str | None = None


class GoldLink(ApiModel):
    """A Sefaria link between the two units: `verse` = a direct verse-to-verse link, `unit` =
    only a passage-level link covers them."""

    level: Literal["verse", "unit"]
    types: list[str]  # connection types (quotation, related, ...); empty when untyped


class LemmaForm(ApiModel):
    lemma: str
    he_lemma: str


class LemmaStat(ApiModel):
    lemma: str
    he_lemma: str
    n_verses: int  # verses containing it


class BookCount(ApiModel):
    book_id: int
    n_verses: int


class ConcordanceHit(ApiModel):
    verse: Verse
    label_en: str
    label_he: str
    display_idxs: list[int]  # display tokens carrying the lemma


class Leitwort(ApiModel):
    lemma: str
    he_lemma: str
    count: int
    expected: float  # occurrences expected from the corpus rate
    g2: float  # Dunning log-likelihood
    multiple_of: list[int]  # 7 / 10 when the count is a multiple
    occurrences: dict[int, list[int]]  # verse_id -> display token indices


class VerseLabel(ApiModel):
    verse_id: int
    label_en: str
    label_he: str


SegmentKind = Literal["turn", "cut", "quiet"]


KqClass = Literal[
    "vowel_letter", "swap", "vowel_position", "metathesis", "division", "qere_only", "ketiv_only",
    "same_letters", "other",
]  # fmt: skip
