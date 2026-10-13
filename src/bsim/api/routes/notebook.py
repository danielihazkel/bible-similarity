"""Your notebook (DESIGN.md §16.47): units kept with notes, and collections of them.

Stored with the pair labels in their writable file (`store/notebook.py`); `serve.labels_writable:
false` turns every write into 403. Responses are `no-store`: they change while the server runs.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response

from bsim.api import queries
from bsim.api.models import (
    CollectionIn,
    NotebookCollection,
    NotebookEntry,
    NotebookResponse,
    NoteIn,
    UnitSummary,
)
from bsim.api.routes._common import Conn, State, unit_or_404, unprocessable
from bsim.config import resolve_path
from bsim.store import notebook as store

router = APIRouter()
NO_STORE = {"Cache-Control": "no-store"}


def get_notebook_conn(state: State) -> Iterator[sqlite3.Connection]:
    conn = store.connect(resolve_path(state.cfg, "labels"))
    try:
        yield conn
    finally:
        conn.close()


NotebookConn = Annotated[sqlite3.Connection, Depends(get_notebook_conn)]


def _writable(state: State) -> None:
    if not state.cfg["serve"]["labels_writable"]:
        raise HTTPException(status_code=403, detail="the notebook is read-only on this server")


def _entries(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> list[NotebookEntry]:
    """Entries of units this build has, in canon order, a verse with its text."""
    units = queries.units_by_id(conn, [r["unit_id"] for r in rows])
    kept = [r for r in rows if r["unit_id"] in units]
    kept.sort(key=lambda r: (units[r["unit_id"]]["start_verse_id"],
                             -units[r["unit_id"]]["n_verses"], r["unit_id"]))  # fmt: skip
    verse_ids = [units[r["unit_id"]]["start_verse_id"] for r in kept
                 if units[r["unit_id"]]["unit_type"] == "verse"]  # fmt: skip
    verses = queries.verses_by_id(conn, verse_ids)
    return [
        NotebookEntry(
            unit=UnitSummary(**units[r["unit_id"]]),
            verse=verses.get(units[r["unit_id"]]["start_verse_id"])
            if units[r["unit_id"]]["unit_type"] == "verse"
            else None,
            **{k: r[k] for k in ("note", "collections", "created_at", "updated_at")},
        )
        for r in kept
    ]


def _check_name(state: State, body: CollectionIn) -> tuple[str, str]:
    nc = state.cfg["serve"]["notebook"]
    name, description = body.name.strip(), body.description.strip()
    if not 1 <= len(name) <= nc["max_name"]:
        raise unprocessable(f"a collection's name has 1 to {nc['max_name']} characters")
    if len(description) > nc["max_note"]:
        raise unprocessable(f"a description has at most {nc['max_note']} characters")
    return name, description


def _collection_or_404(nconn: sqlite3.Connection, collection_id: int) -> dict[str, Any]:
    c = store.collection(nconn, collection_id)
    if c is None:
        raise HTTPException(status_code=404, detail=f"no collection {collection_id}")
    return c


@router.get("/notebook", response_model=NotebookResponse)
def notebook(state: State, conn: Conn, nconn: NotebookConn, response: Response) -> dict[str, Any]:
    """Every entry in canon order, every collection by name."""
    response.headers.update(NO_STORE)
    rows = store.entries(nconn)
    entries = _entries(conn, rows)
    shown = {e.unit.unit_id for e in entries}
    counts: dict[int, int] = {}
    for e in entries:
        for c in e.collections:
            counts[c] = counts.get(c, 0) + 1
    return {
        "writable": state.cfg["serve"]["labels_writable"],
        "entries": entries,
        "collections": [
            NotebookCollection(**{**c, "n_entries": counts.get(c["collection_id"], 0)})
            for c in store.collections(nconn)
        ],
        "hidden": sum(r["unit_id"] not in shown for r in rows),
    }


@router.put("/notebook/entries/{unit_id}", response_model=NotebookEntry)
def put_entry(
    unit_id: str, body: NoteIn, state: State, conn: Conn, nconn: NotebookConn
) -> NotebookEntry:
    """Keep a unit, or change its note (`note` null: keep the note it has)."""
    _writable(state)
    unit_or_404(conn, unit_id)
    limit = state.cfg["serve"]["notebook"]["max_note"]
    if body.note is not None and len(body.note) > limit:
        raise unprocessable(f"a note has at most {limit} characters")
    return _entries(conn, [store.put_entry(nconn, unit_id, body.note)])[0]


@router.delete("/notebook/entries/{unit_id}", status_code=204)
def delete_entry(unit_id: str, state: State, nconn: NotebookConn) -> Response:
    """Remove an entry (and take it out of its collections)."""
    _writable(state)
    if not store.delete_entry(nconn, unit_id):
        raise HTTPException(status_code=404, detail="that unit is not in the notebook")
    return Response(status_code=204)


@router.post("/notebook/collections", response_model=NotebookCollection, status_code=201)
def create_collection(body: CollectionIn, state: State, nconn: NotebookConn) -> dict[str, Any]:
    _writable(state)
    name, description = _check_name(state, body)
    try:
        return store.create_collection(nconn, name, description)
    except store.Conflict as e:
        raise HTTPException(status_code=409, detail="a collection of that name exists") from e


@router.put("/notebook/collections/{collection_id}", response_model=NotebookCollection)
def update_collection(
    collection_id: int, body: CollectionIn, state: State, nconn: NotebookConn
) -> dict[str, Any]:
    """Rename or describe a collection."""
    _writable(state)
    name, description = _check_name(state, body)
    try:
        c = store.update_collection(nconn, collection_id, name, description)
    except store.Conflict as e:
        raise HTTPException(status_code=409, detail="a collection of that name exists") from e
    if c is None:
        raise HTTPException(status_code=404, detail=f"no collection {collection_id}")
    return c


@router.delete("/notebook/collections/{collection_id}", status_code=204)
def delete_collection(collection_id: int, state: State, nconn: NotebookConn) -> Response:
    """Remove a collection; its entries stay in the notebook."""
    _writable(state)
    if not store.delete_collection(nconn, collection_id):
        raise HTTPException(status_code=404, detail=f"no collection {collection_id}")
    return Response(status_code=204)


@router.put("/notebook/collections/{collection_id}/entries/{unit_id}", response_model=NotebookEntry)
def add_member(
    collection_id: int, unit_id: str, state: State, conn: Conn, nconn: NotebookConn
) -> NotebookEntry:
    """Put a unit in a collection (kept as an entry if it was not one)."""
    _writable(state)
    unit_or_404(conn, unit_id)
    _collection_or_404(nconn, collection_id)
    return _entries(conn, [store.add_member(nconn, collection_id, unit_id)])[0]


@router.delete("/notebook/collections/{collection_id}/entries/{unit_id}", status_code=204)
def remove_member(
    collection_id: int, unit_id: str, state: State, nconn: NotebookConn
) -> Response:
    """Take a unit out of a collection (it stays in the notebook)."""
    _writable(state)
    _collection_or_404(nconn, collection_id)
    if not store.remove_member(nconn, collection_id, unit_id):
        raise HTTPException(status_code=404, detail="that unit is not in the collection")
    return Response(status_code=204)
