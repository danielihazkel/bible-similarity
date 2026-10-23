"""`bsim brackets`: resumptive repetition (Wiederaufnahme): a clause repeated after an insertion
(DESIGN.md §16.67).

An editor who inserts a block into a story often returns to it by repeating the clause before the
insertion: Joseph is sold to Potiphar at Gen 37:36, Judah and Tamar follow, and 39:1 tells the sale
again. Does a clause repeated a few verses later mark a block that interrupts its surroundings?

- **Repetitions.** Every pair of verses of one book `min_gap`..`max_gap` verses apart whose content
  words align (Smith-Waterman as `bsim phrases`: a match scores idf x formula weight) with at least
  `min_tokens` tokens and `min_score`; a token matches another by its lemma or by its form without
  prefixes, so a Hebrew clause retold in Aramaic still aligns. With `mutual`, a verse and its
  repeat are each other's best partner.
- **Bracket score.** The `window` verses before the first verse (*before*) and after the repeat
  (*after*), the two frame verses left out, against the block between: the cosine of before and
  after, less the cosine of the block and before + after. High when the text on the two sides
  belongs together and the block does not. Lexical (idf-weighted lemma counts, randomly projected
  to `lex_dims` so windows are prefix differences) and semantic (the final system's verse
  embeddings), averaged.
- **Claim fixed in advance.** The mean bracket score of the repetitions exceeds the mean of random
  brackets of the same span in the same book (`draws` sets), one-sided at `alpha`. Each repetition
  against its own draws gives p, BH q over the repetitions.
- **Known answers.** The brackets of `known` are found (a pair with its first verse in `a` and its
  repeat in `b`) and each beats its random brackets at `alpha`.

Writes `artifacts/brackets/brackets.parquet` (`bracket, book_id, a, b` (verse ids), `n_between`
(verses between), `score, n_tokens, a_words, b_words` (`words.idx`, JSON), `a_disp, b_disp`
(display tokens, JSON), `lex, sem, insertion, p, q, known`) and `brackets.meta.json`.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse

from bsim.analysis.phrases import align, token_weights
from bsim.analysis.segments import lemma_matrix
from bsim.analysis.stats import bh_q, empirical_p
from bsim.config import config_hash, resolve_path
from bsim.data.refs import RefIndex
from bsim.lexical.tokens import Stream, lemma_streams
from bsim.store.lexicon import strip_prefixes
from bsim.text.normalize import fold_finals

Log = Callable[[str], None]


class Tok:
    """A content token that matches another by its lemma or by its form without prefixes."""

    __slots__ = ("form", "lemma")

    def __init__(self, lemma: str, form: str) -> None:
        self.lemma, self.form = lemma, form

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Tok) and (self.lemma == other.lemma or self.form == other.form)

    __hash__ = None  # type: ignore[assignment]

    def __repr__(self) -> str:
        return f"Tok({self.lemma!r}, {self.form!r})"


def token_forms(words: pd.DataFrame, streams: list[Stream]) -> list[list[str]]:
    """Each stream token's word form: consonants without prefixes, finals folded."""
    form = {
        (int(v), int(i)): fold_finals(strip_prefixes(s, str(lem)))
        for v, i, s, lem in zip(words.verse_id, words.idx, words.surface, words.lemma, strict=True)
    }
    return [[form[(v, i)] for i in s.word_idx] for v, s in enumerate(streams)]


def count_matrix(keys: list[list[str]]) -> sparse.csr_matrix:
    """Verses x keys, counts."""
    vid = [v for v, ks in enumerate(keys) for _ in ks]
    codes, _ = pd.factorize(pd.Series([k for ks in keys for k in ks], dtype=object))
    x = sparse.csr_matrix(
        (np.ones(len(vid)), (vid, codes)), shape=(len(keys), max(1, codes.max(initial=-1) + 1))
    )
    x.sum_duplicates()
    return x


def candidates(
    lem: sparse.csr_matrix, form: sparse.csr_matrix, book: np.ndarray, lo: int, hi: int, need: int
) -> np.ndarray:
    """(a, b) pairs of one book, lo <= b - a <= hi, sharing at least `need` tokens by lemma or by
    form (counted with their multiplicity; an upper bound of what can align)."""
    out = []
    n = lem.shape[0]
    for d in range(lo, hi + 1):
        if d >= n:
            break
        shared = np.asarray(lem[:-d].minimum(lem[d:]).sum(axis=1)).ravel()
        shared += np.asarray(form[:-d].minimum(form[d:]).sum(axis=1)).ravel()
        a = np.flatnonzero((shared >= need) & (book[:-d] == book[d:]))
        out.append(np.stack([a, a + d], axis=1))
    return np.concatenate(out) if out else np.zeros((0, 2), dtype=int)


def mutual_best(pairs: pd.DataFrame) -> pd.DataFrame:
    """Pairs whose two verses are each other's best-scoring partner."""
    ends = pd.concat([pairs[["a", "score"]].rename(columns={"a": "v"}),
                      pairs[["b", "score"]].rename(columns={"b": "v"})])  # fmt: skip
    best = ends.groupby("v").score.max()
    keep = (pairs.score >= pairs.a.map(best)) & (pairs.score >= pairs.b.map(best))
    return pairs[keep]


def window_sums(prefix: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """Sum of rows lo..hi-1 from a prefix-sum matrix (row k = sum of rows < k)."""
    return prefix[hi] - prefix[lo]


def _cos(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    dot = np.einsum("ij,ij->i", x, y)
    den = np.linalg.norm(x, axis=1) * np.linalg.norm(y, axis=1)
    return np.divide(dot, den, out=np.zeros_like(dot), where=den > 0)


def insertion(prefix: np.ndarray, a: np.ndarray, b: np.ndarray, w: int) -> np.ndarray:
    """cos(before, after) - cos(block, before + after) for brackets (a, b) with `w` verses each
    side (the frame verses a and b left out)."""
    before = window_sums(prefix, a - w, a)
    after = window_sums(prefix, b + 1, b + 1 + w)
    block = window_sums(prefix, a + 1, b)
    return _cos(before, after) - _cos(block, before + after)


def prefix_sums(m: np.ndarray) -> np.ndarray:
    return np.concatenate([np.zeros((1, m.shape[1])), np.cumsum(m, axis=0)])


def score_brackets(
    prefixes: list[np.ndarray], a: np.ndarray, b: np.ndarray, w: int
) -> tuple[np.ndarray, ...]:
    """Each modality's bracket score, and their mean."""
    parts = [insertion(p, a, b, w) for p in prefixes]
    return (*parts, np.mean(parts, axis=0))


def run_brackets(cfg: dict[str, Any], log: Log = print) -> Path:
    from bsim.analysis.structure import embeddings_path

    bc, pc = cfg["brackets"], cfg["phrases"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    t0 = time.perf_counter()
    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "verse"]
    ).sort_values("verse_id")
    words = pd.read_parquet(
        proc / "words.parquet",
        columns=["verse_id", "idx", "surface", "lemma", "content_lemmas", "display_idx"],
    )
    n = len(verses)
    book = verses.book_id.to_numpy()
    w, alpha = int(bc["window"]), float(bc["alpha"])

    # repetitions
    streams = lemma_streams(words, n)
    weights = token_weights(streams, cfg["lexical"]["formulas"])
    forms = token_forms(words, streams)
    cand = candidates(
        count_matrix([s.tokens for s in streams]), count_matrix(forms), book,
        int(bc["min_gap"]), int(bc["max_gap"]), int(bc["min_tokens"]),
    )  # fmt: skip
    log(f"aligning {len(cand)} verse pairs {bc['min_gap']}–{bc['max_gap']} verses apart")
    toks = [
        [Tok(t, f) for t, f in zip(s.tokens, fs, strict=True)]
        for s, fs in zip(streams, forms, strict=True)
    ]
    wts = [x.tolist() for x in weights]
    rows = []
    for a, b in cand.tolist():
        al = align(toks[a], toks[b], wts[a], wts[b], pc["mismatch"], pc["gap"])
        if len(al.a_pos) >= bc["min_tokens"] and al.score >= bc["min_score"]:
            rows.append((a, b, al.score, len(al.a_pos),
                         sorted({streams[a].word_idx[i] for i in al.a_pos}),
                         sorted({streams[b].word_idx[j] for j in al.b_pos})))  # fmt: skip
    pairs = pd.DataFrame(rows, columns=["a", "b", "score", "n_tokens", "a_words", "b_words"])
    log(f"{len(pairs)} repetitions")
    if bc["mutual"] and len(pairs):
        pairs = mutual_best(pairs)
    # the windows must lie inside the book
    first = verses.groupby("book_id").verse_id.min()
    last = verses.groupby("book_id").verse_id.max()
    bk = book[pairs.a.to_numpy()] if len(pairs) else np.zeros(0, dtype=int)
    inside = (pairs.a.to_numpy() - w >= first.reindex(bk).to_numpy()) & (
        pairs.b.to_numpy() + w <= last.reindex(bk).to_numpy()
    )
    pairs = pairs[inside].sort_values(["a", "b"]).reset_index(drop=True)
    log(f"{len(pairs)} after mutual best and room for the windows")

    # bracket scores: lexical (projected) and semantic
    rng = np.random.default_rng(bc["seed"])
    lem = lemma_matrix(words, n)
    proj = rng.standard_normal((lem.shape[1], int(bc["lex_dims"]))) / math.sqrt(bc["lex_dims"])
    lex = np.asarray(lem @ proj)
    sem = np.load(embeddings_path(cfg)).astype(np.float64)
    prefixes = [prefix_sums(lex), prefix_sums(sem)]
    a, b = pairs.a.to_numpy(), pairs.b.to_numpy()
    s_lex, s_sem, s_all = score_brackets(prefixes, a, b, w) if len(pairs) else (np.zeros(0),) * 3

    # random brackets of the same span in the same book
    reps = int(bc["draws"])
    m = len(pairs)
    null = np.zeros((reps, m))
    if m:
        span = b - a
        lo = first.reindex(book[a]).to_numpy() + w  # the first verse can be lo..hi
        hi = last.reindex(book[a]).to_numpy() - w - span
        for r in range(reps):
            ra = lo + np.floor(rng.random(m) * (hi - lo + 1)).astype(int)
            null[r] = score_brackets(prefixes, ra, ra + span, w)[2]
    p_each = np.array([empirical_p(s_all[i] - 1e-12, null[:, i]) for i in range(m)])
    q = bh_q(p_each)
    obs = float(s_all.mean()) if m else float("nan")
    null_means = null.mean(axis=1) if m else np.zeros(0)
    p = empirical_p(obs - 1e-12, null_means) if m else 1.0
    holds = bool(m and obs > null_means.mean() and p <= alpha)
    log(f"mean bracket score {obs:.4f}, random brackets {null_means.mean():.4f}, p {p:.4g}")

    # the known brackets
    index = RefIndex(verses)
    known_rows, known_of = [], set()
    for kn in bc["known"]:
        (a1, a2), (b1, b2) = index.resolve(kn["a"]), index.resolve(kn["b"])
        hit = pairs[(pairs.a >= a1) & (pairs.a <= a2) & (pairs.b >= b1) & (pairs.b <= b2)]
        row: dict[str, Any] = {"a": kn["a"], "b": kn["b"], "found": not hit.empty,
                               "bracket": None, "insertion": None, "p": None,
                               "beats": False}  # fmt: skip
        if not hit.empty:
            i = int(hit.score.idxmax())
            known_of.add(i)
            row.update(bracket=i, insertion=float(s_all[i]), p=float(p_each[i]),
                       beats=bool(p_each[i] <= alpha))  # fmt: skip
        known_rows.append(row)
    known_holds = bool(known_rows) and all(r["found"] and r["beats"] for r in known_rows)
    log(f"known: {sum(r['found'] for r in known_rows)} of {len(known_rows)} found,"
        f" {sum(r['beats'] for r in known_rows)} beat their random brackets")  # fmt: skip

    disp = {
        (int(v), int(i)): int(d)
        for v, i, d in zip(words.verse_id, words.idx, words.display_idx, strict=True)
        if not pd.isna(d)
    }

    def tokens(v: int, idx: list[int]) -> str:
        return json.dumps(sorted({disp[(v, i)] for i in idx if (v, i) in disp}))

    df = pd.DataFrame(
        {
            "bracket": np.arange(m, dtype=int),
            "book_id": book[a] if m else np.zeros(0, dtype=int),
            "a": a,
            "b": b,
            "n_between": b - a - 1,
            "score": pairs.score.round(3).to_numpy(),
            "n_tokens": pairs.n_tokens.to_numpy(),
            "a_words": [json.dumps(x) for x in pairs.a_words],
            "b_words": [json.dumps(x) for x in pairs.b_words],
            "a_disp": [tokens(v, x) for v, x in zip(a, pairs.a_words, strict=True)],
            "b_disp": [tokens(v, x) for v, x in zip(b, pairs.b_words, strict=True)],
            "lex": s_lex.round(4),
            "sem": s_sem.round(4),
            "insertion": s_all.round(4),
            "p": p_each,
            "q": q,
            "known": [i in known_of for i in range(m)],
        }
    )
    out = art / "brackets"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "brackets.parquet", index=False)
    meta = {
        "config_hash": config_hash(cfg, "brackets", "phrases", "lexical", "final_systems"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "candidates": int(len(cand)),
        "repetitions": int(len(rows)),
        "brackets": m,
        "books": dict(Counter(int(x) for x in df.book_id)),
        "mean": round(obs, 4) if m else None,
        "mean_null": round(float(null_means.mean()), 4) if m else None,
        "p": p,
        "draws": reps,
        "window": w,
        "alpha": alpha,
        "holds": holds,
        "leads": int((df.q <= alpha).sum()),
        "known": known_rows,
        "known_found": sum(r["found"] for r in known_rows),
        "known_beat": sum(r["beats"] for r in known_rows),
        "known_holds": known_holds,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "brackets.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
    log(
        f"done: {m} brackets; the claim {'holds' if holds else 'is not borne out'},"
        f" {meta['leads']} at q ≤ {alpha}; the known {'hold' if known_holds else 'fail'}"
        f" ({meta['seconds']} s) -> {out}"
    )
    return out / "brackets.parquet"
