"""`bsim sequences`: passages that run parallel verse by verse, in the same order (DESIGN.md §16.7).

A retold story, a synoptic parallel (Samuel–Kings ↔ Chronicles, II Sam 22 ↔ Ps 18) or a command
and its execution (Ex 25–31 ↔ 35–40) shows up as a *chain* of similar verse pairs (a, b),
(a+1, b+1), … with both sides advancing together. This is synteny detection over the verse lists:

- Candidates: unordered verse pairs (a < b) within either verse's final fused top
  `sequences.candidate_rank`, neighbours (`retrieval.neighbor_window`) dropped. A pair weighs
  `(R + 1 − rank) / R` (its better rank of the two directions), so rank 1 weighs 1.
- Chaining (dynamic programming over pairs sorted by a, b): a pair extends the best chain ending
  at a pair (a − da, b − db) with 1 ≤ da, db ≤ `max_step` in the same books, paying
  `gap` per skipped verse on either side; a chain restarts when its score would drop below 0.
  Chains are read off greedily from the best end pair, each pair used once; a chain is kept with
  at least `min_pairs` pairs, unless its two spans overlap (a tandem repeat inside one passage).
- Significance: a null that keeps every pair and its weight but shuffles verse order within each
  chapter (both ends of a pair), so topical overlap between two chapters survives and only their
  verse order is destroyed. Chains are rebuilt for `null_reps` shuffles; `q` = (null chains per
  replicate scoring ≥ s) / (observed chains scoring ≥ s), made monotone: the expected share of
  chance chains among those at least as strong (Benjamini–Hochberg style).

Writes `artifacts/sequences/verse.parquet`: `seq_id` (rank by score, 1-based), `a_start, a_end,
b_start, b_end` (verse ids), `a_book, b_book`, `same_chapter` (both starts in one chapter),
`n_pairs`, `score`, `q`, `pairs` (JSON `[[a, b, weight], …]`), plus `verse.meta.json`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.retrieve.filters import neighbor_mask
from bsim.retrieve.fusion import final_systems

Log = Callable[[str], None]


@dataclass(frozen=True)
class Chain:
    a: list[int]  # verse ids, increasing
    b: list[int]
    w: list[float]
    score: float


def candidate_pairs(
    topk: pd.DataFrame, book_id: np.ndarray, max_rank: int, window: int
) -> pd.DataFrame:
    """`a, b, w`: unordered verse pairs (a < b) within the top `max_rank`, neighbours dropped;
    `w = (max_rank + 1 − rank) / max_rank` of the better direction."""
    t = topk[topk["rank"] <= max_rank]
    src = t.src_id.str[2:].astype(np.int64).to_numpy()
    tgt = t.tgt_id.str[2:].astype(np.int64).to_numpy()
    w = (max_rank + 1 - t["rank"].to_numpy(dtype=np.float64)) / max_rank
    keep = ~neighbor_mask(src, tgt, book_id, window)
    df = pd.DataFrame(
        {"a": np.minimum(src, tgt)[keep], "b": np.maximum(src, tgt)[keep], "w": w[keep]}
    )
    return df.groupby(["a", "b"], as_index=False, sort=True).w.max()


def find_chains(
    a: np.ndarray,
    b: np.ndarray,
    w: np.ndarray,
    book_id: np.ndarray,
    max_step: int,
    gap: float,
    min_pairs: int,
    direction: str = "forward",
) -> list[Chain]:
    """Chains of verse pairs, strongest first (see the module docstring). `direction`:
    `forward` (both sides advance), `reverse` (a advances while b retreats: A B C … ↔ … C′ B′ A′)
    or `mixed` (b may step either way: the same scene retold in another order)."""
    order = np.lexsort((b, a))
    A, B, W = a[order].tolist(), b[order].tolist(), w[order].astype(np.float64).tolist()
    book = book_id.tolist()
    n_verses = len(book)
    steps_b = {"forward": (1,), "reverse": (-1,), "mixed": (1, -1)}[direction]
    at = {(x, y): i for i, (x, y) in enumerate(zip(A, B, strict=True))}
    score = list(W)
    prev = [-1] * len(A)
    for i, (x, y) in enumerate(zip(A, B, strict=True)):
        best, bp = 0.0, -1
        for da in range(1, max_step + 1):
            if x - da < 0 or book[x - da] != book[x]:
                break
            for sb in steps_b:
                for db in range(1, max_step + 1):
                    yb = y - sb * db
                    if not 0 <= yb < n_verses or book[yb] != book[y]:
                        break
                    j = at.get((x - da, yb))
                    if j is not None:
                        c = score[j] - gap * (da + db - 2)
                        if c > best:
                            best, bp = c, j
        score[i] += best
        prev[i] = bp

    used = [False] * len(A)
    chains = []
    for i in sorted(range(len(A)), key=lambda k: (-score[k], A[k], B[k])):
        if used[i]:
            continue
        path = []
        j = i
        while j != -1 and not used[j]:
            path.append(j)
            j = prev[j]
        path.reverse()
        for j in path:
            used[j] = True
        if len(path) < min_pairs:
            continue
        ca, cb, cw = [A[j] for j in path], [B[j] for j in path], [W[j] for j in path]
        if book[ca[0]] == book[cb[0]] and ca[-1] >= min(cb[0], cb[-1]):
            continue  # the two spans overlap: a tandem repeat (or a crossing)
        s = cw[0] + sum(
            cw[k] - gap * (ca[k] - ca[k - 1] + abs(cb[k] - cb[k - 1]) - 2)
            for k in range(1, len(path))
        )
        chains.append(Chain(ca, cb, cw, s))
    chains.sort(key=lambda c: (-c.score, c.a[0], c.b[0]))
    return chains


DIRECTIONS = ("forward", "reverse", "mixed")


def is_monotone(c: Chain) -> bool:
    steps = np.sign(np.diff(c.b))
    return bool(np.all(steps > 0) or np.all(steps < 0))


def all_chains(
    a: np.ndarray, b: np.ndarray, w: np.ndarray, book_id: np.ndarray, s: dict[str, Any]
) -> list[tuple[str, Chain]]:
    """Forward chains, then reverse ones, then mixed ones (`s["directions"]`), each kind found
    over all pairs; a later kind's chain is dropped when `s["max_overlap"]` or more of its pairs
    are in a chain already kept, and a mixed chain that is monotone (a forward or reverse chain
    by another name) is dropped."""
    kept: list[tuple[str, Chain]] = []
    used: set[tuple[int, int]] = set()
    for direction in s["directions"]:
        found = find_chains(
            a, b, w, book_id, s["max_step"], s["gap"], s["min_pairs"], direction=direction
        )
        if direction == "mixed":
            found = [c for c in found if not is_monotone(c)]
        new = []
        for c in found:
            pairs = list(zip(c.a, c.b, strict=True))
            if kept and sum(p in used for p in pairs) >= s["max_overlap"] * len(pairs):
                continue
            new.append((direction, c))
        for _, c in new:
            used.update(zip(c.a, c.b, strict=True))
        kept += new
    return kept


def shuffle_within(groups: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """A permutation of `range(len(groups))` that moves ids only within their group."""
    perm = np.arange(len(groups))
    order = np.argsort(groups, kind="stable")
    bounds = np.flatnonzero(np.diff(groups[order])) + 1
    for ids in np.split(order, bounds):
        perm[ids] = rng.permutation(ids)
    return perm


def q_values(observed: np.ndarray, null: np.ndarray, reps: int) -> np.ndarray:
    """Per observed score s: (null scores ≥ s / reps) / (observed scores ≥ s), capped at 1 and
    made monotone (a stronger chain never has a larger q)."""
    if len(observed) == 0:
        return np.zeros(0)
    obs_sorted = np.sort(observed)[::-1]
    null_sorted = np.sort(null)
    n_obs = np.arange(1, len(obs_sorted) + 1)
    n_null = len(null_sorted) - np.searchsorted(null_sorted, obs_sorted, side="left")
    q = np.minimum(1.0, n_null / reps / n_obs)
    q = np.minimum.accumulate(q[::-1])[::-1]
    # back to the input order (ties share the q of their last position)
    rank = len(observed) - np.searchsorted(np.sort(observed), observed, side="right")
    return q[rank]


def chain_frame(
    chains: list[tuple[str, Chain]], q: np.ndarray, book_id: np.ndarray, chapter: np.ndarray
) -> pd.DataFrame:
    """One row per chain; `seq_id` ranks forward chains first (ids stable when reverse / mixed
    chains are added), then reverse, then mixed, each by score."""
    rank = {d: i for i, d in enumerate(DIRECTIONS)}
    order = sorted(
        range(len(chains)),
        key=lambda k: (
            rank[chains[k][0]],
            -chains[k][1].score,
            chains[k][1].a[0],
            chains[k][1].b[0],
        ),
    )
    rows = []
    for seq_id, k in enumerate(order, start=1):
        direction, c = chains[k]
        qk = q[k]
        rows.append(
            {
                "seq_id": seq_id,
                "a_start": c.a[0],
                "a_end": c.a[-1],
                "b_start": min(c.b),
                "b_end": max(c.b),
                "direction": direction,
                "a_book": int(book_id[c.a[0]]),
                "b_book": int(book_id[c.b[0]]),
                "same_chapter": bool(
                    book_id[c.a[0]] == book_id[c.b[0]] and chapter[c.a[0]] == chapter[c.b[0]]
                ),
                "n_pairs": len(c.a),
                "score": round(c.score, 4),
                "q": float(qk),
                "pairs": json.dumps(
                    [[x, y, round(v, 4)] for x, y, v in zip(c.a, c.b, c.w, strict=True)]
                ),
            }
        )
    cols = ["seq_id", "a_start", "a_end", "b_start", "b_end", "direction", "a_book", "b_book"]
    cols.append("same_chapter")
    return pd.DataFrame(rows, columns=[*cols, "n_pairs", "score", "q", "pairs"])


def run_sequences(cfg: dict[str, Any], log: Log = print) -> Path:
    proc = resolve_path(cfg, "data_processed")
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter"])
    system = final_systems(cfg, "verse")["fused"]
    path = resolve_path(cfg, "artifacts") / "topk" / "verse" / f"{system}.parquet"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim fuse` first")
    t0 = time.perf_counter()
    s = cfg["sequences"]
    book, chapter = verses.book_id.to_numpy(), verses.chapter.to_numpy()
    pairs = candidate_pairs(
        pd.read_parquet(path, columns=["src_id", "tgt_id", "rank"]),
        book,
        s["candidate_rank"],
        cfg["retrieval"]["neighbor_window"],
    )
    a, b, w = pairs.a.to_numpy(), pairs.b.to_numpy(), pairs.w.to_numpy()
    log(f"chaining {len(pairs)} candidate pairs from {system} (top {s['candidate_rank']})")
    chains = all_chains(a, b, w, book, s)

    rng = np.random.default_rng(s["seed"])
    groups = book.astype(np.int64) * 1000 + chapter
    null: dict[str, list[float]] = {d: [] for d in s["directions"]}
    for r in range(s["null_reps"]):
        perm = shuffle_within(groups, rng)
        na, nb = perm[a], perm[b]
        for d, c in all_chains(np.minimum(na, nb), np.maximum(na, nb), w, book, s):
            null[d].append(c.score)
        log(f"  null {r + 1}/{s['null_reps']}: {sum(map(len, null.values()))} chance chains so far")
    q = np.zeros(len(chains))
    for d in s["directions"]:
        idx = [k for k, (dk, _) in enumerate(chains) if dk == d]
        scores = np.array([chains[k][1].score for k in idx])
        q[idx] = q_values(scores, np.array(null[d]), s["null_reps"])
    df = chain_frame(chains, q, book, chapter)

    out = resolve_path(cfg, "artifacts") / "sequences"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "verse.parquet")
    meta = {
        "config_hash": config_hash(cfg, "sequences", "retrieval", "fusion"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "system": system,
        "candidates": int(len(pairs)),
        "chains": int(len(df)),
        "null_chains_per_rep": {
            d: round(len(v) / max(1, s["null_reps"]), 1) for d, v in null.items()
        },
        "q_below_0.05": int((df.q < 0.05).sum()),
        "by_direction": {
            d: {
                "chains": int((df.direction == d).sum()),
                "q_below_0.05": int(((df.direction == d) & (df.q < 0.05)).sum()),
            }
            for d in s["directions"]
        },
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "verse.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(
        f"done: {len(df)} chains ({meta['q_below_0.05']} with q < 0.05) in {meta['seconds']} s"
        f" -> {out / 'verse.parquet'}"
    )
    return out / "verse.parquet"
