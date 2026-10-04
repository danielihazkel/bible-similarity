"""`bsim map`: 2-D map of the Tanakh, thematic clusters, book-to-book affinity (DESIGN.md §16.4).

- Unit vectors: the mean of a unit's verse embeddings (final semantic system), L2-normalized.
- Layout: t-SNE (cosine, PCA init, seeded) per unit type, coordinates scaled to 0..1.
- Clusters: KMeans on the unit vectors (`map.clusters[unit_type]`), each labelled by its most
  over-represented content lemmas (Dunning G², function words skipped, as for Leitworte).
- Book affinity: unordered cross-book verse pairs where either verse has the other within its
  fused top `map.affinity_rank` (neighbours are same-book, so none are dropped here). `lift` =
  observed pairs / pairs expected if matches fell between books in proportion to their sizes
  (`n_a · n_b`); `book_order` is the leaf order of an average-linkage clustering of the books on
  `log(1 + lift)` so related books sit together. The `map.examples` strongest pairs per book pair
  are kept.

Writes `artifacts/map/{points,clusters,book_affinity,book_examples}.parquet` + `map.meta.json`.
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

from bsim.analysis.structure import embeddings_path, leitworte
from bsim.config import config_hash, resolve_path
from bsim.retrieve.topk import read_topk

Log = Callable[[str], None]


def unit_vectors(emb: np.ndarray, starts: np.ndarray, ends: np.ndarray) -> np.ndarray:
    """Mean verse embedding per unit (verse ranges inclusive), L2-normalized."""
    csum = np.vstack([np.zeros((1, emb.shape[1])), np.cumsum(emb, axis=0, dtype=np.float64)])
    v = (csum[ends + 1] - csum[starts]) / (ends - starts + 1)[:, None]
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def layout(vectors: np.ndarray, perplexity: float, seed: int) -> np.ndarray:
    from sklearn.manifold import TSNE

    p = min(perplexity, max(2.0, (len(vectors) - 1) / 3))
    xy = TSNE(
        n_components=2, metric="cosine", init="pca", perplexity=p, random_state=seed
    ).fit_transform(vectors)
    xy = xy - xy.min(axis=0)
    return xy / max(float(xy.max()), 1e-9)


def clusters(vectors: np.ndarray, k: int, seed: int) -> np.ndarray:
    from sklearn.cluster import KMeans

    k = min(k, len(vectors))
    return KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(vectors).astype(np.int32)


def cluster_labels(
    labels: np.ndarray,
    unit_lemmas: list[Counter[str]],
    corpus_counts: dict[str, int],
    corpus_total: int,
    skip: set[str],
    top: int,
) -> dict[int, list[str]]:
    out = {}
    for c in sorted(set(labels.tolist())):
        counts: Counter[str] = Counter()
        for i in np.flatnonzero(labels == c):
            counts.update(unit_lemmas[i])
        counts = Counter({t: n for t, n in counts.items() if t not in skip})
        out[c] = [k.lemma for k in leitworte(counts, corpus_counts, corpus_total, 3, top)]
    return out


def book_affinity(
    pairs: pd.DataFrame, book_id: np.ndarray, n_books: int
) -> tuple[pd.DataFrame, np.ndarray]:
    """`a_book, b_book, n_pairs, expected, lift` (a < b, every book pair) and the n x n count
    matrix, from unordered cross-book verse pairs `a, b`."""
    sizes = np.bincount(book_id, minlength=n_books).astype(np.float64)
    m = np.zeros((n_books, n_books))
    ba, bb = book_id[pairs.a.to_numpy()], book_id[pairs.b.to_numpy()]
    np.add.at(m, (np.minimum(ba, bb), np.maximum(ba, bb)), 1)
    iu = np.triu_indices(n_books, k=1)
    weight = np.outer(sizes, sizes)[iu]
    expected = m[iu].sum() * weight / weight.sum()
    df = pd.DataFrame(
        {
            "a_book": iu[0].astype(np.int32),
            "b_book": iu[1].astype(np.int32),
            "n_pairs": m[iu].astype(np.int64),
            "expected": expected,
            "lift": np.divide(m[iu], expected, out=np.zeros_like(expected), where=expected > 0),
        }
    )
    return df, m + m.T


def book_order(aff: pd.DataFrame, n_books: int) -> list[int]:
    from scipy.cluster.hierarchy import leaves_list, linkage

    sim = np.zeros((n_books, n_books))
    sim[aff.a_book, aff.b_book] = np.log1p(aff.lift)
    sim = sim + sim.T
    top = sim.max() or 1.0
    dist = top - sim[np.triu_indices(n_books, k=1)]  # condensed distance
    return leaves_list(linkage(dist, method="average")).astype(int).tolist()


def cross_book_pairs(topk: pd.DataFrame, book_id: np.ndarray, max_rank: int) -> pd.DataFrame:
    """Unordered cross-book pairs `a, b, score` (best of both directions) within `max_rank`."""
    t = topk[topk["rank"] <= max_rank]
    src, tgt = t.src.to_numpy(), t.tgt.to_numpy()
    keep = book_id[src] != book_id[tgt]
    df = pd.DataFrame(
        {"a": np.minimum(src, tgt)[keep], "b": np.maximum(src, tgt)[keep], "score": t.score[keep]}
    )
    return df.groupby(["a", "b"], as_index=False).score.max()


def run_map(cfg: dict[str, Any], log: Log = print) -> Path:
    from bsim.store.db import lemma_parts_pos

    mc = cfg["map"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    units = pd.read_parquet(proc / "units.parquet")
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id"])
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "lemma", "content_lemmas", "morph"]
    )
    emb_path = embeddings_path(cfg)
    fused = art / "topk" / "verse" / f"{cfg['final_systems']['fused']}.parquet"
    for path, cmd in ((emb_path, "embed"), (fused, "fuse")):
        if not path.exists():
            raise RuntimeError(f"{path} missing; run `bsim {cmd}` first")
    t0 = time.perf_counter()
    emb = np.load(emb_path, mmap_mode="r")
    book_id = verses.sort_values("verse_id").book_id.to_numpy()
    n_books = int(book_id.max()) + 1

    # lemma counts per verse, corpus counts, function-word POS
    verse_lemmas: list[Counter[str]] = [Counter() for _ in range(len(book_id))]
    pos: dict[str, Counter[str]] = {}
    for vid, lemma, content, morph in zip(
        words.verse_id, words.lemma, words.content_lemmas, words.morph, strict=True
    ):
        verse_lemmas[vid].update(content)
        for lem, p in lemma_parts_pos(lemma, morph).items():
            pos.setdefault(lem, Counter())[p] += 1
    corpus_counts: Counter[str] = Counter()
    for c in verse_lemmas:
        corpus_counts.update(c)
    corpus_total = sum(corpus_counts.values())
    skip_pos = set(cfg["structure"]["leitwort_skip_pos"])
    skip = {t for t, c in pos.items() if c.most_common(1)[0][0] in skip_pos}

    points, cluster_rows = [], []
    for unit_type, k in mc["clusters"].items():
        u = units[units.unit_type == unit_type].sort_values("start_verse_id").reset_index(drop=True)
        starts, ends = u.start_verse_id.to_numpy(), u.end_verse_id.to_numpy()
        vec = unit_vectors(np.asarray(emb), starts, ends)
        xy = layout(vec, mc["perplexity"], cfg["seed"])
        lab = clusters(vec, k, cfg["seed"])
        lemmas = []
        for s, e in zip(starts, ends, strict=True):
            c: Counter[str] = Counter()
            for v in range(s, e + 1):
                c.update(verse_lemmas[v])
            lemmas.append(c)
        names = cluster_labels(lab, lemmas, corpus_counts, corpus_total, skip, mc["label_lemmas"])
        points.append(
            pd.DataFrame(
                {
                    "unit_id": u.unit_id,
                    "unit_type": unit_type,
                    "x": xy[:, 0],
                    "y": xy[:, 1],
                    "cluster": lab,
                }
            )
        )
        sizes = np.bincount(lab)
        cluster_rows += [(unit_type, c, int(sizes[c]), json.dumps(names[c])) for c in sorted(names)]
        log(f"  {unit_type}: {len(u)} units, {len(names)} clusters")

    pairs = cross_book_pairs(read_topk(fused), book_id, mc["affinity_rank"])
    aff, _ = book_affinity(pairs, book_id, n_books)
    order = book_order(aff, n_books)
    pairs["a_book"], pairs["b_book"] = book_id[pairs.a], book_id[pairs.b]
    swap = pairs.a_book > pairs.b_book  # a < b by verse id already implies a_book <= b_book
    if swap.any():
        raise RuntimeError("verse order and canon order disagree")
    ex = (
        pairs.sort_values(["a_book", "b_book", "score", "a"], ascending=[True, True, False, True])
        .groupby(["a_book", "b_book"])
        .head(mc["examples"])
    )
    ex = ex.assign(rank=ex.groupby(["a_book", "b_book"]).cumcount() + 1)

    out = art / "map"
    out.mkdir(parents=True, exist_ok=True)
    pd.concat(points, ignore_index=True).to_parquet(out / "points.parquet", index=False)
    pd.DataFrame(cluster_rows, columns=["unit_type", "cluster", "size", "lemmas"]).to_parquet(
        out / "clusters.parquet", index=False
    )
    aff.to_parquet(out / "book_affinity.parquet", index=False)
    ex[["a_book", "b_book", "rank", "a", "b", "score"]].rename(
        columns={"a": "a_vid", "b": "b_vid"}
    ).to_parquet(out / "book_examples.parquet", index=False)
    meta = {
        "config_hash": config_hash(cfg, "map", "final_systems", "seed"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "embeddings": emb_path.name,
        "pairs": int(len(pairs)),
        "book_order": order,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "map.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(f"done: map + {len(pairs)} cross-book pairs in {meta['seconds']} s -> {out}")
    return out
