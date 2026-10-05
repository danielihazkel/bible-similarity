"""Response models of the viewer API (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

Mode = Literal["lexical", "semantic", "fused", "structural"]
SearchMode = Literal["lexical", "semantic", "fused"]  # no morphology for free text


class Book(BaseModel):
    book_id: int
    name: str
    he_name: str
    osis: str
    section: str
    n_chapters: int


class UnitSummary(BaseModel):
    unit_id: str
    unit_type: str
    label_en: str
    label_he: str
    book_id: int
    start_verse_id: int
    end_verse_id: int
    n_verses: int
    marker: str | None = None


class Verse(BaseModel):
    verse_id: int
    book_id: int
    chapter: int
    verse: int
    ref: str
    text_display: str
    display_tokens: list[str]
    ketiv_note: str | None = None


class UnitDetail(BaseModel):
    unit: UnitSummary
    verses: list[Verse]
    parents: list[UnitSummary]  # the units of the other types that contain its first verse
    prev_id: str | None
    next_id: str | None


class Breakdown(BaseModel):
    """`lex_*` / `sem_*` are set on fused results only (a list missing the target: None)."""

    score: float
    lex_score: float | None = None
    lex_rank: int | None = None
    sem_score: float | None = None
    sem_rank: int | None = None


class GoldLink(BaseModel):
    """A Sefaria link between the two units: `verse` = a direct verse-to-verse link, `unit` =
    only a passage-level link covers them."""

    level: Literal["verse", "unit"]
    types: list[str]  # connection types (quotation, related, ...); empty when untyped


class PhraseInfo(BaseModel):
    score: float  # local-alignment score (idf-weighted matched lemmas minus penalties)
    n_tokens: int  # matched lemma tokens


class Hit(Breakdown):
    rank: int
    unit: UnitSummary
    verse: Verse | None = None  # verse hits
    preview: str | None = None  # larger units: start of the first verse's display text
    link: GoldLink | None = None  # None: not a Sefaria-linked pair
    phrase: PhraseInfo | None = None  # verse hits sharing an aligned phrase with the source


class SimilarResponse(BaseModel):
    unit: UnitSummary
    mode: Mode
    k: int
    exclude: list[str]
    hits: list[Hit]


class Discovery(BaseModel):
    """An unordered strong pair without a Sefaria link (`a` = the earlier unit)."""

    score: float
    tie: float  # secondary sort: semantic score for fused pairs, else the score
    rank_ab: int | None  # rank of b in a's list; None when b is not in it
    rank_ba: int | None
    a: UnitSummary
    b: UnitSummary
    a_verse: Verse | None = None  # verse pairs
    b_verse: Verse | None = None
    a_preview: str | None = None  # larger units
    b_preview: str | None = None


class DiscoveriesResponse(BaseModel):
    unit_type: str
    mode: Mode
    book: int | None
    cross_book: bool
    total: int  # pairs matching the filters
    offset: int
    limit: int
    items: list[Discovery]


class PhrasePair(BaseModel):
    """A shared phrase: `a_display` / `b_display` = the display tokens of the matched words."""

    score: float
    n_tokens: int
    spread: int  # verses sharing this exact lemma sequence (2 = only this pair)
    a: UnitSummary
    b: UnitSummary
    a_verse: Verse
    b_verse: Verse
    a_display: list[int]
    b_display: list[int]
    link: GoldLink | None = None


class PhrasesResponse(BaseModel):
    book: int | None
    cross_book: bool
    min_tokens: int
    max_spread: int | None
    total: int
    offset: int
    limit: int
    items: list[PhrasePair]


DiffOp = Literal["spelling", "form", "substitution", "omitted", "added", "moved"]


class ChangeExample(BaseModel):
    seq_id: int
    a: int
    b: int
    a_label: str
    b_label: str


class ChangeGroup(BaseModel):
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


class ChangesResponse(BaseModel):
    op: DiffOp
    a_book: int | None
    b_book: int | None
    totals: dict[str, int]  # changes per op under the book filters
    total: int  # groups
    offset: int
    limit: int
    items: list[ChangeGroup]


class VerseDiff(BaseModel):
    """Word-level changes from verse a to verse b: display token index -> op."""

    a: int
    b: int
    a_marks: dict[int, DiffOp]
    b_marks: dict[int, DiffOp]
    counts: dict[str, int]  # ops incl. `same`
    shared: float  # share of the shorter verse's words that keep their lemma
    loose: bool  # below `diffs.min_shared`: no marks (not a close parallel)


class VerseHalves(BaseModel):
    """A verse's cola (te'amim pauses) and how parallel they are (DESIGN.md §16.9)."""

    verse_id: int
    n_cola: int
    cola: list[tuple[int, int]]  # inclusive display-token spans
    pauses: list[str]  # accent of each pause between cola (etnahta, oleh-ve-yored)
    cos: float | None = None
    shared: float | None = None
    shape: float | None = None
    balance: float | None = None
    prob: float | None = None  # probability the halves are parallel like poetry


class UnitParallelism(BaseModel):
    unit: UnitSummary
    parallel_at: float
    mean_prob: float | None
    share_parallel: float | None
    n_scored: int
    verses: list[VerseHalves]


class ParallelUnit(BaseModel):
    unit: UnitSummary
    mean_prob: float
    share_parallel: float
    n_scored: int


class ParallelBook(BaseModel):
    book_id: int
    poetic_accents: bool  # Psalms, Proverbs, Job: the model's positive training books
    mean_prob: float | None
    share_parallel: float | None
    n_scored: int


class ParallelismResponse(BaseModel):
    unit_type: str
    book: int | None
    exclude_poetic: bool
    parallel_at: float
    coefficients: dict[str, float]
    held_out_auc: dict[str, float]
    books: list[ParallelBook]
    total: int
    offset: int
    limit: int
    items: list[ParallelUnit]


class SequenceSummary(BaseModel):
    """Two passages running parallel in the same verse order (DESIGN.md §16.7)."""

    seq_id: int
    a_start: int
    a_end: int
    b_start: int
    b_end: int
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


class SequencesResponse(BaseModel):
    book: int | None
    cross_book: bool
    hide_same_chapter: bool
    max_q: float | None
    min_pairs: int
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[SequenceSummary]


class LadderRow(BaseModel):
    """One row of the side-by-side view: an aligned pair, or a verse skipped on one side."""

    a: int | None
    b: int | None
    weight: float | None = None  # candidate weight (1 = rank 1 in the fused list)
    cosine: float | None = None  # semantic cosine of the pair
    gold: bool = False
    a_marks: dict[int, DiffOp] = {}  # word changes (display token index -> op), aligned pairs
    b_marks: dict[int, DiffOp] = {}
    loose: bool = False  # aligned, but too different to diff word by word


class SequenceDetail(BaseModel):
    sequence: SequenceSummary
    rows: list[LadderRow]
    verses: dict[int, Verse]


class WordRef(BaseModel):
    idx: int  # words.idx (OSHB word order)
    display_idx: int | None  # index into the verse's display_tokens; None when unaligned
    in_formula: bool


class SharedLemma(BaseModel):
    lemma: str
    he_lemma: str
    formula: bool  # every occurrence in both verses lies inside a formula
    a_words: list[WordRef]
    b_words: list[WordRef]


class ExplainResponse(BaseModel):
    a: int
    b: int
    shared: list[SharedLemma]


class LemmaForm(BaseModel):
    lemma: str
    he_lemma: str


class Pair(BaseModel):
    src: int  # verse_id in the "from" unit
    tgt: int  # its best-matching verse_id in the other unit
    cosine: float
    shared: list[LemmaForm]


class CompareResponse(BaseModel):
    a: UnitSummary
    b: UnitSummary
    bma: float  # ½(mean best cosine A→B + mean best cosine B→A)
    a_to_b: list[Pair]
    b_to_a: list[Pair]
    verses: dict[int, Verse]  # every verse of A and B, by verse_id


class SearchHit(Breakdown):
    rank: int
    verse: Verse
    label_en: str
    label_he: str


class SearchResponse(BaseModel):
    query: str
    normalized: str
    tokens: list[str]  # lexical tokens after prefix stripping (bigrams not listed)
    mode: Mode
    k: int
    hits: list[SearchHit]


class ResolveResponse(BaseModel):
    query: str
    unit: UnitSummary | None  # the verse or chapter the query names; None if it is not a reference


class LemmaStat(BaseModel):
    lemma: str
    he_lemma: str
    n_verses: int  # verses containing it


class WordDetail(BaseModel):
    idx: int
    display_idx: int | None
    surface: str  # OSHB (WLC) form, morphemes separated by `/`
    lemma: str  # raw OSHB lemma attribute, e.g. b/7225
    morph: str | None  # OSHB code, e.g. HR/Ncfsa
    morph_he: list[str]  # Hebrew description per morpheme (text/morph.py)
    in_formula: bool
    lemmas: list[LemmaStat]  # its content lemmas


class BookCount(BaseModel):
    book_id: int
    n_verses: int


class ConcordanceHit(BaseModel):
    verse: Verse
    label_en: str
    label_he: str
    display_idxs: list[int]  # display tokens carrying the lemma


class ConcordanceResponse(BaseModel):
    lemma: str
    he_lemma: str
    n_words: int
    n_verses: int
    by_book: list[BookCount]  # canon order, books without it left out
    book: int | None
    total: int  # verses after the book filter
    offset: int
    limit: int
    items: list[ConcordanceHit]


class StructureScore(BaseModel):
    value: float  # similarity (inclusio) or mean mirror-pair similarity (chiasm)
    pct: float  # percentile against the unit's own null, 0..1
    z: float | None = None  # chiasm: distance from the null mean in null SDs
    pair: tuple[int, int] | None = None  # inclusio: verse_ids of the frame pair that scored


class Echo(BaseModel):
    a: int  # verse_id
    b: int
    sim: float


class StructureBasis(BaseModel):
    matrix: list[list[float]]  # verse x verse similarity, rounded to 3 decimals
    inclusio: StructureScore | None
    chiasm: StructureScore | None
    echoes: list[Echo]  # strongest non-adjacent pairs


class Leitwort(BaseModel):
    lemma: str
    he_lemma: str
    count: int
    expected: float  # occurrences expected from the corpus rate
    g2: float  # Dunning log-likelihood
    multiple_of: list[int]  # 7 / 10 when the count is a multiple
    occurrences: dict[int, list[int]]  # verse_id -> display token indices


class StructureResponse(BaseModel):
    unit: UnitSummary
    verse_ids: list[int]
    semantic: StructureBasis
    lexical: StructureBasis
    leitworte: list[Leitwort]


class StructureRank(BaseModel):
    unit: UnitSummary
    semantic_inclusio: float | None
    semantic_inclusio_pct: float | None
    semantic_chiasm: float | None
    semantic_chiasm_pct: float | None
    semantic_chiasm_z: float | None
    lexical_inclusio: float | None
    lexical_inclusio_pct: float | None
    lexical_chiasm: float | None
    lexical_chiasm_pct: float | None
    lexical_chiasm_z: float | None


class StructureRankingResponse(BaseModel):
    unit_type: str
    by: str
    min_verses: int
    total: int
    offset: int
    limit: int
    items: list[StructureRank]


class MapPoint(BaseModel):
    unit_id: str
    label_en: str
    label_he: str
    book_id: int
    n_verses: int
    x: float
    y: float
    cluster: int


class MapCluster(BaseModel):
    cluster: int
    size: int
    lemmas: list[LemmaForm]  # label lemmas, strongest first


class MapResponse(BaseModel):
    unit_type: str
    points: list[MapPoint]
    clusters: list[MapCluster]


class AffinityCell(BaseModel):
    a: int  # book_id, a < b
    b: int
    n_pairs: int
    expected: float
    lift: float  # observed / expected pairs


class AffinityResponse(BaseModel):
    order: list[int]  # book_ids, related books adjacent
    cells: list[AffinityCell]


class AffinityPair(BaseModel):
    score: float
    a: UnitSummary
    b: UnitSummary
    a_verse: Verse
    b_verse: Verse
    link: GoldLink | None = None


class StyloPoint(BaseModel):
    unit_id: str
    label_en: str
    label_he: str
    book_id: int
    n_words: int
    x: float
    y: float


class StyloAxis(BaseModel):
    pc: int
    variance: float  # share of the z-score variance
    positive: list[str]  # Hebrew labels of the heaviest positive loadings
    negative: list[str]


class StyloDelta(BaseModel):
    a: int
    b: int
    delta: float


class StylometryResponse(BaseModel):
    points: list[StyloPoint]
    axes: list[StyloAxis]
    order: list[int]  # books, stylistically similar ones adjacent
    delta: list[StyloDelta]


class StyloFeature(BaseModel):
    feature: str
    label: str
    rate: float  # per word
    z: float  # against the other books


class BookStyle(BaseModel):
    book_id: int
    n_words: int
    over: list[StyloFeature]
    under: list[StyloFeature]
    closest: list[StyloDelta]  # the stylistically nearest books


class Meta(BaseModel):
    build: dict[str, Any]  # the DB `meta` table
    runtime: dict[str, Any]
