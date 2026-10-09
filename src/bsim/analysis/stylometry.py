"""`bsim stylometry`: style profiles of books and chapters (DESIGN.md §16.6).

Features (relative frequencies per word of a unit):
- the `stylometry.mfw` most frequent content lemmas of the corpus (Burrows' "most frequent words",
  mostly function-like: אשר, כל, יהוה, אמר, לא ...);
- morphology rates from the OSHB codes: parts of speech, verb forms (wayyiqtol, qatal, yiqtol,
  weqatal, participle, imperative, infinitives, cohortative / jussive), noun state, the article,
  the conjunction ו, the object marker את, pronominal suffixes, and Aramaic.

Every feature is z-scored across the units of a level (books, or chapters with at least
`min_words` words). Burrows' Delta between two units = mean |z_a − z_b|; books are ordered by an
average-linkage clustering of the Delta matrix. Chapters are projected onto the first two
principal components of their z-scores; each axis is described by its heaviest loadings. Per
book the most over- and under-used features (z) are kept.

These are descriptive statistics of style; groupings are not claims about authorship or date.

Writes `artifacts/stylometry/{points,book_delta,book_features}.parquet` + `stylometry.meta.json`.
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

from bsim.config import config_hash, resolve_path

Log = Callable[[str], None]

# morphology features: name -> Hebrew label (shown in the UI)
MORPH_LABELS = {
    "pos:N": "שם עצם",
    "pos:V": "פועל",
    "pos:A": "שם תואר",
    "pos:P": "כינוי",
    "pos:R": "מילת יחס",
    "pos:C": "מילת חיבור",
    "pos:T": "מילית",
    "pos:D": "תואר הפועל",
    "verb:w": "ויקטל (עתיד מהופך)",
    "verb:p": "קטל (עבר)",
    "verb:i": "יקטל (עתיד)",
    "verb:q": "וקטל (עבר מהופך)",
    "verb:r": "בינוני פועל",
    "verb:s": "בינוני פעול",
    "verb:v": "ציווי",
    "verb:a": "מקור מוחלט",
    "verb:c": "מקור נטוי",
    "verb:h": "עתיד מוארך",
    "verb:j": "עתיד מקוצר",
    "state:c": "נסמך",
    "article": "ה הידיעה",
    "conj": "ו החיבור",
    "object": "את (מושא)",
    "suffix": "כינוי חבור",
    "aramaic": "ארמית",
}


def word_features(morph: str | None) -> list[str]:
    """Morphology features carried by one word (each counted once per word)."""
    if not isinstance(morph, str) or len(morph) < 2:
        return []
    out = {"aramaic"} if morph[0] == "A" else set()
    for m in morph[1:].split("/"):
        if not m:
            continue
        pos = m[0]
        if pos in "NVAPRCTD":
            out.add(f"pos:{pos}")
        if pos == "V" and len(m) > 2:
            out.add(f"verb:{m[2]}")
        if pos == "N" and len(m) >= 5 and m[-1] == "c":
            out.add("state:c")
        if pos == "T" and m[1:2] == "d":
            out.add("article")
        if pos == "T" and m[1:2] == "o":
            out.add("object")
        if pos == "C":
            out.add("conj")
        if pos == "S" and m[1:2] == "p":
            out.add("suffix")
    return sorted(f for f in out if f in MORPH_LABELS)


def feature_counts(
    words: pd.DataFrame, unit_of_word: np.ndarray, n_units: int, mfw: list[str]
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """(units x features counts, words per unit, feature names); `unit_of_word[i]` is the unit
    of the i-th row of `words` (−1: left out)."""
    names = [f"lemma:{lem}" for lem in mfw] + list(MORPH_LABELS)
    col = {n: i for i, n in enumerate(names)}
    counts = np.zeros((n_units, len(names)))
    n_words = np.zeros(n_units)
    for u, lems, morph in zip(unit_of_word, words.content_lemmas, words.morph, strict=True):
        if u < 0:
            continue
        n_words[u] += 1
        for lem in set(lems):
            c = col.get(f"lemma:{lem}")
            if c is not None:
                counts[u, c] += 1
        for f in word_features(morph):
            counts[u, col[f]] += 1
    return counts, n_words, names


def feature_matrix(
    words: pd.DataFrame, unit_of_verse: np.ndarray, n_units: int, mfw: list[str]
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """(units x features relative frequencies, words per unit, feature names)."""
    unit_of_word = np.asarray(unit_of_verse)[words.verse_id.to_numpy()]
    counts, n_words, names = feature_counts(words, unit_of_word, n_units, mfw)
    rel = np.divide(counts, n_words[:, None], out=np.zeros_like(counts), where=n_words[:, None] > 0)
    return rel, n_words, names


def zscores(x: np.ndarray) -> np.ndarray:
    sd = x.std(axis=0)
    return np.divide(x - x.mean(axis=0), sd, out=np.zeros_like(x), where=sd > 0)


def delta_matrix(z: np.ndarray) -> np.ndarray:
    """Burrows' Delta: mean absolute z difference between every pair of rows."""
    return np.abs(z[:, None, :] - z[None, :, :]).mean(axis=2)


def cluster_order(d: np.ndarray) -> list[int]:
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform

    return leaves_list(linkage(squareform(d, checks=False), method="average")).astype(int).tolist()


def pca2(z: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(scores n x 2, loadings 2 x f, explained variance ratio of the 2 components)."""
    zc = z - z.mean(axis=0)
    u, s, vt = np.linalg.svd(zc, full_matrices=False)
    var = s**2 / max((s**2).sum(), 1e-12)
    scores = u[:, :2] * s[:2]
    # sign convention: the heaviest loading of each axis is positive
    for k in range(2):
        if vt[k, np.argmax(np.abs(vt[k]))] < 0:
            vt[k] *= -1
            scores[:, k] *= -1
    return scores, vt[:2], var[:2]


def run_stylometry(cfg: dict[str, Any], log: Log = print) -> Path:
    from bsim.data.canon import BOOKS
    from bsim.store.db import lemma_display_forms

    sc = cfg["stylometry"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    t0 = time.perf_counter()
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id"])
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "surface", "lemma", "content_lemmas", "morph"]
    )
    units = pd.read_parquet(proc / "units.parquet")
    book_id = verses.sort_values("verse_id").book_id.to_numpy()
    lemma_counts: Counter[str] = Counter(t for c in words.content_lemmas for t in c)
    mfw = [t for t, _ in lemma_counts.most_common(sc["mfw"])]

    # books
    n_books = len(BOOKS)
    xb, nwb, names = feature_matrix(words, book_id, n_books, mfw)
    zb = zscores(xb)
    delta = delta_matrix(zb)
    order = cluster_order(delta)
    gloss = dict(zip(*lemma_display_forms(words)[["lemma", "he_lemma"]].T.values, strict=True))

    def label(name: str) -> str:
        kind, key = name.split(":", 1) if name.startswith("lemma:") else ("morph", name)
        return gloss.get(key, key) if kind == "lemma" else MORPH_LABELS[name]

    feat_rows = []
    for b in range(n_books):
        idx = np.argsort(-zb[b], kind="stable")
        picks = [(i, "over") for i in idx[: sc["top_features"]]]
        picks += [(i, "under") for i in idx[::-1][: sc["top_features"]]]
        for rank, (i, side) in enumerate(picks):
            feat_rows.append(
                (b, side, rank, names[i], label(names[i]), float(xb[b, i]), float(zb[b, i]))
            )

    # chapters
    ch = units[units.unit_type == "chapter"].sort_values("start_verse_id").reset_index(drop=True)
    unit_of_verse = np.full(len(book_id), -1)
    for i, (s, e) in enumerate(zip(ch.start_verse_id, ch.end_verse_id, strict=True)):
        unit_of_verse[s : e + 1] = i
    xc, nwc, _ = feature_matrix(words, unit_of_verse, len(ch), mfw)
    keep = nwc >= sc["min_words"]
    zc = zscores(xc[keep])
    scores, loadings, var = pca2(zc)
    axes = []
    for k in range(2):
        idx = np.argsort(-loadings[k], kind="stable")
        axes.append(
            {
                "pc": k + 1,
                "variance": float(var[k]),
                "positive": [label(names[i]) for i in idx[: sc["axis_features"]]],
                "negative": [label(names[i]) for i in idx[::-1][: sc["axis_features"]]],
            }
        )
    xy = scores - scores.min(axis=0)
    xy = xy / np.maximum(xy.max(axis=0), 1e-9)

    out = art / "stylometry"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "unit_id": ch.unit_id[keep].to_numpy(),
            "x": xy[:, 0],
            "y": 1 - xy[:, 1],  # screen y grows downwards
            "n_words": nwc[keep].astype(np.int64),
        }
    ).to_parquet(out / "points.parquet", index=False)
    iu = np.triu_indices(n_books, k=1)
    pd.DataFrame({"a_book": iu[0], "b_book": iu[1], "delta": delta[iu]}).to_parquet(
        out / "book_delta.parquet", index=False
    )
    pd.DataFrame(
        feat_rows, columns=["book_id", "side", "rank", "feature", "label", "rate", "z"]
    ).to_parquet(out / "book_features.parquet", index=False)
    meta = {
        "config_hash": config_hash(cfg, "stylometry"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "features": len(names),
        "mfw": len(mfw),
        "chapters": int(keep.sum()),
        "book_order": order,
        "axes": axes,
        "book_words": nwb.astype(int).tolist(),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "stylometry.meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log(
        f"done: {len(names)} features, {n_books} books, {int(keep.sum())} chapters "
        f"(PC1 {var[0]:.0%}, PC2 {var[1]:.0%}) in {meta['seconds']} s -> {out}"
    )
    return out
