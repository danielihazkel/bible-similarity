"""Response models of `api/routes/segments.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel, SegmentKind, Verse


class SegmentBook(ApiModel):
    """A book's top-K gaps as a segmentation against its MAM breaks or chapters (§16.29)."""

    book_id: int
    ref: Literal["mam", "chapter"]
    k: int  # Pk window, in verses
    pk: float
    pk_null: float  # mean over K random gaps
    pk_p: float
    wd: float
    wd_null: float
    wd_p: float


class SegmentsResponse(ApiModel):
    meta: dict[str, Any]  # window, groups, contrasts, calibration, seams, agreement, kinds
    books: list[SegmentBook]


class SegmentGap(ApiModel):
    """A gap between two verses (`verse_id` = the verse after it), its cohesion and divisions."""

    verse_id: int
    book_id: int
    label: str  # the verse after the gap
    label_he: str
    score: float  # within-book percentile of the cohesion drop (1 = sharpest turn of the book)
    lex: float  # cosine across the gap, lemmas
    sem: float  # the same, embeddings
    mam: Literal["pe", "samekh"] | None
    oshb: Literal["pe", "samekh"] | None
    chapter: bool
    seam: bool
    kind: SegmentKind | None
    verses: list[Verse]  # the verse before and the verse after


class SegmentGapsResponse(ApiModel):
    kind: SegmentKind | None
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[SegmentGap]


class SegmentPoint(ApiModel):
    verse_id: int
    chapter: int
    verse: int
    score: float
    mam: Literal["pe", "samekh"] | None
    oshb: Literal["pe", "samekh"] | None
    chapter_start: bool
    seam: bool
    kind: SegmentKind | None


class SegmentCurve(ApiModel):
    book_id: int
    points: list[SegmentPoint]
    agreement: list[SegmentBook]
