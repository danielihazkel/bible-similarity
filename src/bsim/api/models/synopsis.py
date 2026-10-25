"""Response models of `api/routes/synopsis.py` (DESIGN.md §10, §16.74)."""

from __future__ import annotations

from bsim.api.models.common import ApiModel, Verse
from bsim.api.models.parallels import DiffOp


class SynopsisColumn(ApiModel):
    book_id: int
    label: str  # its passages, "Psalms 105:1–15 + 96:2–12"
    label_he: str


class SynopsisSummary(ApiModel):
    """Parallel sequences joined through shared passages (DESIGN.md §16.74)."""

    syn_id: int  # its first (strongest) chain's seq_id
    seq_ids: list[int]
    columns: list[SynopsisColumn]  # the lead book's first
    n_rows: int
    n_aligned: int  # rows with verses in two or more columns
    breaks: int  # rows placed against a chain's order
    dropped: int  # aligned pairs left out (one passage twice in a row)


class SynopsesResponse(ApiModel):
    max_q: float
    items: list[SynopsisSummary]


class SynopsisCell(ApiModel):
    verse: int | None = None
    marks: dict[int, DiffOp] = {}  # display token -> change against the base column's verse
    loose: bool = False  # too different from the base's verse to diff word by word
    reordered: bool = False  # goes back from the verse above it in its column (the lead's order)


class SynopsisDetail(ApiModel):
    synopsis: SynopsisSummary
    base: int  # the column the others are marked against; its own marks: any column differs
    rows: list[list[SynopsisCell]]
    verses: dict[int, Verse]
