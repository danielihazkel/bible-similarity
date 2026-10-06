"""Your judgements of proposed pairs (DESIGN.md §16.25): the one writable part of the API.

Labels live in their own SQLite file (`paths.labels`, `store/labels.py`), not in the read-only
results DB; `serve.labels_writable: false` turns PUT / DELETE into 403. Responses are `no-store`:
unlike the rest of `/api`, they change while the server runs.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response

from bsim.api import queries
from bsim.api.models import Label, LabelIn, LabelsEval, LabelsResponse, UnitSummary
from bsim.api.routes._common import Conn, State, unit_or_404, unprocessable
from bsim.config import resolve_path
from bsim.eval.labels import live_eval
from bsim.store import labels as store

router = APIRouter()
NO_STORE = {"Cache-Control": "no-store"}


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
