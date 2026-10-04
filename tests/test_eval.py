import json
import math

import numpy as np
import pandas as pd
import pytest

from bsim.config import load_config
from bsim.eval.metrics import evaluate_system, metric_names, mrr_at, ndcg_at, recall_at
from bsim.eval.report import gold_pairs, run_evaluate, unit_gold
from bsim.retrieve.topk import Units

RANKED = [5, 3, 9, 7]
GOLD = {3, 7}


def test_metrics_hand_computed():
    assert recall_at(RANKED, GOLD, 1) == 0.0
    assert recall_at(RANKED, GOLD, 2) == 0.5
    assert recall_at(RANKED, GOLD, 5) == 1.0
    assert mrr_at(RANKED, GOLD, 10) == 0.5
    assert mrr_at(RANKED, GOLD, 1) == 0.0
    expected = (1 / math.log2(3) + 1 / math.log2(5)) / (1 + 1 / math.log2(3))
    assert ndcg_at(RANKED, GOLD, 10) == pytest.approx(expected)
    assert ndcg_at([3, 7], GOLD, 10) == pytest.approx(1.0)


def test_evaluate_system_averages_over_gold_queries():
    m = evaluate_system({0: RANKED}, {0: GOLD, 1: {2}}, [1, 5], 10)
    assert m["queries"] == 2
    assert m["recall@5"] == pytest.approx(0.5)  # query 1 has no predictions -> 0
    assert m["mrr@10"] == pytest.approx(0.25)


def _links(rows: list[tuple[int, int, str, str]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["src_vid", "tgt_vid", "level", "split"])
    df["src_end_vid"], df["tgt_end_vid"] = df.src_vid, df.tgt_vid
    df["rule"], df["connection_type"] = "positional", ""
    return df


def test_gold_pairs_verse_level_of_split():
    links = _links(
        [
            (0, 5, "verse", "dev"),
            (5, 0, "verse", "dev"),
            (0, 6, "verse", "test"),
            (1, 7, "unit", "dev"),
        ]
    )
    assert gold_pairs(links, "dev") == {0: {5}, 5: {0}}


def _topk(rows: list[tuple[int, int, float]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["src", "tgt", "score"])
    df["rank"] = df.groupby("src").cumcount() + 1
    return pd.DataFrame(
        {
            "unit_type": "verse",
            "src_id": "v:" + df.src.astype(str),
            "rank": df["rank"].astype("int32"),
            "tgt_id": "v:" + df.tgt.astype(str),
            "score": df.score.astype("float32"),
        }
    )


def test_run_evaluate_end_to_end(tmp_path):
    cfg = load_config()
    proc, art = tmp_path / "processed", tmp_path / "artifacts"
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art)}
    cfg["eval"] = {**cfg["eval"], "spot_checks": ["B 1:1"]}
    proc.mkdir()
    pd.DataFrame(
        {
            "verse_id": range(8),
            "book_id": [0] * 4 + [1] * 4,
            "chapter": [1] * 8,
            "ref": [f"A 1:{i + 1}" for i in range(4)] + [f"B 1:{i + 1}" for i in range(4)],
        }
    ).to_parquet(proc / "verses.parquet")
    _links(
        [
            (0, 4, "verse", "dev"),
            (4, 0, "verse", "dev"),
            (1, 6, "verse", "train"),
            (6, 1, "verse", "train"),
        ]
    ).to_parquet(proc / "links.parquet")
    verse_dir = art / "topk" / "verse"
    verse_dir.mkdir(parents=True)
    # good: neighbour 1 is filtered, then 4 is rank 1; bad never finds the gold verse
    _topk([(0, 1, 9), (0, 4, 8), (4, 0, 5)]).to_parquet(verse_dir / "good.parquet")
    _topk([(0, 7, 9), (4, 2, 5)]).to_parquet(verse_dir / "bad.parquet")

    out = art / "eval"
    out.mkdir(parents=True)
    old_test = dict.fromkeys(metric_names(cfg["eval"]["ks"], 10), 0.0) | {"queries": 1}
    results = {"verse": {"good": old_test}}
    old = {"splits": {"test": {"evaluated_at": "x", "config_hash": "y", "results": results}}}
    (out / "metrics.json").write_text(json.dumps(old))

    metrics = run_evaluate(cfg, "dev", log=lambda _: None)
    res = metrics["splits"]["dev"]["results"]["verse"]
    assert res["good"]["recall@1"] == 1.0 and res["good"]["queries"] == 2
    assert res["bad"]["ndcg@10"] == 0.0
    assert "test" in json.loads((out / "metrics.json").read_text())["splits"]
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "## Dev" in report and "## Test" in report
    assert "| A 1:1 | B 1:1 |" in report  # bad's missed pair, found by good
    assert "B 1:1" in report


def _unit_links(rows: list[tuple[int, int, int, int, str, str]]) -> pd.DataFrame:
    cols = ["src_vid", "src_end_vid", "tgt_vid", "tgt_end_vid", "level", "split"]
    df = pd.DataFrame(rows, columns=cols)
    df["rule"], df["connection_type"] = "x", ""
    return df


def test_unit_gold_threshold_and_ranges():
    # 3 units over verses 0..8; verse 9 lies outside every unit (parasha-like)
    units = Units(np.array(["a", "b", "c"], dtype=object), np.array([0, 3, 6]), np.array([2, 5, 8]))
    links = _unit_links(
        [
            (0, 0, 3, 3, "verse", "dev"),  # a<->b: two distinct verse links -> gold
            (3, 3, 0, 0, "verse", "dev"),
            (1, 1, 4, 4, "verse", "dev"),
            (4, 4, 1, 1, "verse", "dev"),
            (0, 0, 6, 6, "verse", "dev"),  # a<->c: only one link -> not gold
            (6, 6, 0, 0, "verse", "dev"),
            (0, 0, 1, 1, "verse", "dev"),  # same unit -> ignored
            (2, 2, 9, 9, "verse", "dev"),  # target outside the units -> ignored
            (7, 7, 8, 8, "verse", "test"),
            (5, 6, 1, 1, "unit", "dev"),  # range overlaps b and c -> b->a, c->a
        ]
    )
    gold = unit_gold(links, units, "dev", m=2)
    assert gold == {0: {1}, 1: {0}, 2: {0}}
    assert unit_gold(links, units, "dev", m=1)[0] == {1, 2}
    assert unit_gold(links, units, "train", m=1) == {}


def test_test_split_runs_once_and_only_final_systems(tmp_path):
    cfg = load_config()
    proc, art = tmp_path / "processed", tmp_path / "artifacts"
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art)}
    cfg["final_systems"] = {**cfg["final_systems"], "lexical": "good", "semantic": "sem"}
    proc.mkdir()
    pd.DataFrame(
        {
            "verse_id": range(8),
            "book_id": [0] * 4 + [1] * 4,
            "chapter": [1] * 8,
            "ref": [f"R {i}" for i in range(8)],
        }
    ).to_parquet(proc / "verses.parquet")
    _links([(0, 4, "verse", "test"), (4, 0, "verse", "test")]).to_parquet(proc / "links.parquet")
    verse_dir = art / "topk" / "verse"
    verse_dir.mkdir(parents=True)
    _topk([(0, 4, 9), (4, 0, 5)]).to_parquet(verse_dir / "good.parquet")
    _topk([(0, 7, 9)]).to_parquet(verse_dir / "other.parquet")

    metrics = run_evaluate(cfg, "test", log=lambda _: None)
    assert list(metrics["splits"]["test"]["results"]["verse"]) == ["good"]
    assert metrics["splits"]["test"]["gold"]["verse"] == {"queries": 2, "pairs": 2}
    with pytest.raises(RuntimeError, match="once"):
        run_evaluate(cfg, "test", log=lambda _: None)
    run_evaluate(cfg, "test", log=lambda _: None, force=True)
