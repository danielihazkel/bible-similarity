"""The gazetteer and its map (DESIGN.md §16.56–16.58): every place the text names, its kind and
where it lies, in all the text or in a book or unit; one place's panel and verses; the base map;
the place lists' paths and districts against shuffles."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.common import BookCount, VerseLabel
from bsim.api.models.places import (
    BasemapResponse,
    District,
    DistrictDetail,
    DistrictGrouping,
    DistrictRow,
    DistrictTest,
    DistrictTown,
    MapShape,
    PlaceDetail,
    PlaceKind,
    PlaceList,
    PlaceListDetail,
    PlaceListsResponse,
    PlaceListStep,
    PlaceListTest,
    PlaceName,
    PlacePartner,
    PlaceSite,
    PlacesResponse,
    PlaceVerse,
    PlaceVersesResponse,
)
from bsim.api.routes._common import Conn, State, check_page, span_label, unit_span

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


def _label(labels: dict[int, tuple[str, str]], vid: int) -> VerseLabel:
    return VerseLabel(verse_id=vid, label_en=labels[vid][0], label_he=labels[vid][1])


def _place_lists(conn: Any, rows: list[dict[str, Any]]) -> list[PlaceList]:
    """The tests' rows (both variants per list) as one entry per list."""
    labels = queries.verse_labels(conn, [v for r in rows for v in (r["first_vid"], r["last_vid"])])
    by_key: dict[str, dict[str, dict[str, Any]]] = {}
    for r in rows:
        by_key.setdefault(r["list_key"], {})[r["variant"]] = r
    out = []
    for key, v in by_key.items():
        a = v["all"]
        out.append(PlaceList(
            key=key, kind=a["kind"],
            label_en=span_label(labels, a["first_vid"], a["last_vid"], 0),
            label_he=span_label(labels, a["first_vid"], a["last_vid"], 1),
            first_vid=a["first_vid"], last_vid=a["last_vid"], n_named=a["n_named"],
            all=PlaceListTest(**a), sure=PlaceListTest(**v.get("sure", {"n": 0})),
        ))  # fmt: skip
    return out


def _groupings(conn: Any, meta: dict[str, Any], only: str | None = None) -> list[DistrictGrouping]:
    groups = {k: g for k, g in (meta.get("districts") or {}).items() if only in (None, k)}
    rows = queries.place_districts(conn, only)
    labels = queries.verse_labels(conn, [v for r in rows for v in (r["first_vid"], r["last_vid"])])
    out = []
    for key, g in groups.items():
        by_d: dict[int, dict[str, dict[str, Any]]] = {}
        for r in rows:
            if r["grouping"] == key:
                by_d.setdefault(r["district"], {})[r["variant"]] = r
        districts = []
        for d, v in sorted(by_d.items()):
            r = v.get("all") or v["sure"]
            districts.append(District(
                district=d,
                label_en=span_label(labels, r["first_vid"], r["last_vid"], 0),
                label_he=span_label(labels, r["first_vid"], r["last_vid"], 1),
                first_vid=r["first_vid"], last_vid=r["last_vid"],
                all=DistrictRow(**v["all"]) if "all" in v else None,
                sure=DistrictRow(**v["sure"]) if "sure" in v else None,
            ))  # fmt: skip
        out.append(DistrictGrouping(
            key=key, n_named=g.get("n_named") or 0,
            all=DistrictTest(**(g.get("all") or {"n": 0})),
            sure=DistrictTest(**(g.get("sure") or {"n": 0})),
            districts=districts,
        ))  # fmt: skip
    return out


@router.get("/place-lists", response_model=PlaceListsResponse)
def place_lists(state: State, conn: Conn) -> dict[str, Any]:
    """The place lists' paths against random orders and the town lists' districts against
    shuffled labels, each on every located place and on sure sites alone."""
    meta = state.meta.get("place_lists") or {}
    return {
        "meta": {k: v for k, v in meta.items() if k not in ("lists", "districts")},
        "lists": _place_lists(conn, queries.place_lists(conn)),
        "groupings": _groupings(conn, meta),
    }


@router.get("/place-lists/{key}", response_model=PlaceListDetail)
def place_list(key: str, conn: Conn) -> dict[str, Any]:
    """One list: its located places in the text's order, the km of each step and the short
    path's order."""
    rows = queries.place_lists(conn, key)
    if not rows:
        raise HTTPException(status_code=404, detail=f"unknown place list {key!r}")
    steps = queries.place_list_steps(conn, key)
    labels = queries.verse_labels(conn, [s["verse_id"] for s in steps])
    return {
        "list": _place_lists(conn, rows)[0],
        "steps": [
            PlaceListStep(pos=s["pos"], place=PlaceSite(**s), verse=_label(labels, s["verse_id"]),
                          km=s["km"], sure=bool(s["sure"]), short_pos=s["short_pos"])  # fmt: skip
            for s in steps
        ],
    }


@router.get("/place-districts/{key}", response_model=DistrictDetail)
def place_districts(key: str, state: State, conn: Conn) -> dict[str, Any]:
    """One grouping of town lists: its districts' tests and towns."""
    grouping = _groupings(conn, state.meta.get("place_lists") or {}, key)
    if not grouping:
        raise HTTPException(status_code=404, detail=f"unknown district grouping {key!r}")
    towns = queries.place_district_towns(conn, key)
    labels = queries.verse_labels(conn, [t["verse_id"] for t in towns])
    return {
        "grouping": grouping[0],
        "towns": [
            DistrictTown(district=t["district"], place=PlaceSite(**t),
                         verse=_label(labels, t["verse_id"]), sure=bool(t["sure"]))  # fmt: skip
            for t in towns
        ],
    }
