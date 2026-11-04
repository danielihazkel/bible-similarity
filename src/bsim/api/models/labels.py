"""Response models of `api/routes/labels.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from bsim.api.models.common import ApiModel, UnitSummary, Verse


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


class Suggestion(ApiModel):
    """Claude's reading of a queue pair (`bsim llm-triage`, DESIGN.md §16.81): never a label."""

    verdict: Literal["real", "not", "unsure"]
    p_real: float  # its probability that the connection is real
    kind: str  # one of llm_triage.KINDS (quotation, allusion, parallel_account, ...)
    rationale: str | None  # naming Hebrew words; English glosses removed, None if it glosses


class LlmTriage(ApiModel):
    """The run the suggestions come from, and its calibration."""

    model: str
    rationale: Literal["hebrew", "english"]  # the language its rationales are in
    collected_at: str
    auc: float | None  # p_real, Sefaria dev links against random dev pairs
    min_auc: float
    holds: bool  # suggestions are shown only when it does
    pairs: int  # pairs triaged


class QueueItem(ApiModel):
    """A pair of the label queue (DESIGN.md §16.79): two train-book verses the modes rank apart."""

    a: Verse  # the earlier verse
    b: Verse
    a_id: str
    b_id: str
    lex_rank: int | None  # best rank of the pair in either verse's lexical list (None: beyond k)
    sem_rank: int | None
    disagreement: int  # |lex_rank - sem_rank|, a rank beyond the lists counted as k + 1
    side: Literal["lexical", "semantic", "both"]  # the mode that ranks it higher
    score: float  # its fused score
    suggestion: Suggestion | None = None  # when `bsim llm-triage` read it and its calibration holds


class LabelQueue(ApiModel):
    writable: bool
    split: str  # the split whose books the pairs are between (labels.queue.split)
    k: int  # the component lists' depth (retrieval.k)
    pool: int  # the pairs of the queue, labelled or not
    labelled: int  # of them already labelled
    train_real: int  # your real verse pairs between two books of the split (any page)
    min_train: int  # what training on them needs (labels.min_train)
    llm: LlmTriage | None  # the last `bsim llm-triage` run (None: never run)
    total: int  # unlabelled pairs of the side asked for
    items: list[QueueItem]  # the first `limit` of them, most disagreement first
