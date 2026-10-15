"""Response models of `api/routes/reader.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, KqClass, SegmentKind, UnitSummary


class ReaderSpeaker(ApiModel):
    lemma: str | None  # None: speech whose speaker is not known
    he: str | None
    divine: bool
    n_words: int  # display tokens of the unit spoken by them
    to: list[str]  # Hebrew forms of whom they speak to here, the most words first (§16.44)


class ReaderWordplay(ApiModel):
    display: int  # this word
    partner_vid: int
    partner_display: int | None
    partner_label: str
    partner_label_he: str
    form: str  # consonantal forms of the two words
    partner_form: str
    kind: Literal["substitution", "metathesis", "extension"]
    q: float


class ReaderKetiv(ApiModel):
    display: list[int]  # the read words
    ketiv: str
    qere: str
    cls: KqClass


class ReaderGap(ApiModel):
    """The gap before a verse (§16.29): its cohesion drop and how the text divides there."""

    score: float  # within-book percentile of the drop (1 = the book's sharpest turn)
    kind: SegmentKind | None
    mam: Literal["pe", "samekh"] | None  # paragraph break in the MAM
    chapter: bool


class ReaderRefrain(ApiModel):
    refrain_id: int
    text: str
    k: int  # verses holding it
    known: str | None


class ReaderVerse(ApiModel):
    verse_id: int
    refrains: dict[str, int]  # display token -> index into `refrains`
    mood: dict[str, Literal["distress", "praise"]]  # display token -> its SDBH domains' mood
    source: ReaderSource | None  # the P / non-P split (`bsim pentateuch`; Genesis-Numbers only)
    speech: dict[str, int]  # display token -> index into `speakers`
    phrases: dict[str, int]  # display token -> other verses sharing a phrase through it
    rare: dict[str, int]  # display token -> verses holding its rarest content word (names out)
    wordplay: list[ReaderWordplay]
    ketiv: list[ReaderKetiv]
    gap: ReaderGap | None  # flagged or a MAM break; None otherwise
    gematria: list[int]  # each display token's standard letter value (§16.53; 0: no letters)


class ReaderResponse(ApiModel):
    """The word-level layers of the layered reader (`/reader/{unit_id}`) for one unit."""

    unit: UnitSummary
    rare_verses: int  # a word is rare in at most this many verses
    computed: dict[str, bool]  # stage -> it ran (speech, phrases, wordplay, ketiv, gaps, refrains,
    # mood)
    speakers: list[ReaderSpeaker]  # most words first, the unknown speaker last
    refrains: list[ReaderRefrain]  # strongest first
    verses: list[ReaderVerse]


class ReaderSource(ApiModel):
    side: Literal["P", "nonP"]
    prob: float
    reference: Literal["P", "nonP"] | None
