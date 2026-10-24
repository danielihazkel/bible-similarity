"""Haftarot (`bsim haftarot`, `/haftarot`, DESIGN.md §16.69)."""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import bsim.analysis.haftarot as H
from bsim.analysis.haftarot import (
    best_rank,
    chapters_of,
    label_p,
    parts,
    ranks,
    ref_of,
    rrf_scores,
    shuffle_p,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder


def test_parts_and_refs():
    one = {"k": "Isaiah", "b": "54:1", "e": "55:5"}
    assert parts(one) == [one] and parts([one, one]) == [one, one] and parts(None) == []
    assert ref_of(one) == "Isaiah 54:1-55:5"


def test_chapters_of():
    start, end = np.array([0, 10, 20]), np.array([9, 19, 29])
    # 7 verses in the first chapter, 2 in the second: only the first holds three
    assert chapters_of([3, 4, 5, 6, 7, 8, 9, 10, 11], start, end, 3) == [0]
    assert chapters_of([5, 6, 7, 10, 11, 12], start, end, 3) == [0, 1]
    # none holds three: the one holding most
    assert chapters_of([9, 10, 11], start, end, 3) == [1]


def test_ranks_and_fusion():
    s = np.array([[0.1, 0.9, 0.5], [0.3, 0.3, 0.2]])
    assert ranks(s).tolist() == [[3, 1, 2], [1, 2, 3]]
    assert best_rank(ranks(s)[0], [0, 2]) == 2
    f = rrf_scores(s, s[:, ::-1], 60, 1.0, 1.0)
    # the column both lists put first wins; the two each list puts last but one tie
    assert f[0][1] > f[0][0] and f[0][0] == pytest.approx(f[0][2])


def test_shuffle_and_label_p():
    rng = np.random.default_rng(3)
    # three parashot each ranking its own haftarah's chapter first, another's last
    rank_rows = np.array([[1, 3, 2], [3, 1, 2], [2, 3, 1]])
    gold = [[0], [1], [2]]
    pct = np.zeros(3)
    null, p = shuffle_p(pct, gold, rank_rows, 999, rng)
    assert null > 0 and p < 0.2
    first_two = np.array([True, True, False, False])
    diff, p2 = label_p(np.array([0.0, 0.1, 0.9, 0.8]), first_two, 999, rng)
    assert diff == pytest.approx(0.8) and p2 < 0.2


def corpus(tmp_path):
    """Genesis 1:1-2 (two parashot), Joshua 1-2 and Judges 1 (three chapters of the Prophets)."""
    v = pd.DataFrame({"verse_id": range(9), "book_id": [0, 0, 5, 5, 5, 5, 5, 5, 6],
                      "chapter": [1, 1, 1, 1, 1, 2, 2, 2, 1],
                      "verse": [1, 2, 1, 2, 3, 1, 2, 3, 1]})  # fmt: skip
    units = pd.DataFrame({
        "unit_id": ["p:A", "p:B", "c:5:1", "c:5:2", "c:6:1", "c:0:1"],
        "unit_type": ["parasha", "parasha", "chapter", "chapter", "chapter", "chapter"],
        "start_verse_id": [0, 1, 2, 5, 8, 0], "end_verse_id": [0, 1, 4, 7, 8, 1],
    })  # fmt: skip
    proc, raw = tmp_path / "processed", tmp_path / "raw" / "leyning"
    proc.mkdir()
    raw.mkdir(parents=True)
    v.to_parquet(proc / "verses.parquet")
    units.to_parquet(proc / "units.parquet")
    leyning = {
        "A": {"num": 1, "haft": {"k": "Joshua", "b": "1:1", "e": "1:3"}},
        "B": {"num": 2, "haft": {"k": "Joshua", "b": "2:1", "e": "2:3"},
              "seph": {"k": "Judges", "b": "1:1", "e": "1:1"}, "haftTheme": {"consolation": 1}},
        "A-B": {"num": [1, 2]},
    }  # fmt: skip
    (raw / "aliyot.json").write_text(json.dumps(leyning), "utf-8")
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "data_raw": str(tmp_path / "raw"),
                    "artifacts": str(tmp_path / "artifacts")}  # fmt: skip
    cfg["haftarot"] = {**cfg["haftarot"], "shuffles": 99, "list": 2, "known": ["A"],
                       "known_rank": 1}  # fmt: skip
    return cfg


def test_run_haftarot(tmp_path, monkeypatch):
    cfg = corpus(tmp_path)
    # A's haftarah (Joshua 1) ranks first on both lists; B's (Joshua 2) second
    lex = np.array([[0.9, 0.1, 0.2], [0.8, 0.5, 0.1]])
    scores = {"lexical": lex, "semantic": lex.copy()}
    monkeypatch.setattr(H, "score_matrices", lambda cfg, par, chap: scores)
    H.run_haftarot(cfg, log=lambda _: None)
    out = tmp_path / "artifacts" / "haftarot"
    d = pd.read_parquet(out / "pairs.parquet")
    assert d.parasha.tolist() == ["p:A", "p:B"] and d.name.tolist() == ["A", "B"]
    assert d.chapters.tolist() == ['["c:5:1"]', '["c:5:2"]']
    assert d.rank_fused.tolist() == [1, 2] and d.pct.tolist() == [0.0, 0.5]
    assert d.theme.fillna("-").tolist() == ["-", "consolation"]
    assert d.seph.fillna("-").tolist() == ["-", "Judges 1:1-1:1"]
    lists = pd.read_parquet(out / "lists.parquet")
    assert lists[lists.parasha == "p:B"].chapter.tolist() == ["c:5:1", "c:5:2"]
    assert lists[lists.parasha == "p:B"].haftarah.tolist() == [False, True]
    meta = json.loads((out / "haftarot.meta.json").read_text("utf-8"))
    assert meta["thematic"] == 1 and meta["candidates"] == 3
    assert meta["modes"]["lexical"]["mrr"] == 1.0 and meta["known_holds"]


def test_run_haftarot_needs_every_parasha(tmp_path, monkeypatch):
    cfg = corpus(tmp_path)
    p = tmp_path / "raw" / "leyning" / "aliyot.json"
    p.write_text(json.dumps({"A": {"num": 1, "haft": {"k": "Joshua", "b": "1:1", "e": "1:3"}}}))
    with pytest.raises(RuntimeError, match="2 parasha units against 1"):
        H.run_haftarot(cfg, log=lambda _: None)


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_haftarot_endpoint(client):
    r = client.get("/api/haftarot").json()
    assert r["holds"] and not r["calendar_holds"] and r["known_holds"]
    assert r["modes"]["fused"]["mrr"] == 1.0
    first, second = r["parashot"]
    assert (first["parasha"], first["theme"], first["rank_fused"]) == ("p:Bereshit", None, 1)
    assert first["chapters"] == ["c:1:1"] and first["chapter_labels"]
    assert [c["unit_id"] for c in first["top"]] == ["c:1:1", "c:0:2"]
    assert [c["haftarah"] for c in second["top"]] == [False, True]
    assert second["theme"] == "admonition" and second["seph"] is None


def test_haftarot_findings(client):
    found = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    assert found["haftarot_claim"]["verdict"] == "holds"
    assert found["haftarot_claim"]["values"]["fused_mrr"] == 1.0
    assert found["haftarot_calendar"]["verdict"] == "fails"
    assert found["haftarot_known"]["values"] == {"known": 1, "known_rank": 10, "found": 1,
                                                 "rank_0": 1}  # fmt: skip
