"""Your notebook (DESIGN.md §16.47): bookmarks with notes, and collections of them.

It lives in the same writable file as the pair labels (`paths.labels`, `store/labels.py`), never
in the results DB, which `bsim build-db` rebuilds. An *entry* is a unit you kept (a verse, a
chapter, a pericope …) with a note, possibly empty; a *collection* is a named group of entries.
Adding a unit to a collection keeps it as an entry; removing an entry takes it out of every
collection; removing a collection keeps its entries.

    notebook_entries(unit_id, note, created_at, updated_at)
    notebook_collections(collection_id, name, description, created_at, updated_at)
    notebook_members(collection_id, unit_id, added_at)

Unit ids are those of the results DB; an entry whose unit a later build lacks stays in the file
and is left out of what the API shows.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from bsim.store import labels

SCHEMA = """
CREATE TABLE IF NOT EXISTS notebook_entries (
    unit_id TEXT PRIMARY KEY,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS notebook_collections (
    collection_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notebook_members (
    collection_id INTEGER NOT NULL,
    unit_id TEXT NOT NULL,
    added_at TEXT NOT NULL,
    PRIMARY KEY (collection_id, unit_id)
) WITHOUT ROWID;
"""


class Conflict(ValueError):
    """A collection name already taken."""


def connect(path: Path) -> sqlite3.Connection:
    """Open (creating if needed) the labels file, with the notebook's tables."""
    conn = labels.connect(path)
    conn.executescript(SCHEMA)
    return conn


def entries(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every entry with the ids of its collections (`collections`), in no particular order."""
    member: dict[str, list[int]] = {}
    for cid, uid in conn.execute(
        "SELECT collection_id, unit_id FROM notebook_members ORDER BY collection_id"
    ):
        member.setdefault(uid, []).append(cid)
    return [
        {**dict(r), "collections": member.get(r["unit_id"], [])}
        for r in conn.execute("SELECT * FROM notebook_entries")
    ]


def collections(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every collection with its number of entries, by name."""
    cur = conn.execute(
        "SELECT c.*, COUNT(m.unit_id) AS n_entries FROM notebook_collections c"
        " LEFT JOIN notebook_members m ON m.collection_id = c.collection_id"
        " GROUP BY c.collection_id ORDER BY c.name COLLATE NOCASE, c.collection_id"
    )
    return [dict(r) for r in cur]


def entry(conn: sqlite3.Connection, unit_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM notebook_entries WHERE unit_id = ?", (unit_id,)).fetchone()
    if row is None:
        return None
    cids = [r[0] for r in conn.execute(
        "SELECT collection_id FROM notebook_members WHERE unit_id = ? ORDER BY collection_id",
        (unit_id,),
    )]  # fmt: skip
    return {**dict(row), "collections": cids}


def put_entry(conn: sqlite3.Connection, unit_id: str, note: str | None = None) -> dict[str, Any]:
    """Keep a unit (its note replaced when `note` is given; a new entry's note is empty)."""
    t = labels.now()
    with conn:
        conn.execute(
            "INSERT INTO notebook_entries VALUES (?, ?, ?, ?) ON CONFLICT (unit_id) DO UPDATE SET"
            " note = COALESCE(?, note), updated_at = excluded.updated_at",
            (unit_id, note or "", t, t, note),
        )
    out = entry(conn, unit_id)
    assert out is not None
    return out


def delete_entry(conn: sqlite3.Connection, unit_id: str) -> bool:
    """Remove an entry and take it out of every collection."""
    with conn:
        conn.execute("DELETE FROM notebook_members WHERE unit_id = ?", (unit_id,))
        cur = conn.execute("DELETE FROM notebook_entries WHERE unit_id = ?", (unit_id,))
    return cur.rowcount > 0


def collection(conn: sqlite3.Connection, collection_id: int) -> dict[str, Any] | None:
    return next((c for c in collections(conn) if c["collection_id"] == collection_id), None)


def create_collection(conn: sqlite3.Connection, name: str, description: str = "") -> dict[str, Any]:
    t = labels.now()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO notebook_collections (name, description, created_at, updated_at)"
                " VALUES (?, ?, ?, ?)",
                (name, description, t, t),
            )
    except sqlite3.IntegrityError as e:
        raise Conflict(name) from e
    out = collection(conn, int(cur.lastrowid or 0))
    assert out is not None
    return out


def update_collection(
    conn: sqlite3.Connection, collection_id: int, name: str, description: str
) -> dict[str, Any] | None:
    """Rename / describe a collection (None: no such collection)."""
    try:
        with conn:
            cur = conn.execute(
                "UPDATE notebook_collections SET name = ?, description = ?, updated_at = ?"
                " WHERE collection_id = ?",
                (name, description, labels.now(), collection_id),
            )
    except sqlite3.IntegrityError as e:
        raise Conflict(name) from e
    return collection(conn, collection_id) if cur.rowcount else None


def delete_collection(conn: sqlite3.Connection, collection_id: int) -> bool:
    """Remove a collection; its entries stay."""
    with conn:
        conn.execute("DELETE FROM notebook_members WHERE collection_id = ?", (collection_id,))
        cur = conn.execute(
            "DELETE FROM notebook_collections WHERE collection_id = ?", (collection_id,)
        )
    return cur.rowcount > 0


def add_member(conn: sqlite3.Connection, collection_id: int, unit_id: str) -> dict[str, Any]:
    """Put a unit in a collection, keeping it as an entry if it was not one."""
    put_entry(conn, unit_id)
    t = labels.now()
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO notebook_members VALUES (?, ?, ?)", (collection_id, unit_id, t)
        )
        conn.execute(
            "UPDATE notebook_collections SET updated_at = ? WHERE collection_id = ?",
            (t, collection_id),
        )
    out = entry(conn, unit_id)
    assert out is not None
    return out


def remove_member(conn: sqlite3.Connection, collection_id: int, unit_id: str) -> bool:
    """Take a unit out of a collection (the entry stays)."""
    with conn:
        cur = conn.execute(
            "DELETE FROM notebook_members WHERE collection_id = ? AND unit_id = ?",
            (collection_id, unit_id),
        )
    return cur.rowcount > 0
