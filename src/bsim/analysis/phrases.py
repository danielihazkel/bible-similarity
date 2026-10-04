"""`bsim phrases`: shared phrases between verses by local alignment (DESIGN.md §16).

For every candidate pair (the final lexical verse lists, top `phrases.candidate_rank`, verse
neighbours dropped) the two content-lemma streams are aligned with Smith-Waterman: a matching
token scores its weight `idf · formula weight` (rare words count, formula words barely), a
mismatch costs `mismatch` and a gap `gap`. The best local alignment is a shared phrase when it has
at least `min_tokens` matching tokens and a score of at least `min_score`. Shared vocabulary in a
different order does not align, which separates quotations and fixed phrases from mere topic
overlap.

Writes `artifacts/phrases/verse.parquet`: `a, b` (verse ids, a < b), `score`, `n_tokens`,
`a_words`, `b_words` (`words.idx` of the matched tokens, JSON lists), `spread` (verses sharing the
exact matched lemma sequence), plus `verse.meta.json`.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.lexical.formulas import formula_weights, frequent_ngrams
from bsim.lexical.tokens import Stream, lemma_streams
from bsim.retrieve.filters import neighbor_mask
from bsim.retrieve.fusion import final_systems

Log = Callable[[str], None]


@dataclass(frozen=True)
class Alignment:
    score: float
    a_pos: list[int]  # matched token positions in stream a
    b_pos: list[int]


def align(
    a: Sequence[str],
    b: Sequence[str],
    wa: Sequence[float],
    wb: Sequence[float],
    mismatch: float,
    gap: float,
) -> Alignment:
    """Smith-Waterman local alignment; a match scores the smaller of the two token weights.

    Ties prefer the earliest-ending alignment; the traceback prefers diagonal moves.
    """
    n, m = len(a), len(b)
    if not n or not m:
        return Alignment(0.0, [], [])
    h = [[0.0] * (m + 1) for _ in range(n + 1)]
    best, bi, bj = 0.0, 0, 0
    for i in range(1, n + 1):
        ai, wai, row, prev = a[i - 1], wa[i - 1], h[i], h[i - 1]
        for j in range(1, m + 1):
            diag = prev[j - 1] + (min(wai, wb[j - 1]) if ai == b[j - 1] else -mismatch)
            v = max(0.0, diag, prev[j] - gap, row[j - 1] - gap)
            row[j] = v
            if v > best:
                best, bi, bj = v, i, j
    a_pos, b_pos = [], []
    i, j = bi, bj
    while i > 0 and j > 0 and h[i][j] > 0:
        match = a[i - 1] == b[j - 1]
        step = min(wa[i - 1], wb[j - 1]) if match else -mismatch
        if math.isclose(h[i][j], h[i - 1][j - 1] + step):
            if match:
                a_pos.append(i - 1)
                b_pos.append(j - 1)
            i, j = i - 1, j - 1
        elif math.isclose(h[i][j], h[i - 1][j] - gap):
            i -= 1
        else:
            j -= 1
    return Alignment(best, a_pos[::-1], b_pos[::-1])


def token_weights(streams: list[Stream], formulas: dict[str, Any]) -> list[np.ndarray]:
    """Per stream token: `log(N / df)` (df = verses containing the lemma) x formula weight."""
    df = Counter(t for s in streams for t in set(s.tokens))
    n = len(streams)
    ngrams = frequent_ngrams(streams, formulas["min_n"], formulas["max_n"], formulas["min_verses"])
    fw = formula_weights(streams, ngrams, formulas["weight"])
    return [
        np.array([math.log(n / df[t]) for t in s.tokens], dtype=np.float64) * w
        for s, w in zip(streams, fw, strict=True)
    ]


def candidate_pairs(
    topk: pd.DataFrame, book_id: np.ndarray, max_rank: int, window: int
) -> np.ndarray:
    """Unordered (a, b) verse pairs, a < b, from a verse top-k list; neighbours dropped."""
    t = topk[topk["rank"] <= max_rank]
    src = t.src_id.str[2:].astype(np.int64).to_numpy()
    tgt = t.tgt_id.str[2:].astype(np.int64).to_numpy()
    keep = ~neighbor_mask(src, tgt, book_id, window)
    pairs = np.stack([np.minimum(src, tgt), np.maximum(src, tgt)], axis=1)[keep]
    return np.unique(pairs, axis=0)


def find_phrases(
    streams: list[Stream],
    weights: list[np.ndarray],
    pairs: np.ndarray,
    cfg: dict[str, Any],
) -> pd.DataFrame:
    p = cfg["phrases"]
    rows = []
    toks = [s.tokens for s in streams]
    wts = [w.tolist() for w in weights]
    for a, b in pairs.tolist():
        al = align(toks[a], toks[b], wts[a], wts[b], p["mismatch"], p["gap"])
        if len(al.a_pos) < p["min_tokens"] or al.score < p["min_score"]:
            continue
        wa = sorted({streams[a].word_idx[i] for i in al.a_pos})
        wb = sorted({streams[b].word_idx[j] for j in al.b_pos})
        key = " ".join(toks[a][i] for i in al.a_pos)
        rows.append((a, b, al.score, len(al.a_pos), json.dumps(wa), json.dumps(wb), key))
    cols = ["a", "b", "score", "n_tokens", "a_words", "b_words"]
    df = pd.DataFrame(rows, columns=[*cols, "key"])
    # spread: verses sharing this exact matched lemma sequence (2 = a unique pair; an idiom used
    # in many verses forms a clique of pairs)
    ends = pd.concat(
        [
            df[["key", "a"]].set_axis(["key", "v"], axis=1),
            df[["key", "b"]].set_axis(["key", "v"], axis=1),
        ]
    )
    df["spread"] = df.key.map(ends.drop_duplicates().key.value_counts()).astype("int64")
    df = df.drop(columns="key")
    return df.sort_values(["score", "a", "b"], ascending=[False, True, True], ignore_index=True)


def run_phrases(cfg: dict[str, Any], log: Log = print) -> Path:
    proc = resolve_path(cfg, "data_processed")
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id"])
    words = pd.read_parquet(proc / "words.parquet", columns=["verse_id", "idx", "content_lemmas"])
    system = final_systems(cfg, "verse")["lexical"]
    path = resolve_path(cfg, "artifacts") / "topk" / "verse" / f"{system}.parquet"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim topk --system {system}` first")
    t0 = time.perf_counter()
    streams = lemma_streams(words, len(verses))
    weights = token_weights(streams, cfg["lexical"]["formulas"])
    p = cfg["phrases"]
    pairs = candidate_pairs(
        pd.read_parquet(path, columns=["src_id", "tgt_id", "rank"]),
        verses.book_id.to_numpy(),
        p["candidate_rank"],
        cfg["retrieval"]["neighbor_window"],
    )
    log(f"aligning {len(pairs)} candidate pairs from {system} (top {p['candidate_rank']})")
    df = find_phrases(streams, weights, pairs, cfg)
    out = resolve_path(cfg, "artifacts") / "phrases"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "verse.parquet")
    meta = {
        "config_hash": config_hash(cfg, "phrases", "lexical", "retrieval"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "system": system,
        "candidates": int(len(pairs)),
        "phrases": int(len(df)),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "verse.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(f"done: {len(df)} shared phrases in {meta['seconds']} s -> {out / 'verse.parquet'}")
    return out / "verse.parquet"
