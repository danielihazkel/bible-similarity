"""Response models of `api/routes/syntax.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel, UnitSummary


class ClauseSegment(ApiModel):
    """Consecutive words of a clause in one phrase (BHSA, DESIGN.md §16.26)."""

    function: str  # Pred, Subj, Objc, ... ('' outside any phrase)
    typ: str  # phrase type: VP, NP, PP, ...
    text: str  # the OSHB words, pointed


AddresseeSource = Literal["explicit", "vocative", "pronoun", "turn"]


class ClauseInfo(ApiModel):
    typ: str  # clause type: WayX, xQtX, NmCl, ...
    kind: str  # VC | NC | WP
    txt: str  # text type with its embedding (N, NQ, ?NQQ, ...)
    rela: str  # relation to another clause ('NA' / '' none)
    speech: bool  # direct speech (txt ends in Q)
    speaker: str | None  # lemma
    speaker_he: str | None
    speaker_source: Literal["explicit", "carried", "enclosing"] | None
    divine: bool
    addressee: str | None  # lemma (§16.44)
    addressee_he: str | None
    addressee_source: AddresseeSource | None
    segments: list[ClauseSegment]


class VerseSyntax(ApiModel):
    verse_id: int
    ref: str
    ref_he: str
    clauses: list[ClauseInfo]


class SyntaxNeighbor(ApiModel):
    unit: UnitSummary
    score: float
    preview: str


class UnitSyntax(ApiModel):
    verses: list[VerseSyntax]  # empty without `bsim syntax`
    neighbors: list[SyntaxNeighbor]  # verse units: verses built the same way


class SpeakerTarget(ApiModel):
    key: str  # addressee lemma, or `divine` (the divine names together)
    he: str | None  # None for `divine`
    n_quotes: int


class SpeakerInfo(ApiModel):
    lemma: str
    he: str
    n_words: int
    n_explicit: int
    divine: bool
    to: list[SpeakerTarget] = []  # whom they speak to most (`bsim dialogue`; a book's speakers)


class SpeechShares(ApiModel):
    narration: float
    speech: float
    discourse: float
    divine: float
    attributed: float
    n_words: int


class SpeechBook(SpeechShares):
    book_id: int
    speakers: list[SpeakerInfo]  # the most words first (top `speech_speakers`)


class SpeechChapter(SpeechShares):
    unit_id: str
    chapter: int


class SpeechResponse(ApiModel):
    meta: dict[str, Any]  # `bsim syntax` counts: clauses, speech_clauses, speaker sources
    books: list[SpeechBook]


class SpeechBookResponse(ApiModel):
    book_id: int
    chapters: list[SpeechChapter]
    speakers: list[SpeakerInfo]


class VoiceSpeaker(ApiModel):
    key: str  # speaker lemma, or `divine` (the divine names together)
    he: str | None  # Hebrew form of the lemma; None for `divine`
    n_words: int
    n_explicit: int  # words whose introduction names the speaker itself
    n_clauses: int
    main_book: int
    books: list[int]  # most words first
    delta: float  # Burrows' Delta to the other attributed speech of the same books
    null_mean: float  # ... expected under the within-book label shuffle
    effect: float  # (delta - null mean) / null sd
    p: float
    q: float


class VoicePair(ApiModel):
    a: str  # speaker keys, `narrator`, `unattributed`
    b: str
    delta: float


class VoicesResponse(ApiModel):
    meta: dict[str, Any]  # `bsim voices`: counts, calibration, sensitivity, order, checks
    speakers: list[VoiceSpeaker]  # empty without `bsim voices`
    pairs: list[VoicePair]


class VoiceFeature(ApiModel):
    side: Literal["over", "under"]
    rank: int
    feature: str
    label: str  # Hebrew: the lemma or the morphology feature
    rate: float  # per word in the speaker's speech
    rate_ref: float  # ... in the other attributed speech of the same books
    z: float  # (rate - rate_ref) / chapter sd


class VoiceChapter(ApiModel):
    unit_id: str
    book_id: int
    chapter: int
    n_clauses: int  # the speaker's speech clauses in it


class VoiceDetail(ApiModel):
    speaker: VoiceSpeaker
    features: list[VoiceFeature]
    nearest: list[VoicePair]  # a = this speaker, nearest first
    chapters: list[VoiceChapter]  # where the speaker talks most
