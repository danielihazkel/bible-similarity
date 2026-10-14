"""Response models of `api/routes/labels.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from bsim.api.models.common import ApiModel, UnitSummary


class LabelIn(BaseModel):
    """A judgement of a pair (PUT /labels), in either order."""

    a_id: str
    b_id: str
    label: Literal["real", "not", "unsure"]
    note: str = ""
    mode: str | None = None  # the list the pair was judged in
    score: float | None = None


class Label(ApiModel):
    """A labelled pair (DESIGN.md §16.25); `a` starts earlier in the canon."""

    unit_type: str
    a: UnitSummary
    b: UnitSummary
    label: Literal["real", "not", "unsure"]
    note: str
    mode: str | None
    score: float | None
    labeled_at: str


class LabelsResponse(ApiModel):
    writable: bool  # serve.labels_writable
    counts: dict[str, int]  # real / not / unsure
    items: list[Label]  # most recent first


class LabelSeparation(ApiModel):
    """How one mode's lists separate your real pairs from your not pairs."""

    unit_type: str
    mode: str
    n_real: int
    n_not: int
    found_real: int  # ranked within `k` by either unit
    found_not: int
    recall: float | None  # found_real / n_real
    precision: float | None  # found_real / (found_real + found_not)
    auc: float | None  # reciprocal rank, real vs not (None below labels.min_pairs of either)


class LabelsEval(ApiModel):
    k: int
    min_pairs: int
    rows: list[LabelSeparation]
