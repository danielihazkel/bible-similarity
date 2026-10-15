"""Response models of `api/routes/ciphers.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel, Verse, VerseLabel

CipherName = Literal["atbash", "albam"]


class CipherForm(ApiModel):
    form: str  # the text in the cipher, word by word, final letters at word ends
    n_words: int  # times this form is written in the Bible (0: nowhere; `bsim gematria`)


class CipherValueResponse(ApiModel):
    text: str
    atbash: CipherForm
    albam: CipherForm


class CipherKnown(ApiModel):
    """A case named in advance and whether it is found (§16.54)."""

    verse: VerseLabel
    cipher: CipherName
    text: str  # as written
    name: str  # what it reads as
    found: bool


class CipherChapter(ApiModel):
    cipher: CipherName
    unit_id: str
    label_en: str
    label_he: str
    hits: int
    expected: float  # mean hits of the random pairings
    p: float
    q: float


class CiphersResponse(ApiModel):
    meta: dict[str, Any]  # counts, the checks (`tests`), the parameters
    known: list[CipherKnown]
    chapters: list[CipherChapter]  # chapters with a hit, per cipher, lowest p first


class CipherHit(ApiModel):
    hit_id: int
    cipher: CipherName
    unit_id: str  # its chapter
    verse: Verse
    first_tok: int  # display tokens of the span
    last_tok: int
    span: str
    reads: str  # the name it reads as
    name_lemma: str
    known: str | None  # the case named in advance it is


class CipherHitsResponse(ApiModel):
    cipher: CipherName | None
    book: int | None
    unit: str | None
    known: bool
    total: int
    offset: int
    limit: int
    items: list[CipherHit]  # canon order
