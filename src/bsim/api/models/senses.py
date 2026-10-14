"""Response models of `api/routes/senses.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, LemmaForm, Verse


class LemmaShift(ApiModel):
    """How much a lemma's senses and uses depend on the corpus group (DESIGN.md §16.23)."""

    lemma: str
    he_lemma: str
    n: int  # occurrences compared
    groups: dict[str, int]  # occurrences per corpus group
    k: int  # contextual-use clusters
    silhouette: float
    use_excess: float  # MI(group; use) in bits minus its shuffled mean
    use_q: float
    n_senses: int  # SDBH meanings compared
    sense_excess: float | None  # None: fewer than two meanings to compare
    sense_q: float | None
    nmi: float | None  # contextual clusters vs SDBH meanings
    nmi_null: float | None


class SenseExample(ApiModel):
    verse: Verse
    label_en: str
    label_he: str
    display_idx: int | None  # the occurrence's display token


class LemmaSense(ApiModel):
    kind: Literal["use", "sdbh"]  # contextual-use cluster or SDBH meaning
    sense: str  # cluster number or SDBH meaning id
    n: int
    groups: dict[str, int]
    collocates: list[LemmaForm]  # clusters: lemmas over-represented in its verses
    examples: list[SenseExample]
    domains: list[str]  # SDBH meanings: their domain codes


class LemmaSensesResponse(ApiModel):
    lemma: str
    he_lemma: str
    group_order: list[str]
    shift: LemmaShift | None  # None: the lemma was not compared (rare, or a name)
    uses: list[LemmaSense]
    senses: list[LemmaSense]


class ShiftsResponse(ApiModel):
    by: Literal["sense", "use"]
    max_q: float | None
    group_order: list[str]
    nmi_mean: float | None  # clusters vs SDBH meanings over the lemmas with both
    nmi_null_mean: float | None
    total: int
    offset: int
    limit: int
    items: list[LemmaShift]
