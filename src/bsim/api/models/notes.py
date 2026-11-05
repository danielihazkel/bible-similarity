"""Claude's notes on verse pairs (DESIGN.md §16.88, D144)."""

from __future__ import annotations

from bsim.api.models.common import ApiModel


class PairNote(ApiModel):
    """Claude's reading of a verse pair: a suggestion, never a label."""

    verdict: str  # real | not | unsure
    p_real: float
    kind: str  # one of llm_triage.KINDS
    rationale: str | None  # in Hebrew; None when it glossed a word (D134)
    run: str  # the run it comes from (llm_notes, llm_pool, llm_train, llm_rerank, llm)


class NoteRun(ApiModel):
    model: str
    auc: float | None
    pairs: int


class PairNoteResponse(ApiModel):
    note: PairNote | None
    runs: dict[str, NoteRun]
