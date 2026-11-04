"""`/findings`: the headline result of each analysis, from what its stage recorded (DESIGN.md §10).

Each finding names the claim an analysis tested, the numbers that decide it and a verdict computed
from them at `serve.findings.alpha`, so the page follows a rebuilt DB:

    holds   the expectation is borne out above chance (or the check passes)
    fails   it is not: no better than chance, or the data point the other way
    lead    candidates without a test that separates them from chance

The wording lives in the viewer's catalogs; an analysis whose stage did not run is left out.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter

from bsim.api.models.findings import Finding, FindingsResponse
from bsim.api.routes._common import Conn, State
from bsim.api.routes.findings.common import Meta
from bsim.api.routes.findings.language import (
    _allusions,
    _borrowing,
    _citations,
    _clauses,
    _cognate,
    _dating,
    _dialogue,
    _divisions,
    _echoes,
    _pentateuch,
    _reception,
    _root_leitworte,
    _vocabulary,
    _voices,
    _witnesses,
)
from bsim.api.routes.findings.narrative import (
    _binomials,
    _brackets,
    _divine,
    _etiologies,
    _frameworks,
    _haftarot,
    _retold,
)
from bsim.api.routes.findings.numbers import (
    _chronology,
    _ciphers,
    _els,
    _gematria_links,
    _masorah,
    _sums,
)
from bsim.api.routes.findings.places import _place_arc, _place_links, _place_lists
from bsim.api.routes.findings.poetry import (
    _acrostics,
    _chiasm,
    _forms,
    _lament_turn,
    _lament_turns,
    _laments,
    _meter,
    _psalm_forms,
    _psalm_genres,
    _refrain_regular,
    _refrain_turns,
    _refrains,
    _sevens,
)

router = APIRouter()

BUILDERS: list[Callable[[Meta, sqlite3.Connection, float], Finding | None]] = [
    _acrostics,
    _divisions,
    _dating,
    _borrowing,
    _citations,
    _voices,
    _clauses,
    _meter,
    _cognate,
    _echoes,
    _sevens,
    _chiasm,
    _laments,
    _root_leitworte,
    _refrains,
    _refrain_regular,
    _refrain_turns,
    _psalm_genres,
    _psalm_forms,
    _lament_turn,
    _lament_turns,
    _pentateuch("pentateuch_split", "kappa"),
    _pentateuch("pentateuch_genesis", "kappa_genesis"),
    _pentateuch("pentateuch_names", "names"),
    _dialogue("dialogue_deference", "deference"),
    _dialogue("dialogue_particle", "particle"),
    _dialogue("dialogue_last_word", "last_word"),
    _forms("forms_known"),
    _forms("forms_chance"),
    _forms("forms_parallel"),
    _forms("forms_lists"),
    _ciphers("ciphers_known"),
    _ciphers("ciphers_jeremiah"),
    _ciphers("ciphers_elsewhere"),
    _ciphers("ciphers_albam"),
    _divine("divine_elohistic"),
    _divine("divine_doubled"),
    _etiologies("etiology_echo"),
    _etiologies("etiology_known"),
    _brackets("brackets_insertion"),
    _brackets("brackets_known"),
    _retold("retold_claim"),
    _retold("retold_known"),
    _haftarot("haftarot_claim"),
    _haftarot("haftarot_calendar"),
    _haftarot("haftarot_known"),
    _chronology("chronology_known"),
    _chronology("chronology_syncs"),
    _chronology("chronology_digits"),
    _frameworks("frameworks_cycle"),
    _frameworks("frameworks_cycle_known"),
    _frameworks("frameworks_verdicts"),
    _frameworks("frameworks_verdicts_known"),
    _binomials("binomials_short"),
    _binomials("binomials_late"),
    _binomials("binomials_known"),
    _sums("sums_lists"),
    _sums("sums_parallels"),
    _vocabulary("vocabulary_late"),
    _vocabulary("vocabulary_known"),
    _reception("reception_law"),
    _reception("reception_bavli"),
    _reception("reception_known"),
    _witnesses("witnesses_parallel"),
    _witnesses("witnesses_known"),
    _masorah("masorah_letter"),
    _masorah("masorah_words"),
    _masorah("masorah_verse"),
    _masorah("masorah_books"),
    _gematria_links("gematria_links"),
    _gematria_links("gematria_measures"),
    _gematria_links("gematria_genesis"),
    _place_lists("place_lists_order"),
    _place_lists("place_lists_districts"),
    _place_arc("place_arc_order"),
    _place_arc("place_arc_moves"),
    _place_arc("place_arc_oracles"),
    _place_links("place_links_decay"),
    _place_links("place_links_known"),
    _els("els_counts"),
    _els("els_known"),
    _allusions,
]


@router.get("/findings", response_model=FindingsResponse)
def findings(state: State, conn: Conn) -> dict[str, Any]:
    """The tested claims of the analyses with their deciding numbers and verdicts."""
    alpha = state.cfg["serve"]["findings"]["alpha"]
    items = [f for b in BUILDERS if (f := b(state.meta, conn, alpha)) is not None]
    return {"alpha": alpha, "items": items}
