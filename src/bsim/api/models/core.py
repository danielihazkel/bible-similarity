"""Response models of `api/routes/core.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import (
    ApiModel,
    BookCount,
    ConcordanceHit,
    Exclude,
    GoldLink,
    LemmaForm,
    LemmaStat,
    UnitSummary,
    UnitType,
    Verse,
)

Mode = Literal["lexical", "semantic", "fused", "structural", "domain", "syntax"]


SearchMode = Literal["lexical", "semantic", "fused"]  # no morphology for free text




class UnitDetail(ApiModel):
    unit: UnitSummary
    verses: list[Verse]
    parents: list[UnitSummary]  # the units of the other types that contain its first verse
    prev_id: str | None
    next_id: str | None


class Breakdown(ApiModel):
    """`lex_*` / `sem_*` are set on fused results only (a list missing the target: None); `phr_*`
    on fused results of a unit type whose fusion has the phrase list (§16.50)."""

    score: float
    lex_score: float | None = None
    lex_rank: int | None = None
    sem_score: float | None = None
    sem_rank: int | None = None
    phr_score: float | None = None
    phr_rank: int | None = None


class PhraseInfo(ApiModel):
    score: float  # local-alignment score (idf-weighted matched lemmas minus penalties)
    n_tokens: int  # matched lemma tokens


class Hit(Breakdown):
    rank: int
    unit: UnitSummary
    verse: Verse | None = None  # verse hits
    preview: str | None = None  # larger units: start of the first verse's display text
    link: GoldLink | None = None  # None: not a Sefaria-linked pair
    phrase: PhraseInfo | None = None  # verse hits sharing an aligned phrase with the source


class SimilarResponse(ApiModel):
    unit: UnitSummary
    mode: Mode
    k: int
    exclude: list[Exclude]
    hits: list[Hit]
    phrases: bool = False  # the fused list has a third list: the phrases the units share (§16.50)


class Discovery(ApiModel):
    """An unordered strong pair without a Sefaria link (`a` = the earlier unit)."""

    score: float
    tie: float  # secondary sort: semantic score for fused pairs, else the score
    rank_ab: int | None  # rank of b in a's list; None when b is not in it
    rank_ba: int | None
    a: UnitSummary
    b: UnitSummary
    a_verse: Verse | None = None  # verse pairs
    b_verse: Verse | None = None
    a_preview: str | None = None  # larger units
    b_preview: str | None = None


class DiscoveriesResponse(ApiModel):
    unit_type: UnitType
    mode: Mode
    book: int | None
    cross_book: bool
    unit: str | None  # only the pairs this unit is in
    total: int  # pairs matching the filters
    offset: int
    limit: int
    items: list[Discovery]


class WordRef(ApiModel):
    idx: int  # words.idx (OSHB word order)
    display_idx: int | None  # index into the verse's display_tokens; None when unaligned
    in_formula: bool


class SharedLemma(ApiModel):
    lemma: str
    he_lemma: str
    formula: bool  # every occurrence in both verses lies inside a formula
    a_words: list[WordRef]
    b_words: list[WordRef]


class ExplainResponse(ApiModel):
    a: int
    b: int
    shared: list[SharedLemma]


class Pair(ApiModel):
    src: int  # verse_id in the "from" unit
    tgt: int  # its best-matching verse_id in the other unit
    cosine: float
    shared: list[LemmaForm]


class CompareResponse(ApiModel):
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


class SearchResponse(ApiModel):
    book: int | None = None
    query: str
    normalized: str
    tokens: list[str]  # lexical tokens after prefix stripping (bigrams not listed)
    mode: Mode
    k: int
    hits: list[SearchHit]


class ResolveResponse(ApiModel):
    query: str
    unit: UnitSummary | None  # the verse or chapter the query names; None if it is not a reference


class LemmaLookup(ApiModel):
    query: str
    items: list[LemmaStat]  # exact matches first, then prefixes; the commonest first


class RootRef(ApiModel):
    """A content lemma's root family (DESIGN.md §16.38), when the family has other words."""

    lemma: str
    root: str  # Strong's number of the root
    root_he: str  # the root's Strong's headword


class WordDetail(ApiModel):
    idx: int
    display_idx: int | None
    surface: str  # OSHB (WLC) form, morphemes separated by `/`
    lemma: str  # raw OSHB lemma attribute, e.g. b/7225
    morph: str | None  # OSHB code, e.g. HR/Ncfsa
    morph_he: list[str]  # Hebrew description per morpheme (text/morph.py)
    in_formula: bool
    lemmas: list[LemmaStat]  # its content lemmas
    domains: list[str]  # SDBH domain codes of its content morphemes (`/domains` names them)
    roots: list[RootRef] = []  # its content lemmas' root families (`bsim roots`)


class ConcordanceResponse(ApiModel):
    lemma: str
    he_lemma: str
    n_words: int
    n_verses: int
    by_book: list[BookCount]  # canon order, books without it left out
    book: int | None
    total: int  # verses after the book filter
    offset: int
    limit: int
    items: list[ConcordanceHit]


class Meta(ApiModel):
    build: dict[str, Any]  # the DB `meta` table
    runtime: dict[str, Any]


class EvalResponse(ApiModel):
    splits: dict[str, Any]  # artifacts/eval/metrics.json `splits` (empty before `bsim eval`)
    openbible: dict[str, Any] | None  # artifacts/eval/openbible.json
    etcbc: dict[str, Any] | None  # artifacts/eval/etcbc.json
    supervision: dict[str, Any] | None  # artifacts/eval/supervision_experiments.json
    encoders: dict[str, Any] | None  # artifacts/eval/encoder_experiments.json
    units: dict[str, Any] | None  # artifacts/eval/unit_experiments.json
    final: dict[str, dict[str, str]]  # unit type -> mode -> system served for it
