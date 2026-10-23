"""Response models of `api/routes/retold.py` (DESIGN.md §10, §16.68)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, Verse
from bsim.api.models.dialogue import DialogueParty
from bsim.api.models.parallels import DiffOp

RetoldGroup = Literal["retold", "repeated", "carried", "told", "narrated", "unclear"]
RetoldOrder = Literal["canon", "most", "least"]


class KnownRetelling(ApiModel):
    source: str  # as written in config
    retelling: str
    found: bool
    pairs: list[int]
    group: RetoldGroup | None
    rate: float | None  # changed / aligned positions over its pairs


class RetoldResponse(ApiModel):
    pairs: int
    groups: dict[str, int]  # group -> retellings
    rates: dict[str, float | None]  # group -> mean change rate
    claim: list[RetoldGroup]  # the two groups compared: the first expected to change more
    difference: float | None  # mean rate of the first less the second
    p: float
    shuffles: int
    bins: int
    alpha: float
    holds: bool
    known: list[KnownRetelling]
    known_found: int
    known_holds: bool


class RetoldSide(ApiModel):
    kind: Literal["speech", "narration"]
    teller: DialogueParty | None  # the speaker (None: the narrator, or not known)
    verses: list[Verse]
    marks: list[dict[int, DiffOp]]  # per verse: display token -> its change


class RetoldPair(ApiModel):
    pair: int
    book_id: int
    group: RetoldGroup
    source: RetoldSide
    retelling: RetoldSide
    unit_id: str  # the chapter of the retelling, for the reader
    n_ops: int  # positions aligned word by word
    n_changed: int
    rate: float
    ops: dict[str, int]  # op -> positions
    score: float
    known: bool


class RetoldPage(ApiModel):
    group: RetoldGroup | None
    book: int | None
    order: RetoldOrder
    known: bool
    total: int
    offset: int
    limit: int
    items: list[RetoldPair]
