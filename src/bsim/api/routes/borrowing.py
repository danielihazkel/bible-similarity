"""Which side of a cross-book parallel looks like the borrower (DESIGN.md §16.27)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models import BorrowingBookPair, BorrowingResponse, BorrowingSequence
from bsim.api.routes._common import Conn, State, span_label, unit_or_404, unit_span

router = APIRouter()
COLUMNS = (
    "seq_id",
    "a_book",
    "b_book",
    "n_pairs",
    "language",
    "spelling",
    "smoothing",
    "expansion",
    "n_spelling",
    "n_substitution",
    "known",
    "votes",
    "n_votes",
    "direction",
)


def _sequences(conn: Conn, rows: list[dict[str, Any]]) -> list[BorrowingSequence]:
    ends = [r[k] for r in rows for k in ("a_start", "a_end", "b_start", "b_end")]
    labels = queries.verse_labels(conn, ends)
    return [
        BorrowingSequence(
            **{k: r[k] for k in COLUMNS},
            a_first=r["a_start"],
            b_first=r["b_start"],
            a_label=span_label(labels, r["a_start"], r["a_end"], 0),
            b_label=span_label(labels, r["b_start"], r["b_end"], 0),
            a_label_he=span_label(labels, r["a_start"], r["a_end"], 1),
            b_label_he=span_label(labels, r["b_start"], r["b_end"], 1),
        )
        for r in rows
    ]


@router.get("/borrowing", response_model=BorrowingResponse)
def borrowing(state: State, conn: Conn, unit: str | None = None) -> dict[str, Any]:
    """Book pairs with their parallels, each with its signs and direction, and the check of the
    signs on the directions scholars accept; `unit`: only the parallels touching that unit (and
    their book pairs)."""
    meta = state.meta.get("borrowing") or {}
    span = unit_span(conn, unit)
    rows = (
        queries.borrowing_sequences(conn)
        if span is None
        else queries.borrowing_touching(conn, span)
    )
    by_pair: dict[tuple[int, int], list[BorrowingSequence]] = {}
    for s in _sequences(conn, rows):
        by_pair.setdefault((s.a_book, s.b_book), []).append(s)
    return {
        "unit": unit,
        "checks": meta.get("checks") or {},
        "used_signs": meta.get("used_signs") or [],
        "held_out": meta.get("held_out"),
        "books": [
            BorrowingBookPair(**b, items=by_pair.get((b["a_book"], b["b_book"]), []))
            for b in queries.borrowing_books(conn)
            if span is None or (b["a_book"], b["b_book"]) in by_pair
        ],
    }


@router.get("/borrowing/sequence/{seq_id}", response_model=BorrowingSequence | None)
def borrowing_sequence(seq_id: int, conn: Conn) -> BorrowingSequence | None:
    """The direction estimate of one parallel sequence (None: not a scored cross-book one)."""
    rows = queries.borrowing_sequences(conn, seq_id)
    return _sequences(conn, rows)[0] if rows else None


@router.get("/borrowing/between", response_model=list[BorrowingSequence])
def borrowing_between(a: str, b: str, conn: Conn) -> list[BorrowingSequence]:
    """Scored parallels with one side in unit `a` and the other in unit `b`."""
    ua, ub = unit_or_404(conn, a), unit_or_404(conn, b)
    rows = queries.borrowing_between(
        conn,
        (ua["start_verse_id"], ua["end_verse_id"]),
        (ub["start_verse_id"], ub["end_verse_id"]),
    )
    return _sequences(conn, rows)
