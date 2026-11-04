"""Your judgements of proposed pairs (DESIGN.md §16.25): the one writable part of the API.

Labels live in their own SQLite file (`paths.labels`, `store/labels.py`), not in the read-only
results DB; `serve.labels_writable: false` turns PUT / DELETE into 403. Responses are `no-store`:
unlike the rest of `/api`, they change while the server runs.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from bsim.api import label_queue, queries
from bsim.api.app import NO_STORE
from bsim.api.models.common import UnitSummary
from bsim.api.models.labels import (
    Label,
    LabelIn,
    LabelQueue,
    LabelsEval,
    LabelsResponse,
    QueueItem,
)
from bsim.api.routes._common import Conn, State, unit_or_404, unprocessable
from bsim.config import resolve_path
from bsim.eval.labels import live_eval
from bsim.store import labels as store

router = APIRouter()


def get_labels_conn(state: State) -> Iterator[sqlite3.Connection]:
    conn = store.connect(resolve_path(state.cfg, "labels"))
    try:
        yield conn
    finally:
        conn.close()


LabelsConn = Annotated[sqlite3.Connection, Depends(get_labels_conn)]


def _writable(state: State) -> None:
    if not state.cfg["serve"]["labels_writable"]:
        raise HTTPException(status_code=403, detail="labels are read-only on this server")


def _ordered(conn: sqlite3.Connection, a_id: str, b_id: str) -> tuple[dict, dict]:
    """The two units, the one starting earlier in the canon first (a pair is undirected)."""
    a, b = unit_or_404(conn, a_id), unit_or_404(conn, b_id)
    if a_id == b_id:
        raise unprocessable("a pair needs two different units")
    if a["unit_type"] != b["unit_type"]:
        raise unprocessable("both units of a pair must be of the same type")
    return (a, b) if (a["start_verse_id"], a_id) <= (b["start_verse_id"], b_id) else (b, a)


def _items(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> list[Label]:
    units = queries.units_by_id(conn, [i for r in rows for i in (r["a_id"], r["b_id"])])
    return [
        Label(
            **{k: r[k] for k in ("unit_type", "label", "note", "mode", "score", "labeled_at")},
            a=UnitSummary(**units[r["a_id"]]),
            b=UnitSummary(**units[r["b_id"]]),
        )
        for r in rows
        if r["a_id"] in units and r["b_id"] in units  # units of an older build are left out
    ]


@router.get("/labels", response_model=LabelsResponse)
def labels(state: State, conn: Conn, lconn: LabelsConn, response: Response) -> dict[str, Any]:
    """Every labelled pair, most recent first."""
    response.headers.update(NO_STORE)
    items = _items(conn, store.all_labels(lconn))
    return {
        "writable": state.cfg["serve"]["labels_writable"],
        "counts": {lab: sum(i.label == lab for i in items) for lab in store.LABELS},
        "items": items,
    }


@router.put("/labels", response_model=Label)
def put_label(body: LabelIn, state: State, conn: Conn, lconn: LabelsConn) -> Label:
    """Label a pair (replacing an earlier label of it)."""
    _writable(state)
    a, b = _ordered(conn, body.a_id, body.b_id)
    row = store.put(
        lconn,
        a["unit_type"],
        a["unit_id"],
        b["unit_id"],
        body.label,
        body.note,
        body.mode,
        body.score,
    )
    return _items(conn, [row])[0]


@router.delete("/labels/{a_id}/{b_id}", status_code=204)
def delete_label(a_id: str, b_id: str, state: State, conn: Conn, lconn: LabelsConn) -> Response:
    """Remove a pair's label."""
    _writable(state)
    a, b = _ordered(conn, a_id, b_id)
    if not store.delete(lconn, a["unit_id"], b["unit_id"]):
        raise HTTPException(status_code=404, detail="that pair has no label")
    return Response(status_code=204)


@router.get("/labels/eval", response_model=LabelsEval)
def labels_eval(state: State, conn: Conn, lconn: LabelsConn, response: Response) -> dict[str, Any]:
    """How each mode's lists separate your real pairs from your not pairs (live, all labels)."""
    response.headers.update(NO_STORE)
    lc = state.cfg["labels"]
    return {
        "k": lc["k"],
        "min_pairs": lc["min_pairs"],
        "rows": live_eval(conn, store.all_labels(lconn), lc["k"], lc["min_pairs"]),
    }


@router.get("/labels/queue", response_model=LabelQueue)
def labels_queue(
    state: State,
    conn: Conn,
    lconn: LabelsConn,
    response: Response,
    side: Annotated[str, Query(pattern="^(all|lexical|semantic)$")] = "all",
    limit: int | None = None,
) -> dict[str, Any]:
    """Unlabelled train-book verse pairs where the lexical and semantic lists disagree most
    (DESIGN.md §16.79): what to judge next. 503 `splits_missing` without `splits.json`."""
    response.headers.update(NO_STORE)
    qc, k = state.cfg["labels"]["queue"], state.cfg["retrieval"]["k"]
    limit = qc["size"] if limit is None else limit
    if not 1 <= limit <= qc["max_size"]:
        raise unprocessable(f"limit must be between 1 and {qc['max_size']}")
    books = label_queue.train_books(state.cfg, qc["split"])
    if books is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "splits_missing", "message": "run `bsim build-links` first"},
        )
    pool = label_queue.queue_for(conn, state.db_path, books, k + 1)
    verse_labels = store.all_labels(lconn, "verse")
    done = {(r["a_id"], r["b_id"]) for r in verse_labels}
    done |= {(b, a) for a, b in done}
    real = [r for r in verse_labels if r["label"] == "real"]
    book = {
        v["verse_id"]: v["book_id"]
        for v in queries.verses_by_id(
            conn, [int(i.removeprefix("v:")) for r in real for i in (r["a_id"], r["b_id"])]
        ).values()
    }
    train_real = sum(
        all(book.get(int(r[k].removeprefix("v:"))) in books for k in ("a_id", "b_id")) for r in real
    )
    todo = label_queue.unlabelled(pool, done, side)
    page = todo[:limit]
    verses = queries.verses_by_id(
        conn, [int(i.removeprefix("v:")) for p in page for i in (p.a_id, p.b_id)]
    )
    return {
        "writable": state.cfg["serve"]["labels_writable"],
        "split": qc["split"],
        "k": k,
        "pool": len(pool),
        "labelled": sum((p.a_id, p.b_id) in done for p in pool),
        "train_real": train_real,
        "min_train": state.cfg["labels"]["min_train"],
        "total": len(todo),
        "items": [
            QueueItem(
                a=verses[int(p.a_id.removeprefix("v:"))],
                b=verses[int(p.b_id.removeprefix("v:"))],
                a_id=p.a_id,
                b_id=p.b_id,
                lex_rank=p.lex_rank,
                sem_rank=p.sem_rank,
                disagreement=p.disagreement,
                side=p.side,
                score=p.score,
            )
            for p in page
        ],
    }
