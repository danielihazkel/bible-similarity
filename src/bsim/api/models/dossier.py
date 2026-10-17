"""Response models of `api/routes/dossier.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel

DossierKind = Literal[
    "phrases", "sequences", "changes", "borrowing", "wordplay", "alliteration", "rhymes",
    "typescenes", "discoveries", "seams", "names", "acrostic", "dating", "structure", "speech",
    "voices", "network", "divisions", "ketiv", "citations", "allusions", "mirrors", "echoes",
    "meter", "roots", "refrains", "psalms", "pentateuch", "dialogue", "forms", "places",
    "ciphers", "gematria", "labels",
]  # fmt: skip


class DossierEntry(ApiModel):
    """One analysis on one unit (`/dossier`); which fields carry what depends on `kind`."""

    kind: DossierKind
    scope: Literal["unit", "chapter"]  # read on the unit itself or on its chapter
    computed: bool  # False: the stage did not run (or does not cover this unit type)
    count: int | None = None  # rows found, 1 / 0 for a yes / no finding, a rank (network)
    # divisions: count = flagged gaps in the unit; value / key = score / kind of its opening gap
    total: int | None = None  # network: units ranked; gematria: other verses of the verse's value
    # lowest q (acrostic, structure), score (dating), net fall (meter), a verse's letter value
    # (gematria)
    value: float | None = None
    # speech: speaker lemma; voices: voice profile key; places: the most named place's id;
    # ciphers: the first hit's words as written
    key: str | None = None
    # speech / voices: the speaker's Hebrew form; places: the most named place; ciphers: the name
    # the first hit reads as; gematria: the tradition's texts found (` · `)
    label: str | None = None
    target_unit: str | None = None  # the chapter read for a chapter-scope entry


class Dossier(ApiModel):
    unit_id: str
    entries: list[DossierEntry]
