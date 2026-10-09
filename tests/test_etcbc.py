import json

import pandas as pd
from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.eval.etcbc import coverage, gold_links, parallels_only, read_edges
from bsim.fixture import fixture_encoder


def test_read_edges_with_values(tmp_path):
    path = tmp_path / "crossref.tf"
    path.write_text(
        "@edge\n@edgeValues\n@valueType=int\n\n10\t12,14-15\t80\n13\t90\n20\t10\t75\n", "utf-8"
    )
    # the second line has no source: the node after the previous one (11)
    assert read_edges(path) == [
        (10, 12, 80), (10, 14, 80), (10, 15, 80), (11, 13, 90), (20, 10, 75),
    ]  # fmt: skip


def test_gold_links_drop_neighbours_and_keep_the_best_value():
    vid_of = {1: 100, 2: 101, 3: 500, 4: 900}
    book_of = {100: 0, 101: 0, 500: 0, 900: 5}
    split_of_book = {0: "train", 5: "dev"}
    edges = [(1, 2, 90), (1, 3, 80), (3, 1, 85), (1, 4, 99), (1, 7, 99)]
    links, stats = gold_links(edges, vid_of, book_of, split_of_book, window=2)
    assert stats == {"edges": 5, "unmapped": 1, "neighbours": 1, "pairs": 2}
    rows = set(links.itertuples(index=False, name=None))
    assert (100, 500, 85, "train") in rows and (500, 100, 85, "train") in rows
    assert (100, 900, 99, "dev") in rows  # a dev book makes the pair dev


def test_parallels_only_drops_formula_cliques():
    clique = [(a, b) for a in range(10, 17) for b in range(10, 17) if a != b]
    pairs = [(1, 2), (2, 1), *clique]
    links = pd.DataFrame(
        [(a, b, 80, "dev") for a, b in pairs], columns=["src_vid", "tgt_vid", "similarity", "split"]
    )
    kept = parallels_only(links, 5)
    assert set(zip(kept.src_vid, kept.tgt_vid, strict=True)) == {(1, 2), (2, 1)}


def test_coverage(tmp_path):
    art = tmp_path
    (art / "sequences").mkdir()
    seq = {"q": [0.01, 0.5], "pairs": ["[[1, 2, 1.0], [3, 4, 1.0]]", "[[5, 6, 1.0]]"]}
    pd.DataFrame(seq).to_parquet(art / "sequences" / "verse.parquet")
    (art / "phrases").mkdir()
    pd.DataFrame({"a": [2], "b": [1]}).to_parquet(art / "phrases" / "verse.parquet")
    (art / "topk" / "verse").mkdir(parents=True)
    pd.DataFrame({"src_id": ["v:5"], "tgt_id": ["v:6"], "rank": [1]}).to_parquet(
        art / "topk" / "verse" / "fused.parquet"
    )
    cfg = {"etcbc": {"max_q": 0.05}, "final_systems": {"fused": "fused"}}
    c = coverage({(1, 2), (5, 6)}, art, cfg)
    assert c["in_sequence"] == 0.5 and c["in_phrase"] == 0.5 and c["in_fused_top10"] == 0.5
    assert c["sequence_pairs"] == 2 and c["sequence_pairs_in_etcbc"] == 0.5


def test_eval_endpoint_serves_etcbc(built):
    cfg, _ = built
    client = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    assert client.get("/api/eval").json()["etcbc"] is None
    folder = cfg["paths"]["artifacts"]
    from pathlib import Path

    (Path(folder) / "eval").mkdir(parents=True, exist_ok=True)
    (Path(folder) / "eval" / "etcbc.json").write_text(json.dumps({"split": "dev", "results": {}}))
    assert client.get("/api/eval").json()["etcbc"]["split"] == "dev"
