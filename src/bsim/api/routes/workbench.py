"""The workbench (DESIGN.md §16.64): two sets of words contrasted value by value, and a pattern
checked on a set against its own surroundings. Both are computed on request from the word table
of pattern search; the notebook's collections are read live, so a set naming one is not cached."""

from __future__ import annotations

import sqlite3
from typing import Any

import numpy as np
from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models.workbench import (
    CheckBook,
    CheckResponse,
    ContrastResponse,
    ContrastRow,
    SetSummary,
    WorkbenchExample,
    WorkbenchFeature,
    WorkbenchWithin,
)
from bsim.api.patterns import PatternError, normalize, parse
from bsim.api.routes._common import Conn, State, unprocessable
from bsim.api.workbench import (
    Corpus,
    Resolved,
    SetError,
    check,
    contrast,
    feature_words,
    parse_set,
    resolve,
)
from bsim.config import resolve_path
from bsim.store import notebook as store

router = APIRouter()


def _pattern_rows(state: State, query: str) -> np.ndarray:
    """A pattern query's matches (`PatternError` when it cannot run), cached as /patterns does."""
    pc = state.cfg["serve"]["patterns"]
    table = state.word_table()
    query = normalize(query)
    terms = parse(query, pc["max_patterns"], table.max_words)
    rows = state.pattern_cache.get(query)
    if rows is None:
        rows = table.match(terms, pc["max_matches"])
        state.pattern_cache.put(query, rows)
    return rows


def _corpus(state: State, conn: sqlite3.Connection) -> Corpus:
    def unit_span(unit_id: str) -> tuple[int, int] | None:
        u = queries.unit(conn, unit_id)
        return None if u is None else (u["start_verse_id"], u["end_verse_id"])

    def collection_spans(collection_id: int) -> list[tuple[int, int]] | None:
        nconn = store.connect(resolve_path(state.cfg, "labels"))
        try:
            if store.collection(nconn, collection_id) is None:
                return None
            ids = [e["unit_id"] for e in store.entries(nconn) if collection_id in e["collections"]]
        finally:
            nconn.close()
        units = queries.units_by_id(conn, ids)
        return [(u["start_verse_id"], u["end_verse_id"]) for u in units.values()]

    return Corpus(
        verse_book=state.verse_books,
        verse_chapter=state.verse_chapters,
        sections=queries.book_sections(conn),
        unit_span=unit_span,
        collection_spans=collection_spans,
        pattern_rows=lambda q: _pattern_rows(state, q),
    )


def _summary(state: State, spec: str, r: Resolved) -> SetSummary:
    """A set as counted: the verses that hold its words."""
    vids = np.unique(state.word_table().verse[r.words])
    return SetSummary(
        spec=spec,
        verses=len(vids),
        words=int(r.words.sum()),
        books=[int(b) for b in np.unique(state.verse_books[vids])],
        filtered=r.filtered,
    )


def _problem(which: str, e: SetError) -> dict[str, Any]:
    return {"set": which, **e.as_dict()}


@router.get("/workbench/contrast", response_model=ContrastResponse)
def workbench_contrast(
    state: State,
    conn: Conn,
    a: str = "",
    b: str = "",
    feature: WorkbenchFeature = "lemma",
    rows: int | None = None,
) -> dict[str, Any]:
    """Each value of a feature scored by how much commoner it is in set A than in set B (empty B:
    every word not in A), by G² with BH q; the strongest of each side with example verses."""
    wc = state.cfg["serve"]["workbench"]
    rows = wc["rows"] if rows is None else rows
    if not 1 <= rows <= wc["max_rows"]:
        raise unprocessable(f"rows must be between 1 and {wc['max_rows']}")
    spec_a, spec_b = " ".join(a.split()), " ".join(b.split())
    empty = {"feature": feature, "error": None, "a": None, "b": None, "overlap": 0, "total_a": 0.0,
             "total_b": 0.0, "tested": 0, "min_count": wc["min_count"], "alpha": wc["alpha"],
             "significant_a": 0, "significant_b": 0, "over_a": [], "over_b": []}  # fmt: skip
    key = ("contrast", spec_a, spec_b, feature, rows)
    cacheable = "collection:" not in (spec_a + spec_b).lower()
    if cacheable and (hit := state.workbench_cache.get(key)) is not None:
        return hit
    table = state.word_table()
    corpus = _corpus(state, conn)
    which = "a"
    try:
        ra = resolve(parse_set(spec_a, wc["max_items"], wc["max_chars"]), corpus, table)
        which = "b"
        if spec_b:
            rb = resolve(parse_set(spec_b, wc["max_items"], wc["max_chars"]), corpus, table)
        else:
            rb = Resolved(~ra.verses, ~ra.words, ra.filtered)
    except SetError as e:
        return {**empty, "error": _problem(which, e)}
    overlap = int((ra.words & rb.words).sum())
    words_b = rb.words & ~ra.words
    if not words_b.any():
        return {**empty, "error": _problem("b", SetError("no_words", 0, ""))}
    domains = state.domain_table()
    c = contrast(table, domains, feature, ra.words, words_b, wc["min_count"])
    order = np.argsort(-c.g2, kind="stable")
    sides: dict[str, list[int]] = {"a": [], "b": []}
    for k in order:
        if len(sides[c.side[k]]) < rows:
            sides[c.side[k]].append(int(k))
    shown = [c.keys[c.tested[k]] for s in sides.values() for k in s]
    labels = queries.value_labels(conn, feature, shown)
    picks: dict[str, list[int]] = {}
    for side, words in (("a", ra.words), ("b", words_b)):
        for k in sides[side]:
            key_ = c.keys[c.tested[k]]
            vids = np.unique(table.verse[feature_words(table, domains, feature, key_, words)])
            picks[f"{side}:{key_}"] = [int(v) for v in vids[: wc["examples"]]]
    vlabels = queries.verse_labels(conn, [v for vs in picks.values() for v in vs])

    def row(side: str, k: int) -> ContrastRow:
        i = int(c.tested[k])
        key_ = c.keys[i]
        return ContrastRow(
            key=key_,
            label=labels.get(key_),
            a=float(c.a[i]),
            b=float(c.b[i]),
            rate_a=1000 * float(c.a[i]) / c.total_a,
            rate_b=1000 * float(c.b[i]) / c.total_b,
            log_ratio=float(c.log_ratio[k]),
            g2=float(c.g2[k]),
            p=float(c.p[k]),
            q=float(c.q[k]),
            examples=[
                WorkbenchExample(verse_id=v, label=vlabels[v][0], label_he=vlabels[v][1])
                for v in picks[f"{side}:{key_}"]
                if v in vlabels
            ],
        )

    sig = c.q <= wc["alpha"]
    out = {
        **empty,
        "a": _summary(state, spec_a, ra),
        "b": _summary(state, spec_b, Resolved(rb.verses, words_b, rb.filtered)),
        "overlap": overlap,
        "total_a": c.total_a,
        "total_b": c.total_b,
        "tested": len(c.tested),
        "significant_a": int((sig & (c.side == "a")).sum()),
        "significant_b": int((sig & (c.side == "b")).sum()),
        "over_a": [row("a", k) for k in sides["a"]],
        "over_b": [row("b", k) for k in sides["b"]],
    }
    if cacheable:
        state.workbench_cache.put(key, out)
    return out


@router.get("/workbench/check", response_model=CheckResponse)
def workbench_check(
    state: State,
    conn: Conn,
    q: str = "",
    set: str = "",  # noqa: A002 - the query parameter's name
    within: WorkbenchWithin = "book",
    draws: int | None = None,
) -> dict[str, Any]:
    """Whether a pattern matches more often (or less) in the set's verses than in the set's
    verses drawn again at random within each book, chapter or the whole corpus."""
    wc = state.cfg["serve"]["workbench"]
    draws = wc["draws"] if draws is None else draws
    if not 99 <= draws <= wc["max_draws"]:
        raise unprocessable(f"draws must be between 99 and {wc['max_draws']}")
    query, spec = normalize(q), " ".join(set.split())
    empty = {"q": query, "within": within, "draws": draws, "error": None, "pattern_error": None,
             "set": None, "testable": False, "matches": 0, "words": 0, "rate": 0.0,
             "rest_matches": 0, "rest_words": 0, "rest_rate": 0.0, "null_mean": 0.0,
             "null_low": 0.0, "null_high": 0.0, "p_high": 1.0, "p_low": 1.0, "groups": 0,
             "fixed_verses": 0, "books": []}  # fmt: skip
    key = ("check", query, spec, within, draws)
    cacheable = "collection:" not in spec.lower()
    if cacheable and (hit := state.workbench_cache.get(key)) is not None:
        return hit
    table = state.word_table()
    try:
        rows = _pattern_rows(state, query)
    except PatternError as e:
        return {**empty, "pattern_error": e.as_dict()}
    try:
        items = parse_set(spec, wc["max_items"], wc["max_chars"])
        only = next((it for it in items if it.kind == "only"), None)
        if only is not None:
            raise SetError("filter_in_check", only.at, f"only:{only.value}")
        r = resolve(items, _corpus(state, conn), table)
    except SetError as e:
        return {**empty, "error": _problem("set", e)}
    n = state.n_verses
    matches = np.bincount(table.verse[rows[:, 0]], minlength=n) if len(rows) else np.zeros(n)
    words = np.bincount(table.verse, minlength=n)
    books, chapters = state.verse_books, state.verse_chapters
    groups = {"corpus": np.zeros(n, dtype=np.int64), "book": books,
              "chapter": books * 1000 + chapters}[within]  # fmt: skip
    ck = check(matches, words, r.verses, groups, draws, wc["seed"])
    per_book = []
    for bk in np.unique(books[r.verses]):
        sel = r.verses & (books == bk)
        per_book.append(CheckBook(book_id=int(bk), matches=int(matches[sel].sum()),
                                  words=int(words[sel].sum())))  # fmt: skip
    out = {
        **empty,
        "set": _summary(state, spec, r),
        "testable": ck.testable,
        "matches": ck.matches,
        "words": ck.words,
        "rate": ck.rate,
        "rest_matches": ck.rest_matches,
        "rest_words": ck.rest_words,
        "rest_rate": 1000 * ck.rest_matches / ck.rest_words if ck.rest_words else 0.0,
        "null_mean": ck.null_mean,
        "null_low": ck.null_low,
        "null_high": ck.null_high,
        "p_high": ck.p_high,
        "p_low": ck.p_low,
        "groups": ck.groups,
        "fixed_verses": ck.fixed_verses,
        "books": per_book,
    }
    if cacheable:
        state.workbench_cache.put(key, out)
    return out
