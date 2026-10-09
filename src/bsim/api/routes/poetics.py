"""Inner-unit structure, verse halves and wordplay (DESIGN.md §16.2, §16.9, §16.10)."""

from __future__ import annotations

import json
import math
import sqlite3
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from fastapi import APIRouter

from bsim.analysis import structure as st
from bsim.api import queries
from bsim.api.app import ServeState
from bsim.api.models import (
    Acrostic,
    AcrosticLine,
    AcrosticsResponse,
    Alliteration,
    AlliterationResponse,
    Echo,
    Leitwort,
    LemmaForm,
    ParallelBook,
    ParallelismResponse,
    ParallelUnit,
    RelationPair,
    Rhyme,
    RhymesResponse,
    StructureBasis,
    StructureRank,
    StructureRankingResponse,
    StructureResponse,
    StructureScore,
    UnitParallelism,
    UnitSummary,
    VerseHalves,
    VerseLabel,
    WordPair,
    WordPairsResponse,
    WordplayPair,
    WordplayResponse,
)
from bsim.api.routes._common import (
    Conn,
    State,
    check_min,
    check_page,
    check_unit_type,
    unit_or_404,
    unit_span,
    unprocessable,
)

router = APIRouter()


def _poetic_book_ids(state: ServeState) -> list[int]:
    from bsim.data.canon import BY_OSIS

    return [BY_OSIS[o].book_id for o in state.cfg["parallelism"]["train_positive"]]


@router.get("/parallelism/{unit_id}", response_model=UnitParallelism)
def unit_parallelism(unit_id: str, state: State, conn: Conn) -> dict[str, Any]:
    """The cola of a unit's verses and how parallel each verse's halves are (DESIGN.md §16.9)."""
    u = unit_or_404(conn, unit_id)
    rows = queries.parallelism_verses(conn, u["start_verse_id"], u["end_verse_id"])
    at = state.cfg["parallelism"]["parallel_at"]
    probs = [r["prob"] for r in rows if r["prob"] is not None]
    pairs = {r["verse_id"]: json.loads(r["relation_pairs"] or "[]") for r in rows}
    he = queries.gloss(conn, (x for ps in pairs.values() for a, b, _ in ps for x in (a, b)))
    return {
        "unit": u,
        "parallel_at": at,
        "mean_prob": float(np.mean(probs)) if probs else None,
        "share_parallel": float(np.mean([p >= at for p in probs])) if probs else None,
        "n_scored": len(probs),
        "verses": [
            VerseHalves(
                **{
                    **r,
                    "cola": json.loads(r["cola"]),
                    "pauses": json.loads(r["pauses"]),
                    "clauses": json.loads(r["clauses"]),
                    "relation_pairs": [
                        RelationPair(a=a, b=b, kind=k, a_he=he.get(a, a), b_he=he.get(b, b))
                        for a, b, k in pairs[r["verse_id"]]
                    ],
                }
            )
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
    sort: str = "prob",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Units ranked by how parallel their verse halves are (`sort=antithetic`: by the share of
    their parallel verses typed antithetic, among units with `typing_min_parallel` of them),
    plus per-book means; `exclude_poetic` hides Psalms / Proverbs / Job (poetry hidden in prose
    and prophecy)."""
    if sort not in ("prob", "antithetic"):
        raise unprocessable(f"sort must be prob or antithetic, not {sort!r}")
    check_unit_type(unit_type, [t for t in state.cfg["units"]["types"] if t != "verse"])
    check_page(state, limit, offset)
    check_min(min_verses, "min_verses")
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
        sort,
        pc["typing_min_parallel"] if sort == "antithetic" else 0,
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
        "sort": sort,
        "min_parallel": pc["typing_min_parallel"] if sort == "antithetic" else 0,
        "typing": meta.get("typing"),
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
                n_parallel=r["n_parallel"],
                share_antithetic=r["share_antithetic"],
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
    check_page(state, limit, offset)
    if kind is not None and kind not in WORDPLAY_KINDS:
        raise unprocessable(f"kind must be one of {list(WORDPLAY_KINDS)}")
    span = None
    if unit is not None:
        u = unit_or_404(conn, unit)
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
                a_label_he=labels[r["a_vid"]][1],
                b_label_he=labels[r["b_vid"]][1],
                verses=[verses[v] for v in dict.fromkeys((r["a_vid"], r["b_vid"]))],
            )
            for r in rows
        ],
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
    u = unit_or_404(conn, unit_id)
    c = state.cfg["structure"]
    if u["unit_type"] == "verse":
        raise unprocessable("structure applies to chapters, pericopes and parashot")
    if u["n_verses"] > c["max_verses"]:
        raise unprocessable(f"structure is shown for units of at most {c['max_verses']} verses")
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
    check_unit_type(unit_type, state.cfg["structure"]["unit_types"])
    if by not in queries.STRUCTURE_SORT:
        raise unprocessable(f"by must be one of {sorted(queries.STRUCTURE_SORT)}")
    check_page(state, limit, offset)
    check_min(min_verses, "min_verses")
    total, rows = queries.structure_page(conn, unit_type, by, min_verses, limit, offset)
    units_ = queries.units_by_id(conn, [r["unit_id"] for r in rows])
    items = [
        StructureRank(
            unit=UnitSummary(**units_[r["unit_id"]]),
            **{k: r[k] for k in (*st.SCORE_COLS, *st.Q_COLS)},
        )
        for r in rows
    ]
    return {
        "unit_type": unit_type,
        "by": by,
        "min_verses": min_verses,
        "leitwort_numbers": state.meta.get("leitwort_numbers"),
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
    }


def _acrostic(r: dict[str, Any], unit: dict[str, Any]) -> Acrostic:
    return Acrostic(
        unit=UnitSummary(**unit),
        **{k: r[k] for k in Acrostic.model_fields if k not in ("unit", "chain")},
        chain=[
            AcrosticLine(verse_id=v, display_idx=i, letter=c) for v, i, c in json.loads(r["chain"])
        ],
    )


@router.get("/acrostics", response_model=AcrosticsResponse)
def acrostics(
    state: State,
    conn: Conn,
    max_q: float | None = 0.05,
    book: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Chapters whose lines run through the alphabet, most significant first (DESIGN.md §16.15)."""
    check_page(state, limit, offset)
    if max_q is not None and not 0 <= max_q <= 1:
        raise unprocessable("max_q must be between 0 and 1")
    total, rows = queries.acrostics_page(conn, max_q, book, limit, offset)
    units_ = queries.units_by_id(conn, [r["unit_id"] for r in rows])
    return {
        "max_q": max_q,
        "book": book,
        "known_recall": (state.meta.get("acrostics") or {}).get("known_recall"),
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [_acrostic(r, units_[r["unit_id"]]) for r in rows],
    }


@router.get("/acrostics/{unit_id}", response_model=Acrostic | None)
def unit_acrostic(unit_id: str, conn: Conn) -> Acrostic | None:
    """A chapter's best alphabetic chain (null for units without one)."""
    u = unit_or_404(conn, unit_id)
    r = queries.acrostic(conn, unit_id)
    return None if r is None else _acrostic(r, u)


@router.get("/word-pairs", response_model=WordPairsResponse)
def word_pairs(
    state: State,
    conn: Conn,
    max_q: float | None = 0.05,
    lemma: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Lemma pairs that answer each other across parallel lines (DESIGN.md §16.18)."""
    check_page(state, limit, offset)
    if max_q is not None and not 0 <= max_q <= 1:
        raise unprocessable("max_q must be between 0 and 1")
    total, rows = queries.word_pairs_page(conn, max_q, lemma, limit, offset)
    gloss = queries.gloss(conn, (x for r in rows for x in (r["a_lemma"], r["b_lemma"])))
    examples = {r["a_lemma"] + "|" + r["b_lemma"]: json.loads(r["examples"]) for r in rows}
    labels = queries.verse_labels(conn, (v for ex in examples.values() for v in ex))
    form = lambda lem: LemmaForm(lemma=lem, he_lemma=gloss.get(lem, lem))  # noqa: E731
    return {
        "max_q": max_q,
        "lemma": lemma,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            WordPair(
                a=form(r["a_lemma"]),
                b=form(r["b_lemma"]),
                **{k: r[k] for k in ("n", "expected", "g2", "q", "reverse")},
                examples=[
                    VerseLabel(verse_id=v, label_en=labels[v][0], label_he=labels[v][1])
                    for v in examples[r["a_lemma"] + "|" + r["b_lemma"]]
                ],
            )
            for r in rows
        ],
    }


@router.get("/alliteration", response_model=AlliterationResponse)
def alliteration(
    state: State,
    conn: Conn,
    book: int | None = None,
    unit: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Cola ranked by how unlikely their shared initial sounds are (candidates: none survive
    the multiple-testing correction; DESIGN.md §16.19)."""
    check_page(state, limit, offset)
    span = None
    if unit is not None:
        u = unit_or_404(conn, unit)
        span = (u["start_verse_id"], u["end_verse_id"])
    total, rows = queries.alliteration_page(conn, book, span, limit, offset)
    vids = [r["verse_id"] for r in rows]
    verses = queries.verses_by_id(conn, vids)
    labels = queries.verse_labels(conn, vids)
    return {
        "book": book,
        "unit": unit,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            Alliteration(
                verse=verses[r["verse_id"]],
                label=labels[r["verse_id"]][0],
                label_he=labels[r["verse_id"]][1],
                words=json.loads(r["words"]),
                **{k: r[k] for k in ("colon", "sound", "count", "n_words", "p", "q")},
            )
            for r in rows
        ],
    }


@router.get("/rhymes", response_model=RhymesResponse)
def rhymes(
    state: State,
    conn: Conn,
    book: int | None = None,
    max_q: float | None = None,
    unit: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Runs of consecutive cola ending alike, most significant first; `unit`: runs overlapping
    that unit."""
    check_page(state, limit, offset)
    if max_q is not None and not 0 <= max_q <= 1:
        raise unprocessable("max_q must be between 0 and 1")
    total, rows = queries.rhymes_page(conn, book, max_q, limit, offset, unit_span(conn, unit))
    vids = sorted({v for r in rows for v in range(r["start_vid"], r["end_vid"] + 1)})
    verses = queries.verses_by_id(conn, vids)
    labels = queries.verse_labels(conn, [v for r in rows for v in (r["start_vid"], r["end_vid"])])

    def label(a: int, b: int, lang: int = 0) -> str:
        return labels[a][lang] if a == b else f"{labels[a][lang]} – {labels[b][lang]}"

    return {
        "book": book,
        "max_q": max_q,
        "unit": unit,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            Rhyme(
                start_vid=r["start_vid"],
                end_vid=r["end_vid"],
                label=label(r["start_vid"], r["end_vid"]),
                label_he=label(r["start_vid"], r["end_vid"], 1),
                n_cola=r["n_cola"],
                ending=r["ending"],
                members=[tuple(m) for m in json.loads(r["members"])],
                verses=[verses[v] for v in range(r["start_vid"], r["end_vid"] + 1)],
                p=r["p"],
                q=r["q"],
            )
            for r in rows
        ],
    }
