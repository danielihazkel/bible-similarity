"""A unit's neighbourhood graph (DESIGN.md §11.1, D149)."""

from __future__ import annotations

from bsim.api.models.common import ApiModel, UnitSummary


class NeighbourNode(ApiModel):
    unit: UnitSummary
    hop: int  # 0 the unit itself, 1 its own list, 2 a neighbour's
    x: float  # 0..1, the unit at 0.5, 0.5
    y: float


class NeighbourEdge(ApiModel):
    a: str  # unit ids
    b: str
    kinds: list[str]  # of api/neighbourhood.KINDS, the colour's first
    score: float | None  # the fused score, for an edge of the lists


class NeighbourhoodResponse(ApiModel):
    unit: UnitSummary
    k: int
    hops: int
    truncated: bool  # max_nodes reached: some hits not drawn
    nodes: list[NeighbourNode]
    edges: list[NeighbourEdge]
