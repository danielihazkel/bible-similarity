"""`bsim seams`: where the style of a book changes (DESIGN.md §16.12).

The stylometry features (§16.6: most frequent lemmas + morphology rates, Aramaic included) are
counted per verse. At every verse boundary of a book, the `block_words` words before it and the
`block_words` words after it (whole verses, inside the book) are compared with Burrows' Delta:
the mean over features of |rate_before − rate_after| / sd, where sd is the spread of the feature
across chapters of the corpus (chapters with ≥ `stylometry.min_words` words). The curve of these
shifts along the book peaks where the style turns.

Significance per book: verse order is shuffled `null_reps` times and the curve recomputed; the
threshold is the 95th percentile of the shuffled curves' maxima, so a book has about a 5 % chance
of showing any seam by accident (family-wise). Seams are the curve's peaks above the threshold,
taken strongest first, at least `block_words` words apart; each lists the features that change
most (z difference, sign = after minus before).

Like §16.6 this is descriptive: a seam is a change of style (genre, language, speaker, source),
not a claim about authorship.

Writes `artifacts/seams/`: `curve.parquet` (`book_id, verse_id` = first verse after the boundary,
`shift`), `seams.parquet` (`book_id, verse_id, shift, threshold, rank, features` JSON) and
`seams.meta.json` (per-book thresholds).
"""

from __future__ import annotations

import json
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.stylometry import MORPH_LABELS, feature_matrix
from bsim.config import config_hash, resolve_path

Log = Callable[[str], None]


def shift_curve(counts: np.ndarray, n_words: np.ndarray, sd: np.ndarray, block: int) -> np.ndarray:
    """Delta between the `block` words before and after every verse boundary of one book.

    `counts` (verses x features) and `n_words` are in reading order; entry k is the boundary
    before verse k (NaN where either side has fewer than `block` words)."""
    n = len(n_words)
    cw = np.concatenate([[0.0], np.cumsum(n_words)])
    cc = np.vstack([np.zeros(counts.shape[1]), np.cumsum(counts, axis=0)])
    out = np.full(n, np.nan)
    for k in range(1, n):
        lo = np.searchsorted(cw, cw[k] - block, side="right") - 1  # whole verses, ≥ block words
        hi = np.searchsorted(cw, cw[k] + block, side="left")
        if lo < 0 or hi > n:
            continue
        wl, wr = cw[k] - cw[lo], cw[hi] - cw[k]
        if wl < block or wr < block:
            continue
        rl = (cc[k] - cc[lo]) / wl
        rr = (cc[hi] - cc[k]) / wr
        out[k] = float(np.mean(np.abs(rl - rr) / sd))
    return out


def pick_peaks(
    curve: np.ndarray, n_words: np.ndarray, threshold: float, min_words: int
) -> list[int]:
    """Indexes of the curve's highest points above `threshold`, at least `min_words` apart."""
    cw = np.concatenate([[0.0], np.cumsum(n_words)])
    order = [k for k in np.argsort(-np.nan_to_num(curve, nan=-1.0)) if curve[k] > threshold]
    chosen: list[int] = []
    for k in order:
        if all(abs(cw[k] - cw[j]) >= min_words for j in chosen):
            chosen.append(int(k))
    return chosen


def changed_features(
    counts: np.ndarray, n_words: np.ndarray, sd: np.ndarray, k: int, block: int, top: int
) -> list[tuple[int, float]]:
    """(feature index, z difference after − before) of the `top` features changing most at k."""
    cw = np.concatenate([[0.0], np.cumsum(n_words)])
    lo = max(0, int(np.searchsorted(cw, cw[k] - block, side="right")) - 1)
    hi = min(len(n_words), int(np.searchsorted(cw, cw[k] + block, side="left")))
    rl = counts[lo:k].sum(axis=0) / max(1.0, n_words[lo:k].sum())
    rr = counts[k:hi].sum(axis=0) / max(1.0, n_words[k:hi].sum())
    z = (rr - rl) / sd
    idx = np.argsort(-np.abs(z), kind="stable")[:top]
    return [(int(i), float(z[i])) for i in idx]


def run_seams(cfg: dict[str, Any], log: Log = print) -> Path:
    from bsim.store.db import lemma_display_forms

    sc, st = cfg["seams"], cfg["stylometry"]
    proc = resolve_path(cfg, "data_processed")
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter"])
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "surface", "lemma", "content_lemmas", "morph"]
    )
    t0 = time.perf_counter()
    lemma_counts: Counter[str] = Counter(t for c in words.content_lemmas for t in c)
    mfw = [t for t, _ in lemma_counts.most_common(st["mfw"])]
    n = len(verses)
    rel, n_words, names = feature_matrix(words, np.arange(n), n, mfw)
    counts = rel * n_words[:, None]

    # feature spread across chapters (the unit stylometry z-scores at)
    chap = (verses.book_id * 1000 + verses.chapter).to_numpy()
    _, chap_of_verse = np.unique(chap, return_inverse=True)
    n_ch = int(chap_of_verse.max()) + 1
    ch_counts = np.zeros((n_ch, counts.shape[1]))
    np.add.at(ch_counts, chap_of_verse, counts)
    ch_words = np.bincount(chap_of_verse, weights=n_words, minlength=n_ch)
    big = ch_words >= st["min_words"]
    sd = (ch_counts[big] / ch_words[big, None]).std(axis=0)
    keep = sd > 0
    counts, sd, names = (
        counts[:, keep],
        sd[keep],
        [nm for nm, k in zip(names, keep, strict=True) if k],
    )

    gloss = dict(zip(*lemma_display_forms(words)[["lemma", "he_lemma"]].T.values, strict=True))

    def label(name: str) -> str:
        return gloss.get(name[6:], name[6:]) if name.startswith("lemma:") else MORPH_LABELS[name]

    rng = np.random.default_rng(sc["seed"])
    block = sc["block_words"]
    curves, seams, thresholds = [], [], {}
    for book, g in verses.groupby("book_id", sort=True):
        vids = g.verse_id.to_numpy()
        bc, bw = counts[vids], n_words[vids]
        curve = shift_curve(bc, bw, sd, block)
        if np.isnan(curve).all():
            continue
        maxima = []
        for _ in range(sc["null_reps"]):
            perm = rng.permutation(len(vids))
            maxima.append(np.nanmax(shift_curve(bc[perm], bw[perm], sd, block)))
        thr = float(np.quantile(maxima, 0.95))
        thresholds[int(book)] = round(thr, 4)
        curves.append(pd.DataFrame({"book_id": book, "verse_id": vids, "shift": curve}))
        for rank, k in enumerate(pick_peaks(curve, bw, thr, block), start=1):
            feats = changed_features(bc, bw, sd, k, block, sc["top_features"])
            seams.append(
                (
                    int(book),
                    int(vids[k]),
                    round(float(curve[k]), 4),
                    round(thr, 4),
                    rank,
                    json.dumps(
                        [[names[i], label(names[i]), round(z, 3)] for i, z in feats],
                        ensure_ascii=False,
                    ),
                )
            )
    curve_df = pd.concat(curves, ignore_index=True).dropna(subset=["shift"])
    curve_df["shift"] = curve_df["shift"].round(4)
    seam_df = pd.DataFrame(
        seams, columns=["book_id", "verse_id", "shift", "threshold", "rank", "features"]
    )
    out = resolve_path(cfg, "artifacts") / "seams"
    out.mkdir(parents=True, exist_ok=True)
    curve_df.to_parquet(out / "curve.parquet")
    seam_df.to_parquet(out / "seams.parquet")
    meta = {
        "config_hash": config_hash(cfg, "seams", "stylometry"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "books": len(thresholds),
        "seams": int(len(seam_df)),
        "thresholds": thresholds,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "seams.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(f"done: {len(seam_df)} seams in {len(thresholds)} books ({meta['seconds']} s) -> {out}")
    return out
