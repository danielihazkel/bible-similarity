import pandas as pd

from bsim.analysis.network import analyse, unit_edges
from bsim.config import load_config


def units(n, book=0):
    return pd.DataFrame(
        {
            "unit_id": [f"c:{book}:{i}" for i in range(1, n + 1)],
            "book_id": book,
            "start_verse_id": range(0, 10 * n, 10),
        }
    )


def test_unit_edges_symmetric_best_rank_and_no_adjacent():
    u = units(5)
    topk = pd.DataFrame(
        {
            "src_id": ["c:0:1", "c:0:3", "c:0:1", "c:0:2"],
            "tgt_id": ["c:0:3", "c:0:1", "c:0:2", "c:0:5"],
            "rank": [3, 1, 1, 11],
        }
    )
    e = unit_edges(topk, u, max_rank=10, skip_adjacent=True)
    # 1-3 from both directions keeps the better weight; 1-2 are adjacent; 2-5 is beyond rank 10
    assert e.values.tolist() == [["c:0:1", "c:0:3", 1.0]]
    assert len(unit_edges(topk, u, 10, skip_adjacent=False)) == 2


def test_analyse_finds_two_communities_and_central_node():
    cfg = load_config()
    nodes = [f"u{i}" for i in range(8)]
    book = {u: 0 if i < 4 else 1 for i, u in enumerate(nodes)}
    clique = lambda xs: [(a, b, 1.0) for i, a in enumerate(xs) for b in xs[i + 1 :]]  # noqa: E731
    edges = pd.DataFrame(
        clique(nodes[:4]) + clique(nodes[4:]) + [("u0", "u4", 0.1)], columns=["a", "b", "weight"]
    )
    df, comms = analyse(
        nodes, edges, book, {**cfg, "network": {**cfg["network"], "resolution": 1.0}}
    )
    assert sorted(map(sorted, comms)) == [nodes[:4], nodes[4:]]
    d = df.set_index("unit_id")
    assert d.pagerank.idxmax() in ("u0", "u4")  # the bridge ends are the most central
    assert d.cross_book["u0"] > 0 and d.cross_book["u1"] == 0
    assert d.x.between(0, 1).all() and d.y.between(0, 1).all()
