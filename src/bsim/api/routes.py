"""`/api` endpoints (DESIGN.md §10). Bad parameters -> 422, unknown ids -> 404."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from collections.abc import Iterator
from typing import Annotated, Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from bsim.api import queries
from bsim.api.app import ServeState
from bsim.api.models import (
    Book,
    CompareResponse,
    ExplainResponse,
    Hit,
    LemmaForm,
    Meta,
    Mode,
    Pair,
    SearchHit,
    SearchResponse,
    SharedLemma,
    SimilarResponse,
    UnitDetail,
    UnitSummary,
    WordRef,
)
from bsim.api.search import EncoderUnavailable
from bsim.api.search import search as run_search
from bsim.store.db import similar as db_similar
from bsim.text.normalize import consonantal

router = APIRouter(prefix="/api")


def get_state(request: Request) -> ServeState:
    return request.app.state.serve


def get_conn(state: Annotated[ServeState, Depends(get_state)]) -> Iterator[sqlite3.Connection]:
    conn = state.connect()
    try:
        yield conn
    finally:
        conn.close()


State = Annotated[ServeState, Depends(get_state)]
Conn = Annotated[sqlite3.Connection, Depends(get_conn)]


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


def _k(state: ServeState, k: int | None) -> int:
    k = state.cfg["serve"]["default_k"] if k is None else k
    k_max = state.cfg["retrieval"]["k"]
    if not 1 <= k <= k_max:
        raise _unprocessable(f"k must be between 1 and {k_max}")
    return k


def _unit_or_404(conn: sqlite3.Connection, unit_id: str) -> dict[str, Any]:
    u = queries.unit(conn, unit_id)
    if u is None:
        raise HTTPException(status_code=404, detail=f"unknown unit {unit_id!r}")
    return u


def _verse_or_404(state: ServeState, verse_id: int) -> int:
    if not 0 <= verse_id < state.n_verses:
        raise HTTPException(status_code=404, detail=f"unknown verse {verse_id}")
    return verse_id


def _num(v: Any, cast: type) -> Any:
    """numpy / pandas scalar -> int or float; NaN / NA (missing breakdown) -> None."""
    return None if v is None or pd.isna(v) else cast(v)


@router.get("/books", response_model=list[Book])
def books(conn: Conn) -> list[dict[str, Any]]:
    return queries.books(conn)


@router.get("/units/{unit_type}", response_model=list[UnitSummary])
def units(
    unit_type: str, state: State, conn: Conn, book: int | None = None
) -> list[dict[str, Any]]:
    types = state.cfg["units"]["types"]
    if unit_type not in types:
        raise _unprocessable(f"unknown unit type {unit_type!r}; choose from {types}")
    return queries.units_of_type(conn, unit_type, book)


@router.get("/unit/{unit_id}", response_model=UnitDetail)
def unit(unit_id: str, conn: Conn) -> dict[str, Any]:
    u = _unit_or_404(conn, unit_id)
    prev_id, next_id = queries.neighbours(conn, u)
    return {
        "unit": u,
        "verses": queries.verse_range(conn, u["start_verse_id"], u["end_verse_id"]),
        "parents": queries.parents(conn, u),
        "prev_id": prev_id,
        "next_id": next_id,
    }


@router.get("/similar/{unit_id}", response_model=SimilarResponse)
def similar(
    unit_id: str,
    state: State,
    conn: Conn,
    mode: Mode = "fused",
    k: int | None = None,
    exclude: Annotated[str, Query(description="comma-separated: neighbors, chapter, book")] = "",
) -> dict[str, Any]:
    u = _unit_or_404(conn, unit_id)
    k = _k(state, k)
    filters = [f.strip() for f in exclude.split(",") if f.strip()]
    try:
        rows = db_similar(
            conn,
            u["unit_type"],
            mode,
            unit_id,
            k=k,
            exclude=filters,
            window=state.cfg["retrieval"]["neighbor_window"],
        )
    except ValueError as e:
        raise _unprocessable(str(e)) from e
    targets = queries.units_by_id(conn, [r["tgt_id"] for r in rows])
    starts = [t["start_verse_id"] for t in targets.values()]
    if u["unit_type"] == "verse":
        verses, previews = queries.verses_by_id(conn, starts), {}
    else:
        verses, previews = {}, queries.previews(conn, starts, state.cfg["serve"]["preview_chars"])
    hits = []
    for r in rows:
        t = targets[r["tgt_id"]]
        hits.append(
            Hit(
                rank=r["rank"],
                score=r["score"],
                lex_score=r["lex_score"],
                lex_rank=r["lex_rank"],
                sem_score=r["sem_score"],
                sem_rank=r["sem_rank"],
                unit=UnitSummary(**t),
                verse=verses.get(t["start_verse_id"]),
                preview=previews.get(t["start_verse_id"]),
            )
        )
    return {"unit": u, "mode": mode, "k": k, "exclude": filters, "hits": hits}


@router.get("/explain", response_model=ExplainResponse)
def explain(a: int, b: int, state: State, conn: Conn) -> dict[str, Any]:
    _verse_or_404(state, a)
    _verse_or_404(state, b)
    occ: dict[int, dict[str, list[WordRef]]] = {a: defaultdict(list), b: defaultdict(list)}
    for w in queries.words(conn, [a, b]):
        ref = WordRef(idx=w["idx"], display_idx=w["display_idx"], in_formula=bool(w["in_formula"]))
        for lemma in dict.fromkeys(w["content_lemmas"].split()):
            occ[w["verse_id"]][lemma].append(ref)
    shared = [lem for lem in occ[a] if lem in occ[b]]
    gloss = queries.gloss(conn, shared)
    return {
        "a": a,
        "b": b,
        "shared": [
            SharedLemma(
                lemma=lem,
                he_lemma=gloss.get(lem, lem),
                formula=all(r.in_formula for r in occ[a][lem] + occ[b][lem]),
                a_words=occ[a][lem],
                b_words=occ[b][lem],
            )
            for lem in shared
        ],
    }


def _best_pairs(
    sims: np.ndarray,
    src_ids: list[int],
    tgt_ids: list[int],
    lemmas: dict[int, list[str]],
    gloss: dict[str, str],
) -> list[Pair]:
    best = sims.argmax(axis=1)  # ties: the first (lowest verse id)
    pairs = []
    for i, j in enumerate(best):
        src, tgt = src_ids[i], tgt_ids[j]
        tgt_lemmas = set(lemmas.get(tgt, []))
        shared = [lem for lem in lemmas.get(src, []) if lem in tgt_lemmas]
        pairs.append(
            Pair(
                src=src,
                tgt=tgt,
                cosine=float(sims[i, j]),
                shared=[LemmaForm(lemma=lem, he_lemma=gloss.get(lem, lem)) for lem in shared],
            )
        )
    return pairs


@router.get("/compare", response_model=CompareResponse)
def compare(a: str, b: str, state: State, conn: Conn) -> dict[str, Any]:
    ua, ub = _unit_or_404(conn, a), _unit_or_404(conn, b)
    a_ids = list(range(ua["start_verse_id"], ua["end_verse_id"] + 1))
    b_ids = list(range(ub["start_verse_id"], ub["end_verse_id"] + 1))
    ea = np.asarray(state.emb[a_ids[0] : a_ids[-1] + 1], dtype=np.float32)
    eb = np.asarray(state.emb[b_ids[0] : b_ids[-1] + 1], dtype=np.float32)
    sims = ea @ eb.T
    lemmas = queries.verse_lemmas(queries.words(conn, a_ids + b_ids))
    gloss = queries.gloss(conn, (lem for lems in lemmas.values() for lem in lems))
    bma = 0.5 * (float(sims.max(axis=1).mean()) + float(sims.max(axis=0).mean()))
    return {
        "a": ua,
        "b": ub,
        "bma": bma,
        "a_to_b": _best_pairs(sims, a_ids, b_ids, lemmas, gloss),
        "b_to_a": _best_pairs(sims.T, b_ids, a_ids, lemmas, gloss),
        "verses": queries.verses_by_id(conn, a_ids + b_ids),
    }


@router.get("/search", response_model=SearchResponse)
def search(
    q: str, state: State, conn: Conn, mode: Mode = "fused", k: int | None = None
) -> dict[str, Any]:
    k = _k(state, k)
    max_chars = state.cfg["serve"]["search"]["max_query_chars"]
    if len(q) > max_chars:
        raise _unprocessable(f"query longer than {max_chars} characters")
    if not consonantal(q):
        raise _unprocessable("the query has no Hebrew letters")
    try:
        normalized, tokens, df = run_search(state, q, mode, k)
    except EncoderUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    vids = df.tgt.tolist()
    verses = queries.verses_by_id(conn, vids)
    labels = queries.verse_labels(conn, vids)
    hits = []
    for row in df.to_dict("records"):
        vid = int(row["tgt"])
        hits.append(
            SearchHit(
                rank=int(row["rank"]),
                score=float(row["score"]),
                lex_score=_num(row.get("lex_score"), float),
                lex_rank=_num(row.get("lex_rank"), int),
                sem_score=_num(row.get("sem_score"), float),
                sem_rank=_num(row.get("sem_rank"), int),
                verse=verses[vid],
                label_en=labels[vid][0],
                label_he=labels[vid][1],
            )
        )
    return {
        "query": q,
        "normalized": normalized,
        "tokens": tokens,
        "mode": mode,
        "k": k,
        "hits": hits,
    }


@router.get("/meta", response_model=Meta)
def meta(state: State) -> dict[str, Any]:
    ready = getattr(state.encoder, "ready", True)
    return {"build": state.meta, "runtime": {**state.runtime, "encoder_ready": ready}}
