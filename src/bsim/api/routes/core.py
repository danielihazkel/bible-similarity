"""Books, units, similar, discoveries, explain, compare, search, resolve, words, lemma, meta."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from typing import Annotated, Any

import numpy as np
from fastapi import APIRouter, HTTPException, Query, Response

from bsim.api import queries
from bsim.api.app import ServeState
from bsim.api.models import (
    Book,
    BookCount,
    CompareResponse,
    ConcordanceHit,
    ConcordanceResponse,
    DiscoveriesResponse,
    Discovery,
    EvalResponse,
    ExplainResponse,
    Hit,
    LemmaForm,
    LemmaStat,
    Meta,
    Mode,
    Pair,
    PhraseInfo,
    ResolveResponse,
    SearchHit,
    SearchMode,
    SearchResponse,
    SharedLemma,
    SimilarResponse,
    UnitDetail,
    UnitSummary,
    WordDetail,
    WordRef,
)
from bsim.api.resolve import resolve as resolve_ref
from bsim.api.routes._common import (
    Conn,
    State,
    check_k,
    check_page,
    check_unit_type,
    gold_link,
    num,
    unit_or_404,
    unprocessable,
    verse_or_404,
)
from bsim.api.search import EncoderLoading, EncoderUnavailable
from bsim.api.search import search as run_search
from bsim.config import resolve_path
from bsim.retrieve.fusion import final_systems
from bsim.store.db import similar as db_similar
from bsim.text.morph import decode as decode_morph
from bsim.text.normalize import consonantal

router = APIRouter()


@router.get("/books", response_model=list[Book])
def books(conn: Conn) -> list[dict[str, Any]]:
    return queries.books(conn)


@router.get("/units/{unit_type}", response_model=list[UnitSummary])
def units(
    unit_type: str, state: State, conn: Conn, book: int | None = None, chapter: int | None = None
) -> list[dict[str, Any]]:
    """Units of a type per book (verses: per book, or per chapter with `chapter`)."""
    check_unit_type(unit_type, state.cfg["units"]["types"])
    if unit_type == "verse" and book is None:
        raise unprocessable("verse units are listed per book: pass `book`")
    if chapter is not None and book is None:
        raise unprocessable("`chapter` needs `book`")
    return queries.units_of_type(conn, unit_type, book, chapter)


@router.get("/unit/{unit_id}", response_model=UnitDetail)
def unit(unit_id: str, conn: Conn) -> dict[str, Any]:
    u = unit_or_404(conn, unit_id)
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
    exclude: Annotated[
        str, Query(description="comma-separated: neighbors, chapter, book, known")
    ] = "",
) -> dict[str, Any]:
    u = unit_or_404(conn, unit_id)
    k = check_k(state, k)
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
        raise unprocessable(str(e)) from e
    targets = queries.units_by_id(conn, [r["tgt_id"] for r in rows])
    starts = [t["start_verse_id"] for t in targets.values()]
    verses, previews = _texts(state, conn, u["unit_type"], starts)
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
                link=gold_link(r["link_level"], r["link_type"]),
                phrase=None
                if r["phrase_score"] is None
                else PhraseInfo(score=r["phrase_score"], n_tokens=r["phrase_tokens"]),
            )
        )
    return {"unit": u, "mode": mode, "k": k, "exclude": filters, "hits": hits}


def _texts(
    state: ServeState, conn: sqlite3.Connection, unit_type: str, starts: list[int]
) -> tuple[dict[int, Any], dict[int, str]]:
    """(verses, previews) by start verse_id: full verses for verse units, else previews."""
    if unit_type == "verse":
        return queries.verses_by_id(conn, starts), {}
    return {}, queries.previews(conn, starts, state.cfg["serve"]["preview_chars"])


@router.get("/discoveries", response_model=DiscoveriesResponse)
def discoveries(
    state: State,
    conn: Conn,
    unit_type: str = "verse",
    mode: Mode = "semantic",
    book: int | None = None,
    cross_book: bool = False,
    unit: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Strong pairs without a Sefaria link; `unit`: the pairs that unit is in (its type)."""
    check_unit_type(unit_type, state.cfg["units"]["types"])
    check_page(state, limit, offset)
    if unit is not None:
        unit_type = unit_or_404(conn, unit)["unit_type"]
    total, rows = queries.discoveries(conn, unit_type, mode, book, cross_book, limit, offset, unit)
    units_ = queries.units_by_id(conn, [i for r in rows for i in (r["a_id"], r["b_id"])])
    verses, previews = _texts(
        state, conn, unit_type, [u["start_verse_id"] for u in units_.values()]
    )
    items = []
    for r in rows:
        a, b = units_[r["a_id"]], units_[r["b_id"]]
        sa, sb = a["start_verse_id"], b["start_verse_id"]
        items.append(
            Discovery(
                score=r["score"],
                tie=r["tie"],
                rank_ab=r["rank_ab"],
                rank_ba=r["rank_ba"],
                a=UnitSummary(**a),
                b=UnitSummary(**b),
                a_verse=verses.get(sa),
                b_verse=verses.get(sb),
                a_preview=previews.get(sa),
                b_preview=previews.get(sb),
            )
        )
    return {
        "unit_type": unit_type,
        "mode": mode,
        "book": book,
        "cross_book": cross_book,
        "unit": unit,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
    }


@router.get("/explain", response_model=ExplainResponse)
def explain(a: int, b: int, state: State, conn: Conn) -> dict[str, Any]:
    verse_or_404(state, a)
    verse_or_404(state, b)
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
    ua, ub = unit_or_404(conn, a), unit_or_404(conn, b)
    cap = state.cfg["serve"]["max_compare_verses"]
    if max(ua["n_verses"], ub["n_verses"]) > cap:
        raise unprocessable(f"only units of at most {cap} verses can be compared")
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
    q: str,
    state: State,
    conn: Conn,
    mode: SearchMode = "fused",
    k: int | None = None,
    book: int | None = None,
) -> dict[str, Any]:
    """Free-text Hebrew search; `k` up to `serve.search.max_k`; `book`: only its verses."""
    k = state.cfg["serve"]["default_k"] if k is None else k
    max_k = state.cfg["serve"]["search"]["max_k"]
    if not 1 <= k <= max_k:
        raise unprocessable(f"k must be between 1 and {max_k}")
    mask = None
    if book is not None:
        mask = state.verse_books == book
        if not mask.any():
            raise HTTPException(status_code=404, detail=f"unknown book {book}")
    max_chars = state.cfg["serve"]["search"]["max_query_chars"]
    if len(q) > max_chars:
        raise unprocessable(f"query longer than {max_chars} characters")
    if not consonantal(q):
        raise unprocessable("the query has no Hebrew letters")
    try:
        normalized, tokens, df = run_search(state, q, mode, k, mask)
    except EncoderLoading as e:
        retry = str(state.cfg["serve"]["encoder_retry_s"])
        raise HTTPException(status_code=503, detail=str(e), headers={"Retry-After": retry}) from e
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
                lex_score=num(row.get("lex_score"), float),
                lex_rank=num(row.get("lex_rank"), int),
                sem_score=num(row.get("sem_score"), float),
                sem_rank=num(row.get("sem_rank"), int),
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
        "book": book,
        "hits": hits,
    }


@router.get("/resolve", response_model=ResolveResponse)
def resolve(q: str, conn: Conn) -> dict[str, Any]:
    """The verse or chapter a reference names (`Gen 1:1`, `בראשית א א`), or `unit: null`."""
    r = resolve_ref(q)
    unit_id = None
    if r is not None and r.verse is None:
        unit_id = f"c:{r.book.book_id}:{r.chapter}"
    elif r is not None:
        vid = queries.verse_at(conn, r.book.book_id, r.chapter, r.verse)
        unit_id = None if vid is None else f"v:{vid}"
    return {"query": q, "unit": queries.unit(conn, unit_id) if unit_id else None}


def _lemma_stat(stats: dict[str, dict[str, Any]], lemma: str) -> LemmaStat:
    s = stats.get(lemma, {})
    return LemmaStat(lemma=lemma, he_lemma=s.get("he_lemma", lemma), n_verses=s.get("n_verses", 0))


@router.get("/words/{verse_id}", response_model=list[WordDetail])
def words(verse_id: int, state: State, conn: Conn) -> list[WordDetail]:
    """Every OSHB word of a verse with its morphology and content lemmas."""
    verse_or_404(state, verse_id)
    rows = queries.words(conn, [verse_id], detail=True)
    stats = queries.lemma_stats(conn, (lem for w in rows for lem in w["content_lemmas"].split()))
    return [
        WordDetail(
            idx=w["idx"],
            display_idx=w["display_idx"],
            surface=w["surface"],
            lemma=w["lemma"],
            morph=w["morph"],
            morph_he=decode_morph(w["morph"]),
            in_formula=bool(w["in_formula"]),
            lemmas=[_lemma_stat(stats, lem) for lem in dict.fromkeys(w["content_lemmas"].split())],
            domains=(w["domains"] or "").split(),
        )
        for w in rows
    ]


@router.get("/lemma/{lemma}", response_model=ConcordanceResponse)
def lemma(
    lemma: str,
    state: State,
    conn: Conn,
    book: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Concordance: the verses containing a content lemma, with per-book counts."""
    stats = queries.lemma_stats(conn, [lemma]).get(lemma)
    if stats is None:
        raise HTTPException(status_code=404, detail=f"unknown lemma {lemma!r}")
    check_page(state, limit, offset)
    by_book = queries.lemma_books(conn, lemma)
    total = sum(b["n_verses"] for b in by_book if book is None or b["book_id"] == book)
    vids = queries.lemma_page(conn, lemma, book, limit, offset)
    verses = queries.verses_by_id(conn, vids)
    labels = queries.verse_labels(conn, vids)
    marks: dict[int, set[int]] = defaultdict(set)
    for w in queries.words(conn, vids):
        if w["display_idx"] is not None and lemma in w["content_lemmas"].split():
            marks[w["verse_id"]].add(w["display_idx"])
    return {
        "lemma": lemma,
        "he_lemma": stats["he_lemma"],
        "n_words": stats["n_words"],
        "n_verses": stats["n_verses"],
        "by_book": [BookCount(**b) for b in by_book],
        "book": book,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            ConcordanceHit(
                verse=verses[v],
                label_en=labels[v][0],
                label_he=labels[v][1],
                display_idxs=sorted(marks[v]),
            )
            for v in vids
        ],
    }


@router.get("/meta", response_model=Meta)
def meta(state: State, response: Response) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"  # encoder_ready changes after startup
    ready = getattr(state.encoder, "ready", True)
    error = getattr(state.encoder, "error", None)
    return {
        "build": state.meta,
        "runtime": {**state.runtime, "encoder_ready": ready, "encoder_error": error},
    }


@router.get("/eval", response_model=EvalResponse)
def evaluation(state: State) -> dict[str, Any]:
    """Retrieval metrics against the Sefaria gold (dev, and the one test run) and OpenBible."""
    folder = resolve_path(state.cfg, "artifacts") / "eval"

    def read(name: str) -> dict[str, Any] | None:
        path = folder / name
        return json.loads(path.read_text("utf-8")) if path.exists() else None

    metrics = read("metrics.json") or {}
    types = [t for t in state.cfg["units"]["types"] if t != "parasha"]  # no parasha gold
    return {
        "splits": metrics.get("splits", {}),
        "openbible": read("openbible.json"),
        "final": {t: final_systems(state.cfg, t) for t in types},
    }
