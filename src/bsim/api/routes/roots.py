"""Root families (DESIGN.md §16.38): the tests, words of one root side by side, Leitworte that
only show counted by root, and one root's family with its verses."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.common import BookCount, ConcordanceHit, LemmaStat, UnitSummary
from bsim.api.models.roots import (
    HiddenRoot,
    HiddenRootsResponse,
    RootBook,
    RootFamily,
    RootKnown,
    RootPair,
    RootPairKind,
    RootPairsResponse,
    RootsResponse,
)
from bsim.api.routes._common import Conn, State, check_page, unit_or_404, unit_span

router = APIRouter()


def _stat(stats: dict[str, dict[str, Any]], lemma: str) -> LemmaStat:
    s = stats.get(lemma, {})
    return LemmaStat(lemma=lemma, he_lemma=s.get("he_lemma", lemma), n_verses=s.get("n_verses", 0))


def _root_he(conn: sqlite3.Connection, root: str) -> str:
    row = conn.execute("SELECT root_he FROM lemma_roots WHERE root = ? LIMIT 1", (root,)).fetchone()
    return row[0] if row else root


@router.get("/roots", response_model=RootsResponse)
def roots(state: State, conn: Conn) -> dict[str, Any]:
    """Families, the side-by-side test, the Leitworte named in advance and the books."""
    meta = state.meta.get("roots") or {}
    known = meta.get("known") or []
    units = queries.units_by_id(conn, [f"c:{k['book_id']}:{k['chapter_no']}" for k in known])
    return {
        "meta": {k: v for k, v in meta.items() if k != "known"},
        "known": [
            RootKnown(
                unit=UnitSummary(**units[f"c:{k['book_id']}:{k['chapter_no']}"]),
                root=k["root"],
                root_he=k["he"],
                lemma_rank=k["lemma_rank"],
                root_rank=k["root_rank"],
            )
            for k in known
            if f"c:{k['book_id']}:{k['chapter_no']}" in units
        ],
        "books": [
            RootBook(**r)
            for r in queries._dicts(conn.execute("SELECT * FROM root_books ORDER BY book_id"))
            if r["words"]
        ],
    }


@router.get("/roots/pairs", response_model=RootPairsResponse)
def root_pairs(
    state: State,
    conn: Conn,
    kind: RootPairKind | None = None,
    book: int | None = None,
    unit: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Two words of one root side by side in a verse, in canon order."""
    check_page(state, limit, offset)
    total, rows = queries.root_pairs_page(conn, kind, book, unit_span(conn, unit), limit, offset)
    vids = [r["verse_id"] for r in rows]
    verses, labels = queries.verses_by_id(conn, vids), queries.verse_labels(conn, vids)
    stats = queries.lemma_stats(conn, (x for r in rows for x in (r["a_lemma"], r["b_lemma"])))
    index = state.roots(conn)
    items = []
    for r in rows:
        disp = queries.display_map(conn, r["verse_id"])
        marks = {disp[i]: side for side, i in enumerate((r["a_idx"], r["b_idx"])) if i in disp}
        items.append(
            RootPair(
                pair_id=r["pair_id"],
                verse_id=r["verse_id"],
                label=labels[r["verse_id"]][0],
                label_he=labels[r["verse_id"]][1],
                kind=r["kind"],
                root=r["root"],
                root_he=index.root_of.get(r["a_lemma"], (r["root"], r["root"]))[1],
                a=_stat(stats, r["a_lemma"]),
                b=_stat(stats, r["b_lemma"]),
                verse=verses[r["verse_id"]],
                marks=marks,
            )
        )
    return {"kind": kind, "book": book, "unit": unit, "total": total, "offset": offset,
            "limit": limit, "items": items}  # fmt: skip


@router.get("/roots/hidden", response_model=HiddenRootsResponse)
def hidden_roots(
    state: State,
    conn: Conn,
    book: int | None = None,
    unit: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Chapter Leitworte that only show when a root's words are counted together, strongest
    first; `unit` = the chapters it overlaps."""
    check_page(state, limit, offset)
    chapters = None
    if unit is not None:
        u = unit_or_404(conn, unit)
        chapters = [
            c["unit_id"]
            for c in [u, *queries.parents(conn, u)]
            if c["unit_type"] == "chapter"
        ]
        if u["unit_type"] in ("pericope", "parasha"):
            chapters = [
                r[0]
                for r in conn.execute(
                    "SELECT unit_id FROM units WHERE unit_type = 'chapter'"
                    " AND start_verse_id <= ? AND end_verse_id >= ?",
                    (u["end_verse_id"], u["start_verse_id"]),
                )
            ]
    total, rows = queries.hidden_roots_page(conn, book, chapters, limit, offset)
    units = queries.units_by_id(conn, [r["unit_id"] for r in rows])
    index = state.roots(conn)
    items = []
    for r in rows:
        u = units[r["unit_id"]]
        members = index.members.get(r["root"], [])
        present = [
            lem
            for (lem,) in conn.execute(
                "SELECT DISTINCT lemma FROM lemma_verses WHERE verse_id BETWEEN ? AND ?"
                f" AND lemma IN ({','.join('?' * len(members))})",
                (u["start_verse_id"], u["end_verse_id"], *members),
            )
        ] if members else []
        stats = queries.lemma_stats(conn, present)
        items.append(
            HiddenRoot(
                unit=UnitSummary(**u),
                rank=r["rank"],
                root=r["root"],
                root_he=index.root_of.get(present[0], (r["root"], r["root"]))[1]
                if present
                else r["root"],
                count=r["count"],
                g2=r["g2"],
                n_words=r["n_words"],
                lemma_rank=r["lemma_rank"],
                lemmas=sorted((_stat(stats, lem) for lem in present), key=lambda s: -s.n_verses),
            )
        )
    return {"book": book, "unit": unit, "total": total, "offset": offset, "limit": limit,
            "items": items}  # fmt: skip


@router.get("/root/{root}", response_model=RootFamily)
def root_family(
    root: str,
    state: State,
    conn: Conn,
    book: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """A root's family (its words, how Strong's derives them) and the verses holding any of
    them, with per-book counts."""
    members = state.roots(conn).members.get(root)
    if not members or len(members) < 2:  # a word alone is read in its concordance
        raise HTTPException(status_code=404, detail=f"no root family {root!r}")
    check_page(state, limit, offset)
    stats = queries.lemma_stats(conn, members)
    links = dict(
        conn.execute(
            f"SELECT lemma, link FROM lemma_roots WHERE lemma IN ({','.join('?' * len(members))})"
            " AND link IS NOT NULL",
            members,
        ).fetchall()
    )
    by_book = queries.lemmas_books(conn, members)
    total = sum(b["n_verses"] for b in by_book if book is None or b["book_id"] == book)
    vids = queries.lemmas_page(conn, members, book, limit, offset)
    verses, labels = queries.verses_by_id(conn, vids), queries.verse_labels(conn, vids)
    wanted = set(members)
    marks: dict[int, set[int]] = defaultdict(set)
    for w in queries.words(conn, vids):
        if w["display_idx"] is not None and wanted & set(w["content_lemmas"].split()):
            marks[w["verse_id"]].add(w["display_idx"])
    return {
        "root": root,
        "root_he": _root_he(conn, root),
        "members": sorted(
            (_stat(stats, lem) for lem in members if lem in stats), key=lambda s: -s.n_verses
        ),
        "links": links,
        "n_verses": sum(b["n_verses"] for b in by_book),
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
