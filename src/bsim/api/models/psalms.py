"""Response models of `api/routes/psalms.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any

from bsim.api.models.common import ApiModel


class PsalmVerse(ApiModel):
    verse: int
    words: int  # without the superscription
    distress: int  # words in the `psalms.distress` domains
    praise: int


class PsalmTurn(ApiModel):
    """Where a psalm's mood rises most: the first verse after the split."""

    verse_id: int
    verse: int
    label: str
    label_he: str
    stat: float  # mood rate (praise - distress words per word) after - before
    p: float  # against verse orders shuffled within the psalm
    before: float
    after: float


class Psalm(ApiModel):
    """One psalm's form (DESIGN.md §16.42)."""

    unit_id: str
    label: str
    label_he: str
    chapter: int
    genre: str | None  # Gunkel's (core cases); None: mixed or disputed
    cluster: int  # Ward cluster of the form features
    words: int
    features: dict[str, float]  # per word: persons, imperatives, questions, distress, praise
    turn: PsalmTurn | None  # None: too short
    mood: list[PsalmVerse]


class PsalmKnownTurn(ApiModel):
    """A turn scholarship names, fixed in advance, and the split found."""

    verse_id: int
    label: str
    label_he: str
    turn_vid: int | None
    turn_label: str | None
    turn_label_he: str | None
    p: float | None
    found: bool | None  # None: the psalm is too short
    chance: float | None  # share of the possible splits within the tolerance


class PsalmsResponse(ApiModel):
    meta: dict[str, Any]  # genre test, crosstab, checks, profiles, laments vs hymns, robustness
    known: list[PsalmKnownTurn]


class PsalmsListResponse(ApiModel):
    genre: str | None
    cluster: int | None
    turned: bool
    unit: str | None
    sort: str
    total: int
    offset: int
    limit: int
    items: list[Psalm]
