"""Shared significance helpers for the pattern analyses (DESIGN.md §16.14).

- `empirical_p`: a Monte Carlo p-value with the +1 correction, `(1 + #null ≥ obs) / (1 + reps)`,
  so a score no shuffle reached is never p = 0 (`tail="less"` for a score better when small).
- `bh_q`: Benjamini–Hochberg q-values over a family of p-values. A finding with q ≤ 0.05 belongs
  to a list in which about 5 % of the entries are expected to be chance. Every analysis that
  scores many units at once (acrostics, rewrites, inclusio / chiasm) reports q next to its score.
- `q_values`: the false discovery rate of each score against an empirical null (shuffles pooled).
- `pct_to_p`: the upper-tail p-value of a percentile measured against `samples` null draws.
- `permute_within`: labels shuffled inside groups (a book, a chapter), the null of an analysis
  that must keep each group's mix (voices §16.28, divisions §16.29); `shuffle_within`: the
  permutation of positions that does the same (sequences §16.7, wordplay, allusions).
- `g2_table`: Dunning's log-likelihood G² of a 2 × 2 table (rewrites, word pairs, name links,
  sense collocates). Keyness against the rest of the corpus (§16.2) and a unit's domains against
  the corpus share keep their own two-cell forms.
- `kmeans`: sklearn's k-means on one thread, so a seed gives one answer (senses, map clusters;
  §16.52).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np


def empirical_p(observed: float, null: Any, tail: str = "greater") -> float:
    """`(1 + #null ≥ observed) / (1 + reps)`; `tail="less"` counts the null at most `observed`
    (a score that is better when small: a distance, a dispersion)."""
    null = np.asarray(null)
    hits = null >= observed if tail == "greater" else null <= observed
    return float((1 + np.sum(hits)) / (1 + len(null)))


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


def q_values(observed: np.ndarray, null: np.ndarray, reps: int) -> np.ndarray:
    """Per observed score s: (null scores ≥ s / reps) / (observed scores ≥ s), capped at 1 and
    made monotone (a stronger score never has a larger q): the false discovery rate against an
    empirical null pooled over `reps` shuffles (sequences, allusions, wordplay, type scenes; for
    p-values, where small is strong, pass both negated: refrains)."""
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


def shuffle_within(groups: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """A permutation of `range(len(groups))` that moves positions only within their group."""
    perm = np.arange(len(groups))
    order = np.argsort(groups, kind="stable")
    bounds = np.flatnonzero(np.diff(groups[order])) + 1
    for ids in np.split(order, bounds):
        perm[ids] = rng.permutation(ids)
    return perm


def kmeans(x: np.ndarray, k: int, n_init: int, seed: int) -> Any:
    """A fitted `KMeans`, run on one thread. With several, its OpenMP threads add their partial
    centre sums in the order they finish: the same seed and data give centres that differ in the
    last bits, and at times another optimum (§16.52). sklearn is imported first, since the thread
    limit only reaches an OpenMP runtime already loaded."""
    from sklearn.cluster import KMeans
    from threadpoolctl import threadpool_limits

    with threadpool_limits(1):
        return KMeans(n_clusters=k, n_init=n_init, random_state=seed).fit(x)


def g2_table(n11: float, row: float, col: float, total: float) -> float:
    """Dunning's G² of a 2 × 2 table given its top-left cell, its row and column totals and the
    grand total (empty cells add nothing)."""
    cells = [n11, row - n11, col - n11, total - row - col + n11]
    expected = [row * col, row * (total - col), (total - row) * col, (total - row) * (total - col)]
    g2 = sum(
        o * math.log(o * total / e) for o, e in zip(cells, expected, strict=True) if o > 0 and e > 0
    )
    return max(0.0, 2 * g2)
