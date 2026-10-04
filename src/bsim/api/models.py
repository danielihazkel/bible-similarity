"""Response models of the viewer API (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

Mode = Literal["lexical", "semantic", "fused"]


class Book(BaseModel):
    book_id: int
    name: str
    he_name: str
    osis: str
    section: str
    n_chapters: int


class UnitSummary(BaseModel):
    unit_id: str
    unit_type: str
    label_en: str
    label_he: str
    book_id: int
    start_verse_id: int
    end_verse_id: int
    n_verses: int
    marker: str | None = None


class Verse(BaseModel):
    verse_id: int
    book_id: int
    chapter: int
    verse: int
    ref: str
    text_display: str
    display_tokens: list[str]
    ketiv_note: str | None = None


class UnitDetail(BaseModel):
    unit: UnitSummary
    verses: list[Verse]
    parents: list[UnitSummary]  # the units of the other types that contain its first verse
    prev_id: str | None
    next_id: str | None


class Breakdown(BaseModel):
    """`lex_*` / `sem_*` are set on fused results only (a list missing the target: None)."""

    score: float
    lex_score: float | None = None
    lex_rank: int | None = None
    sem_score: float | None = None
    sem_rank: int | None = None


class Hit(Breakdown):
    rank: int
    unit: UnitSummary
    verse: Verse | None = None  # verse hits
    preview: str | None = None  # larger units: start of the first verse's display text


class SimilarResponse(BaseModel):
    unit: UnitSummary
    mode: Mode
    k: int
    exclude: list[str]
    hits: list[Hit]


class WordRef(BaseModel):
    idx: int  # words.idx (OSHB word order)
    display_idx: int | None  # index into the verse's display_tokens; None when unaligned
    in_formula: bool


class SharedLemma(BaseModel):
    lemma: str
    he_lemma: str
    formula: bool  # every occurrence in both verses lies inside a formula
    a_words: list[WordRef]
    b_words: list[WordRef]


class ExplainResponse(BaseModel):
    a: int
    b: int
    shared: list[SharedLemma]


class LemmaForm(BaseModel):
    lemma: str
    he_lemma: str


class Pair(BaseModel):
    src: int  # verse_id in the "from" unit
    tgt: int  # its best-matching verse_id in the other unit
    cosine: float
    shared: list[LemmaForm]


class CompareResponse(BaseModel):
    a: UnitSummary
    b: UnitSummary
    bma: float  # ½(mean best cosine A→B + mean best cosine B→A)
    a_to_b: list[Pair]
    b_to_a: list[Pair]
    verses: dict[int, Verse]  # every verse of A and B, by verse_id


class SearchHit(Breakdown):
    rank: int
    verse: Verse
    label_en: str
    label_he: str


class SearchResponse(BaseModel):
    query: str
    normalized: str
    tokens: list[str]  # lexical tokens after prefix stripping (bigrams not listed)
    mode: Mode
    k: int
    hits: list[SearchHit]


class Meta(BaseModel):
    build: dict[str, Any]  # the DB `meta` table
    runtime: dict[str, Any]
