"""Response models of `api/routes/echoes.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel, UnitSummary

EchoBasis = Literal["cited", "borrowed", "language", "conflict", "none"]


class EchoBook(ApiModel):
    src_book: int  # drawn on
    dst_book: int  # echoing it
    cited: int  # directed chapter pairs by the layer that decided them
    borrowed: int
    language: int


class EchoChapter(ApiModel):
    unit: UnitSummary
    lends: int  # directed pairs it is the source of
    borrows: int  # ... the echo of
    lends_explicit: int  # cited or borrowed only
    borrows_explicit: int


class EchoesResponse(ApiModel):
    meta: dict[str, Any]  # language_gap, pairs, bases, checks, language_forward / backward, cycles
    books: list[EchoBook]
    sources: list[EchoChapter]


class EchoEdge(ApiModel):
    """A cross-book chapter pair with a direction when a layer decides one (§16.36); a is the
    earlier in the canon."""

    edge_id: int
    a: UnitSummary
    b: UnitSummary
    weight: float  # network edge weight
    n_cited: int  # resolved citations from b into a
    borrowed: int  # +1 b borrowed from a, -1 a from b, 0 none / unclear
    gap: float | None  # late-profile score of b minus a (None: a side out of domain)
    language: int | None  # the gap's vote, 0 under the threshold
    direction: int  # +1 b echoes a, -1 a echoes b, 0 undecided
    basis: EchoBasis


class EchoListResponse(ApiModel):
    basis: EchoBasis | None
    directed: bool | None
    backward: bool | None
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[EchoEdge]
