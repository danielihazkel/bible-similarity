"""Response models of `api/routes/poetics.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import (
    ApiModel,
    Leitwort,
    LemmaForm,
    LemmaStat,
    UnitSummary,
    UnitType,
    Verse,
    VerseLabel,
)

StructureSort = Literal[
    "semantic_chiasm", "lexical_chiasm", "semantic_inclusio", "lexical_inclusio"
]


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
    unit_type: UnitType
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


class RootLeitwort(ApiModel):
    """A root over-represented in the unit, its words counted together (DESIGN.md §16.38)."""

    root: str
    root_he: str
    count: int
    expected: float
    g2: float
    lemmas: list[LemmaStat]  # the family's words in the unit
    hidden: bool  # two or more words, none of them among the Leitworte by lemma
    occurrences: dict[int, list[int]]  # verse_id -> display token indices


class StructureResponse(ApiModel):
    unit: UnitSummary
    verse_ids: list[int]
    semantic: StructureBasis
    lexical: StructureBasis
    leitworte: list[Leitwort]
    root_leitworte: list[RootLeitwort] = []  # empty without `bsim roots`


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
    unit_type: UnitType
    by: StructureSort
    min_verses: int
    # multiples-of-m check of Leitwort counts (`structure.leitwort_numbers`), m -> stats
    leitwort_numbers: dict[str, Any] | None = None
    total: int
    offset: int
    limit: int
    items: list[StructureRank]


class AcrosticLine(ApiModel):
    verse_id: int
    display_idx: int
    letter: str


class Acrostic(ApiModel):
    """A chapter's best alphabetic chain (DESIGN.md §16.15)."""

    unit: UnitSummary
    granularity: Literal["verse", "colon"]
    order_name: Literal["standard", "pe-ayin"]
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
