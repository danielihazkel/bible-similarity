"""Response models of the viewer API (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Mode = Literal["lexical", "semantic", "fused", "structural", "domain"]
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
