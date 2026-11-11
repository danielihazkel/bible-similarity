"""A unit's parallels two hops out, as a graph (DESIGN.md §11.1, D149)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from bsim.api import neighbourhood as nb
from bsim.api.models.neighbourhood import NeighbourhoodResponse
from bsim.api.routes._common import Conn, State, unit_or_404, unprocessable

router = APIRouter()


@router.get("/neighbourhood/{unit_id}", response_model=NeighbourhoodResponse)
def neighbourhood(
    unit_id: str, state: State, conn: Conn, k: int | None = None, hops: int | None = None
) -> dict[str, Any]:
    """The unit, its fused list's hits and theirs (`hops`), each edge with the kinds that join it,
    laid out around the unit."""
    nc = state.cfg["serve"]["neighbourhood"]
    unit_or_404(conn, unit_id)
    k = nc["k"] if k is None else k
    hops = nc["hops"] if hops is None else hops
    if not 1 <= k <= nc["max_k"]:
        raise unprocessable(f"k must be 1..{nc['max_k']}")
    if not 1 <= hops <= nc["max_hops"]:
        raise unprocessable(f"hops must be 1..{nc['max_hops']}")
    return nb.neighbourhood(conn, state.cfg, unit_id, k, hops)
