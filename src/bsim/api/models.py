"""Response models of the viewer API (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Mode = Literal["lexical", "semantic", "fused", "structural", "domain", "syntax"]
SearchMode = Literal["lexical", "semantic", "fused"]  # no morphology for free text


class ApiModel(BaseModel):
    """Base of every response model: a field with a default is still always present in the
    response, so the OpenAPI schema (the viewer's generated types) marks it required."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class Book(ApiModel):
    book_id: int
    name: str
    he_name: str
    osis: str
    section: str
    n_chapters: int


class UnitSummary(ApiModel):
    unit_id: str
    unit_type: str
    label_en: str
    label_he: str
    book_id: int
    start_verse_id: int
    end_verse_id: int
    n_verses: int
    marker: str | None = None


class Verse(ApiModel):
    verse_id: int
    book_id: int
    chapter: int
    verse: int
    ref: str
    ref_he: str
    text_display: str
    display_tokens: list[str]
    ketiv_note: str | None = None


class UnitDetail(ApiModel):
    unit: UnitSummary
    verses: list[Verse]
    parents: list[UnitSummary]  # the units of the other types that contain its first verse
    prev_id: str | None
    next_id: str | None


class Breakdown(ApiModel):
    """`lex_*` / `sem_*` are set on fused results only (a list missing the target: None)."""

    score: float
    lex_score: float | None = None
    lex_rank: int | None = None
    sem_score: float | None = None
    sem_rank: int | None = None


class GoldLink(ApiModel):
    """A Sefaria link between the two units: `verse` = a direct verse-to-verse link, `unit` =
    only a passage-level link covers them."""

    level: Literal["verse", "unit"]
    types: list[str]  # connection types (quotation, related, ...); empty when untyped


class PhraseInfo(ApiModel):
    score: float  # local-alignment score (idf-weighted matched lemmas minus penalties)
    n_tokens: int  # matched lemma tokens


class Hit(Breakdown):
    rank: int
    unit: UnitSummary
    verse: Verse | None = None  # verse hits
    preview: str | None = None  # larger units: start of the first verse's display text
    link: GoldLink | None = None  # None: not a Sefaria-linked pair
    phrase: PhraseInfo | None = None  # verse hits sharing an aligned phrase with the source


class SimilarResponse(ApiModel):
    unit: UnitSummary
    mode: Mode
    k: int
    exclude: list[str]
    hits: list[Hit]


class Discovery(ApiModel):
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


class DiscoveriesResponse(ApiModel):
    unit_type: str
    mode: Mode
    book: int | None
    cross_book: bool
    unit: str | None  # only the pairs this unit is in
    total: int  # pairs matching the filters
    offset: int
    limit: int
    items: list[Discovery]


class PhrasePair(ApiModel):
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


class PhrasesResponse(ApiModel):
    book: int | None
    unit: str | None  # only phrases with a side in this unit
    cross_book: bool
    min_tokens: int
    max_spread: int | None
    total: int
    offset: int
    limit: int
    items: list[PhrasePair]


DiffOp = Literal["spelling", "form", "substitution", "omitted", "added", "moved"]


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


class RelationPair(ApiModel):
    """A word pair that types a parallel verse: SDBH antonyms or synonyms, or two lemmas in one
    semantic domain (DESIGN.md §16.22)."""

    a: str  # content lemma in the first half
    b: str
    kind: Literal["antonym", "synonym", "domain"]
    a_he: str
    b_he: str


class VerseHalves(ApiModel):
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
    clauses: list[tuple[int, int]] = []  # spans between accent pauses of level 1-2
    next_prob: float | None = None  # bicolon with the next verse (two one-colon verses)
    relation: Literal["antithetic", "synonymous"] | None = None  # parallel verses with a lexicon
    relation_pairs: list[RelationPair] = []


class UnitParallelism(ApiModel):
    unit: UnitSummary
    parallel_at: float
    mean_prob: float | None
    share_parallel: float | None
    n_scored: int
    verses: list[VerseHalves]


class ParallelUnit(ApiModel):
    unit: UnitSummary
    mean_prob: float
    share_parallel: float
    n_scored: int
    n_parallel: int  # verses at `parallel_at` or above
    share_antithetic: float | None  # of the parallel verses (None: none, or no lexicon)


class ParallelBook(ApiModel):
    book_id: int
    poetic_accents: bool  # Psalms, Proverbs, Job: the model's positive training books
    mean_prob: float | None
    share_parallel: float | None
    n_scored: int


class ParallelismResponse(ApiModel):
    unit_type: str
    book: int | None
    exclude_poetic: bool
    parallel_at: float
    coefficients: dict[str, float]
    held_out_auc: dict[str, float]
    sort: Literal["prob", "antithetic"]
    min_parallel: int  # parallel verses a unit needs (0 unless sorted by antithetic share)
    typing: dict[str, Any] | None  # antithetic / synonymous typing check (§16.22), None without it
    books: list[ParallelBook]
    total: int
    offset: int
    limit: int
    items: list[ParallelUnit]


class WordplayPair(ApiModel):
    """Two sound-alike words close together (DESIGN.md §16.10)."""

    a_vid: int
    b_vid: int
    a_display: int | None  # display token of each word (highlight); None when unaligned
    b_display: int | None
    a_form: str
    b_form: str
    a_he: str  # lemma display forms
    b_he: str
    kind: Literal["substitution", "metathesis", "extension"]
    gap: int
    score: float
    q: float
    a_label: str
    b_label: str
    a_label_he: str
    b_label_he: str
    verses: list[Verse]  # one verse, or two when the pair crosses a verse boundary


class WordplayResponse(ApiModel):
    book: int | None
    kind: str | None
    unit: str | None
    total: int
    expected_by_chance: float | None  # pairs per shuffled text (whole corpus)
    offset: int
    limit: int
    items: list[WordplayPair]


EntityKind = Literal["person", "place", "mixed", "unclear"]


class Entity(ApiModel):
    """A name (OSHB proper-noun lemma) with its kind guessed from context (DESIGN.md §16.11)."""

    lemma: str
    he: str
    kind: EntityKind
    n_mentions: int
    n_verses: int
    n_here: int | None = None  # mentions in the requested book / unit
    first_vid: int
    last_vid: int
    kind_source: Literal["lexicon", "cues"]  # Strong's part of speech, or the context cues


class EntitiesResponse(ApiModel):
    kind: str | None
    book: int | None
    q: str | None
    total: int
    offset: int
    limit: int
    items: list[Entity]


class EntityPartner(ApiModel):
    lemma: str
    he: str
    kind: EntityKind
    n_verses: int  # verses shared
    expected: float  # by chance
    g2: float


class EntityLink(ApiModel):
    a: str
    b: str
    n_verses: int
    g2: float


class EntityDetail(ApiModel):
    entity: Entity
    first_label: str
    last_label: str
    first_label_he: str
    last_label_he: str
    by_book: list[BookCount]
    partners: list[EntityPartner]
    links: list[EntityLink]  # links among the partners (for the network drawing)


class SeamFeature(ApiModel):
    feature: str
    label: str  # Hebrew label of the lemma or morphology feature
    z: float  # change at the seam in corpus SDs (after minus before)


class Seam(ApiModel):
    """A point where a book's style changes (DESIGN.md §16.12)."""

    book_id: int
    verse_id: int  # first verse after the seam
    label: str
    label_he: str
    shift: float
    threshold: float
    rank: int
    features: list[SeamFeature]


class CurvePoint(ApiModel):
    verse_id: int
    chapter: int
    verse: int
    shift: float


class SeamsResponse(ApiModel):
    book: int | None
    block_words: int
    threshold: float | None
    curve: list[CurvePoint]  # empty without a book
    seams: list[Seam]


class SequenceSummary(ApiModel):
    """Two passages running parallel in the same verse order (DESIGN.md §16.7)."""

    seq_id: int
    a_start: int
    a_end: int
    b_start: int
    b_end: int
    direction: str = "forward"  # forward | reverse (mirrored order) | mixed (reordered)
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


class SequencesResponse(ApiModel):
    book: int | None
    cross_book: bool
    hide_same_chapter: bool
    max_q: float | None
    min_pairs: int
    unit: str | None
    direction: str | None = None
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


class WordRef(ApiModel):
    idx: int  # words.idx (OSHB word order)
    display_idx: int | None  # index into the verse's display_tokens; None when unaligned
    in_formula: bool


class SharedLemma(ApiModel):
    lemma: str
    he_lemma: str
    formula: bool  # every occurrence in both verses lies inside a formula
    a_words: list[WordRef]
    b_words: list[WordRef]


class ExplainResponse(ApiModel):
    a: int
    b: int
    shared: list[SharedLemma]


class LemmaForm(ApiModel):
    lemma: str
    he_lemma: str


class Pair(ApiModel):
    src: int  # verse_id in the "from" unit
    tgt: int  # its best-matching verse_id in the other unit
    cosine: float
    shared: list[LemmaForm]


class CompareResponse(ApiModel):
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


class SearchResponse(ApiModel):
    book: int | None = None
    query: str
    normalized: str
    tokens: list[str]  # lexical tokens after prefix stripping (bigrams not listed)
    mode: Mode
    k: int
    hits: list[SearchHit]


class ResolveResponse(ApiModel):
    query: str
    unit: UnitSummary | None  # the verse or chapter the query names; None if it is not a reference


class LemmaStat(ApiModel):
    lemma: str
    he_lemma: str
    n_verses: int  # verses containing it


class WordDetail(ApiModel):
    idx: int
    display_idx: int | None
    surface: str  # OSHB (WLC) form, morphemes separated by `/`
    lemma: str  # raw OSHB lemma attribute, e.g. b/7225
    morph: str | None  # OSHB code, e.g. HR/Ncfsa
    morph_he: list[str]  # Hebrew description per morpheme (text/morph.py)
    in_formula: bool
    lemmas: list[LemmaStat]  # its content lemmas
    domains: list[str]  # SDBH domain codes of its content morphemes (`/domains` names them)


class BookCount(ApiModel):
    book_id: int
    n_verses: int


class ConcordanceHit(ApiModel):
    verse: Verse
    label_en: str
    label_he: str
    display_idxs: list[int]  # display tokens carrying the lemma


class ConcordanceResponse(ApiModel):
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


class DatingChapter(ApiModel):
    """A chapter's Late Biblical Hebrew profile (DESIGN.md §16.24)."""

    unit_id: str
    book_id: int
    chapter: int
    n_words: int  # Hebrew words (Aramaic left out)
    role: Literal["early", "late", "scored"]  # training books are scored held out
    out_of_domain: bool  # poetry: the model is calibrated on prose
    score: float | None  # 0 = like Genesis–Kings, 1 = like the late books; None: too short
    features: dict[str, float]  # shrunk feature rates
    drivers: list[str]  # features pushing the score up most


class DatingBook(ApiModel):
    book_id: int
    role: Literal["early", "late", "scored"]
    out_of_domain: bool
    n_chapters: int
    score: float | None  # mean chapter score
    low: float | None  # 10th / 90th chapter percentiles
    high: float | None
    features: dict[str, float]  # the book's feature rates


class SynopticExample(ApiModel):
    """A Samuel–Kings passage and its Chronicles parallel, scored by models that saw neither."""

    early_first: int  # first verse id
    late_first: int
    early_label: str
    late_label: str
    early_label_he: str
    late_label_he: str
    early_score: float
    late_score: float


class DatingResponse(ApiModel):
    features: list[str]
    coefficients: dict[str, float]  # standardized logistic-regression weights
    held_out_auc: float | None  # leave-one-book-out over the training books
    held_out_auc_grammar: float | None  # ... without the late-word feature
    train_chapters: dict[str, int]
    synoptic: dict[str, Any]  # pairs, later, p, later_grammar, p_grammar
    synoptic_examples: list[SynopticExample]  # the largest gaps
    books: list[DatingBook]


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


class StructureScore(ApiModel):
    value: float  # similarity (inclusio) or mean mirror-pair similarity (chiasm)
    pct: float  # percentile against the unit's own null, 0..1
    z: float | None = None  # chiasm: distance from the null mean in null SDs
    pair: tuple[int, int] | None = None  # inclusio: verse_ids of the frame pair that scored


class Echo(ApiModel):
    a: int  # verse_id
    b: int
    sim: float


class StructureBasis(ApiModel):
    matrix: list[list[float]]  # verse x verse similarity, rounded to 3 decimals
    inclusio: StructureScore | None
    chiasm: StructureScore | None
    echoes: list[Echo]  # strongest non-adjacent pairs


class Leitwort(ApiModel):
    lemma: str
    he_lemma: str
    count: int
    expected: float  # occurrences expected from the corpus rate
    g2: float  # Dunning log-likelihood
    multiple_of: list[int]  # 7 / 10 when the count is a multiple
    occurrences: dict[int, list[int]]  # verse_id -> display token indices


class StructureResponse(ApiModel):
    unit: UnitSummary
    verse_ids: list[int]
    semantic: StructureBasis
    lexical: StructureBasis
    leitworte: list[Leitwort]


class StructureRank(ApiModel):
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
    semantic_inclusio_q: float | None = None  # Benjamini-Hochberg over the unit type
    semantic_chiasm_q: float | None = None
    lexical_inclusio_q: float | None = None
    lexical_chiasm_q: float | None = None


class StructureRankingResponse(ApiModel):
    unit_type: str
    by: str
    min_verses: int
    # multiples-of-m check of Leitwort counts (`structure.leitwort_numbers`), m -> stats
    leitwort_numbers: dict[str, Any] | None = None
    total: int
    offset: int
    limit: int
    items: list[StructureRank]


class MapPoint(ApiModel):
    unit_id: str
    label_en: str
    label_he: str
    book_id: int
    n_verses: int
    x: float
    y: float
    cluster: int


class MapCluster(ApiModel):
    cluster: int
    size: int
    lemmas: list[LemmaForm]  # label lemmas, strongest first


class MapResponse(ApiModel):
    unit_type: str
    points: list[MapPoint]
    clusters: list[MapCluster]


class AffinityCell(ApiModel):
    a: int  # book_id, a < b
    b: int
    n_pairs: int
    expected: float
    lift: float  # observed / expected pairs


class AffinityResponse(ApiModel):
    order: list[int]  # book_ids, related books adjacent
    cells: list[AffinityCell]


class AffinityPair(ApiModel):
    score: float
    a: UnitSummary
    b: UnitSummary
    a_verse: Verse
    b_verse: Verse
    link: GoldLink | None = None


class StyloPoint(ApiModel):
    unit_id: str
    label_en: str
    label_he: str
    book_id: int
    n_words: int
    x: float
    y: float


class StyloAxis(ApiModel):
    pc: int
    variance: float  # share of the z-score variance
    positive: list[str]  # Hebrew labels of the heaviest positive loadings
    negative: list[str]


class StyloDelta(ApiModel):
    a: int
    b: int
    delta: float


class StylometryResponse(ApiModel):
    points: list[StyloPoint]
    axes: list[StyloAxis]
    order: list[int]  # books, stylistically similar ones adjacent
    delta: list[StyloDelta]


class StyloFeature(ApiModel):
    feature: str
    label: str
    rate: float  # per word
    z: float  # against the other books


class BookStyle(ApiModel):
    book_id: int
    n_words: int
    over: list[StyloFeature]
    under: list[StyloFeature]
    closest: list[StyloDelta]  # the stylistically nearest books


class Meta(ApiModel):
    build: dict[str, Any]  # the DB `meta` table
    runtime: dict[str, Any]


class EvalResponse(ApiModel):
    splits: dict[str, Any]  # artifacts/eval/metrics.json `splits` (empty before `bsim eval`)
    openbible: dict[str, Any] | None  # artifacts/eval/openbible.json
    final: dict[str, dict[str, str]]  # unit type -> mode -> system served for it


class AcrosticLine(ApiModel):
    verse_id: int
    display_idx: int
    letter: str


class Acrostic(ApiModel):
    """A chapter's best alphabetic chain (DESIGN.md §16.15)."""

    unit: UnitSummary
    granularity: str  # verse | colon
    order_name: str  # standard | pe-ayin
    score: float
    n_letters: int
    missing: int
    first_letter: str
    last_letter: str
    n_lines: int
    p: float
    q: float
    chain: list[AcrosticLine]


class AcrosticsResponse(ApiModel):
    max_q: float | None
    book: int | None
    known_recall: float | None
    total: int
    offset: int
    limit: int
    items: list[Acrostic]


class Rewrite(ApiModel):
    """A change one book makes consistently against another (DESIGN.md §16.16)."""

    a_book: int
    b_book: int
    op: str  # substitution | omitted | added
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
    op: str | None
    max_q: float | None
    total: int
    offset: int
    limit: int
    items: list[Rewrite]


class NetworkNode(ApiModel):
    unit: UnitSummary
    pagerank: float
    strength: float
    partners: int
    cross_book: float
    community: int
    x: float
    y: float


class NetworkEdge(ApiModel):
    a: str
    b: str
    weight: float


class NetworkCommunity(ApiModel):
    community: int
    size: int
    lemmas: list[LemmaForm]
    books: list[BookCount]  # units per book, most first


class NetworkResponse(ApiModel):
    unit_type: str
    communities: list[NetworkCommunity]
    central: list[NetworkNode]  # highest PageRank


class CommunityResponse(ApiModel):
    unit_type: str
    community: NetworkCommunity
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]


class UnitNetwork(ApiModel):
    """Where a unit sits in the network: its metrics and its centrality rank."""

    node: NetworkNode
    rank: int  # 1 = highest PageRank of its unit type
    of: int
    community_size: int


class VerseLabel(ApiModel):
    verse_id: int
    label_en: str
    label_he: str


class WordPair(ApiModel):
    """Two lemmas that answer each other across the members of parallel lines (§16.18)."""

    a: LemmaForm  # in the first member
    b: LemmaForm
    n: int
    expected: float
    g2: float
    q: float
    reverse: int  # the pair in the other order
    examples: list[VerseLabel]


class WordPairsResponse(ApiModel):
    max_q: float | None
    lemma: str | None
    total: int
    offset: int
    limit: int
    items: list[WordPair]


class Alliteration(ApiModel):
    """A colon whose content words share an initial sound (DESIGN.md §16.19)."""

    verse: Verse
    label: str
    label_he: str
    colon: int
    sound: str
    count: int
    n_words: int
    words: list[int]  # display indexes of the alliterating words
    p: float
    q: float


class AlliterationResponse(ApiModel):
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[Alliteration]


class Rhyme(ApiModel):
    """Consecutive cola whose last words end alike."""

    start_vid: int
    end_vid: int
    label: str
    label_he: str
    n_cola: int
    ending: str
    members: list[tuple[int, int]]  # (verse_id, display_idx) of each colon's last word
    verses: list[Verse]
    p: float
    q: float


class RhymesResponse(ApiModel):
    book: int | None
    max_q: float | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[Rhyme]


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


class LabelIn(BaseModel):
    """A judgement of a pair (PUT /labels), in either order."""

    a_id: str
    b_id: str
    label: Literal["real", "not", "unsure"]
    note: str = ""
    mode: str | None = None  # the list the pair was judged in
    score: float | None = None


class Label(ApiModel):
    """A labelled pair (DESIGN.md §16.25); `a` starts earlier in the canon."""

    unit_type: str
    a: UnitSummary
    b: UnitSummary
    label: Literal["real", "not", "unsure"]
    note: str
    mode: str | None
    score: float | None
    labeled_at: str


class LabelsResponse(ApiModel):
    writable: bool  # serve.labels_writable
    counts: dict[str, int]  # real / not / unsure
    items: list[Label]  # most recent first


class LabelSeparation(ApiModel):
    """How one mode's lists separate your real pairs from your not pairs."""

    unit_type: str
    mode: str
    n_real: int
    n_not: int
    found_real: int  # ranked within `k` by either unit
    found_not: int
    recall: float | None  # found_real / n_real
    precision: float | None  # found_real / (found_real + found_not)
    auc: float | None  # reciprocal rank, real vs not (None below labels.min_pairs of either)


class LabelsEval(ApiModel):
    k: int
    min_pairs: int
    rows: list[LabelSeparation]


class ClauseSegment(ApiModel):
    """Consecutive words of a clause in one phrase (BHSA, DESIGN.md §16.26)."""

    function: str  # Pred, Subj, Objc, ... ('' outside any phrase)
    typ: str  # phrase type: VP, NP, PP, ...
    text: str  # the OSHB words, pointed


class ClauseInfo(ApiModel):
    typ: str  # clause type: WayX, xQtX, NmCl, ...
    kind: str  # VC | NC | WP
    txt: str  # text type with its embedding (N, NQ, ?NQQ, ...)
    rela: str  # relation to another clause ('NA' / '' none)
    speech: bool  # direct speech (txt ends in Q)
    speaker: str | None  # lemma
    speaker_he: str | None
    speaker_source: Literal["explicit", "carried", "enclosing"] | None
    divine: bool
    segments: list[ClauseSegment]


class VerseSyntax(ApiModel):
    verse_id: int
    ref: str
    ref_he: str
    clauses: list[ClauseInfo]


class SyntaxNeighbor(ApiModel):
    unit: UnitSummary
    score: float
    preview: str


class UnitSyntax(ApiModel):
    verses: list[VerseSyntax]  # empty without `bsim syntax`
    neighbors: list[SyntaxNeighbor]  # verse units: verses built the same way


class SpeakerInfo(ApiModel):
    lemma: str
    he: str
    n_words: int
    n_explicit: int
    divine: bool


class SpeechShares(ApiModel):
    narration: float
    speech: float
    discourse: float
    divine: float
    attributed: float
    n_words: int


class SpeechBook(SpeechShares):
    book_id: int
    speakers: list[SpeakerInfo]  # the most words first (top `speech_speakers`)


class SpeechChapter(SpeechShares):
    unit_id: str
    chapter: int


class SpeechResponse(ApiModel):
    meta: dict[str, Any]  # `bsim syntax` counts: clauses, speech_clauses, speaker sources
    books: list[SpeechBook]


class SpeechBookResponse(ApiModel):
    book_id: int
    chapters: list[SpeechChapter]
    speakers: list[SpeakerInfo]


class VoiceSpeaker(ApiModel):
    key: str  # speaker lemma, or `divine` (the divine names together)
    he: str | None  # Hebrew form of the lemma; None for `divine`
    n_words: int
    n_explicit: int  # words whose introduction names the speaker itself
    n_clauses: int
    main_book: int
    books: list[int]  # most words first
    delta: float  # Burrows' Delta to the other attributed speech of the same books
    null_mean: float  # ... expected under the within-book label shuffle
    effect: float  # (delta - null mean) / null sd
    p: float
    q: float


class VoicePair(ApiModel):
    a: str  # speaker keys, `narrator`, `unattributed`
    b: str
    delta: float


class VoicesResponse(ApiModel):
    meta: dict[str, Any]  # `bsim voices`: counts, calibration, sensitivity, order, checks
    speakers: list[VoiceSpeaker]  # empty without `bsim voices`
    pairs: list[VoicePair]


class VoiceFeature(ApiModel):
    side: str  # over | under
    rank: int
    feature: str
    label: str  # Hebrew: the lemma or the morphology feature
    rate: float  # per word in the speaker's speech
    rate_ref: float  # ... in the other attributed speech of the same books
    z: float  # (rate - rate_ref) / chapter sd


class VoiceChapter(ApiModel):
    unit_id: str
    book_id: int
    chapter: int
    n_clauses: int  # the speaker's speech clauses in it


class VoiceDetail(ApiModel):
    speaker: VoiceSpeaker
    features: list[VoiceFeature]
    nearest: list[VoicePair]  # a = this speaker, nearest first
    chapters: list[VoiceChapter]  # where the speaker talks most


DossierKind = Literal[
    "phrases", "sequences", "changes", "borrowing", "wordplay", "alliteration", "rhymes",
    "typescenes", "discoveries", "seams", "names", "acrostic", "dating", "structure", "speech",
    "voices", "network", "divisions", "ketiv", "citations", "allusions", "mirrors", "labels",
]  # fmt: skip


class DossierEntry(ApiModel):
    """One analysis on one unit (`/dossier`); which fields carry what depends on `kind`."""

    kind: DossierKind
    scope: Literal["unit", "chapter"]  # read on the unit itself or on its chapter
    computed: bool  # False: the stage did not run (or does not cover this unit type)
    count: int | None = None  # rows found, 1 / 0 for a yes / no finding, a rank (network)
    # divisions: count = flagged gaps in the unit; value / key = score / kind of its opening gap
    total: int | None = None  # network: units ranked
    value: float | None = None  # lowest q (acrostic, structure), score (dating)
    key: str | None = None  # speech: speaker lemma; voices: voice profile key
    label: str | None = None  # speech / voices: the speaker's Hebrew form
    target_unit: str | None = None  # the chapter read for a chapter-scope entry


class Dossier(ApiModel):
    unit_id: str
    entries: list[DossierEntry]


class SignCheck(ApiModel):
    agree: int  # sequences a sign points the accepted way
    n: int  # sequences it voted on
    p: float | None  # two-sided sign test
    unclear: int | None = None  # held-out check: sequences left undecided


class BorrowingSequence(ApiModel):
    """Which side of a cross-book parallel looks like the borrower (DESIGN.md §16.27). A is the
    side earlier in the canon; a sign > 0 says B looks later."""

    seq_id: int
    a_book: int
    b_book: int
    a_first: int
    b_first: int
    a_label: str
    b_label: str
    a_label_he: str
    b_label_he: str
    n_pairs: int
    language: float
    spelling: float | None
    smoothing: float | None
    expansion: float | None
    n_spelling: int
    n_substitution: int
    known: Literal["a_to_b", "b_to_a"] | None
    votes: int
    n_votes: int
    direction: Literal["a_to_b", "b_to_a", "unclear"]


class BorrowingBookPair(ApiModel):
    a_book: int
    b_book: int
    sequences: int
    n_pairs: int
    votes: int
    a_to_b: int
    b_to_a: int
    known: Literal["a_to_b", "b_to_a"] | None
    direction: Literal["a_to_b", "b_to_a", "unclear"]
    items: list[BorrowingSequence]


class BorrowingResponse(ApiModel):
    unit: str | None  # only the parallels touching this unit
    checks: dict[str, SignCheck]  # each sign and all four on the accepted directions
    used_signs: list[str]  # the signs that vote
    held_out: SignCheck | None  # signs chosen without each book pair, scored on it
    books: list[BorrowingBookPair]  # the most parallel verses first


SegmentKind = Literal["turn", "cut", "quiet"]


class SegmentBook(ApiModel):
    """A book's top-K gaps as a segmentation against its MAM breaks or chapters (§16.29)."""

    book_id: int
    ref: Literal["mam", "chapter"]
    k: int  # Pk window, in verses
    pk: float
    pk_null: float  # mean over K random gaps
    pk_p: float
    wd: float
    wd_null: float
    wd_p: float


class SegmentsResponse(ApiModel):
    meta: dict[str, Any]  # window, groups, contrasts, calibration, seams, agreement, kinds
    books: list[SegmentBook]


class SegmentGap(ApiModel):
    """A gap between two verses (`verse_id` = the verse after it), its cohesion and divisions."""

    verse_id: int
    book_id: int
    label: str  # the verse after the gap
    label_he: str
    score: float  # within-book percentile of the cohesion drop (1 = sharpest turn of the book)
    lex: float  # cosine across the gap, lemmas
    sem: float  # the same, embeddings
    mam: Literal["pe", "samekh"] | None
    oshb: Literal["pe", "samekh"] | None
    chapter: bool
    seam: bool
    kind: SegmentKind | None
    verses: list[Verse]  # the verse before and the verse after


class SegmentGapsResponse(ApiModel):
    kind: SegmentKind | None
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[SegmentGap]


class SegmentPoint(ApiModel):
    verse_id: int
    chapter: int
    verse: int
    score: float
    mam: Literal["pe", "samekh"] | None
    oshb: Literal["pe", "samekh"] | None
    chapter_start: bool
    seam: bool
    kind: SegmentKind | None


class SegmentCurve(ApiModel):
    book_id: int
    points: list[SegmentPoint]
    agreement: list[SegmentBook]


KqClass = Literal[
    "vowel_letter", "swap", "vowel_position", "metathesis", "division", "qere_only", "ketiv_only",
    "same_letters", "other",
]  # fmt: skip


class KqBook(ApiModel):
    book_id: int
    n: int
    words: int
    rate: float  # per 1,000 words
    vowel_letter: int
    ketiv_fuller: float | None  # share of vowel-letter pairs written fuller than read
    swap: int
    division: int
    other_cls: int
    form: int
    word: int


class KqLetter(ApiModel):
    pair: str  # two letters, sorted
    n: int
    expected: float
    ratio: float | None
    p: float
    q: float
    lookalike: bool


class KetivResponse(ApiModel):
    meta: dict[str, Any]  # pairs, classes, grammar, euphemisms, features, checks
    books: list[KqBook]
    letters: list[KqLetter]  # pairs with at least one swap


class KqPair(ApiModel):
    """One ketiv / qere (§16.30): what is written, what is read, and how they differ."""

    kq_id: int
    verse_id: int
    book_id: int
    label: str
    label_he: str
    ketiv: str
    qere: str
    cls: KqClass
    fuller: Literal["ketiv", "qere"] | None
    letters: str | None
    grammar: Literal["spelling", "form", "word"] | None
    features: list[str]
    euphemism: bool
    parallel: Literal["qere", "ketiv", "neither"] | None
    partner_vid: int | None
    partner_label: str | None
    partner_label_he: str | None
    partner_form: str | None
    verse: Verse
    display: list[int]  # display tokens of the read words


class KqPairsResponse(ApiModel):
    cls: KqClass | None
    grammar: str | None
    parallel: str | None
    euphemism: bool | None
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[KqPair]


CitationFamily = Literal["written", "word", "command"]


class CitationBook(ApiModel):
    book_id: int  # citing
    target_book: int  # cited
    n: int


class CitationsResponse(ApiModel):
    meta: dict[str, Any]  # citations, resolved, families, gold, word_lag_median, book_pairs
    books: list[CitationBook]


class CitationCandidate(ApiModel):
    verse_id: int
    label: str
    label_he: str
    score: float


class Citation(ApiModel):
    """A verse with a formula of reference and its best source (§16.31)."""

    cite_id: int
    family: CitationFamily
    verse_id: int
    book_id: int
    label: str
    label_he: str
    formula: str
    verse: Verse
    target: Verse | None
    target_label: str | None
    target_label_he: str | None
    score: float | None
    pct: float | None
    resolved: bool
    candidates: list[CitationCandidate]  # the best first, the source itself included
    gold_rank: int | None  # a named source's rank among the candidates (None: not named / missed)
    named: bool  # scholarship names a source for this citation


class CitationListResponse(ApiModel):
    family: CitationFamily | None
    resolved: bool | None
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[Citation]


class AllusionLemma(ApiModel):
    lemma: str  # Strong's number
    form: str


class Allusion(ApiModel):
    """Two passages of a few verses sharing rare words (§16.32)."""

    allusion_id: int
    a_start: int
    a_end: int
    b_start: int
    b_end: int
    a_label: str
    a_label_he: str
    b_label: str
    b_label_he: str
    n_shared: int
    score: float
    q: float
    known: bool  # already a fused neighbour or a parallel sequence
    lemmas: list[AllusionLemma]
    a_verses: list[Verse]
    b_verses: list[Verse]
    a_marks: dict[int, list[int]]  # verse_id -> display tokens of the shared words
    b_marks: dict[int, list[int]]


class AllusionsResponse(ApiModel):
    meta: dict[str, Any]  # rare_lemmas, window, pairs, known, max_q, strong, best_new_q
    known: bool | None
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[Allusion]


class MirrorsResponse(ApiModel):
    meta: dict[str, Any]  # words (all / poetry / prose), clauses (by_pair), full_mirrors


class MirrorVerse(ApiModel):
    """A verse whose twice-used lemmas all nest: A B C … C B A (§16.33)."""

    verse_id: int
    label: str
    label_he: str
    poetic: bool
    n_pairs: int
    n_words: int
    p: float
    q: float
    verse: Verse
    marks: dict[int, int]  # display token -> 0-based nesting depth of its lemma


class MirrorVersesResponse(ApiModel):
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[MirrorVerse]


class MirrorClause(ApiModel):
    """Two consecutive clauses with the same two constituents, in the same or reversed order."""

    pair_id: int
    verse_id: int
    label: str
    label_he: str
    poetic: bool
    pair: str
    first: str
    second: str
    mirrored: bool
    verse: Verse
    marks: dict[int, int]  # display token -> 0 (the first clause's first constituent) or 1


class MirrorClausesResponse(ApiModel):
    pair: str | None
    mirrored: bool | None
    poetic: bool | None
    book: int | None
    unit: str | None
    total: int
    offset: int
    limit: int
    items: list[MirrorClause]
