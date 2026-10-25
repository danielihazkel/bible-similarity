"""Response models of `api/routes/align.py` (DESIGN.md §10, §16.73)."""

from __future__ import annotations

from bsim.api.models.common import ApiModel


class WordLink(ApiModel):
    a_display: int | None  # the word's display token in verse a
    b_display: int | None
    a_form: str  # consonantal, as the encoder read it
    b_form: str
    cos: float
    same_lemma: bool  # a shared word, not only a link of meaning


class AlignResponse(ApiModel):
    a: int
    b: int
    encoder: str | None  # the final semantic encoder
    min_cos: float
    links: list[WordLink]  # best first
