"""Response models of `api/routes/mirrors.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any

from bsim.api.models.common import ApiModel, Verse


class MirrorsResponse(ApiModel):
    meta: dict[str, Any]  # words (all / poetry / prose), clauses (by_pair), full_mirrors


class MirrorVerse(ApiModel):
    """A verse whose twice-used lemmas all nest: A B C … C B A (§16.33)."""

    verse_id: int
    label: str
    label_he: str
    poetic: bool
    n_pairs: int
    n_words: int
    p: float
    q: float
    verse: Verse
    marks: dict[int, int]  # display token -> 0-based nesting depth of its lemma


class MirrorVersesResponse(ApiModel):
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[MirrorVerse]


class MirrorClause(ApiModel):
    """Two consecutive clauses with the same two constituents, in the same or reversed order."""

    pair_id: int
    verse_id: int
    label: str
    label_he: str
    poetic: bool
    pair: str
    first: str
    second: str
    mirrored: bool
    verse: Verse
    marks: dict[int, int]  # display token -> 0 (the first clause's first constituent) or 1


class MirrorClausesResponse(ApiModel):
    pair: str | None
    mirrored: bool | None
    poetic: bool | None
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[MirrorClause]
