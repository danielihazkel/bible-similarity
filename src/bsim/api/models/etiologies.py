"""Response models of `api/routes/etiologies.py` (DESIGN.md §10, §16.66)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, Verse


class KnownEtiology(ApiModel):
    ref: str  # as written in config
    name: str
    found: bool  # the formula finds a naming of this name in this verse
    naming: int | None
    score: float | None
    rank_p: float | None
    echoes: bool  # its own explanation beats all but `known_rank` of the others


class Naming(ApiModel):
    naming: int
    unit_id: str  # the verse's chapter, for the reader
    verse: Verse
    name: str  # consonantal
    kind: Literal["person", "place"]
    name_first: int | None  # display tokens of the name
    name_last: int | None
    echo_word: str | None  # the explanation word that echoes the name best
    echo_disp: int | None
    words: int  # explanation words in the verse
    score: float  # share of a name word's consonants in order in that word
    chance: float | None  # the name's mean echo with the other explanations
    rank_p: float | None  # its own explanation's rank among all of them
    p: float | None  # its echo against random verses without a naming
    q: float | None  # BH of p over the namings
    known: bool


class EtiologiesResponse(ApiModel):
    namings: list[Naming]  # canon order
    places: int
    explained: int  # namings whose verse has explanation words
    mean_own: float | None  # mean echo of the names with their own explanations
    mean_null: float | None  # ... with the explanations shuffled among them
    p: float
    shuffles: int
    alpha: float
    holds: bool
    leads: int  # namings at q <= alpha
    known: list[KnownEtiology]
    known_found: int
    known_echo: int
    known_rank: float
    known_share: float
    known_holds: bool
