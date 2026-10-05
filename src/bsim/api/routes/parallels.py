"""Parallel sequences and how they differ (DESIGN.md §16.7, §16.8)."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException

from bsim.analysis import diffs as df_
from bsim.analysis import sequences as sq
from bsim.api import queries
from bsim.api.app import ServeState
from bsim.api.models import (
    ChangeExample,
    ChangeGroup,
    ChangesResponse,
    LadderRow,
    Rewrite,
    RewriteProfile,
    RewritesResponse,
    SequenceDetail,
    SequencesResponse,
    SequenceSummary,
    VerseDiff,
)
from bsim.api.routes._common import (
    Conn,
    State,
    check_min,
    check_page,
    unit_or_404,
    unprocessable,
    verse_or_404,
)

router = APIRouter()


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
    verse_or_404(state, a)
    verse_or_404(state, b)
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
        raise unprocessable(f"op must be one of {[o for o in df_.OPS if o != 'same']}")
    check_page(state, limit, offset)
    total, groups = queries.change_groups(conn, op, a_book, b_book, limit, offset)
    keys = {k for g in groups for k in (g["a_key"], g["b_key"]) if k and not k.startswith("~")}
    gloss = queries.gloss(conn, (p for k in keys for p in k.split("+")))
    by_form = op in queries.FORM_OPS

    def group(g: dict[str, Any]) -> tuple[str | None, str | None]:
        return (g["a_form"], g["b_form"]) if by_form else (g["a_key"], g["b_key"])

    ex = queries.change_examples(conn, op, a_book, b_book, [group(g) for g in groups], 3)
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
    direction: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Passages that run parallel verse by verse, strongest first (DESIGN.md §16.7);
    `unit`: only chains touching that unit's verses; `direction`: forward | reverse | mixed."""
    check_page(state, limit, offset)
    if direction is not None and direction not in sq.DIRECTIONS:
        raise unprocessable(f"direction must be one of {list(sq.DIRECTIONS)}")
    check_min(min_pairs, "min_pairs")
    if max_q is not None and not 0 <= max_q <= 1:
        raise unprocessable("max_q must be between 0 and 1")
    span = None
    if unit is not None:
        u = unit_or_404(conn, unit)
        span = (u["start_verse_id"], u["end_verse_id"])
    total, rows = queries.sequences_page(
        conn, book, cross_book, hide_same_chapter, max_q, min_pairs, span, limit, offset, direction
    )
    return {
        "book": book,
        "cross_book": cross_book,
        "hide_same_chapter": hide_same_chapter,
        "max_q": max_q,
        "min_pairs": min_pairs,
        "unit": unit,
        "direction": direction,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": _sequence_summaries(conn, rows),
    }


@router.get("/sequences/{seq_id}", response_model=SequenceDetail)
def sequence_detail(seq_id: int, state: State, conn: Conn) -> dict[str, Any]:
    """One chain side by side: aligned pairs, plus the verses skipped on either side (cached:
    every pair is word-aligned)."""
    cached = state.sequence_cache.get(seq_id)
    if cached is None:
        cached = _sequence_detail(seq_id, state, conn)
        state.sequence_cache.put(seq_id, cached)
    return cached


def _sequence_detail(seq_id: int, state: ServeState, conn: sqlite3.Connection) -> dict[str, Any]:
    r = queries.sequence(conn, seq_id)
    if r is None:
        raise HTTPException(status_code=404, detail=f"unknown sequence {seq_id}")
    pairs = [(int(a), int(b), float(w), bool(g)) for a, b, w, g in json.loads(r["pairs"])]
    rows: list[LadderRow] = []
    for k, (a, b, w, gold) in enumerate(pairs):
        if k:
            pa, pb = pairs[k - 1][:2]
            rows += [LadderRow(a=x, b=None) for x in range(pa + 1, a)]
            # the verses skipped on the b side, in reading order of the chain (none when the
            # b side jumps back and forth)
            if r["direction"] == "forward":
                rows += [LadderRow(a=None, b=y) for y in range(pb + 1, b)]
            elif r["direction"] == "reverse":
                rows += [LadderRow(a=None, b=y) for y in range(pb - 1, b, -1)]
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


@router.get("/rewrites", response_model=RewritesResponse)
def rewrites(
    state: State,
    conn: Conn,
    a_book: int | None = None,
    b_book: int | None = None,
    op: str | None = None,
    max_q: float | None = 0.05,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Changes one book makes consistently against another (DESIGN.md §16.16)."""
    check_page(state, limit, offset)
    if op is not None and op not in df_.REWRITE_OPS:
        raise unprocessable(f"op must be one of {list(df_.REWRITE_OPS)}")
    if max_q is not None and not 0 <= max_q <= 1:
        raise unprocessable("max_q must be between 0 and 1")
    total, rows = queries.rewrites_page(conn, a_book, b_book, op, max_q, limit, offset)
    keys = {k for r in rows for k in (r["a_key"], r["b_key"]) if k and not k.startswith("~")}
    gloss = queries.gloss(conn, (p for k in keys for p in k.split("+")))
    return {
        "a_book": a_book,
        "b_book": b_book,
        "op": op,
        "max_q": max_q,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            Rewrite(**r, a_he=_key_he(r["a_key"], gloss), b_he=_key_he(r["b_key"], gloss))
            for r in rows
        ],
    }


@router.get("/rewrite-profiles", response_model=list[RewriteProfile])
def rewrite_profiles(conn: Conn) -> list[RewriteProfile]:
    """Per book pair of parallel passages: how many verses were diffed and how they differ."""
    return [RewriteProfile(**r) for r in queries.rewrite_profiles(conn)]
