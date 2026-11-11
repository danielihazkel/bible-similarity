"""A unit's neighbourhood: its parallels two hops out, each edge with the kinds that join it
(DESIGN.md §11.1, D149; M161).

From the unit, each node's stored fused list (`k` hits; a verse's own neighbours left out) adds its
hits as nodes, `hops` times, until `max_nodes`. An edge of these lists is `fused`, and `lexical` /
`semantic` where that list alone ranks the pair within `k`, `phrase` where the two share a phrase
(§16.1), `known` where a gold set links them. Among the nodes found, more edges from what is
stored: a significant parallel sequence (§16.7) or allusion (§16.32) with a side in each node,
a resolved citation (§16.31) from one into the other, and between chapters an echo (§16.36),
`borrowing` where the parallel sequences decide a direction. Nothing is added as a node by these.
Laid out by a seeded spring layout with the unit fixed in the middle, as the network is (§16.17).
"""

from __future__ import annotations

import sqlite3
from typing import Any

import numpy as np

from bsim.api import queries
from bsim.store.db import similar

# an edge is drawn in the colour of its first kind in this order
KINDS = (
    "citation", "known", "sequence", "allusion", "borrowing", "echo", "phrase", "lexical",
    "semantic", "fused",
)  # fmt: skip


def _spans(conn: sqlite3.Connection, sql: str, args: list[Any]) -> list[tuple[int, int, int, int]]:
    return [tuple(r) for r in conn.execute(sql, args).fetchall()]  # type: ignore[misc]


def neighbourhood(
    conn: sqlite3.Connection, cfg: dict[str, Any], unit_id: str, k: int, hops: int
) -> dict[str, Any]:
    nc = cfg["serve"]["neighbourhood"]
    centre = queries.unit(conn, unit_id)
    assert centre is not None
    utype = centre["unit_type"]
    exclude = ["neighbors"] if utype == "verse" else []
    window = cfg["retrieval"]["neighbor_window"]
    hop = {unit_id: 0}
    edges: dict[tuple[str, str], dict[str, Any]] = {}
    truncated = False
    frontier = [unit_id]
    for h in range(1, hops + 1):
        nxt = []
        for src in frontier:
            for r in similar(conn, utype, "fused", src, k=k, exclude=exclude, window=window):
                t = r["tgt_id"]
                if t not in hop:
                    if len(hop) >= nc["max_nodes"]:
                        truncated = True
                        continue
                    hop[t] = h
                    nxt.append(t)
                e = edges.setdefault(tuple(sorted((src, t))), {"kinds": {"fused"}, "score": 0.0})
                e["score"] = max(e["score"], float(r["score"]))
                if r["lex_rank"] is not None and r["lex_rank"] <= k:
                    e["kinds"].add("lexical")
                if r["sem_rank"] is not None and r["sem_rank"] <= k:
                    e["kinds"].add("semantic")
                if r["phr_rank"] is not None or r["phrase_score"] is not None:
                    e["kinds"].add("phrase")
                if r["link_level"] is not None:
                    e["kinds"].add("known")
        frontier = nxt

    units = queries.units_by_id(conn, list(hop))
    span = {u: (units[u]["start_verse_id"], units[u]["end_verse_id"]) for u in hop}

    def inside(lo: int, hi: int) -> list[str]:
        return [u for u, (s, e) in span.items() if s <= hi and e >= lo]

    def join(a_nodes: list[str], b_nodes: list[str], kind: str) -> None:
        for x in a_nodes:
            for y in b_nodes:
                if x != y:
                    edges.setdefault(tuple(sorted((x, y))), {"kinds": set(), "score": None})[
                        "kinds"
                    ].add(kind)

    for table, kind, max_q in (
        ("sequences", "sequence", nc["sequence_max_q"]),
        ("allusions", "allusion", nc["allusion_max_q"]),
    ):
        seen = set()
        for s, e in span.values():
            rows = _spans(
                conn,
                f"SELECT a_start, a_end, b_start, b_end FROM {table} WHERE q <= ?"
                " AND ((a_start <= ? AND a_end >= ?) OR (b_start <= ? AND b_end >= ?))",
                [max_q, e, s, e, s],
            )
            for row in rows:
                if row not in seen:
                    seen.add(row)
                    join(inside(row[0], row[1]), inside(row[2], row[3]), kind)
    for s, e in span.values():
        for vid, tgt in conn.execute(
            "SELECT verse_id, target_vid FROM citations"
            " WHERE resolved = 1 AND target_vid IS NOT NULL AND verse_id BETWEEN ? AND ?",
            [s, e],
        ).fetchall():
            join(inside(vid, vid), inside(tgt, tgt), "citation")
    if utype == "chapter":
        ids = list(hop)
        marks = ",".join("?" * len(ids))
        for a, b, borrowed in conn.execute(
            f"SELECT a, b, borrowed FROM echo_edges WHERE a IN ({marks}) AND b IN ({marks})",
            [*ids, *ids],
        ).fetchall():
            join([a], [b], "borrowing" if borrowed else "echo")

    xy = layout(list(hop), edges, unit_id, nc)
    return {
        "unit": centre,
        "k": k,
        "hops": hops,
        "truncated": truncated,
        "nodes": [
            {"unit": units[u], "hop": h, "x": xy[u][0], "y": xy[u][1]} for u, h in hop.items()
        ],
        "edges": [
            {
                "a": a,
                "b": b,
                "kinds": [x for x in KINDS if x in e["kinds"]],
                "score": None if e["score"] is None else round(e["score"], 4),
            }
            for (a, b), e in sorted(edges.items())
        ],  # fmt: skip
    }


def layout(
    nodes: list[str], edges: dict[tuple[str, str], dict[str, Any]], centre: str, nc: dict[str, Any]
) -> dict[str, tuple[float, float]]:
    """Seeded spring layout, the centre fixed in the middle, scaled to 0..1 around it."""
    import networkx as nx

    if len(nodes) == 1:
        return {centre: (0.5, 0.5)}
    g = nx.Graph()
    g.add_nodes_from(nodes)  # in walk order: the seeded start does not depend on set order
    for (a, b), e in edges.items():
        g.add_edge(a, b, weight=1.0 + len(e["kinds"]))
    pos = nx.spring_layout(
        g, pos={centre: (0.0, 0.0)}, fixed=[centre], weight="weight", seed=nc["seed"],
        iterations=nc["iterations"],
    )  # fmt: skip
    arr = np.array([pos[u] for u in nodes]) - np.array(pos[centre])
    r = float(np.abs(arr).max()) or 1.0
    arr = 0.5 + arr / (2 * r) * (1 - 2 * nc["margin"])
    return {
        u: (round(float(p[0]), 4), round(float(p[1]), 4)) for u, p in zip(nodes, arr, strict=True)
    }
