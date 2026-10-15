"""The gazetteer (DESIGN.md §16.56): every place the text names, its kind and where it lies, in
all the text or in a book or unit."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models.places import PlaceKind, PlaceSite, PlacesResponse
from bsim.api.routes._common import Conn, State, unit_span

router = APIRouter()


@router.get("/places", response_model=PlacesResponse)
def places(
    state: State,
    conn: Conn,
    kind: PlaceKind | None = None,
    book: int | None = None,
    unit: str | None = None,
) -> dict[str, Any]:
    """The places (of a kind), most named first; in a book or unit, those named there."""
    rows = queries.places_list(conn, kind, book, unit_span(conn, unit))
    return {
        "meta": state.meta.get("places") or {},
        "kind": kind,
        "book": book,
        "unit": unit,
        "items": [PlaceSite(**r) for r in rows],
    }
