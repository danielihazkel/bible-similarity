"""Response models of `api/routes/places.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel, BookCount, Verse, VerseLabel

PlaceKind = Literal["town", "region", "landform", "water"]
NameKind = Literal["person", "people", "location", "landform", "water"]


class PlaceSite(ApiModel):
    """A place the text names and where it lies (§16.56)."""

    place_id: int
    he: str  # its Hebrew name (consonants)
    kind: PlaceKind | None
    lat: float | None
    lon: float | None
    score: int | None  # OpenBible's votes for the identification, 0..1000
    coord_source: Literal["openbible", "tipnr"] | None
    runner_up: float | None  # the second identification's votes as a share of the best
    n_identifications: int
    n_verses: int  # verses naming it
    n_here: int | None = None  # ... in the book / unit asked for (or by the name asked for)
    first_vid: int
    lemmas: list[str]  # the name lemmas that are this place


class PlaceMatch(PlaceSite):
    """A place the jump box found by a name (§16.57)."""

    exact: bool  # a name of it is the form asked for (else a name starts with it)
    first_label: str
    first_label_he: str


class PlaceLookup(ApiModel):
    query: str
    items: list[PlaceMatch]  # exact matches first, then prefixes; the most named first


class PlacesResponse(ApiModel):
    meta: dict[str, Any]  # counts, how mentions were matched, kinds, the hand check
    kind: PlaceKind | None
    book: int | None
    unit: str | None
    items: list[PlaceSite]  # most named first (in the book / unit: there)


class MapShape(ApiModel):
    layer: Literal["land", "lakes", "rivers"]
    rings: list[list[list[float]]]  # [[lon, lat], ...] per ring (rivers: per piece of the line)


class BasemapResponse(ApiModel):
    box: list[float]  # lon_min, lat_min, lon_max, lat_max
    shapes: list[MapShape]  # land first, then lakes, then rivers


class PlaceName(ApiModel):
    lemma: str
    he: str  # the name lemma's Hebrew form
    n_verses: int  # verses where it is this place


class PlacePartner(ApiModel):
    place_id: int
    he: str
    kind: PlaceKind | None
    n_verses: int  # verses naming both


class PlaceDetail(ApiModel):
    place: PlaceSite
    first_label: str
    first_label_he: str
    names: list[PlaceName]  # the names that are this place
    by_book: list[BookCount]
    partners: list[PlacePartner]  # places named in the same verses, most shared first


class PlaceVerse(ApiModel):
    verse: Verse
    tokens: list[int]  # display tokens naming the place


class PlaceVersesResponse(ApiModel):
    place_id: int
    total: int
    offset: int
    limit: int
    items: list[PlaceVerse]  # canon order


PlaceListKind = Literal["itinerary", "boundary", "towns", "nations"]


class NullHistogram(ApiModel):
    lo: float  # km: the first bin's left edge
    hi: float  # ... the last bin's right edge
    counts: list[int]  # random orders per bin


class PlaceListTest(ApiModel):
    """A list's path in the text's order against random orders of its places (§16.58)."""

    n: int  # places tested (located; sure sites only, for `sure`)
    path_km: float | None  # None: too few places to test
    null_mean: float | None
    null_sd: float | None
    p: float | None  # the share of random orders as short
    short_km: float | None  # a short path through the same places (nearest neighbour + 2-opt)
    order_score: float | None  # 0: no shorter than random; 1: as short as the short path
    hist: NullHistogram | None


class PlaceList(ApiModel):
    key: str
    kind: PlaceListKind
    label_en: str
    label_he: str
    first_vid: int
    last_vid: int
    n_named: int  # places of the kinds counted that the verses name
    all: PlaceListTest
    sure: PlaceListTest


class DistrictTest(ApiModel):
    """Mean km between two towns of one district against shuffled labels."""

    n: int
    districts: int | None = None
    within_km: float | None = None
    null_mean: float | None = None
    p: float | None = None
    all_km: float | None = None  # mean km between any two towns of the grouping
    nearest_same: float | None = None  # share of towns whose nearest town is of their district


class DistrictRow(ApiModel):
    n: int
    within_km: float | None  # None: a single town
    null_mean: float | None
    p: float | None


class District(ApiModel):
    district: int  # from 1
    label_en: str
    label_he: str
    first_vid: int
    last_vid: int
    all: DistrictRow | None
    sure: DistrictRow | None


class DistrictGrouping(ApiModel):
    key: str
    n_named: int
    all: DistrictTest
    sure: DistrictTest
    districts: list[District]


class PlaceListsResponse(ApiModel):
    meta: dict[str, Any]  # shuffles, alpha, sure_score, how many lists hold
    lists: list[PlaceList]
    groupings: list[DistrictGrouping]


class PlaceListStep(ApiModel):
    pos: int  # from 1
    place: PlaceSite
    verse: VerseLabel  # where the list first names it
    km: float | None  # from the place before
    sure: bool
    short_pos: int  # its place on the short path


class PlaceListDetail(ApiModel):
    list: PlaceList
    steps: list[PlaceListStep]


class DistrictTown(ApiModel):
    district: int
    place: PlaceSite
    verse: VerseLabel
    sure: bool


class DistrictDetail(ApiModel):
    grouping: DistrictGrouping
    towns: list[DistrictTown]


class ArcPlace(ApiModel):
    place_id: int
    he: str
    kind: PlaceKind | None


class ArcChapter(ApiModel):
    """A chapter's centre: the mean on the sphere of the places it names (§16.60)."""

    book_id: int
    chapter: int
    unit_id: str  # c:{book_id}:{chapter}
    label_en: str
    label_he: str
    first_vid: int
    n_mentions: int  # (place, verse) mentions
    n_places: int
    lat: float
    lon: float
    spread_km: float  # mean km of its mentions from its centre
    reach_km: float  # its centre's km from Jerusalem
    step_km: float | None  # from the book's placed chapter before
    prev_chapter: int | None
    top_place: ArcPlace | None  # the place it names most
    oracle: bool


class ArcBook(ApiModel):
    book_id: int
    name: str
    he_name: str
    chapters: int
    n: int  # placed chapters
    mean_step: float | None  # km between consecutive placed chapters (None: too few to test)
    null_mean: float | None  # ... in shuffled orders
    ratio: float | None
    p: float | None


class ArcTest(ApiModel):
    chapters: int
    placed: int
    books: int  # books tested
    steps: int
    mean_step: float | None
    null_mean: float | None
    p: float | None
    books_held: int


class ArcMoveEnd(ApiModel):
    label_en: str
    label_he: str
    unit_id: str
    n_mentions: int
    n_places: int
    lat: float
    lon: float
    spread_km: float
    top_place: ArcPlace | None
    to_from_region: float  # km from the region the text leaves
    to_to_region: float  # km from the region it goes to
    nearest: str  # the nearest of the regions


class ArcMove(ApiModel):
    key: str
    from_region: str
    to_region: str
    start: ArcMoveEnd | None  # the span before
    end: ArcMoveEnd | None  # the span after
    km: float | None  # between their centres
    holds: bool | None


class OracleTest(ApiModel):
    n: int
    n_other: int
    observed: float  # the oracles' mean km
    other: float  # the other prophetic chapters' mean
    median: float
    other_median: float
    null_mean: float  # the mean with labels shuffled
    p: float


class ArcOracles(ApiModel):
    labels_en: list[str]
    labels_he: list[str]
    chapters: int
    placed: int
    alpha: float  # each measure's level (alpha / 2)
    spread: OracleTest | None
    reach: OracleTest | None
    holds: bool | None
    items: list[ArcChapter]  # the oracles' placed chapters


class PlaceArcResponse(ApiModel):
    meta: dict[str, Any]  # shuffles, alpha, min_mentions, min_chapters, the regions' points
    arc: ArcTest | None
    books: list[ArcBook]
    moves: list[ArcMove]
    oracles: ArcOracles | None


class PlaceArcBookResponse(ApiModel):
    book: ArcBook
    items: list[ArcChapter]  # its placed chapters in order


class LinkPlace(ApiModel):
    place_id: int
    he: str
    kind: PlaceKind | None
    lat: float
    lon: float


class PlaceLinkPair(ApiModel):
    """Two places named together (§16.61)."""

    a: LinkPlace
    b: LinkPlace
    n_together: int  # verses naming both
    n_a: int
    n_b: int
    expected: float
    g2: float
    km: float
    lead_rank: int | None  # among pairs at least `far_km` apart, by G²


class DecayTest(ApiModel):
    """Spearman's rho between linked pairs' G² and km against shuffled coordinates."""

    places: int | None = None
    pairs: int
    rho: float | None = None
    null_mean: float | None = None
    null_q05: float | None = None
    null_q95: float | None = None
    p: float | None = None
    median_km: float | None = None
    verses: int | None = None  # verses in scope


class DecayBin(ApiModel):
    bin: int
    lo_km: float
    hi_km: float | None
    pairs: int  # pairs of places named in `min_together` verses or more
    linked: int
    share: float | None
    median_g2: float | None


DecayVariant = Literal["all", "sure", "no_lists"]


class DecayRow(ApiModel):
    variant: DecayVariant
    test: DecayTest
    bins: list[DecayBin]


class KnownLink(ApiModel):
    a: str  # the Hebrew names in config
    b: str
    found: bool
    pair: PlaceLinkPair | None
    rank: int | None  # among the far pairs
    holds: bool


class LinkPoint(ApiModel):
    km: float
    g2: float
    far: bool  # at least `far_km` apart


class PlaceLinksResponse(ApiModel):
    meta: dict[str, Any]  # shuffles, alpha, min_together, sure_score, far_km, top, far_pairs
    lists_en: list[str]  # the `no_lists` variant's spans
    lists_he: list[str]
    variants: list[DecayRow]
    known: list[KnownLink]
    leads: list[PlaceLinkPair]
    scatter: list[LinkPoint]  # every linked pair (`all`): its km and G²


PlaceLinkSort = Literal["g2", "km", "near"]


class PlaceLinkPairsResponse(ApiModel):
    place: int | None
    sort: PlaceLinkSort
    far: bool
    total: int
    offset: int
    limit: int
    items: list[PlaceLinkPair]
