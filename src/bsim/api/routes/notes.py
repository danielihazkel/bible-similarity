"""Claude's note on a verse pair (DESIGN.md §16.88, D144): a suggestion, personal only."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from bsim.api import notes
from bsim.api.models.notes import PairNoteResponse
from bsim.api.routes._common import State

router = APIRouter()


@router.get("/pair-note", response_model=PairNoteResponse)
def pair_note(a: int, b: int, state: State) -> dict[str, Any]:
    """The note on verses `a` and `b` (verse ids, either order), and the runs notes come from."""
    runs, _ = notes.notes(state.cfg)
    return {"note": notes.note_for(state.cfg, a, b), "runs": runs}
