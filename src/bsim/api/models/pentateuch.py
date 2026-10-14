"""Response models of `api/routes/pentateuch.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any

from bsim.api.models.common import ApiModel


class SourceWord(ApiModel):
    token: str  # Strong's number (`@h` / `@q`: the stem), or `p:x` for a prefix
    he: str | None
    weight: float  # standardized coefficient toward the side


class SourceSynonym(ApiModel):
    name: str
    members: list[str]
    he: list[str | None]
    p_like: list[int]  # uses of each member on the P-like side
    non_p: list[int]


class PentateuchResponse(ApiModel):
    meta: dict[str, Any]  # tests, confusion, books, names, grid, parameters
    p_like: list[SourceWord]  # the words that pull a verse to the P-like side most
    non_p: list[SourceWord]
    synonyms: list[SourceSynonym]


class SourceChapter(ApiModel):
    unit_id: str
    label: str
    label_he: str
    book_id: int
    chapter: int
    verses: int
    p_like: float  # share of its verses on the P-like side
    assigned: int
    p_ref: float | None  # share of its assigned verses the reference calls P


class PentateuchChaptersResponse(ApiModel):
    book: int | None
    total: int
    offset: int
    limit: int
    items: list[SourceChapter]
