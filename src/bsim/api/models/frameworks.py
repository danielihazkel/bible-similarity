"""Response models of `api/routes/frameworks.py` (DESIGN.md §10, §16.71)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, Verse


class SlotHit(ApiModel):
    slot: str
    verse_id: int | None  # where it is found (None: absent)
    ref: str | None
    ref_he: str | None


class Episode(ApiModel):
    episode: str
    judge: str  # Hebrew
    seq: int
    ref: str  # the episode's first verse
    ref_he: str
    first_vid: int
    last_vid: int
    n_slots: int
    share: float
    slots: list[SlotHit]  # in the order of `frameworks.slots`


class FrameworkKing(ApiModel):
    king: str
    name: str  # Hebrew
    kingdom: Literal["judah", "israel"]
    seq: int  # the order of the formulas in the text
    first_vid: int
    verdict: Literal["good", "bad"] | None
    verdict_verse: Verse | None
    slots: list[SlotHit]  # the regnal slots, in the order of `frameworks.regnal`


class KnownCycle(ApiModel):
    episode: str
    expect: str
    missing: list[str]
    holds: bool


class KnownVerdict(ApiModel):
    king: str
    expected: str
    found: str | None
    holds: bool


class FrameworksResponse(ApiModel):
    episodes: list[Episode]
    slots: list[str]
    open: int
    rho: float
    cycle_p: float
    cycle_holds: bool
    known_cycle: list[KnownCycle]
    known_cycle_holds: bool
    kings: list[FrameworkKing]
    verdicts: int
    good: int
    bad: int
    within: dict[str, float]  # kingdom -> mean cosine of its verdicts' wording
    within_all: float | None
    between: float | None
    difference: float
    expected: float
    verdict_p: float
    verdict_holds: bool
    known_verdicts: list[KnownVerdict]
    known_verdicts_holds: bool
    regnal: list[str]
    by_kingdom: dict[str, dict[str, float]]  # kingdom -> slot (and verdict_vid) -> share of kings
    shuffles: int
    alpha: float
