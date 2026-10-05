"""Corpus map, book affinity, stylometry, style seams, people and places
(DESIGN.md §16.4, §16.6, §16.11, §16.12)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models import (
    AffinityCell,
    AffinityPair,
    AffinityResponse,
    BookCount,
    BookStyle,
    CommunityResponse,
    CurvePoint,
    EntitiesResponse,
    Entity,
    EntityDetail,
    EntityLink,
    EntityPartner,
    LemmaForm,
    MapCluster,
    MapPoint,
    MapResponse,
    NetworkCommunity,
    NetworkEdge,
    NetworkNode,
    NetworkResponse,
    Seam,
    SeamFeature,
    SeamsResponse,
    StyloAxis,
    StyloDelta,
    StyloFeature,
    StylometryResponse,
    StyloPoint,
    UnitNetwork,
    UnitSummary,
)
from bsim.api.routes._common import (
    Conn,
    State,
    check_page,
    check_unit_type,
    gold_link,
    unit_or_404,
    unprocessable,
)
from bsim.text.normalize import consonantal

router = APIRouter()


ENTITY_KINDS = ("person", "place", "mixed", "unclear")


@router.get("/entities", response_model=EntitiesResponse)
def entities(
    state: State,
    conn: Conn,
    kind: str | None = None,
    book: int | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Names (people, places), most mentioned first; `q`: Hebrew letters of the name."""
    check_page(state, limit, offset)
    if kind is not None and kind not in ENTITY_KINDS:
        raise unprocessable(f"kind must be one of {list(ENTITY_KINDS)}")
    text = consonantal(q) if q else None
    total, rows = queries.entities_page(conn, kind, book, text, limit, offset)
    return {
        "kind": kind,
        "book": book,
        "q": q,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [Entity(**r) for r in rows],
    }


@router.get("/entities/{lemma}", response_model=EntityDetail)
def entity_detail(lemma: str, conn: Conn, partners: int = 15) -> dict[str, Any]:
    """One name: its mentions per book and the names it appears with (G² over verses)."""
    e = queries.entity(conn, lemma)
    if e is None:
        raise HTTPException(status_code=404, detail=f"unknown name {lemma!r}")
    if not 1 <= partners <= 50:
        raise unprocessable("partners must be between 1 and 50")
    ps = queries.entity_partners(conn, lemma, partners)
    labels = queries.verse_labels(conn, [e["first_vid"], e["last_vid"]])
    return {
        "entity": Entity(**e),
        "first_label": labels[e["first_vid"]][0],
        "last_label": labels[e["last_vid"]][0],
        "by_book": [
            BookCount(book_id=b["book_id"], n_verses=b["n"])
            for b in queries.entity_books(conn, lemma)
        ],
        "partners": [EntityPartner(**p) for p in ps],
        "links": [
            EntityLink(**x) for x in queries.entity_links_among(conn, [p["lemma"] for p in ps])
        ],
    }


@router.get("/unit-entities/{unit_id}", response_model=list[Entity])
def unit_entities(unit_id: str, conn: Conn, limit: int = 30) -> list[Entity]:
    """The names in a unit, most mentioned there first."""
    u = unit_or_404(conn, unit_id)
    if not 1 <= limit <= 100:
        raise unprocessable("limit must be between 1 and 100")
    rows = queries.unit_entities(conn, u["start_verse_id"], u["end_verse_id"], limit)
    return [Entity(**r) for r in rows]


@router.get("/seams", response_model=SeamsResponse)
def seams(
    state: State, conn: Conn, book: int | None = None, limit: int = 30, offset: int = 0
) -> dict[str, Any]:
    """Where style changes (DESIGN.md §16.12): a book's shift curve and seams, or without a
    book the strongest seams of the corpus."""
    check_page(state, limit, offset)
    meta = state.meta.get("seams", {})
    rows = queries.seams_of(conn, book, limit, offset)
    labels = queries.verse_labels(conn, [r["verse_id"] for r in rows])
    return {
        "book": book,
        "block_words": meta.get("block_words", state.cfg["seams"]["block_words"]),
        "threshold": meta.get("thresholds", {}).get(str(book)) if book is not None else None,
        "curve": [CurvePoint(**c) for c in queries.seam_curve(conn, book)]
        if book is not None
        else [],
        "seams": [
            Seam(
                **{k: r[k] for k in ("book_id", "verse_id", "shift", "threshold", "rank")},
                label=labels[r["verse_id"]][0],
                features=[
                    SeamFeature(feature=f, label=lab, z=z)
                    for f, lab, z in json.loads(r["features"])
                ],
            )
            for r in rows
        ],
    }


@router.get("/map/{unit_type}", response_model=MapResponse)
def corpus_map(unit_type: str, state: State, conn: Conn) -> dict[str, Any]:
    """2-D layout and thematic clusters of one unit type (DESIGN.md §16.4)."""
    check_unit_type(unit_type, list(state.cfg["map"]["clusters"]))
    clusters = queries.map_clusters(conn, unit_type)
    gloss = queries.gloss(conn, (lem for c in clusters for lem in c["lemmas"]))
    return {
        "unit_type": unit_type,
        "points": [MapPoint(**p) for p in queries.map_points(conn, unit_type)],
        "clusters": [
            MapCluster(
                cluster=c["cluster"],
                size=c["size"],
                lemmas=[LemmaForm(lemma=lem, he_lemma=gloss.get(lem, lem)) for lem in c["lemmas"]],
            )
            for c in clusters
        ],
    }


@router.get("/affinity", response_model=AffinityResponse)
def affinity(state: State, conn: Conn) -> dict[str, Any]:
    """Book x book lift of cross-book verse matches."""
    return {
        "order": state.meta.get("book_order", []),
        "cells": [
            AffinityCell(
                a=r["a_book"],
                b=r["b_book"],
                n_pairs=r["n_pairs"],
                expected=r["expected"],
                lift=r["lift"],
            )
            for r in queries.book_affinity(conn)
        ],
    }


@router.get("/affinity/{a}/{b}", response_model=list[AffinityPair])
def affinity_pairs(a: int, b: int, conn: Conn) -> list[AffinityPair]:
    """The strongest verse pairs between two books (book `a` on the `a` side)."""
    known = {r["book_id"] for r in queries.books(conn)}
    for book in (a, b):
        if book not in known:
            raise HTTPException(status_code=404, detail=f"unknown book {book}")
    rows = queries.book_examples(conn, a, b)
    if a > b:
        rows = [{**r, "a_vid": r["b_vid"], "b_vid": r["a_vid"]} for r in rows]
    vids = [v for r in rows for v in (r["a_vid"], r["b_vid"])]
    verses = queries.verses_by_id(conn, vids)
    units_ = queries.units_by_id(conn, [f"v:{v}" for v in vids])
    links = queries.verse_links(conn, [(r["a_vid"], r["b_vid"]) for r in rows])
    return [
        AffinityPair(
            score=r["score"],
            a=UnitSummary(**units_[f"v:{r['a_vid']}"]),
            b=UnitSummary(**units_[f"v:{r['b_vid']}"]),
            a_verse=verses[r["a_vid"]],
            b_verse=verses[r["b_vid"]],
            link=gold_link(*links[(r["a_vid"], r["b_vid"])])
            if (r["a_vid"], r["b_vid"]) in links
            else None,
        )
        for r in rows
    ]


@router.get("/stylometry", response_model=StylometryResponse)
def stylometry(state: State, conn: Conn) -> dict[str, Any]:
    """Chapter PCA of style features, the axes' loadings and the book Delta matrix."""
    sm = state.meta.get("stylometry") or {}
    return {
        "points": [StyloPoint(**p) for p in queries.stylo_points(conn)],
        "axes": [StyloAxis(**a) for a in sm.get("axes") or []],
        "order": sm.get("book_order") or [],
        "delta": [
            StyloDelta(a=r["a_book"], b=r["b_book"], delta=r["delta"])
            for r in queries.stylo_delta(conn)
        ],
    }


@router.get("/stylometry/book/{book_id}", response_model=BookStyle)
def book_style(book_id: int, state: State, conn: Conn) -> dict[str, Any]:
    """A book's most over- / under-used style features and its nearest books by Delta."""
    rows = queries.stylo_features(conn, book_id)
    if not rows:
        raise HTTPException(status_code=404, detail=f"unknown book {book_id}")
    words = (state.meta.get("stylometry") or {}).get("book_words") or []
    near = queries.stylo_delta(conn, book_id)[: state.cfg["stylometry"]["top_features"]]
    return {
        "book_id": book_id,
        "n_words": words[book_id] if book_id < len(words) else 0,
        "over": [
            StyloFeature(**{k: r[k] for k in ("feature", "label", "rate", "z")})
            for r in rows
            if r["side"] == "over"
        ],
        "under": [
            StyloFeature(**{k: r[k] for k in ("feature", "label", "rate", "z")})
            for r in rows
            if r["side"] == "under"
        ],
        "closest": [
            StyloDelta(
                a=book_id,
                b=r["b_book"] if r["a_book"] == book_id else r["a_book"],
                delta=r["delta"],
            )
            for r in near
        ],
    }


def _community(conn, row: dict[str, Any]) -> NetworkCommunity:
    lemmas = json.loads(row["lemmas"])
    gloss = queries.gloss(conn, lemmas)
    return NetworkCommunity(
        community=row["community"],
        size=row["size"],
        lemmas=[LemmaForm(lemma=lem, he_lemma=gloss.get(lem, lem)) for lem in lemmas],
        books=[BookCount(book_id=b, n_verses=n) for b, n in json.loads(row["books"])],
    )


def _nodes(conn, rows: list[dict[str, Any]]) -> list[NetworkNode]:
    units_ = queries.units_by_id(conn, [r["unit_id"] for r in rows])
    return [
        NetworkNode(
            unit=UnitSummary(**units_[r["unit_id"]]),
            **{k: r[k] for k in NetworkNode.model_fields if k != "unit"},
        )
        for r in rows
    ]


def _network_type(state, unit_type: str) -> str:
    return check_unit_type(unit_type, list(state.cfg["network"]["unit_types"]))


@router.get("/network/{unit_type}", response_model=NetworkResponse)
def network(unit_type: str, state: State, conn: Conn, central: int = 20) -> dict[str, Any]:
    """Communities of passages that echo each other, and the most central passages
    (DESIGN.md §16.17)."""
    _network_type(state, unit_type)
    if not 1 <= central <= 100:
        raise unprocessable("central must be between 1 and 100")
    return {
        "unit_type": unit_type,
        "communities": [_community(conn, r) for r in queries.network_communities(conn, unit_type)],
        "central": _nodes(conn, queries.network_nodes(conn, unit_type, top=central)),
    }


@router.get("/network/{unit_type}/{community}", response_model=CommunityResponse)
def network_community(unit_type: str, community: int, state: State, conn: Conn) -> dict[str, Any]:
    """One community: its passages (with their layout) and the echoes among them."""
    _network_type(state, unit_type)
    row = queries.network_community(conn, unit_type, community)
    if row is None:
        raise HTTPException(status_code=404, detail=f"unknown community {community}")
    rows = queries.network_nodes(conn, unit_type, community)
    edges = queries.network_edges_among(conn, unit_type, [r["unit_id"] for r in rows])
    return {
        "unit_type": unit_type,
        "community": _community(conn, row),
        "nodes": _nodes(conn, rows),
        "edges": [NetworkEdge(**e) for e in edges],
    }


@router.get("/unit-network/{unit_id}", response_model=UnitNetwork | None)
def unit_network(unit_id: str, conn: Conn) -> UnitNetwork | None:
    """A unit's place in the network (null for unit types without one)."""
    unit_or_404(conn, unit_id)
    n = queries.network_node(conn, unit_id)
    if n is None:
        return None
    size = queries.network_community(conn, n["unit_type"], n["community"])["size"]
    return UnitNetwork(node=_nodes(conn, [n])[0], rank=n["rank"], of=n["of"], community_size=size)
