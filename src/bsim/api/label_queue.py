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

The pool (~79k pairs on the full build) is read once per results DB and kept in memory
(about 2 s).
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
    ranks (the fused list's `lex_rank` / `sem_rank`).

    The ranks come from one scan of the fused verse rows in key order, each probing the pairs
    wanted (an automatic index), all inside SQLite: a lookup per pair took 48 s with the DB cold
    in the OS cache, and a scan joined in Python 62 s while the server's startup threads ran."""
    if not books:
        return []
    marks = ", ".join("?" * len(books))
    ids = sorted(books)
    where = (
        f"unit_type = 'verse' AND mode = 'fused' AND a_book IN ({marks}) AND b_book IN ({marks})"
    )
    pairs = conn.execute(
        f"SELECT a_id, b_id, score, tie FROM discoveries WHERE {where}", (*ids, *ids)
    ).fetchall()
    ranks = {
        (s, t): (lex, sem)
        for s, t, lex, sem in conn.execute(
            f"WITH d AS MATERIALIZED (SELECT a_id, b_id FROM discoveries WHERE {where}),"
            " w(s, t) AS MATERIALIZED (SELECT a_id, b_id FROM d UNION ALL SELECT b_id, a_id FROM d)"
            " SELECT m.src_id, m.tgt_id, m.lex_rank, m.sem_rank"
            " FROM matches m CROSS JOIN w ON w.s = m.src_id AND w.t = m.tgt_id"
            " WHERE m.unit_type = 'verse' AND m.mode = 'fused'",
            (*ids, *ids),
        )
    }
    none = (None, None)
    return [
        (a, b, score, tie, *ranks.get((a, b), none), *ranks.get((b, a), none))
        for a, b, score, tie in pairs
    ]


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


_triage: dict[tuple, tuple[dict[str, Any] | None, dict[tuple[str, str], dict[str, Any]]]] = {}


def suggestions(
    cfg: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[tuple[str, str], dict[str, Any]]]:
    """`bsim llm-triage`'s last run (§16.81): its meta and pair -> suggestion (the answers that
    could be read), read again when the files change; (None, {}) when it never ran."""
    out = resolve_path(cfg, "artifacts") / "llm"
    files = [out / "llm_triage.meta.json", out / "triage.parquet"]
    if not all(f.exists() for f in files):
        return None, {}
    key = tuple(f.stat().st_mtime_ns for f in files)
    with _lock:
        if key not in _triage:
            import pandas as pd

            meta = json.loads(files[0].read_text("utf-8"))
            df = pd.read_parquet(files[1])
            df = df[df.status == "ok"]
            from bsim.eval.llm_triage import clean_rationale

            rows = {
                (a, b): {
                    "verdict": v,
                    "p_real": float(p),
                    "kind": k,
                    "rationale": clean_rationale(r),
                }
                for a, b, v, p, k, r in zip(
                    df.a_id, df.b_id, df.verdict, df.p_real, df.kind, df.rationale, strict=True
                )
            }
            _triage.clear()
            _triage[key] = (meta, rows)
        return _triage[key]


def preload(cfg: dict[str, Any], db: Path, connect: Any) -> None:
    """Build the pool in the background when the server starts (`labels.queue.preload`): read
    while the other startup threads read the DB, a first build takes up to a minute. Any failure
    (no split, an older DB) is left for the request to report."""
    try:
        books = train_books(cfg, cfg["labels"]["queue"]["split"])
        if books is None:
            return
        conn = connect()
        try:
            queue_for(conn, db, books, cfg["retrieval"]["k"] + 1)
        finally:
            conn.close()
    except (sqlite3.Error, OSError, KeyError):
        return


def unlabelled(pool: list[QueuePair], labelled: set[tuple[str, str]], side: str) -> list[QueuePair]:
    """The pool without labelled pairs, of one side (`all`: every pair)."""
    return [
        p for p in pool if (p.a_id, p.b_id) not in labelled and (side == "all" or p.side == side)
    ]
