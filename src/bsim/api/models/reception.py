"""Response models of `api/routes/reception.py` (DESIGN.md §10, §16.77)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, Page, Verse

Corpus = Literal["mishnah", "tosefta", "bavli", "yerushalmi"]


class ReceptionCounts(ApiModel):
    """Citations (a rabbinic passage with a verse) by corpus."""

    mishnah: int
    tosefta: int
    bavli: int
    yerushalmi: int
    total: int


class ReceptionBook(ReceptionCounts):
    book_id: int
    verses: int


class ReceptionChapter(ReceptionCounts):
    book_id: int
    chapter: int
    unit_id: str
    verses: int


class KnownCitation(ApiModel):
    cite: str  # the passage as Sefaria cites it
    ref: str  # the verse
    verse: Verse | None
    found: bool


class ReceptionResponse(ApiModel):
    citations: int
    verses_cited: int
    by_corpus: dict[str, int]
    passages: dict[str, int]  # rabbinic passages citing at least one verse, by corpus
    dropped_long: int  # links to more than `max_span` verses, not counted per verse
    legal_verses: int  # the Torah's verses in the law's blocks
    narrative_verses: int
    ratios: dict[str, float]  # the Torah's citations per verse of the law over the narrative's
    law_p: float  # the Mishnah's ratio against the law's blocks shifted round each book
    law_holds: bool
    gap: float  # the Mishnah's ratio less the Bavli's
    gap_p: float  # ... against the corpus of each citation shuffled between the two
    gap_holds: bool
    known: list[KnownCitation]
    known_holds: bool
    max_span: int
    shifts: int
    alpha: float
    books: list[ReceptionBook]  # canon order
    chapters: list[ReceptionChapter]  # canon order


class ReceptionVerse(ReceptionCounts):
    verse: Verse


class ReceptionVersesResponse(Page[ReceptionVerse]):
    corpus: Corpus | None
    book: int | None


class ReceptionCitation(ApiModel):
    corpus: Corpus
    title: str  # Sefaria's title of the text
    cite: str  # the passage as Sefaria cites it (Berakhot 2a:1)
    cite_he: str  # ... in Hebrew, as printed editions cite it
    url: str  # the passage on Sefaria, in Hebrew
    verse_id: int
    ref: str
    ref_he: str


class ReceptionCitationsResponse(Page[ReceptionCitation]):
    unit_id: str
    corpus: Corpus | None
    counts: ReceptionCounts  # the unit's citations by corpus (all pages)
