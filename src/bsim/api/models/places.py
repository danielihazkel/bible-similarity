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
