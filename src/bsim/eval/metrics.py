"""Ranking metrics with binary relevance (DESIGN.md §8.3).

Per query: recall@k, MRR@k and nDCG@k over a ranked target list and a gold set; systems are
macro-averaged over every gold query (a query the system returns nothing for scores 0).
"""

from __future__ import annotations

import math
from collections.abc import Hashable, Iterable, Mapping, Sequence

Id = Hashable


def recall_at(ranked: Sequence[Id], gold: set[Id], k: int) -> float:
    return len(set(ranked[:k]) & gold) / len(gold)


def mrr_at(ranked: Sequence[Id], gold: set[Id], k: int) -> float:
    for i, t in enumerate(ranked[:k]):
        if t in gold:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at(ranked: Sequence[Id], gold: set[Id], k: int) -> float:
    dcg = sum(1.0 / math.log2(i + 2) for i, t in enumerate(ranked[:k]) if t in gold)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(gold), k)))
    return dcg / idcg


def metric_names(ks: Iterable[int], rank_k: int) -> list[str]:
    return [f"recall@{k}" for k in ks] + [f"mrr@{rank_k}", f"ndcg@{rank_k}"]


def query_metrics(
    ranked: Sequence[Id], gold: set[Id], ks: Iterable[int], rank_k: int
) -> dict[str, float]:
    out = {f"recall@{k}": recall_at(ranked, gold, k) for k in ks}
    out[f"mrr@{rank_k}"] = mrr_at(ranked, gold, rank_k)
    out[f"ndcg@{rank_k}"] = ndcg_at(ranked, gold, rank_k)
    return out


def evaluate_system(
    ranked: Mapping[Id, Sequence[Id]],
    gold: Mapping[Id, set[Id]],
    ks: Iterable[int],
    rank_k: int,
) -> dict[str, float]:
    """Macro-averaged metrics over the gold queries, plus `queries` (their count)."""
    ks = list(ks)
    names = metric_names(ks, rank_k)
    totals = dict.fromkeys(names, 0.0)
    queries = [q for q, g in gold.items() if g]
    for q in queries:
        for name, v in query_metrics(ranked.get(q, []), gold[q], ks, rank_k).items():
            totals[name] += v
    n = len(queries)
    out: dict[str, float] = {name: (v / n if n else 0.0) for name, v in totals.items()}
    out["queries"] = n
    return out


def per_query(
    ranked: Mapping[Id, Sequence[Id]], gold: Mapping[Id, set[Id]], metric: str
) -> dict[Id, float]:
    """One metric (`ndcg@10`, `recall@50`, `mrr@10`) per gold query."""
    name, k = metric.split("@")
    fn = {"ndcg": ndcg_at, "recall": recall_at, "mrr": mrr_at}[name]
    return {q: fn(ranked.get(q, []), g, int(k)) for q, g in gold.items() if g}


def paired_bootstrap(
    diff: Sequence[float], reps: int, seed: int, level: float = 0.95
) -> dict[str, float]:
    """Mean of per-query differences (system - baseline) with a percentile bootstrap CI over
    queries, and how many queries got better / worse."""
    import numpy as np

    d = np.asarray(diff, dtype=np.float64)
    if not len(d):
        return {"mean": 0.0, "lo": 0.0, "hi": 0.0, "better": 0, "worse": 0, "queries": 0}
    rng = np.random.default_rng(seed)
    means = np.empty(reps)
    for i in range(0, reps, 1000):  # chunks bound the index matrix
        n = min(1000, reps - i)
        means[i : i + n] = d[rng.integers(0, len(d), size=(n, len(d)))].mean(1)
    tail = (1 - level) / 2
    return {
        "mean": float(d.mean()),
        "lo": float(np.quantile(means, tail)),
        "hi": float(np.quantile(means, 1 - tail)),
        "better": int((d > 1e-12).sum()),
        "worse": int((d < -1e-12).sum()),
        "queries": len(d),
    }
