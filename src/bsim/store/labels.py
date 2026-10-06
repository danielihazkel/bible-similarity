"""Your own judgements of proposed pairs (DESIGN.md §16.25): a small writable SQLite file.

`results.sqlite` is rebuilt by `bsim build-db` and opened read-only by the API; labels are the
one thing a person adds, so they live apart, at `paths.labels` (under `data/`, never committed).
A pair is undirected: it is stored once, `a_id` the unit that starts earlier in the canon.

    labels(unit_type, a_id, b_id, label, note, mode, score, labeled_at)

`label` is `real` (a connection worth recording), `not` (a coincidence of words or meaning) or
`unsure`. `mode` / `score` record where the pair was judged (the list that proposed it), so the
labels can later be read against the bias of what was shown.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LABELS = ("real", "not", "unsure")

SCHEMA = """
CREATE TABLE IF NOT EXISTS labels (
    unit_type TEXT NOT NULL,
    a_id TEXT NOT NULL,             -- the unit starting earlier in the canon
    b_id TEXT NOT NULL,
    label TEXT NOT NULL CHECK (label IN ('real', 'not', 'unsure')),
    note TEXT NOT NULL DEFAULT '',
    mode TEXT,                      -- the list the pair was judged in (lexical | semantic | ...)
    score REAL,                     -- its score there
    labeled_at TEXT NOT NULL,       -- ISO time of the last change
    PRIMARY KEY (a_id, b_id)
) WITHOUT ROWID;
"""

COLUMNS = ("unit_type", "a_id", "b_id", "label", "note", "mode", "score", "labeled_at")


def connect(path: Path) -> sqlite3.Connection:
    """Open (creating if needed) the labels file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


def put(
    conn: sqlite3.Connection,
    unit_type: str,
    a_id: str,
    b_id: str,
    label: str,
    note: str = "",
    mode: str | None = None,
    score: float | None = None,
) -> dict[str, Any]:
    """Insert or replace the label of the pair (a_id, b_id), already in canon order."""
    if label not in LABELS:
        raise ValueError(f"label must be one of {', '.join(LABELS)}")
    row = (unit_type, a_id, b_id, label, note, mode, score, now())
    with conn:
        conn.execute(f"INSERT OR REPLACE INTO labels VALUES ({', '.join('?' * len(COLUMNS))})", row)
    return dict(zip(COLUMNS, row, strict=True))


def delete(conn: sqlite3.Connection, a_id: str, b_id: str) -> bool:
    with conn:
        cur = conn.execute("DELETE FROM labels WHERE a_id = ? AND b_id = ?", (a_id, b_id))
    return cur.rowcount > 0


def all_labels(conn: sqlite3.Connection, unit_type: str | None = None) -> list[dict[str, Any]]:
    """Every label, most recent first."""
    sql = "SELECT * FROM labels"
    args: tuple[str, ...] = ()
    if unit_type is not None:
        sql, args = sql + " WHERE unit_type = ?", (unit_type,)
    return [dict(r) for r in conn.execute(sql + " ORDER BY labeled_at DESC, a_id, b_id", args)]


def read_labels(path: Path) -> list[dict[str, Any]]:
    """Every label of the file at `path` (none when it does not exist yet)."""
    if not path.exists():
        return []
    conn = connect(path)
    try:
        return all_labels(conn)
    finally:
        conn.close()


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
