"""How often each detector is right, by Claude's reading (DESIGN.md §16.86, D142, D147)."""

from __future__ import annotations

from bsim.api.models.common import ApiModel


class PrecisionRow(ApiModel):
    """One population judged: `strongest` (a detector's strongest findings), `shown` (what its
    page lists by default) or `marked` (what the page marks as strong)."""

    set: str
    population: int | None  # the size of the list drawn from (None for M152's run)
    judged: int
    right: int
    wrong: int
    unsure: int
    precision: float | None  # right / (right + wrong)
    lo: float | None  # Wilson 95 % interval
    hi: float | None


class PrecisionRun(ApiModel):
    run: str  # its folder under artifacts/
    population: str  # strongest | pages
    model: str
    collected_at: str
    places_right: str  # the calibration, "45 / 50"
    known_right: str


class DetectorPrecisionResponse(ApiModel):
    runs: list[PrecisionRun]
    detectors: dict[str, list[PrecisionRow]]
