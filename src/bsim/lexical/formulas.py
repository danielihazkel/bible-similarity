"""Frequent formulas and their down-weighting (DESIGN.md §5.1).

A formula is a token n-gram (n = min_n..max_n) occurring in more than `min_verses` distinct
verses, e.g. וידבר ה' אל משה לאמר. Every token inside an occurrence of any formula gets weight
`alpha` instead of 1. The exported list keeps only *closed* n-grams (not contained in a longer
formula with the same verse count) so it stays readable; weights use all of them.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd

from bsim.lexical.tokens import Stream

Ngram = tuple[str, ...]


def _ngrams(tokens: list[str], n: int) -> list[Ngram]:
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def frequent_ngrams(
    streams: list[Stream], min_n: int, max_n: int, min_verses: int
) -> dict[Ngram, int]:
    """N-grams found in more than `min_verses` distinct verses -> their verse count."""
    out: dict[Ngram, int] = {}
    for n in range(min_n, max_n + 1):
        counts: Counter[Ngram] = Counter()
        for s in streams:
            counts.update(set(_ngrams(s.tokens, n)))
        out.update({g: c for g, c in counts.items() if c > min_verses})
    return out


def closed(ngrams: dict[Ngram, int]) -> dict[Ngram, int]:
    """Drop n-grams that are the prefix or suffix of a longer one with the same verse count.

    Checking one-token extensions is enough: any longer superset with the same count implies an
    intermediate one with the same count, which is frequent too.
    """
    absorbed = set()
    for g, c in ngrams.items():
        for sub in (g[:-1], g[1:]):
            if ngrams.get(sub) == c:
                absorbed.add(sub)
    return {g: c for g, c in ngrams.items() if g not in absorbed}


def formula_weights(
    streams: list[Stream], ngrams: dict[Ngram, int], alpha: float
) -> list[np.ndarray]:
    """Per-token weights: `alpha` inside any formula occurrence, 1.0 elsewhere."""
    lengths = sorted({len(g) for g in ngrams})
    out = []
    for s in streams:
        w = np.ones(len(s.tokens), dtype=np.float64)
        for n in lengths:
            for i, g in enumerate(_ngrams(s.tokens, n)):
                if g in ngrams:
                    w[i : i + n] = alpha
        out.append(w)
    return out


def formulas_frame(
    ngrams: dict[Ngram, int],
    streams: list[Stream],
    surfaces: list[list[str]],
    refs: list[str],
) -> pd.DataFrame:
    """One row per formula: lemmas, n, verse count, most common Hebrew form, an example ref.

    `surfaces[verse_id][word_idx]` is the consonantal surface of that word.
    """
    lengths = sorted({len(g) for g in ngrams})
    forms: dict[Ngram, Counter[str]] = {g: Counter() for g in ngrams}
    example: dict[Ngram, int] = {}
    for vid, s in enumerate(streams):
        for n in lengths:
            for i, g in enumerate(_ngrams(s.tokens, n)):
                if g in forms:
                    idxs = dict.fromkeys(s.word_idx[i : i + n])  # ordered, unique
                    forms[g][" ".join(surfaces[vid][j] for j in idxs)] += 1
                    example.setdefault(g, vid)
    rows = [
        {
            "formula": " ".join(g),
            "n": len(g),
            "n_verses": c,
            "he": forms[g].most_common(1)[0][0],
            "example_ref": refs[example[g]],
        }
        for g, c in ngrams.items()
    ]
    cols = ["formula", "n", "n_verses", "he", "example_ref"]
    df = pd.DataFrame(rows, columns=cols)
    return df.sort_values(["n_verses", "n", "formula"], ascending=[False, False, True]).reset_index(
        drop=True
    )
