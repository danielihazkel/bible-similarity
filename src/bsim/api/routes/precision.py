"""How often each detector is right (DESIGN.md §16.86, D147): Claude's reading, personal only."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from bsim.api import precision as pr
from bsim.api.models.precision import DetectorPrecisionResponse
from bsim.api.routes._common import State

router = APIRouter()


@router.get("/detector-precision", response_model=DetectorPrecisionResponse)
def detector_precision(state: State) -> dict[str, Any]:
    """Each audited detector's precision, one row per population judged, and the runs."""
    return pr.precision(state.cfg)
