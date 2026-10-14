"""Response models of `api/routes/corpus.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Literal

from bsim.api.models.common import (
    ApiModel,
    BookCount,
    GoldLink,
    LemmaForm,
    UnitSummary,
    UnitType,
    Verse,
)

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


class MapPoint(ApiModel):
    unit_id: str
    label_en: str
    label_he: str
    book_id: int
    n_verses: int
    x: float
    y: float
    cluster: int
    list_verses: int  # verses inside a list (`bsim forms`, §16.45)


class MapCluster(ApiModel):
    cluster: int
    size: int
    lemmas: list[LemmaForm]  # label lemmas, strongest first


class MapResponse(ApiModel):
    unit_type: UnitType
    points: list[MapPoint]
    clusters: list[MapCluster]
    lists: bool  # lists computed (`bsim forms`): the map can be coloured by them


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
    unit_type: UnitType
    communities: list[NetworkCommunity]
    central: list[NetworkNode]  # highest PageRank


class CommunityResponse(ApiModel):
    unit_type: UnitType
    community: NetworkCommunity
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]


class UnitNetwork(ApiModel):
    """Where a unit sits in the network: its metrics and its centrality rank."""

    node: NetworkNode
    rank: int  # 1 = highest PageRank of its unit type
    of: int
    community_size: int
