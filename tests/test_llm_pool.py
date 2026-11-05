"""The judged dev pool (series L3, §16.83): the pool, the judged gold scored on condensed
lists, the run with a fake batch client, and the rule that dev judgements never train."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from bsim.config import load_config, resolve_path
from bsim.eval import llm_pool as lp
from bsim.eval.metrics import per_query
from bsim.train.pairs import extra_links
from llm_fakes import fake_client


def _list(rows):
    return pd.DataFrame(rows, columns=["src", "tgt", "rank"])


def test_pool_pairs():
    lex = _list([(1, 2, 1), (1, 3, 2), (1, 4, 3), (9, 8, 1)])
    sem = _list([(1, 3, 1), (1, 5, 2), (2, 1, 1)])
    gold = {1: {4}, 2: {7}}
    pool = lp.pool_pairs({"lex": lex, "sem": sem}, {1, 2}, gold, 2, lambda df: df)
    # (1, 4) is Sefaria's, query 9 is not a dev query, (2, 1) is (1, 2) again
    assert list(zip(pool.a, pool.b, pool.systems, strict=True)) == [
        (1, 2, "lex,sem"),
        (1, 3, "lex,sem"),
        (1, 5, "sem"),
    ]
    # the filter runs before the depth: a dropped neighbour lets the next target in
    drop2 = lp.pool_pairs({"lex": lex}, {1}, {}, 2, lambda df: df[df.tgt != 2])
    assert list(zip(drop2.a, drop2.b, strict=True)) == [(1, 3), (1, 4)]


def _judged(rows):
    return pd.DataFrame(rows, columns=["a", "b", "status", "verdict"])


def test_judged_gold_and_condensed_lists():
    sef = {1: {4}, 2: {7}, 5: set()}
    judged = _judged(
        [(1, 2, "ok", "real"), (1, 3, "ok", "not"), (1, 6, "ok", "unsure"),
         (2, 9, "errored", None), (8, 9, "ok", "real")]
    )  # fmt: skip
    g = lp.judged_gold(sef, judged)
    assert g.relevant == {1: {2, 4}, 2: {1, 7}}  # both directions, Sefaria's queries only
    assert g.judged == {1: {2, 3, 4}, 2: {1, 7}}  # unsure and errored are unjudged
    ranked = {1: [6, 3, 2, 4, 11], 2: [9, 7, 1]}
    cond = g.condensed(ranked)
    assert cond == {1: [3, 2, 4], 2: [7, 1]}
    assert g.coverage(ranked, 2) == 0.5  # of 1's (6, 3) and 2's (9, 7): 3 and 7
    pq = per_query(cond, g.relevant, "ndcg@10")
    assert pq[2] == 1.0 and 0 < pq[1] < 1
    # an unsure counted as not relevant instead
    g2 = lp.judged_gold(sef, judged, unsure="not")
    assert g2.judged[1] == {2, 3, 4, 6}


def test_p_at():
    assert lp.p_at([1, 2, 3], {2}, 5) == 0.2
    assert lp.p_at([], {2}, 5) == 0.0


def test_dev_judgements_never_train():
    with pytest.raises(RuntimeError, match="never trains"):
        extra_links(load_config(), "llm_pool")


@pytest.fixture
def run_cfg(tmp_path, monkeypatch):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "artifacts": str(tmp_path / "artifacts")}
    items = pd.DataFrame(
        {
            "set": ["calibration"] * 4 + ["pool"] * 3,
            "custom_id": ["cal-0", "cal-1", "cal-2", "cal-3", "pool-0", "pool-1", "pool-2"],
            "a": [0, 1, 2, 3, 0, 1, 2],
            "b": [5, 6, 7, 8, 3, 2, 9],
            "gold": [True, True, False, False, None, None, None],
            "systems": [None] * 4 + ["fused", "lexical,fused", "semantic"],
        }
    )
    monkeypatch.setattr(lp, "build_items", lambda cfg, log: items)
    monkeypatch.setattr(
        lp, "verse_texts", lambda cfg: {i: {"ref": f"R {i}", "text": "א"} for i in range(10)}
    )
    return cfg


def _ans(verdict, p):
    return {"verdict": verdict, "p_real": p, "kind": "allusion", "rationale": "שמים"}


def test_dry_run_sends_nothing(run_cfg):
    client, batches = fake_client({})
    out = lp.run_llm_pool(run_cfg, log=lambda s: None, dry_run=True, client=client)
    assert out["dry_run"] and out["requests"] == 7 and batches.created == []
    assert out["budget_usd"] == run_cfg["llm_pool"]["budget_usd"]


def test_a_run_collected(run_cfg):
    answers = {
        "cal-0": _ans("real", 0.9), "cal-1": _ans("not", 0.6), "cal-2": _ans("not", 0.2),
        "cal-3": _ans("not", 0.1), "pool-0": _ans("real", 0.8), "pool-1": _ans("unsure", 0.5),
        "pool-2": None,
    }  # fmt: skip
    client, _ = fake_client(answers)
    meta = lp.run_llm_pool(run_cfg, log=lambda s: None, client=client, sleep=lambda s: None)
    c = meta["calibration"]
    assert (c["auc"], c["holds"], c["recall"]) == (1.0, True, 0.5)
    assert meta["pool"]["verdicts"] == {"real": 1, "not": 0, "unsure": 1}
    out = resolve_path(run_cfg, "artifacts") / "llm_pool"
    judged = pd.read_parquet(out / "judged.parquet")
    assert judged.status.tolist() == ["ok", "ok", "errored"]
    assert judged.systems.tolist() == ["fused", "lexical,fused", "semantic"]
    g = lp.load_judged_gold(run_cfg, {0: {5}, 1: {6}}, log=lambda s: None)
    assert g is not None and g.relevant == {0: {3, 5}, 1: {6}}
    # a failed calibration: no gold
    meta_path = out / "llm_pool.meta.json"
    m = json.loads(meta_path.read_text("utf-8"))
    m["calibration"]["holds"] = False
    meta_path.write_text(json.dumps(m), "utf-8")
    said = []
    assert lp.load_judged_gold(run_cfg, {0: {5}}, log=said.append) is None
    assert "calibration failed" in said[0]


def test_no_run_no_gold(tmp_path):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "artifacts": str(tmp_path)}
    said = []
    assert lp.load_judged_gold(cfg, {}, log=said.append) is None and "missing" in said[0]
