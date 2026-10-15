"""The gazetteer and its map (DESIGN.md §16.56–16.57): every place the text names, its kind and
where it lies, in all the text or in a book or unit; one place's panel and verses; the base map."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.common import BookCount
from bsim.api.models.places import (
    BasemapResponse,
    MapShape,
    PlaceDetail,
    PlaceKind,
    PlaceName,
    PlacePartner,
    PlaceSite,
    PlacesResponse,
    PlaceVerse,
    PlaceVersesResponse,
)
from bsim.api.routes._common import Conn, State, check_page, unit_span

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


@router.get("/places/basemap", response_model=BasemapResponse)
def basemap(state: State, conn: Conn) -> dict[str, Any]:
    """Land, lakes and rivers of the region (Natural Earth), in longitude / latitude."""
    meta = state.meta.get("places") or {}
    return {
        "box": (meta.get("map") or {}).get("box") or [],
        "shapes": [MapShape(**s) for s in queries.map_shapes(conn)],
    }


def _place_or_404(conn: Any, place_id: int) -> dict[str, Any]:
    p = queries.place(conn, place_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"unknown place {place_id}")
    return p


@router.get("/places/{place_id}", response_model=PlaceDetail)
def place_detail(place_id: int, state: State, conn: Conn) -> dict[str, Any]:
    """One place: the names that are it, its verses per book and the places named with it."""
    p = _place_or_404(conn, place_id)
    labels = queries.verse_labels(conn, [p["first_vid"]])
    limit = state.cfg["serve"]["places"]["partners"]
    return {
        "place": PlaceSite(**p),
        "first_label": labels[p["first_vid"]][0],
        "first_label_he": labels[p["first_vid"]][1],
        "names": [PlaceName(**r) for r in queries.place_names(conn, place_id)],
        "by_book": [BookCount(**r) for r in queries.place_books(conn, place_id)],
        "partners": [PlacePartner(**r) for r in queries.place_partners(conn, place_id, limit)],
    }


@router.get("/places/{place_id}/verses", response_model=PlaceVersesResponse)
def place_verses(
    place_id: int, state: State, conn: Conn, limit: int = 20, offset: int = 0
) -> dict[str, Any]:
    """The verses naming a place, in canon order, with the words that name it."""
    _place_or_404(conn, place_id)
    check_page(state, limit, offset)
    total, rows = queries.place_verses_page(conn, place_id, limit, offset)
    vids = [r["verse_id"] for r in rows]
    verses = queries.verses_by_id(conn, vids)
    lemmas = {r["verse_id"]: set(r["lemmas"].split()) for r in rows}
    tokens: dict[int, set[int]] = {v: set() for v in vids}
    for w in queries.words(conn, vids):
        here = lemmas[w["verse_id"]] & set(w["content_lemmas"].split())
        if w["display_idx"] is not None and here:
            tokens[w["verse_id"]].add(w["display_idx"])
    return {
        "place_id": place_id,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [PlaceVerse(verse=verses[v], tokens=sorted(tokens[v])) for v in vids],
    }
