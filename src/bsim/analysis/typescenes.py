"""`bsim typescenes`: recurring plot skeletons across passages (DESIGN.md §16.20).

A type-scene — the meeting at a well, the annunciation to a barren wife — retells the same
sequence of actions with other people, places and words. Verse similarity and shared phrases
look at wording; here only the order of the actions counts.

- Sequence: the verbs of each pericope (≤ `max_verses` verses) in order, as lemmas; verbs used in
  more than `max_df` of the pericopes (אמר, היה, …) are left out — they occur everywhere.
- Candidates: pericope pairs sharing verbs whose idf (over pericopes) sums to `min_shared_idf`,
  each pericope keeping its `max_partners` strongest; pairs in the same pericope span skipped.
- Alignment: Smith–Waterman over the two verb sequences, a match scoring its lemma's idf, a
  mismatch −`mismatch`, a gap −`gap`; the best local alignment with ≥ `min_matches` matches.
- Null: verb order shuffled inside every pericope (`null_reps` times), the same pairs aligned
  again: shared vocabulary is kept and only the order destroyed, so `q` (as for parallel
  sequences, §16.7) is the expected share of chance alignments among those at least as strong.
- `parallel_text`: a significant parallel sequence (§16.7) joins verses of the two pericopes —
  the same text told twice rather than a type-scene.

Writes `artifacts/typescenes/pairs.parquet` (`a_unit, b_unit, a_book, b_book, score,
n_matches, aligned` = JSON `[a_vid, b_vid, lemma]` per matched verb, `q`, `parallel_text`) plus
`typescenes.meta.json`.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.sequences import q_values
from bsim.config import config_hash, resolve_path

Log = Callable[[str], None]

Verb = tuple[int, str]  # (verse_id, lemma)


def verb_sequences(
    words: pd.DataFrame, units: pd.DataFrame, max_verses: int
) -> dict[str, list[Verb]]:
    """Pericope id -> its verbs in order (lemma of the verb morpheme)."""
    from bsim.store.db import lemma_parts_pos  # store.db imports the analysis modules

    by_verse: dict[int, list[str]] = defaultdict(list)
    w = words.sort_values(["verse_id", "idx"], kind="stable")
    for vid, lemma, morph in zip(w.verse_id, w.lemma, w.morph, strict=True):
        for lem, pos in lemma_parts_pos(lemma, morph).items():
            if pos == "V":
                by_verse[int(vid)].append(lem)
    out = {}
    for u in units.itertuples(index=False):
        if u.n_verses <= max_verses:
            out[u.unit_id] = [
                (v, lem) for v in range(u.start_verse_id, u.end_verse_id + 1) for lem in by_verse[v]
            ]
    return out


def smith_waterman(
    a: list[str], b: list[str], idf: dict[str, float], mismatch: float, gap: float
) -> tuple[float, list[tuple[int, int]]]:
    """Best local alignment score and its matched positions (i in a, j in b)."""
    n, m = len(a), len(b)
    if not n or not m:
        return 0.0, []
    # plain lists: indexing numpy scalars in this double loop is several times slower
    h = [[0.0] * (m + 1) for _ in range(n + 1)]
    best, at = 0.0, (0, 0)
    for i in range(1, n + 1):
        ai, w, hp, hc = a[i - 1], idf.get(a[i - 1], 0.0), h[i - 1], h[i]
        for j in range(1, m + 1):
            v = hp[j - 1] + (w if ai == b[j - 1] else -mismatch)
            up, left = hp[j] - gap, hc[j - 1] - gap
            if up > v:
                v = up
            if left > v:
                v = left
            if v > 0.0:
                hc[j] = v
                if v > best:
                    best, at = v, (i, j)
    path = []
    i, j = at
    while i > 0 and j > 0 and h[i][j] > 0:
        match = a[i - 1] == b[j - 1]
        s = idf.get(a[i - 1], 0.0) if match else -mismatch
        if abs(h[i][j] - (h[i - 1][j - 1] + s)) < 1e-9:
            if match:
                path.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif abs(h[i][j] - (h[i - 1][j] - gap)) < 1e-9:
            i -= 1
        else:
            j -= 1
    return float(best), path[::-1]


def candidates(
    seqs: dict[str, list[str]], idf: dict[str, float], min_shared: float, max_partners: int
) -> list[tuple[str, str]]:
    """Unit pairs sharing enough rare verbs; each unit keeps its strongest partners."""
    index: dict[str, list[str]] = defaultdict(list)
    for u, s in seqs.items():
        for lem in set(s):
            index[lem].append(u)
    shared: dict[str, Counter[str]] = defaultdict(Counter)
    for lem, us in index.items():
        for x in us:
            for y in us:
                if x < y:
                    shared[x][y] += idf[lem]
    best: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for x, ys in shared.items():
        for y, w in ys.items():
            if w >= min_shared:
                best[x].append((w, y))
                best[y].append((w, x))
    keep = set()
    for x, lst in best.items():
        for _, y in sorted(lst, reverse=True)[:max_partners]:
            keep.add((min(x, y), max(x, y)))
    return sorted(keep)


def run_typescenes(cfg: dict[str, Any], log: Log = print) -> Path:
    tc = cfg["typescenes"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    seq_path = art / "sequences" / "verse.parquet"
    if not seq_path.exists():
        raise RuntimeError(f"{seq_path} missing; run `bsim sequences` first")
    t0 = time.perf_counter()
    units = pd.read_parquet(proc / "units.parquet")
    units = units[units.unit_type == tc["unit_type"]].sort_values("start_verse_id")
    words = pd.read_parquet(proc / "words.parquet", columns=["verse_id", "idx", "lemma", "morph"])
    verbs = verb_sequences(words, units, tc["max_verses"])
    df = Counter(lem for s in verbs.values() for lem in {lem for _, lem in s})
    n_units = len(verbs)
    common = {lem for lem, d in df.items() if d / n_units > tc["max_df"]}
    idf = {lem: math.log(n_units / d) for lem, d in df.items()}
    verbs = {u: [(v, lem) for v, lem in s if lem not in common] for u, s in verbs.items()}
    verbs = {u: s for u, s in verbs.items() if len(s) >= tc["min_matches"]}
    lemmas = {u: [lem for _, lem in s] for u, s in verbs.items()}
    pairs = candidates(lemmas, idf, tc["min_shared_idf"], tc["max_partners"])
    log(
        f"{len(verbs)} pericopes, {len(common)} common verbs left out, {len(pairs)} candidate pairs"
    )

    def align(seqs: dict[str, list[str]]) -> list[tuple[float, list[tuple[int, int]]]]:
        return [smith_waterman(seqs[a], seqs[b], idf, tc["mismatch"], tc["gap"]) for a, b in pairs]

    found = align(lemmas)
    rng = np.random.default_rng(tc["seed"])
    null: list[float] = []
    for r in range(tc["null_reps"]):
        shuffled = {u: list(rng.permutation(s)) for u, s in lemmas.items()}
        null += [sc for sc, path in align(shuffled) if len(path) >= tc["min_matches"]]
        log(f"  null {r + 1}/{tc['null_reps']}")

    book = dict(zip(units.unit_id, units.book_id.astype(int), strict=True))
    span = {u.unit_id: (u.start_verse_id, u.end_verse_id) for u in units.itertuples(index=False)}
    seqs = pd.read_parquet(seq_path)
    strong = seqs[seqs.q <= 0.05]
    linked = {(int(a), int(b)) for p in strong.pairs for a, b, *_ in json.loads(p)}

    rows = []
    for (a, b), (score, path) in zip(pairs, found, strict=True):
        if len(path) < tc["min_matches"]:
            continue
        aligned = [[verbs[a][i][0], verbs[b][j][0], verbs[a][i][1]] for i, j in path]
        (a0, a1), (b0, b1) = span[a], span[b]
        textual = any(
            (x, y) in linked or (y, x) in linked
            for x in range(a0, a1 + 1)
            for y in range(b0, b1 + 1)
            if abs(x - y) > 0
        )
        rows.append(
            (a, b, book[a], book[b], round(score, 3), len(path), json.dumps(aligned), textual)
        )
    out_df = pd.DataFrame(
        rows,
        columns=[
            "a_unit",
            "b_unit",
            "a_book",
            "b_book",
            "score",
            "n_matches",
            "aligned",
            "parallel_text",
        ],
    )
    out_df["q"] = q_values(out_df.score.to_numpy(), np.array(null), tc["null_reps"])
    out_df = out_df.sort_values(["q", "score"], ascending=[True, False], ignore_index=True)

    out = art / "typescenes"
    out.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(out / "pairs.parquet")
    meta = {
        "config_hash": config_hash(cfg, "typescenes"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "pericopes": len(verbs),
        "common_verbs": sorted(common),
        "candidates": len(pairs),
        "pairs": int(len(out_df)),
        "q_below_0.05": int((out_df.q <= 0.05).sum()),
        "q_below_0.05_not_textual": int(((out_df.q <= 0.05) & ~out_df.parallel_text).sum()),
        "null_per_rep": round(len(null) / max(1, tc["null_reps"]), 1),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "typescenes.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(
        f"done: {meta['q_below_0.05']} alignments with q <= 0.05"
        f" ({meta['q_below_0.05_not_textual']} not textual parallels) in {meta['seconds']} s"
    )
    return out / "pairs.parquet"
