"""The label queue (`GET /labels/queue`, DESIGN.md §16.79, D132): pairs worth judging first.

Discoveries (strong fused pairs no gold links, §16.25) are labelled in the order a list shows
them, so the labels describe the top of that list. The queue asks instead where the two ways of
reading disagree: the fused verse discoveries ranked by `|lex_rank - sem_rank|`, each mode's best
rank of the pair in either direction, a rank beyond the component lists (`retrieval.k`) counted
as `k + 1`. A pair one mode puts first and the other does not list at all comes first; its
label says which of the two was right. Ties go to the stronger fused pair; pairs equal in
both take the two sides in turn (within a side, the stored tie-break, the semantic score where
there is one, decides). Without the turns the semantic side would fill the top: a pair only the
lexical list ranks has no semantic score, and its fused score equals its semantic twin's.

Only pairs between two **train-split** books are offered (the Sefaria split rule,
`data_processed/splits.json`), so whatever the queue gathers may train the semantic model
(`train.supervised.extra_pairs: [labels]`, `train/pairs.py`) while the dev and test labels, and
`bsim eval-labels`, stay as they were. Pairs already labelled (any label) are left out.

The pool (~79k pairs on the full build) is read once per results DB and kept in memory.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bsim.config import resolve_path
from bsim.data.canon import BY_SEFARIA

SIDES = ("all", "lexical", "semantic")


@dataclass(frozen=True)
class QueuePair:
    a_id: str
    b_id: str
    lex_rank: int | None  # best rank of the pair in either unit's lexical list (None: beyond k)
    sem_rank: int | None
    disagreement: int
    score: float  # the fused score
    tie: float

    @property
    def side(self) -> str:
        """The mode that ranks the pair higher (`both` when they agree)."""
        lex, sem = self.lex_rank or 10**9, self.sem_rank or 10**9
        return "lexical" if lex < sem else "semantic" if sem < lex else "both"


def train_books(cfg: dict[str, Any], split: str) -> set[int] | None:
    """The book ids of a split, from `splits.json` (None when the splits are not built)."""
    path = resolve_path(cfg, "data_processed") / "splits.json"
    if not path.exists():
        return None
    books = json.loads(path.read_text("utf-8"))["books"]
    return {BY_SEFARIA[b].book_id for b, s in books.items() if s == split}


def best(*ranks: int | None) -> int | None:
    known = [r for r in ranks if r is not None]
    return min(known) if known else None


def rank_queue(rows: list[tuple], missing: int) -> list[QueuePair]:
    """`(a_id, b_id, score, tie, lex_ab, sem_ab, lex_ba, sem_ba)` rows, most disagreement first."""
    pairs = []
    for a, b, score, tie, lab, sab, lba, sba in rows:
        lex, sem = best(lab, lba), best(sab, sba)
        gap = abs((lex or missing) - (sem or missing))
        pairs.append(QueuePair(a, b, lex, sem, gap, float(score), float(tie)))
    # each side in its own order; equal disagreement and fused score: the sides take turns
    by = lambda p: (-p.disagreement, -p.score, -p.tie, p.a_id, p.b_id)  # noqa: E731
    turn: dict[QueuePair, int] = {}
    for side in ("lexical", "semantic", "both"):
        group = sorted((p for p in pairs if p.side == side), key=by)
        for i, p in enumerate(group):
            prev = group[i - 1] if i else None
            same = prev is not None and (prev.disagreement, prev.score) == (p.disagreement, p.score)
            turn[p] = turn[prev] + 1 if same else 0
    order = {"lexical": 0, "semantic": 1, "both": 2}
    return sorted(
        pairs, key=lambda p: (-p.disagreement, -p.score, turn[p], order[p.side], *by(p)[2:])
    )


def pool_rows(conn: sqlite3.Connection, books: set[int]) -> list[tuple]:
    """The fused verse discoveries between two of `books`, with each direction's component
    ranks (the fused list's `lex_rank` / `sem_rank`)."""
    if not books:
        return []
    marks = ", ".join("?" * len(books))
    sql = (
        "SELECT d.a_id, d.b_id, d.score, d.tie, ab.lex_rank, ab.sem_rank, ba.lex_rank, ba.sem_rank"
        " FROM discoveries d"
        " LEFT JOIN matches ab ON ab.unit_type = d.unit_type AND ab.mode = d.mode"
        "  AND ab.src_id = d.a_id AND ab.tgt_id = d.b_id"
        " LEFT JOIN matches ba ON ba.unit_type = d.unit_type AND ba.mode = d.mode"
        "  AND ba.src_id = d.b_id AND ba.tgt_id = d.a_id"
        f" WHERE d.unit_type = 'verse' AND d.mode = 'fused'"
        f" AND d.a_book IN ({marks}) AND d.b_book IN ({marks})"
    )
    ids = sorted(books)
    return conn.execute(sql, (*ids, *ids)).fetchall()


_cache: dict[tuple, list[QueuePair]] = {}
_lock = threading.Lock()


def queue_for(conn: sqlite3.Connection, db: Path, books: set[int], missing: int) -> list[QueuePair]:
    """The ranked pool of the DB at `db`, built on first use (and again after a rebuild)."""
    key = (str(db.resolve()), db.stat().st_mtime_ns, frozenset(books), missing)
    with _lock:
        if key not in _cache:
            _cache.clear()
            _cache[key] = rank_queue(pool_rows(conn, books), missing)
        return _cache[key]


def unlabelled(pool: list[QueuePair], labelled: set[tuple[str, str]], side: str) -> list[QueuePair]:
    """The pool without labelled pairs, of one side (`all`: every pair)."""
    return [
        p for p in pool if (p.a_id, p.b_id) not in labelled and (side == "all" or p.side == side)
    ]
