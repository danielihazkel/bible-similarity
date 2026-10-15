"""Response models of `api/routes/places.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel, BookCount, Verse

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
