"""Response models of `api/routes/haftarot.py` (DESIGN.md §10, §16.69)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel

HaftarahTheme = Literal["admonition", "consolation"]


class HaftarahMode(ApiModel):
    mrr: float  # over the haftarot the calendar does not fix
    hits: int  # within the list's length
    median: float  # median rank
    pct: float  # mean rank percentile (0: first of the chapters)


class KnownHaftarah(ApiModel):
    parasha: str
    rank: int
    holds: bool


class HaftarahChapter(ApiModel):
    rank: int
    unit_id: str
    label_en: str
    label_he: str
    lex_rank: int
    sem_rank: int
    haftarah: bool  # holds the haftarah's verses


class Haftarah(ApiModel):
    parasha: str  # unit id
    num: int
    label_en: str
    label_he: str
    theme: HaftarahTheme | None  # fixed by the calendar
    haft: str  # Ashkenazi haftarah refs
    seph: str | None  # Sephardi, where it differs
    chapters: list[str]  # the chapter units holding it
    chapter_labels: list[str]  # their English labels
    chapter_labels_he: list[str]
    rank_lexical: int
    rank_semantic: int
    rank_fused: int
    pct: float
    known: bool
    top: list[HaftarahChapter]  # the parasha's first chapters of the Prophets (fused)


class HaftarotResponse(ApiModel):
    candidates: int  # chapters of the Prophets
    thematic: int  # haftarot the calendar does not fix
    claim_mode: str
    shuffles: int
    alpha: float
    list: int
    thematic_pct: float
    shuffled_pct: float
    p: float
    holds: bool
    calendar_pct: float
    difference: float
    calendar_p: float
    calendar_holds: bool
    modes: dict[str, HaftarahMode]
    known: list[KnownHaftarah]
    known_rank: int
    known_holds: bool
    parashot: list[Haftarah]  # in order
