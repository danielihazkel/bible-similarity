"""Response models of `api/routes/gematria.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Literal

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
