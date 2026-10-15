"""Response models of `api/routes/places.py` (DESIGN.md §10)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel

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
