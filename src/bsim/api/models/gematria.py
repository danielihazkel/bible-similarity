"""Response models of `api/routes/gematria.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel, Verse, VerseLabel

GematriaSystem = Literal["standard", "gadol", "ordinal", "katan"]


class GematriaValues(ApiModel):
    """A text's value in each system (§16.53)."""

    standard: int  # א 1 … ת 400, a final form as its letter
    gadol: int  # the final forms ך ם ן ף ץ at 500 … 900
    ordinal: int  # a letter's place, 1 … 22
    katan: int  # the standard value without its zeros, 1 … 9 a letter


class GematriaValueResponse(ApiModel):
    text: str
    letters: str  # its Hebrew letters, without spaces
    values: GematriaValues


class GematriaKnown(ApiModel):
    """A traditional equivalence of `gematria.known` and its standard value."""

    text: str
    value: int


class GematriaResponse(ApiModel):
    """How much of the text has one value in one system."""

    computed: bool  # `bsim gematria` ran for this build
    value: int
    system: GematriaSystem
    forms: int  # word forms
    words: int  # ... their occurrences
    lemmas: int
    verses: int
    known: list[GematriaKnown]  # every equivalence of the config, whatever its value


class GematriaForm(ApiModel):
    form: str  # consonants, as written (qere)
    values: GematriaValues
    n_words: int
    n_verses: int
    verses: list[VerseLabel]  # its first verses


class GematriaFormsResponse(ApiModel):
    value: int
    system: GematriaSystem
    total: int
    offset: int
    limit: int
    items: list[GematriaForm]  # commonest first


class GematriaLemma(ApiModel):
    lemma: str
    he: str  # the form valued: Strong's headword (pointed), else the commonest form
    values: GematriaValues
    n_words: int


class GematriaLemmasResponse(ApiModel):
    value: int
    system: GematriaSystem
    total: int
    offset: int
    limit: int
    items: list[GematriaLemma]  # commonest first


class GematriaVerse(ApiModel):
    verse: Verse
    label_en: str
    label_he: str
    values: GematriaValues
    n_letters: int
    n_words: int


class GematriaVersesResponse(ApiModel):
    value: int
    system: GematriaSystem
    book: int | None
    total: int
    offset: int
    limit: int
    items: list[GematriaVerse]  # canon order


LinkMeasure = Literal["domains", "root", "vector"]


class LinkTest(ApiModel):
    """Equal-value (or one-root) pairs against matched pairs on one measure (§16.59)."""

    n: int  # pairs
    observed: float  # their mean relatedness
    null_mean: float  # the matched pairs' mean over the draws
    null_q05: float
    null_q95: float
    p: float  # the share of draws as related
    unmatched: float  # share of matched draws that found no partner


class LinkLemma(ApiModel):
    lemma: str
    he: str  # its Strong's headword (pointed), as `gematria_lemmas`
    n_words: int


class LinkEquivalence(ApiModel):
    """A traditional equivalence: its relatedness and rank among all equal-value pairs."""

    a_text: str
    b_text: str
    found: bool  # both are lemmas of the test
    a: LinkLemma | None = None
    b: LinkLemma | None = None
    value: int | None = None
    equal: bool | None = None
    domains: float | None = None
    root: float | None = None
    vector: float | None = None
    domains_rank: float | None = None  # share of equal-value pairs less related
    root_rank: float | None = None
    vector_rank: float | None = None


class LinkProperty(ApiModel):
    key: str
    kind: Literal["words", "letters", "multiple", "triangular", "prime_factors"]
    n: int | None
    holds_here: bool  # in the verse named
    verses: int  # verses that have it


class LinkVerse(ApiModel):
    """The numbers claimed for one verse (Gen 1:1), counted over every verse."""

    verse: VerseLabel
    value: int
    words: int
    letters: int
    largest_prime: int
    n_verses: int
    all: int  # verses with every property
    expected_all: float  # ... if the properties were independent
    unique_here: bool  # the only verse with its own word count, letter count and largest prime
    unique_share: float  # share of verses that are the only one with their own
    twins: list[VerseLabel]  # the others with its own
    properties: list[LinkProperty]


class GematriaLinksResponse(ApiModel):
    meta: dict[str, Any]  # system, draws, alpha, lemmas, pairs, same_letters, tested, root_pairs
    equal: dict[LinkMeasure, LinkTest]  # equal-value pairs against matched pairs
    root_family: dict[LinkMeasure, LinkTest]  # the check: pairs of one root family
    equivalences: list[LinkEquivalence]
    verse: LinkVerse | None


class GematriaPair(ApiModel):
    a: LinkLemma
    b: LinkLemma
    value: int
    same_letters: bool
    domains: float
    root: bool
    vector: float


class GematriaPairsResponse(ApiModel):
    value: int | None
    sort: Literal["vector", "domains", "value"]
    same_letters: bool  # pairs spelled alike included
    total: int
    offset: int
    limit: int
    items: list[GematriaPair]
