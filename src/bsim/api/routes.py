"""`/api` endpoints (DESIGN.md §10). Bad parameters -> 422, unknown ids -> 404."""

from __future__ import annotations

import json
import math
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Iterator
from typing import Annotated, Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from bsim.analysis import diffs as df_
from bsim.analysis import structure as st
from bsim.api import queries
from bsim.api.app import ServeState
from bsim.api.models import (
    AffinityCell,
    AffinityPair,
    AffinityResponse,
    Book,
    BookCount,
    BookStyle,
    ChangeExample,
    ChangeGroup,
    ChangesResponse,
    CompareResponse,
    ConcordanceHit,
    ConcordanceResponse,
    DiscoveriesResponse,
    Discovery,
    Echo,
    ExplainResponse,
    GoldLink,
    Hit,
    LadderRow,
    Leitwort,
    LemmaForm,
    LemmaStat,
    MapCluster,
    MapPoint,
    MapResponse,
    Meta,
    Mode,
    Pair,
    ParallelBook,
    ParallelismResponse,
    ParallelUnit,
    PhraseInfo,
    PhrasePair,
    PhrasesResponse,
    ResolveResponse,
    SearchHit,
    SearchMode,
    SearchResponse,
    SequenceDetail,
    SequencesResponse,
    SequenceSummary,
    SharedLemma,
    SimilarResponse,
    StructureBasis,
    StructureRank,
    StructureRankingResponse,
    StructureResponse,
    StructureScore,
    StyloAxis,
    StyloDelta,
    StyloFeature,
    StylometryResponse,
    StyloPoint,
    UnitDetail,
    UnitParallelism,
    UnitSummary,
    VerseDiff,
    VerseHalves,
    WordDetail,
    WordplayPair,
    WordplayResponse,
    WordRef,
)
from bsim.api.resolve import resolve as resolve_ref
from bsim.api.search import EncoderUnavailable
from bsim.api.search import search as run_search
from bsim.store.db import similar as db_similar
from bsim.text.morph import decode as decode_morph
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


def _page(state: ServeState, limit: int, offset: int) -> None:
    max_page = state.cfg["serve"]["max_page"]
    if not 1 <= limit <= max_page:
        raise _unprocessable(f"limit must be between 1 and {max_page}")
    if offset < 0:
        raise _unprocessable("offset must not be negative")


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
    exclude: Annotated[
        str, Query(description="comma-separated: neighbors, chapter, book, known")
    ] = "",
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
                link=_gold_link(r["link_level"], r["link_type"]),
                phrase=None
                if r["phrase_score"] is None
                else PhraseInfo(score=r["phrase_score"], n_tokens=r["phrase_tokens"]),
            )
        )
    return {"unit": u, "mode": mode, "k": k, "exclude": filters, "hits": hits}


def _gold_link(level: str | None, types: str | None) -> GoldLink | None:
    if level is None:
        return None
    return GoldLink(level=level, types=[t for t in (types or "").split(",") if t])


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
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    types = state.cfg["units"]["types"]
    if unit_type not in types:
        raise _unprocessable(f"unknown unit type {unit_type!r}; choose from {types}")
    _page(state, limit, offset)
    total, rows = queries.discoveries(conn, unit_type, mode, book, cross_book, limit, offset)
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
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
    }


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
    cap = state.cfg["serve"]["max_compare_verses"]
    if max(ua["n_verses"], ub["n_verses"]) > cap:
        raise _unprocessable(f"units longer than serve.max_compare_verses = {cap} verses")
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
    q: str, state: State, conn: Conn, mode: SearchMode = "fused", k: int | None = None
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
    _verse_or_404(state, verse_id)
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
    _page(state, limit, offset)
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


def _phrase_pairs(
    conn: sqlite3.Connection, rows: list[dict[str, Any]], first: int | None = None
) -> list[PhrasePair]:
    """Phrase rows -> response items; `first` puts that verse on the `a` side."""
    flipped = [
        r
        if first is None or r["a"] == first
        else {**r, "a": r["b"], "b": r["a"], "a_words": r["b_words"], "b_words": r["a_words"]}
        for r in rows
    ]
    vids = [v for r in flipped for v in (r["a"], r["b"])]
    verses = queries.verses_by_id(conn, vids)
    units_ = queries.units_by_id(conn, [f"v:{v}" for v in vids])
    display: dict[tuple[int, int], int] = {
        (w["verse_id"], w["idx"]): w["display_idx"]
        for w in queries.words(conn, vids)
        if w["display_idx"] is not None
    }
    links = queries.verse_links(conn, [(r["a"], r["b"]) for r in flipped])

    def shown(vid: int, idxs: str) -> list[int]:
        return sorted({display[(vid, i)] for i in json.loads(idxs) if (vid, i) in display})

    return [
        PhrasePair(
            score=r["score"],
            n_tokens=r["n_tokens"],
            spread=r["spread"],
            a=UnitSummary(**units_[f"v:{r['a']}"]),
            b=UnitSummary(**units_[f"v:{r['b']}"]),
            a_verse=verses[r["a"]],
            b_verse=verses[r["b"]],
            a_display=shown(r["a"], r["a_words"]),
            b_display=shown(r["b"], r["b_words"]),
            link=_gold_link(*links[(r["a"], r["b"])]) if (r["a"], r["b"]) in links else None,
        )
        for r in flipped
    ]


@router.get("/phrases/{verse_id}", response_model=list[PhrasePair])
def phrases_of(verse_id: int, state: State, conn: Conn) -> list[PhrasePair]:
    """Every verse sharing an aligned phrase with this one (this verse on the `a` side)."""
    _verse_or_404(state, verse_id)
    return _phrase_pairs(conn, queries.phrases_of(conn, verse_id), first=verse_id)


@router.get("/phrases", response_model=PhrasesResponse)
def phrases(
    state: State,
    conn: Conn,
    book: int | None = None,
    cross_book: bool = False,
    min_tokens: int = 3,
    max_spread: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """The strongest shared phrases in the corpus (`max_spread`: hide recurring idioms)."""
    _page(state, limit, offset)
    total, rows = queries.phrases_page(
        conn, book, cross_book, min_tokens, max_spread, limit, offset
    )
    return {
        "book": book,
        "cross_book": cross_book,
        "min_tokens": min_tokens,
        "max_spread": max_spread,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": _phrase_pairs(conn, rows),
    }


# when several OSHB words share one display token, the more telling change is shown
_OP_RANK = {
    op: i for i, op in enumerate(("substitution", "added", "omitted", "moved", "form", "spelling"))
}


def _verse_diff(
    state: ServeState, conn: sqlite3.Connection, a: int, b: int
) -> tuple[dict[int, str], dict[int, str], Counter, float]:
    """(A display marks, B display marks, op counts, shared ratio) of the word alignment of
    verses a -> b; no marks below `diffs.min_shared`."""
    rows = queries.words(conn, [a, b], detail=True)
    seq = {v: [w for w in rows if w["verse_id"] == v] for v in (a, b)}
    words = {
        v: [df_.make_word(w["idx"], w["content_lemmas"], w["lemma"], w["surface"]) for w in ws]
        for v, ws in seq.items()
    }
    d = state.cfg["diffs"]
    ops = df_.align_words(words[a], words[b], d["match"], d["mismatch"], d["gap"])
    marks: dict[int, dict[int, str]] = {a: {}, b: {}}
    counts = Counter(o.op for o in ops)
    shared = df_.shared_ratio(ops, len(words[a]), len(words[b]))
    if a == b or shared < d["min_shared"]:
        return {}, {}, counts, shared

    def mark(v: int, pos: int | None, op: str) -> None:
        if pos is None or op == "same":
            return
        di = seq[v][pos]["display_idx"]
        if di is not None and (di not in marks[v] or _OP_RANK[op] < _OP_RANK[marks[v][di]]):
            marks[v][di] = op

    for o in ops:
        mark(a, o.a, o.op)
        mark(b, o.b, o.op)
    return marks[a], marks[b], counts, shared


def _key_he(key: str | None, gloss: dict[str, str]) -> str | None:
    if key is None:
        return None
    letters = df_.key_letters(key)
    return letters if letters is not None else " ".join(gloss.get(k, k) for k in key.split("+"))


@router.get("/diff", response_model=VerseDiff)
def verse_diff(a: int, b: int, state: State, conn: Conn) -> dict[str, Any]:
    """Word-level changes from verse a to verse b (any two verses; DESIGN.md §16.8)."""
    _verse_or_404(state, a)
    _verse_or_404(state, b)
    am, bm, counts, shared = _verse_diff(state, conn, a, b)
    return {
        "a": a,
        "b": b,
        "a_marks": am,
        "b_marks": bm,
        "counts": dict(counts),
        "shared": round(shared, 4),
        "loose": shared < state.cfg["diffs"]["min_shared"],
    }


@router.get("/changes", response_model=ChangesResponse)
def changes(
    state: State,
    conn: Conn,
    op: str = "substitution",
    a_book: int | None = None,
    b_book: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """How parallel passages differ across the corpus: changes grouped by word, most frequent
    first, with up to 3 example verse pairs (A = earlier passage in canon order)."""
    if op not in df_.OPS or op == "same":
        raise _unprocessable(f"op must be one of {[o for o in df_.OPS if o != 'same']}")
    _page(state, limit, offset)
    total, groups = queries.change_groups(conn, op, a_book, b_book, limit, offset)
    keys = {k for g in groups for k in (g["a_key"], g["b_key"]) if k and not k.startswith("~")}
    gloss = queries.gloss(conn, (p for k in keys for p in k.split("+")))
    by_form = op in queries.FORM_OPS

    def group(g: dict[str, Any]) -> tuple[str | None, str | None]:
        return (g["a_form"], g["b_form"]) if by_form else (g["a_key"], g["b_key"])

    ex = {group(g): queries.change_examples(conn, op, a_book, b_book, *group(g), 3) for g in groups}
    labels = queries.verse_labels(
        conn, (v for es in ex.values() for e in es for v in (e["a"], e["b"]))
    )
    return {
        "op": op,
        "a_book": a_book,
        "b_book": b_book,
        "totals": queries.change_totals(conn, a_book, b_book),
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            ChangeGroup(
                **g,
                a_he=g["a_form"] if by_form else _key_he(g["a_key"], gloss),
                b_he=g["b_form"] if by_form else _key_he(g["b_key"], gloss),
                examples=[
                    ChangeExample(**e, a_label=labels[e["a"]][0], b_label=labels[e["b"]][0])
                    for e in ex[group(g)]
                ],
            )
            for g in groups
        ],
    }


def _poetic_book_ids(state: ServeState) -> list[int]:
    from bsim.data.canon import BY_OSIS

    return [BY_OSIS[o].book_id for o in state.cfg["parallelism"]["train_positive"]]


@router.get("/parallelism/{unit_id}", response_model=UnitParallelism)
def unit_parallelism(unit_id: str, state: State, conn: Conn) -> dict[str, Any]:
    """The cola of a unit's verses and how parallel each verse's halves are (DESIGN.md §16.9)."""
    u = _unit_or_404(conn, unit_id)
    rows = queries.parallelism_verses(conn, u["start_verse_id"], u["end_verse_id"])
    at = state.cfg["parallelism"]["parallel_at"]
    probs = [r["prob"] for r in rows if r["prob"] is not None]
    return {
        "unit": u,
        "parallel_at": at,
        "mean_prob": float(np.mean(probs)) if probs else None,
        "share_parallel": float(np.mean([p >= at for p in probs])) if probs else None,
        "n_scored": len(probs),
        "verses": [
            VerseHalves(**{**r, "cola": json.loads(r["cola"]), "pauses": json.loads(r["pauses"])})
            for r in rows
        ],
    }


@router.get("/parallelism", response_model=ParallelismResponse)
def parallelism_ranking(
    state: State,
    conn: Conn,
    unit_type: str = "chapter",
    book: int | None = None,
    exclude_poetic: bool = False,
    min_verses: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Units ranked by how parallel their verse halves are, plus per-book means;
    `exclude_poetic` hides Psalms / Proverbs / Job (poetry hidden in prose and prophecy)."""
    types = [t for t in state.cfg["units"]["types"] if t != "verse"]
    if unit_type not in types:
        raise _unprocessable(f"unknown unit type {unit_type!r}; choose from {types}")
    _page(state, limit, offset)
    pc = state.cfg["parallelism"]
    poetic = _poetic_book_ids(state)
    total, rows = queries.parallelism_units(
        conn,
        unit_type,
        book,
        poetic if exclude_poetic else [],
        pc["parallel_at"],
        pc["min_chapter_verses"] if min_verses is None else min_verses,
        limit,
        offset,
    )
    units_ = queries.units_by_id(conn, [r["unit_id"] for r in rows])
    meta = state.meta.get("parallelism", {})
    return {
        "unit_type": unit_type,
        "book": book,
        "exclude_poetic": exclude_poetic,
        "parallel_at": pc["parallel_at"],
        "coefficients": meta.get("coefficients", {}),
        "held_out_auc": meta.get("held_out_auc", {}),
        "books": [
            ParallelBook(**b, poetic_accents=b["book_id"] in poetic)
            for b in queries.parallelism_books(conn, pc["parallel_at"])
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            ParallelUnit(
                unit=UnitSummary(**units_[r["unit_id"]]),
                mean_prob=r["mean_prob"],
                share_parallel=r["share_parallel"],
                n_scored=r["n_scored"],
            )
            for r in rows
        ],
    }


WORDPLAY_KINDS = ("substitution", "metathesis", "extension")


@router.get("/wordplay", response_model=WordplayResponse)
def wordplay(
    state: State,
    conn: Conn,
    book: int | None = None,
    kind: str | None = None,
    unit: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Sound-alike words close together, strongest first (DESIGN.md §16.10); `unit`: pairs
    touching that unit's verses."""
    _page(state, limit, offset)
    if kind is not None and kind not in WORDPLAY_KINDS:
        raise _unprocessable(f"kind must be one of {list(WORDPLAY_KINDS)}")
    span = None
    if unit is not None:
        u = _unit_or_404(conn, unit)
        span = (u["start_verse_id"], u["end_verse_id"])
    total, rows = queries.wordplay_page(conn, book, kind, span, limit, offset)
    vids = [v for r in rows for v in (r["a_vid"], r["b_vid"])]
    verses = queries.verses_by_id(conn, vids)
    labels = queries.verse_labels(conn, vids)
    gloss = queries.gloss(conn, (lem for r in rows for lem in (r["a_lemma"], r["b_lemma"])))
    return {
        "book": book,
        "kind": kind,
        "unit": unit,
        "total": total,
        "expected_by_chance": state.meta.get("wordplay", {}).get("null_pairs_per_rep"),
        "offset": offset,
        "limit": limit,
        "items": [
            WordplayPair(
                **{k: r[k] for k in ("a_vid", "b_vid", "a_display", "b_display", "a_form")},
                **{k: r[k] for k in ("b_form", "kind", "gap", "score", "q")},
                a_he=gloss.get(r["a_lemma"], r["a_form"]),
                b_he=gloss.get(r["b_lemma"], r["b_form"]),
                a_label=labels[r["a_vid"]][0],
                b_label=labels[r["b_vid"]][0],
                verses=[verses[v] for v in dict.fromkeys((r["a_vid"], r["b_vid"]))],
            )
            for r in rows
        ],
    }


def _sequence_summaries(
    conn: sqlite3.Connection, rows: list[dict[str, Any]]
) -> list[SequenceSummary]:
    ends = [v for r in rows for v in (r["a_start"], r["a_end"], r["b_start"], r["b_end"])]
    labels = queries.verse_labels(conn, ends)

    def span(first: int, last: int, lang: int) -> str:
        a, b = labels[first][lang], labels[last][lang]
        if first == last:
            return a
        # "Genesis 24:2" + "Genesis 24:16" -> "Genesis 24:2–16"
        common = 0
        while common < min(len(a), len(b)) and a[common] == b[common]:
            common += 1
        cut = max(a.rfind(" ", 0, common), a.rfind(":", 0, common)) + 1
        return f"{a}–{b[cut:]}" if cut > 0 else f"{a} – {b}"

    return [
        SequenceSummary(
            **{k: r[k] for k in r if k != "pairs"},
            a_label=span(r["a_start"], r["a_end"], 0),
            b_label=span(r["b_start"], r["b_end"], 0),
            a_label_he=span(r["a_start"], r["a_end"], 1),
            b_label_he=span(r["b_start"], r["b_end"], 1),
        )
        for r in rows
    ]


@router.get("/sequences", response_model=SequencesResponse)
def sequences(
    state: State,
    conn: Conn,
    book: int | None = None,
    cross_book: bool = False,
    hide_same_chapter: bool = False,
    max_q: float | None = None,
    min_pairs: int = 1,  # stored chains already have `sequences.min_pairs`
    unit: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Passages that run parallel in the same verse order, strongest first (DESIGN.md §16.7);
    `unit`: only chains touching that unit's verses."""
    _page(state, limit, offset)
    if max_q is not None and not 0 <= max_q <= 1:
        raise _unprocessable("max_q must be between 0 and 1")
    span = None
    if unit is not None:
        u = _unit_or_404(conn, unit)
        span = (u["start_verse_id"], u["end_verse_id"])
    total, rows = queries.sequences_page(
        conn, book, cross_book, hide_same_chapter, max_q, min_pairs, span, limit, offset
    )
    return {
        "book": book,
        "cross_book": cross_book,
        "hide_same_chapter": hide_same_chapter,
        "max_q": max_q,
        "min_pairs": min_pairs,
        "unit": unit,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": _sequence_summaries(conn, rows),
    }


@router.get("/sequences/{seq_id}", response_model=SequenceDetail)
def sequence_detail(seq_id: int, state: State, conn: Conn) -> dict[str, Any]:
    """One chain side by side: aligned pairs, plus the verses skipped on either side."""
    r = queries.sequence(conn, seq_id)
    if r is None:
        raise HTTPException(status_code=404, detail=f"unknown sequence {seq_id}")
    pairs = [(int(a), int(b), float(w), bool(g)) for a, b, w, g in json.loads(r["pairs"])]
    rows: list[LadderRow] = []
    for k, (a, b, w, gold) in enumerate(pairs):
        if k:
            pa, pb = pairs[k - 1][:2]
            rows += [LadderRow(a=x, b=None) for x in range(pa + 1, a)]
            rows += [LadderRow(a=None, b=y) for y in range(pb + 1, b)]
        cos = float(np.dot(state.emb[a], state.emb[b]))
        am, bm, _, shared = _verse_diff(state, conn, a, b)
        rows.append(
            LadderRow(
                a=a,
                b=b,
                weight=w,
                cosine=round(cos, 4),
                gold=gold,
                a_marks=am,
                b_marks=bm,
                loose=shared < state.cfg["diffs"]["min_shared"],
            )
        )
    vids = list(range(r["a_start"], r["a_end"] + 1)) + list(range(r["b_start"], r["b_end"] + 1))
    return {
        "sequence": _sequence_summaries(conn, [r])[0],
        "rows": rows,
        "verses": queries.verses_by_id(conn, vids),
    }


def _score(s: st.Score | None, verse_ids: list[int]) -> StructureScore | None:
    if s is None:
        return None
    pair = (verse_ids[s.pair[0]], verse_ids[s.pair[1]]) if s.pair else None
    return StructureScore(value=s.value, pct=s.pct, z=s.z, pair=pair)


@router.get("/structure/{unit_id}", response_model=StructureResponse)
def structure(unit_id: str, state: State, conn: Conn) -> dict[str, Any]:
    """Verse-by-verse similarity, inclusio, chiasm and Leitworte of a chapter / pericope /
    parasha (DESIGN.md §16.2)."""
    u = _unit_or_404(conn, unit_id)
    c = state.cfg["structure"]
    if u["unit_type"] == "verse":
        raise _unprocessable("structure applies to chapters, pericopes and parashot")
    if u["n_verses"] > c["max_verses"]:
        raise _unprocessable(f"unit has more than structure.max_verses = {c['max_verses']} verses")
    cached = state.structure_cache.get(unit_id)
    if cached is None:
        cached = _structure(u, state, conn)
        state.structure_cache.put(unit_id, cached)
    return cached


def _structure(u: dict[str, Any], state: ServeState, conn: sqlite3.Connection) -> dict[str, Any]:
    c = state.cfg["structure"]
    vids = list(range(u["start_verse_id"], u["end_verse_id"] + 1))
    rows = queries.words(conn, vids)
    bags: dict[int, list[str]] = defaultdict(list)
    for w in rows:
        bags[w["verse_id"]].extend(w["content_lemmas"].split())
    stats = queries.lemma_stats(conn, (t for b in bags.values() for t in b))
    idf = {t: math.log(state.n_verses / s["n_verses"]) for t, s in stats.items()}
    mats = {
        "semantic": st.semantic_matrix(np.asarray(state.emb[vids[0] : vids[-1] + 1])),
        "lexical": st.lexical_matrix([bags[v] for v in vids], idf),
    }
    bases = {}
    for basis, s in mats.items():
        inc = st.inclusio(s, c["min_verses_inclusio"], c["samples"], c["seed"])
        chi = st.chiasm(s, c["min_verses_chiasm"], c["samples"], c["seed"])
        bases[basis] = StructureBasis(
            matrix=np.round(s, 3).tolist(),
            inclusio=_score(inc, vids),
            chiasm=_score(chi, vids),
            echoes=[Echo(a=vids[i], b=vids[j], sim=v) for i, j, v in st.echoes(s, c["echoes"])],
        )
    skip = set(c["leitwort_skip_pos"])
    counts = Counter(t for b in bags.values() for t in b if stats.get(t, {}).get("pos") not in skip)
    keys = st.leitworte(
        counts,
        {t: s["n_words"] for t, s in stats.items()},
        state.lemma_total(conn),
        c["leitwort_min_count"],
        c["leitwort_top"],
    )
    occ: dict[str, dict[int, set[int]]] = defaultdict(lambda: defaultdict(set))
    wanted = {k.lemma for k in keys}
    for w in rows:
        if w["display_idx"] is not None:
            for t in set(w["content_lemmas"].split()) & wanted:
                occ[t][w["verse_id"]].add(w["display_idx"])
    return {
        "unit": u,
        "verse_ids": vids,
        **bases,
        "leitworte": [
            Leitwort(
                lemma=k.lemma,
                he_lemma=stats[k.lemma]["he_lemma"],
                count=k.count,
                expected=k.expected,
                g2=k.g2,
                multiple_of=[m for m in (7, 10) if k.count % m == 0],
                occurrences={v: sorted(ix) for v, ix in occ[k.lemma].items()},
            )
            for k in keys
        ],
    }


@router.get("/structure", response_model=StructureRankingResponse)
def structure_ranking(
    state: State,
    conn: Conn,
    unit_type: str = "chapter",
    by: str = "semantic_chiasm",
    min_verses: int = 5,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Units ranked by an inclusio / chiasm percentile."""
    types = state.cfg["structure"]["unit_types"]
    if unit_type not in types:
        raise _unprocessable(f"unknown unit type {unit_type!r}; choose from {types}")
    if by not in queries.STRUCTURE_SORT:
        raise _unprocessable(f"by must be one of {sorted(queries.STRUCTURE_SORT)}")
    _page(state, limit, offset)
    total, rows = queries.structure_page(conn, unit_type, by, min_verses, limit, offset)
    units_ = queries.units_by_id(conn, [r["unit_id"] for r in rows])
    items = [
        StructureRank(unit=UnitSummary(**units_[r["unit_id"]]), **{k: r[k] for k in st.SCORE_COLS})
        for r in rows
    ]
    return {
        "unit_type": unit_type,
        "by": by,
        "min_verses": min_verses,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
    }


@router.get("/map/{unit_type}", response_model=MapResponse)
def corpus_map(unit_type: str, state: State, conn: Conn) -> dict[str, Any]:
    """2-D layout and thematic clusters of one unit type (DESIGN.md §16.4)."""
    types = list(state.cfg["map"]["clusters"])
    if unit_type not in types:
        raise _unprocessable(f"unknown unit type {unit_type!r}; choose from {types}")
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
            link=_gold_link(*links[(r["a_vid"], r["b_vid"])])
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


@router.get("/meta", response_model=Meta)
def meta(state: State, response: Response) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"  # encoder_ready changes after startup
    ready = getattr(state.encoder, "ready", True)
    return {"build": state.meta, "runtime": {**state.runtime, "encoder_ready": ready}}
