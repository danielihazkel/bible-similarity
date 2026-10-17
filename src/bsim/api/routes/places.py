"""The gazetteer and its map (DESIGN.md §16.56–16.60): every place the text names, its kind and
where it lies, in all the text or in a book or unit; one place's panel and verses; the base map;
the place lists' paths and districts against shuffles; the geographic arc of the chapters."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.common import BookCount, VerseLabel
from bsim.api.models.places import (
    ArcBook,
    ArcChapter,
    ArcMove,
    ArcMoveEnd,
    ArcOracles,
    ArcPlace,
    ArcTest,
    BasemapResponse,
    DecayBin,
    DecayRow,
    DecayTest,
    District,
    DistrictDetail,
    DistrictGrouping,
    DistrictRow,
    DistrictTest,
    DistrictTown,
    KnownLink,
    LinkPlace,
    LinkPoint,
    MapShape,
    PlaceArcBookResponse,
    PlaceArcResponse,
    PlaceDetail,
    PlaceKind,
    PlaceLinkPair,
    PlaceLinkPairsResponse,
    PlaceLinkSort,
    PlaceLinksResponse,
    PlaceList,
    PlaceListDetail,
    PlaceListsResponse,
    PlaceListStep,
    PlaceListTest,
    PlaceLookup,
    PlaceMatch,
    PlaceName,
    PlacePartner,
    PlaceSite,
    PlacesResponse,
    PlaceVerse,
    PlaceVersesResponse,
)
from bsim.api.routes._common import (
    Conn,
    State,
    check_page,
    span_label,
    unit_span,
    unprocessable,
)
from bsim.data.canon import BOOKS, hebrew_numeral
from bsim.data.refs import parse_ref

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


@router.get("/places/lookup", response_model=PlaceLookup)
def place_lookup(q: str, conn: Conn, limit: int = 6) -> dict[str, Any]:
    """Places by a Hebrew name (pointing ignored, prefixes dropped as for `/lemmas`) or a name's
    Strong's number, for the jump box: exact matches first, the most named first."""
    if not 1 <= limit <= 50:
        raise unprocessable("limit must be between 1 and 50")
    rows = queries.place_lookup(conn, q, limit)
    labels = queries.verse_labels(conn, [r["first_vid"] for r in rows])
    return {
        "query": q,
        "items": [
            PlaceMatch(**r, first_label=labels[r["first_vid"]][0],
                       first_label_he=labels[r["first_vid"]][1])  # fmt: skip
            for r in rows
        ],
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


def _top(place_id: int | None, he: str | None, kind: str | None) -> ArcPlace | None:
    return None if place_id is None else ArcPlace(place_id=place_id, he=he or "", kind=kind)


def _arc_chapter(r: dict[str, Any]) -> ArcChapter:
    b, c = r["book_id"], r["chapter"]
    return ArcChapter(
        **{k: r[k] for k in ("book_id", "chapter", "first_vid", "n_mentions", "n_places", "lat",
                             "lon", "spread_km", "reach_km", "step_km", "prev_chapter")},
        unit_id=f"c:{b}:{c}",
        label_en=f"{BOOKS[b].sefaria} {c}",
        label_he=f"{BOOKS[b].he} {hebrew_numeral(c)}",
        top_place=_top(r["top_place"], r["top_he"], r["top_kind"]),
        oracle=bool(r["oracle"]),
    )  # fmt: skip


def _arc_book(r: dict[str, Any]) -> ArcBook:
    b = BOOKS[r["book_id"]]
    return ArcBook(**r, name=b.sefaria, he_name=b.he)


def _ref_labels(conn: Any, ref: str, vids: list[int]) -> tuple[str, str, str]:
    """A span's English and Hebrew labels and its unit: "Genesis 35–37" / "בראשית לה–לז" and the
    first chapter for whole chapters; else the verse range and its first verse."""
    r = parse_ref(ref)
    if r.v1 is None:
        b = r.book
        tail_en, tail_he = (f"–{r.c2}", f"–{hebrew_numeral(r.c2)}") if r.c2 != r.c1 else ("", "")
        return (f"{b.sefaria} {r.c1}{tail_en}", f"{b.he} {hebrew_numeral(r.c1)}{tail_he}",
                f"c:{b.book_id}:{r.c1}")  # fmt: skip
    labels = queries.verse_labels(conn, vids)
    first, last = vids
    return span_label(labels, first, last, 0), span_label(labels, first, last, 1), f"v:{first}"


def _move(conn: Any, mv: dict[str, Any]) -> ArcMove:
    ends = {}
    for side in ("from", "to"):
        end = mv.get(side)
        if end is None:
            ends[side] = None
            continue
        en, he, unit = _ref_labels(conn, mv[f"{side}_ref"], mv[f"{side}_vids"])
        top = queries.place(conn, end["top_place"]) if end.get("top_place") is not None else None
        ends[side] = ArcMoveEnd(
            **{k: end[k] for k in ("n_mentions", "n_places", "lat", "lon", "spread_km",
                                   "to_from_region", "to_to_region", "nearest")},
            label_en=en, label_he=he, unit_id=unit,
            top_place=_top(top["place_id"], top["he"], top["kind"]) if top else None,
        )  # fmt: skip
    return ArcMove(
        key=mv["key"], from_region=mv["from_region"], to_region=mv["to_region"],
        start=ends["from"], end=ends["to"], km=mv.get("km"), holds=mv.get("holds"),
    )  # fmt: skip


@router.get("/place-arc", response_model=PlaceArcResponse)
def place_arc(state: State, conn: Conn) -> dict[str, Any]:
    """The geographic arc (§16.60): consecutive chapters' centres against shuffled orders, per
    book and over all; the known moves; the oracles against the nations against the other
    prophetic chapters, with their chapters."""
    meta = state.meta.get("place_arc") or {}
    o = meta.get("oracles") or {}
    oracles = None
    if o:
        labels = [_ref_labels(conn, ref, [0, 0]) for ref in o.get("refs") or []]
        oracles = ArcOracles(
            labels_en=[x[0] for x in labels], labels_he=[x[1] for x in labels],
            chapters=o.get("chapters") or 0, placed=o.get("placed") or 0,
            alpha=o.get("alpha") or 0.025, spread=o.get("spread"), reach=o.get("reach"),
            holds=o.get("holds"),
            items=[_arc_chapter(r) for r in queries.place_arc_chapters(conn, oracle=True)],
        )  # fmt: skip
    return {
        "meta": {k: meta.get(k) for k in ("shuffles", "alpha", "min_mentions", "min_chapters",
                                          "regions") if k in meta},  # fmt: skip
        "arc": ArcTest(**meta["arc"]) if meta.get("arc") else None,
        "books": [_arc_book(r) for r in queries.place_arc_books(conn)],
        "moves": [_move(conn, mv) for mv in meta.get("moves") or []],
        "oracles": oracles,
    }


@router.get("/place-arc/{book_id}", response_model=PlaceArcBookResponse)
def place_arc_book(book_id: int, conn: Conn) -> dict[str, Any]:
    """One book's placed chapters in order: centre, spread and the step from the one before."""
    book = next((r for r in queries.place_arc_books(conn) if r["book_id"] == book_id), None)
    if book is None:
        raise HTTPException(status_code=404, detail=f"no arc for book {book_id}")
    return {
        "book": _arc_book(book),
        "items": [_arc_chapter(r) for r in queries.place_arc_chapters(conn, book_id)],
    }


def _link_pair(r: dict[str, Any]) -> PlaceLinkPair:
    side = {s: LinkPlace(place_id=r[s], he=r[f"{s}_he"], kind=r[f"{s}_kind"], lat=r[f"{s}_lat"],
                         lon=r[f"{s}_lon"]) for s in ("a", "b")}  # fmt: skip
    return PlaceLinkPair(
        **side, **{k: r[k] for k in ("n_together", "n_a", "n_b", "expected", "g2", "km",
                                     "lead_rank")},
    )  # fmt: skip


@router.get("/place-links", response_model=PlaceLinksResponse)
def place_links(state: State, conn: Conn) -> dict[str, Any]:
    """Do places named together lie together (§16.61)? Per variant, rho between the linked
    pairs' G² and km against shuffled coordinates, and the decay curve; the known answers and
    the leads (far apart, strongly linked)."""
    meta = state.meta.get("place_links") or {}
    tests = meta.get("tests") or {}
    bins: dict[str, list[DecayBin]] = {}
    for r in queries.place_link_bins(conn):
        bins.setdefault(r.pop("variant"), []).append(DecayBin(**r))
    variants = [DecayRow(variant=v, test=DecayTest(**tests[v]), bins=bins.get(v, []))
                for v in ("all", "sure", "no_lists") if v in tests]  # fmt: skip
    n_leads = meta.get("leads") or 25
    leads = [_link_pair(r) for r in queries.place_links_page(conn, None, "g2", True, n_leads, 0)[1]]
    known = []
    for k in meta.get("known") or []:
        pair = None
        if k.get("a_id") is not None:
            rows = queries.place_links_page(conn, k["a_id"], "g2", False, 1000, 0)[1]
            pair = next((_link_pair(r) for r in rows if k["b_id"] in (r["a"], r["b"])), None)
        known.append(KnownLink(a=k["a"], b=k["b"], found=k["found"], pair=pair, rank=k["rank"],
                               holds=k["holds"]))  # fmt: skip
    labels = [_ref_labels(conn, ref, [0, 0]) for ref in meta.get("lists") or []]
    return {
        "meta": {k: meta.get(k) for k in ("shuffles", "alpha", "min_together", "sure_score",
                                          "far_km", "top", "far_pairs") if k in meta},  # fmt: skip
        "lists_en": [x[0] for x in labels],
        "lists_he": [x[1] for x in labels],
        "variants": variants,
        "known": known,
        "leads": leads,
        "scatter": [LinkPoint(**r) for r in queries.place_link_points(conn)],
    }


@router.get("/place-links/pairs", response_model=PlaceLinkPairsResponse)
def place_link_pairs(
    state: State,
    conn: Conn,
    place: int | None = None,
    sort: PlaceLinkSort = "g2",
    far: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Linked pairs of places: all, or one place's; strongest first, farthest or nearest first;
    `far`: pairs at least `far_km` apart (the leads)."""
    check_page(state, limit, offset)
    total, rows = queries.place_links_page(conn, place, sort, far, limit, offset)
    return {"place": place, "sort": sort, "far": far, "total": total, "offset": offset,
            "limit": limit, "items": [_link_pair(r) for r in rows]}  # fmt: skip
