"""`bsim network`: the network of echoes between passages (DESIGN.md §16.17).

Every chapter / pericope is a node; an edge joins two units when either has the other in its
final fused top `network.edge_rank`, weighted `(R + 1 − rank) / R` by the better direction (the
weighting of §16.7). With `skip_adjacent`, edges between consecutive units of one book are left
out: neighbours are alike by continuity, and would chain each book into one long community.

- Centrality: weighted PageRank (`damping`), the passages the rest of the Bible echoes most; plus
  each node's strength (sum of edge weights), partners and the share of that strength reaching
  other books (`cross_book`).
- Communities: Louvain (networkx, `resolution`, seeded) — groups of passages that echo each
  other more than the rest, across books. Each is labelled by its over-represented content lemmas
  (Dunning G², function words skipped, as for the map clusters §16.4) and its books.
- Layout: a seeded spring layout inside each community (scaled to 0..1), so the viewer draws a
  community without simulating forces.

Writes `artifacts/network/{nodes,edges,communities}.parquet` plus `network.meta.json`.
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

from bsim.analysis.corpus_map import cluster_labels
from bsim.config import config_hash, resolve_path
from bsim.retrieve.fusion import final_systems

Log = Callable[[str], None]


def unit_edges(
    topk: pd.DataFrame, units: pd.DataFrame, max_rank: int, skip_adjacent: bool
) -> pd.DataFrame:
    """`a, b, weight` (unit ids, a < b in start-verse order) from a unit type's top-k lists."""
    order = units.sort_values("start_verse_id").reset_index(drop=True)
    pos = dict(zip(order.unit_id, range(len(order)), strict=True))
    book = dict(zip(order.unit_id, order.book_id, strict=True))
    t = topk[topk["rank"] <= max_rank]
    w = (max_rank + 1 - t["rank"].to_numpy(dtype=np.float64)) / max_rank
    src, tgt = t.src_id.to_numpy(), t.tgt_id.to_numpy()
    first = np.array([pos[s] < pos[g] for s, g in zip(src, tgt, strict=True)], dtype=bool)
    df = pd.DataFrame({"a": np.where(first, src, tgt), "b": np.where(first, tgt, src), "weight": w})
    df = df[df.a != df.b]
    if skip_adjacent:
        adjacent = [
            book[a] == book[b] and abs(pos[a] - pos[b]) == 1
            for a, b in zip(df.a, df.b, strict=True)
        ]
        df = df[~np.array(adjacent, dtype=bool)]
    return df.groupby(["a", "b"], as_index=False, sort=True).weight.max()


def analyse(
    nodes: list[str], edges: pd.DataFrame, book: dict[str, int], cfg: dict[str, Any]
) -> tuple[pd.DataFrame, list[list[str]]]:
    """Per node: pagerank, strength, partners, cross_book, community, x, y; and the communities
    (largest first)."""
    import networkx as nx

    n = cfg["network"]
    g = nx.Graph()
    g.add_nodes_from(nodes)
    g.add_weighted_edges_from(edges[["a", "b", "weight"]].itertuples(index=False, name=None))
    rank = nx.pagerank(g, alpha=n["damping"], weight="weight")
    comms = nx.community.louvain_communities(
        g, weight="weight", resolution=n["resolution"], seed=n["seed"]
    )
    comms = sorted(
        (sorted(c, key=nodes.index) for c in comms), key=lambda c: (-len(c), nodes.index(c[0]))
    )
    member = {u: k for k, c in enumerate(comms) for u in c}
    xy: dict[str, tuple[float, float]] = {}
    for c in comms:
        if len(c) == 1:
            xy[c[0]] = (0.5, 0.5)
            continue
        pos = nx.spring_layout(g.subgraph(c), weight="weight", seed=n["seed"])
        arr = np.array([pos[u] for u in c])
        lo, span = arr.min(axis=0), np.ptp(arr, axis=0)
        span[span == 0] = 1.0
        for u, p in zip(c, (arr - lo) / span, strict=True):
            xy[u] = (round(float(p[0]), 4), round(float(p[1]), 4))
    rows = []
    for u in nodes:
        strength = sum(d["weight"] for _, _, d in g.edges(u, data=True))
        cross = sum(d["weight"] for _, v, d in g.edges(u, data=True) if book[v] != book[u])
        rows.append(
            {
                "unit_id": u,
                "pagerank": rank[u],
                "strength": round(strength, 4),
                "partners": g.degree(u),
                "cross_book": round(cross / strength, 4) if strength else 0.0,
                "community": member[u],
                "x": xy[u][0],
                "y": xy[u][1],
            }
        )
    return pd.DataFrame(rows), comms


def run_network(cfg: dict[str, Any], log: Log = print) -> Path:
    from bsim.store.db import lemma_parts_pos  # store.db imports the analysis modules

    n = cfg["network"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    units = pd.read_parquet(proc / "units.parquet")
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "lemma", "content_lemmas", "morph"]
    )
    t0 = time.perf_counter()
    n_verses = int(words.verse_id.max()) + 1
    verse_lemmas: list[Counter[str]] = [Counter() for _ in range(n_verses)]
    pos: dict[str, Counter[str]] = {}
    for vid, lemma, content, morph in zip(
        words.verse_id, words.lemma, words.content_lemmas, words.morph, strict=True
    ):
        verse_lemmas[vid].update(content)
        for lem, p in lemma_parts_pos(lemma, morph).items():
            pos.setdefault(lem, Counter())[p] += 1
    corpus: Counter[str] = Counter()
    for c in verse_lemmas:
        corpus.update(c)
    skip_pos = set(cfg["structure"]["leitwort_skip_pos"])
    skip = {t for t, c in pos.items() if c.most_common(1)[0][0] in skip_pos}

    all_nodes, all_edges, all_comms, summary = [], [], [], {}
    for unit_type in n["unit_types"]:
        path = art / "topk" / unit_type / f"{final_systems(cfg, unit_type)['fused']}.parquet"
        if not path.exists():
            raise RuntimeError(f"{path} missing; run `bsim fuse` first")
        u = units[units.unit_type == unit_type].sort_values("start_verse_id")
        book = dict(zip(u.unit_id, u.book_id.astype(int), strict=True))
        edges = unit_edges(
            pd.read_parquet(path, columns=["src_id", "tgt_id", "rank"]),
            u,
            n["edge_rank"],
            n["skip_adjacent"],
        )
        nodes = u.unit_id.tolist()
        node_df, comms = analyse(nodes, edges, book, cfg)
        lemmas = []
        for s, e in zip(u.start_verse_id, u.end_verse_id, strict=True):
            c: Counter[str] = Counter()
            for v in range(s, e + 1):
                c.update(verse_lemmas[v])
            lemmas.append(c)
        labels = cluster_labels(
            node_df.community.to_numpy(), lemmas, corpus, corpus.total(), skip, n["label_lemmas"]
        )
        for k, members in enumerate(comms):
            books = Counter(book[m] for m in members)
            all_comms.append(
                (unit_type, k, len(members), json.dumps(labels[k]), json.dumps(books.most_common()))
            )
        all_nodes.append(node_df.assign(unit_type=unit_type))
        all_edges.append(edges.assign(unit_type=unit_type))
        summary[unit_type] = {
            "nodes": len(nodes),
            "edges": int(len(edges)),
            "communities": len(comms),
            "largest": [len(c) for c in comms[:5]],
        }
        log(f"  {unit_type}: {len(nodes)} units, {len(edges)} edges, {len(comms)} communities")

    out = art / "network"
    out.mkdir(parents=True, exist_ok=True)
    pd.concat(all_nodes, ignore_index=True).to_parquet(out / "nodes.parquet", index=False)
    pd.concat(all_edges, ignore_index=True).to_parquet(out / "edges.parquet", index=False)
    pd.DataFrame(
        all_comms, columns=["unit_type", "community", "size", "lemmas", "books"]
    ).to_parquet(out / "communities.parquet", index=False)
    meta = {
        "config_hash": config_hash(cfg, "network", "final_systems"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        **summary,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "network.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(f"done: network in {meta['seconds']} s -> {out}")
    return out
