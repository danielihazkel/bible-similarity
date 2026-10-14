"""The Pentateuch's sources (DESIGN.md §16.43): an unsupervised P / non-P split of
Genesis-Numbers, its checks against the reference, the words that decide it, and the split
chapter by chapter."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models.pentateuch import (
    PentateuchChaptersResponse,
    PentateuchResponse,
    SourceChapter,
    SourceSynonym,
    SourceWord,
)
from bsim.api.routes._common import Conn, State, check_page

router = APIRouter()


def hebrew(conn: sqlite3.Connection, tokens: list[str], prefixes: dict[str, str]) -> dict[str, str]:
    """token -> Hebrew form: a prefix letter, or the lemma of a Strong's number (the stem marker
    `@h` / `@q` is the viewer's to name; the lexicon's homograph letter is tried)."""
    bare = {t: t.split("@")[0] for t in tokens if not t.startswith("p:")}
    keys = [*bare.values(), *(f"{b}{x}" for b in bare.values() for x in "abc")]
    found = queries.gloss(conn, keys)
    out = {t: prefixes.get(t[2:], t[2:]) for t in tokens if t.startswith("p:")}
    for t, b in bare.items():
        he = found.get(b) or next((found[f"{b}{x}"] for x in "abc" if f"{b}{x}" in found), None)
        if he is not None:
            out[t] = he
    return out


@router.get("/pentateuch", response_model=PentateuchResponse)
def pentateuch(state: State, conn: Conn) -> dict[str, Any]:
    """The split's three checks fixed in advance, its agreement by book, the divine names, the
    robustness grid, and the words and synonym choices that decide it."""
    meta = state.meta.get("pentateuch") or {}
    feats = meta.get("features") or {}
    syns = meta.get("synonyms") or []
    tokens = [f["token"] for side in feats.values() for f in side]
    tokens += [m for s in syns for m in s["members"]]
    he = hebrew(conn, tokens, meta.get("prefixes") or {})
    return {
        "meta": {k: v for k, v in meta.items() if k not in ("features", "synonyms", "prefixes")},
        "p_like": [SourceWord(he=he.get(f["token"]), **f) for f in feats.get("p_like", [])],
        "non_p": [SourceWord(he=he.get(f["token"]), **f) for f in feats.get("non_p", [])],
        "synonyms": [
            SourceSynonym(he=[he.get(m) for m in s["members"]], **s) for s in syns
        ],
    }


@router.get("/pentateuch/chapters", response_model=PentateuchChaptersResponse)
def pentateuch_chapters(
    state: State, conn: Conn, book: int | None = None, limit: int = 60, offset: int = 0
) -> dict[str, Any]:
    """Each chapter of Genesis-Numbers: the share of its verses on the P-like side against the
    share the reference calls P."""
    check_page(state, limit, offset)
    total, rows = queries.pentateuch_chapters_page(conn, book, limit, offset)
    items = [
        SourceChapter(label=r["label_en"], label_he=r["label_he"],
                      **{k: r[k] for k in ("unit_id", "book_id", "chapter", "verses", "p_like",
                                           "assigned", "p_ref")})
        for r in rows
    ]  # fmt: skip
    return {"book": book, "total": total, "offset": offset, "limit": limit, "items": items}
