"""Response models of `api/routes/domains.py` (DESIGN.md §10)."""

from __future__ import annotations

from bsim.api.models.common import ApiModel, BookCount, UnitSummary, Verse


class DomainInfo(ApiModel):
    """An SDBH lexical semantic domain (DESIGN.md §16.22); counts include its subdomains."""

    code: str  # 3 digits per level
    level: int
    parent: str | None
    label_en: str
    n_verses: int
    weight: float  # content words in it (a word split over k domains counts 1/k)


class DomainHit(ApiModel):
    verse: Verse
    label_en: str
    label_he: str
    display_idxs: list[int]  # display tokens in the domain
    weight: float


class DomainResponse(ApiModel):
    domain: DomainInfo
    path: list[DomainInfo]  # its broader domains, from the top
    children: list[DomainInfo]
    by_book: list[BookCount]
    book: int | None
    total: int
    offset: int
    limit: int
    items: list[DomainHit]


class DomainShare(ApiModel):
    domain: DomainInfo
    weight: float  # its content words in the unit
    expected: float  # at the corpus share
    lift: float
    g2: float  # Dunning's G², negative when under-represented


class UnitDomains(ApiModel):
    unit: UnitSummary
    total: float  # tagged content words in the unit
    themes: list[DomainShare]  # most over-represented domains below the top level
    broad: list[DomainShare]  # every second-level domain present, largest first
