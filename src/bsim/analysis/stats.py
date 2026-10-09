"""Shared significance helpers for the pattern analyses (DESIGN.md §16.14).

- `empirical_p`: a Monte Carlo p-value with the +1 correction, `(1 + #null ≥ obs) / (1 + reps)`,
  so a score no shuffle reached is never p = 0.
- `bh_q`: Benjamini–Hochberg q-values over a family of p-values. A finding with q ≤ 0.05 belongs
  to a list in which about 5 % of the entries are expected to be chance. Every analysis that
  scores many units at once (acrostics, rewrites, inclusio / chiasm) reports q next to its score.
- `pct_to_p`: the upper-tail p-value of a percentile measured against `samples` null draws.
- `permute_within`: labels shuffled inside groups (a book, a chapter), the null of an analysis
  that must keep each group's mix (voices §16.28, divisions §16.29).
"""

from __future__ import annotations

import numpy as np


def empirical_p(observed: float, null: np.ndarray) -> float:
    null = np.asarray(null)
    return float((1 + np.sum(null >= observed)) / (1 + len(null)))


def bh_q(p: np.ndarray) -> np.ndarray:
    """Benjamini–Hochberg q-values in the input order; NaN p-values stay NaN (not counted)."""
    p = np.asarray(p, dtype=np.float64)
    q = np.full(p.shape, np.nan)
    ok = np.flatnonzero(~np.isnan(p))
    if len(ok) == 0:
        return q
    order = ok[np.argsort(p[ok], kind="stable")]
    ranked = p[order] * len(ok) / np.arange(1, len(ok) + 1)
    q[order] = np.minimum(1.0, np.minimum.accumulate(ranked[::-1])[::-1])
    return q


def pct_to_p(pct: np.ndarray, samples: int) -> np.ndarray:
    """p of a score at percentile `pct` (share of null draws below it) among `samples` draws."""
    pct = np.asarray(pct, dtype=np.float64)
    return (1 + samples * (1 - pct)) / (1 + samples)


def permute_within(lab: np.ndarray, group: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """`lab` shuffled among the rows of each group (each group keeps its labels)."""
    by_group = np.argsort(group, kind="stable")
    shuffled = np.lexsort((rng.random(len(lab)), group))
    out = np.empty_like(lab)
    out[by_group] = lab[shuffled]
    return out
