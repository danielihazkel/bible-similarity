"""The Late Biblical Hebrew profile of books and chapters (DESIGN.md §16.24)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models import DatingBook, DatingChapter, DatingResponse, SynopticExample
from bsim.api.routes._common import Conn, State, span_label, unit_or_404
from bsim.store.db import DATING_FEATURES

router = APIRouter()


def _chapter(r: dict[str, Any]) -> DatingChapter:
    return DatingChapter(
        **{k: r[k] for k in ("unit_id", "book_id", "chapter", "n_words", "role", "score")},
        out_of_domain=bool(r["out_of_domain"]),
        features={f: r[f] for f in DATING_FEATURES},
        drivers=json.loads(r["drivers"]),
    )


@router.get("/dating", response_model=DatingResponse)
def dating(state: State, conn: Conn) -> dict[str, Any]:
    """Every book's mean profile and spread, the model and its checks (held-out AUC, the
    synoptic parallels of Samuel–Kings and Chronicles)."""
    meta = state.meta.get("dating") or {}
    syn = meta.get("synoptic") or {}
    ex = syn.get("examples") or []
    ends = [v for e in ex for v in (*e["early"], *e["late"])]
    labels = queries.verse_labels(conn, ends)
    return {
        "features": meta.get("features") or list(DATING_FEATURES),
        "coefficients": meta.get("coefficients") or {},
        "held_out_auc": meta.get("held_out_auc"),
        "held_out_auc_grammar": meta.get("held_out_auc_grammar"),
        "train_chapters": meta.get("train_chapters") or {},
        "synoptic": {
            k: syn.get(k) for k in ("pairs", "later", "p", "later_grammar", "p_grammar")
        },
        "synoptic_examples": [
            SynopticExample(
                early_first=e["early"][0],
                late_first=e["late"][0],
                early_label=span_label(labels, *e["early"], 0),
                late_label=span_label(labels, *e["late"], 0),
                early_label_he=span_label(labels, *e["early"], 1),
                late_label_he=span_label(labels, *e["late"], 1),
                early_score=e["early_score"],
                late_score=e["late_score"],
            )
            for e in ex
        ],
        "books": [
            DatingBook(
                **{k: r[k] for k in ("book_id", "role", "n_chapters", "score", "low", "high")},
                out_of_domain=bool(r["out_of_domain"]),
                features={f: r[f] for f in DATING_FEATURES},
            )
            for r in queries.dating_books(conn)
        ],
    }


@router.get("/dating/book/{book_id}", response_model=list[DatingChapter])
def dating_book(book_id: int, conn: Conn) -> list[DatingChapter]:
    """A book's chapters with their profile, features and drivers, in order."""
    rows = queries.dating_chapters(conn, book_id)
    if not rows and book_id not in {b["book_id"] for b in queries.dating_books(conn)}:
        raise HTTPException(status_code=404, detail=f"unknown book {book_id}")
    return [_chapter(r) for r in rows]


@router.get("/unit-dating/{unit_id}", response_model=DatingChapter | None)
def unit_dating(unit_id: str, conn: Conn) -> DatingChapter | None:
    """The profile of the chapter a unit starts in (None without `bsim dating`)."""
    u = unit_or_404(conn, unit_id)
    r = queries.dating_chapter_of(conn, u["start_verse_id"])
    return _chapter(r) if r else None
