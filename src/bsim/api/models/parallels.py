"""Response models of `api/routes/parallels.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import ApiModel, UnitSummary, Verse

DiffOp = Literal["spelling", "form", "substitution", "omitted", "added", "moved"]


SequenceDirection = Literal["forward", "reverse", "mixed"]  # mirrored order; reordered
RewriteOp = Literal["substitution", "omitted", "added"]


class ChangeExample(ApiModel):
    seq_id: int
    a: int
    b: int
    a_label: str
    b_label: str
    a_label_he: str
    b_label_he: str


class ChangeGroup(ApiModel):
    """One kind of change between parallel verses, e.g. יהוה → אלהים."""

    a_key: str | None  # word key in the earlier passage (None: added; spelling / form groups)
    b_key: str | None  # in the later passage (None: omitted / moved; spelling / form groups)
    a_form: str | None = None  # written forms: how spelling / form changes are grouped
    b_form: str | None = None
    a_he: str | None  # what to show: the lemma's display form, or the written form
    b_he: str | None
    count: int
    n_sequences: int
    examples: list[ChangeExample]


class ChangesResponse(ApiModel):
    op: DiffOp
    a_book: int | None
    b_book: int | None
    unit: str | None  # only verse pairs with a side in this unit
    totals: dict[str, int]  # changes per op under the book filters
    total: int  # groups
    offset: int
    limit: int
    items: list[ChangeGroup]


class VerseDiff(ApiModel):
    """Word-level changes from verse a to verse b: display token index -> op."""

    a: int
    b: int
    a_marks: dict[int, DiffOp]
    b_marks: dict[int, DiffOp]
    counts: dict[str, int]  # ops incl. `same`
    shared: float  # share of the shorter verse's words that keep their lemma
    loose: bool  # below `diffs.min_shared`: no marks (not a close parallel)


class SequenceSummary(ApiModel):
    """Two passages running parallel in the same verse order (DESIGN.md §16.7)."""

    seq_id: int
    a_start: int
    a_end: int
    b_start: int
    b_end: int
    direction: SequenceDirection = "forward"
    a_label: str  # "Genesis 24:2–16"
    b_label: str
    a_label_he: str
    b_label_he: str
    a_book: int
    b_book: int
    same_chapter: bool
    n_pairs: int  # aligned verse pairs
    score: float  # chain score (pair weights minus gap costs)
    q: float  # expected share of chance chains at least this strong
    n_gold: int  # aligned pairs that are Sefaria links


class BookSpan(ApiModel):
    book_id: int
    start: int  # first verse id
    end: int  # last verse id


class SequenceArcsResponse(ApiModel):
    """Every chain at once, for the arc diagram across the canon."""

    max_q: float | None
    direction: str | None
    total: int  # chains matching; at most `serve.max_arcs` are returned, strongest first
    books: list[BookSpan]
    items: list[SequenceSummary]


class SequencesResponse(ApiModel):
    book: int | None
    cross_book: bool
    hide_same_chapter: bool
    max_q: float | None
    min_pairs: int
    unit: str | None
    direction: SequenceDirection | None = None
    total: int
    offset: int
    limit: int
    items: list[SequenceSummary]


class LadderRow(ApiModel):
    """One row of the side-by-side view: an aligned pair, or a verse skipped on one side."""

    a: int | None
    b: int | None
    weight: float | None = None  # candidate weight (1 = rank 1 in the fused list)
    cosine: float | None = None  # semantic cosine of the pair
    gold: bool = False
    a_marks: dict[int, DiffOp] = {}  # word changes (display token index -> op), aligned pairs
    b_marks: dict[int, DiffOp] = {}
    loose: bool = False  # aligned, but too different to diff word by word


class SequenceDetail(ApiModel):
    sequence: SequenceSummary
    rows: list[LadderRow]
    verses: dict[int, Verse]


class Rewrite(ApiModel):
    """A change one book makes consistently against another (DESIGN.md §16.16)."""

    a_book: int
    b_book: int
    op: RewriteOp
    a_key: str | None
    b_key: str | None
    a_he: str | None
    b_he: str | None
    n: int
    base: int
    rate: float | None
    g2: float
    p: float
    q: float


class RewriteProfile(ApiModel):
    a_book: int
    b_book: int
    verse_pairs: int
    a_words: int
    b_words: int
    spelling: int
    form: int
    substitution: int
    omitted: int
    added: int
    moved: int
    to_plene: int
    to_defective: int


class RewritesResponse(ApiModel):
    a_book: int | None
    b_book: int | None
    op: RewriteOp | None
    max_q: float | None
    total: int
    offset: int
    limit: int
    items: list[Rewrite]


class AlignedVerb(ApiModel):
    a_vid: int
    b_vid: int
    lemma: str
    he_lemma: str


class TypeScene(ApiModel):
    """Two passages whose actions follow the same order (DESIGN.md §16.20)."""

    a: UnitSummary
    b: UnitSummary
    score: float
    n_matches: int
    aligned: list[AlignedVerb]
    parallel_text: bool
    q: float


class TypeScenesResponse(ApiModel):
    book: int | None
    max_q: float | None
    hide_textual: bool
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[TypeScene]
