"""Response models of `api/routes/findings.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel

FindingKey = Literal[
    "acrostics", "divisions", "dating", "borrowing", "citations", "voices", "clauses", "meter",
    "cognate", "echoes", "sevens", "chiasm", "laments", "root_leitworte", "allusions", "refrains",
    "refrain_regular", "refrain_turns", "psalm_genres", "psalm_forms", "lament_turn",
    "lament_turns", "pentateuch_split", "pentateuch_genesis", "pentateuch_names",
    "dialogue_deference", "dialogue_particle", "dialogue_last_word", "forms_known", "forms_chance",
    "forms_parallel", "forms_lists", "ciphers_known", "ciphers_jeremiah", "ciphers_elsewhere",
    "ciphers_albam", "masorah_letter", "masorah_words", "masorah_verse", "masorah_books",
    "gematria_links", "gematria_measures", "gematria_genesis", "place_lists_order",
    "place_lists_districts", "place_arc_order", "place_arc_moves", "place_arc_oracles",
    "place_links_decay", "place_links_known", "els_counts", "els_known", "divine_elohistic",
    "divine_doubled", "etiology_echo", "etiology_known",
    "brackets_insertion", "brackets_known", "retold_claim", "retold_known",
]  # fmt: skip


class Finding(ApiModel):
    """One analysis's tested claim (`/findings`): the deciding numbers and the verdict they give."""

    key: FindingKey
    verdict: Literal["holds", "fails", "lead"]
    values: dict[str, float | None]  # which keys depends on `key`


class FindingsResponse(ApiModel):
    alpha: float
    items: list[Finding]  # in the order the page shows them; analyses not computed are left out
