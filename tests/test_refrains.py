"""Refrains (`bsim refrains`, `/refrains`, DESIGN.md §16.40)."""

import json
import sqlite3

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.refrains import (
    extend,
    fdr,
    find_runs,
    run_refrains,
    seeds,
    spacing_p,
    token_stream,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder

REFRAIN = [("1000", "HVqp3ms"), ("2000", "HNcmsa"), ("3000", "HNcmsa")]
NAMED = [("4000", "HNpm"), ("1121", "HNcmsc"), ("5000", "HNpm")]  # X son of Y: one content word


def write_toy(tmp_path, refrain_at, named_at, turns_after):
    """Two books of filler words; the refrain (prefixed ו in one verse) in book 0."""
    rng = np.random.default_rng(1)
    verses, words = [], []
    n = 300
    for v in range(n + 40):
        book = 0 if v < n else 1
        toks = [(str(10000 + int(rng.integers(0, 400))), "HNcmsa") for _ in range(8)]
        if v in refrain_at:
            toks[2:2] = REFRAIN
        if v in named_at:
            toks[5:5] = NAMED
        ref = f"B{book} 1:{(v if book == 0 else v - n) + 1}"
        verses.append((v, book, ref, [f"w{v}_{i}" for i in range(len(toks))]))
        for i, (lem, morph) in enumerate(toks):
            if v == refrain_at[1] and lem == "1000":
                lem, morph = "c/1000", "HC/Vqp3ms"  # ו + the verb: the prefix drops out
            words.append((v, i, lem, morph, i))
    proc = tmp_path / "processed"
    proc.mkdir()
    pd.DataFrame(verses, columns=["verse_id", "book_id", "ref", "display_tokens"]).to_parquet(
        proc / "verses.parquet"
    )
    pd.DataFrame(words, columns=["verse_id", "idx", "lemma", "morph", "display_idx"]).to_parquet(
        proc / "words.parquet"
    )
    seg = tmp_path / "artifacts" / "segments"
    seg.mkdir(parents=True)
    score = [0.95 if v - 1 in turns_after else 0.3 for v in range(1, n)]
    pd.DataFrame({"verse_id": range(1, n), "score": score}).to_parquet(seg / "gaps.parquet")
    cfg = load_config()
    art = str(tmp_path / "artifacts")
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": art}
    cfg["refrains"] = {
        **cfg["refrains"],
        "shuffles": 5,
        "draws": 200,
        "known": [["R", ["B0 1:6", "B0 1:11", "B0 1:16"]], ["S", ["B1 1:1", "B1 1:2", "B1 1:3"]]],
    }
    return cfg


def test_tokens_drop_prefixes_and_names_are_not_content():
    w = pd.DataFrame(
        {"verse_id": [0, 0, 0], "idx": [0, 1, 2], "lemma": ["c/3808", "7725", "4000"],
         "morph": ["HC/Td", "HVqp2mp", "HNpm"]}  # fmt: skip
    )
    t = token_stream(w)
    assert t.lemma.tolist() == ["3808", "7725", "4000"]
    assert t.content.tolist() == [False, True, False]
    assert t.pos.tolist() == [0, 1, 2]


def test_seeds_need_content_words():
    t = pd.DataFrame(
        {"verse_id": [0] * 4 + [1] * 3, "idx": [0, 1, 2, 3, 0, 1, 2],
         "lemma": ["a", "b", "c", "d", "a", "b", "c"],
         "content": [True, True, False, False, True, True, False],
         "pos": [0, 1, 2, 3, 0, 1, 2]}  # fmt: skip
    )
    g = seeds(t, 3, 2)
    # a b c in both verses; b c d has one content word; nothing spans the two verses
    assert len(g) == 2 and g.key.nunique() == 1 and g.start.tolist() == [0, 0]


def test_runs_burst_and_chance():
    g = pd.DataFrame(
        {"key": [1, 1, 1, 1, 2, 2, 2], "verse_id": [5, 10, 15, 90, 1, 50, 99],
         "book_id": 0, "df": [4, 4, 4, 4, 3, 3, 3]}  # fmt: skip
    )
    runs = find_runs(g, np.array([100]), 20, 3)
    # seed 1: three verses within 20 of each other (90 is too far); seed 2 is spread out
    assert runs.verses.tolist() == [(5, 10, 15)] and runs.p[0] < 0.05
    q = fdr(np.array([0.001, 0.01, 0.5]), [np.array([0.2]), np.array([0.005, 0.6])])
    assert q[0] == 0 and q[1] == pytest.approx(0.25) and q[2] >= q[1]


def test_extend_and_spacing():
    lemmas = {
        0: ["x", "a", "b", "c", "d"],
        1: ["a", "b", "c", "d", "y"],
        2: ["z", "a", "b", "c", "e"],
    }
    starts, n = extend((0, 1, 2), [1, 0, 1], 3, lemmas)
    assert starts == [1, 0, 1] and n == 3  # d is not in verse 2
    starts, n = extend((0, 1), [1, 0], 3, lemmas)
    assert n == 4
    rng = np.random.default_rng(0)
    cv, p = spacing_p([10, 20, 30, 40, 50], 500, 0.05, rng)
    assert cv == 0 and p <= 0.05
    assert spacing_p([1, 2, 3], 500, 0.05, rng)[1] is None  # one placement only
    assert spacing_p([1, 4, 8], 500, 0.05, rng)[1] is None  # too few to reach 0.05


def test_run_refrains(tmp_path):
    at = [5, 10, 15, 20, 25]
    cfg = write_toy(tmp_path, at, [30, 33, 36], turns_after=at)
    out = run_refrains(cfg, log=lambda _: None)
    ref = pd.read_parquet(out / "refrains.parquet")
    meta = json.loads((out / "refrains.meta.json").read_text(encoding="utf-8"))
    top = ref.iloc[0]
    assert (top.k, top.first_vid, top.last_vid) == (5, 5, 25) and top.lemmas == "1000 2000 3000"
    assert top.strongest and top.known == "R" and top.regular_p <= 0.05
    assert top.text == "w5_2 w5_3 w5_4"
    occ = pd.read_parquet(out / "occurrences.parquet")
    assert occ[occ.refrain_id == top.refrain_id][["first", "last"]].values.tolist() == [[2, 4]] * 5
    # a man named through his story (name, son, name) is not a refrain
    assert not ref.lemmas.str.contains("4000").any()
    assert meta["known_found"] == 1 and meta["known"][1]["refrain_id"] is None
    assert meta["detect"]["observed"] >= 1 and meta["regular"]["regular"] >= 1
    assert meta["turns"]["observed"] > meta["turns"]["expected"] and meta["turns"]["p"] <= 0.05


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_refrains_api(client):
    r = client.get("/api/refrains").json()
    assert r["meta"]["detect"] == {"observed": 2, "expected": 0.1}
    assert [k["refrain_id"] for k in r["known"]] == [1, None]
    assert r["books"] == [{"book_id": 0, "refrains": 2, "strongest": 1}]
    page = client.get("/api/refrains/list").json()
    assert [i["refrain_id"] for i in page["items"]] == [1]  # the strongest of each group
    every = client.get("/api/refrains/list?strongest=false").json()
    assert every["total"] == 2
    first = every["items"][0]
    assert [o["verse_id"] for o in first["occurrences"]] == [0, 1, 2]
    assert len(first["verses"]) == 3 and first["occurrences"][0]["first"] == 1
    unit = client.get("/api/refrains/list?strongest=false&unit=v:4").json()
    assert [i["refrain_id"] for i in unit["items"]] == [2]
    assert client.get("/api/refrains/list?known=true&strongest=false").json()["total"] == 1


def test_refrains_dossier_findings_export_reader(client):
    d = client.get("/api/dossier/v:2").json()["entries"]
    assert next(e for e in d if e["kind"] == "refrains")["count"] == 2
    f = {x["key"]: x for x in client.get("/api/findings").json()["items"]}
    assert f["refrains"]["verdict"] == "holds" and f["refrains"]["values"]["found"] == 1
    assert f["refrain_regular"]["verdict"] == "holds" and f["refrain_turns"]["verdict"] == "holds"
    csv = client.get("/api/export/refrains.csv?strongest=false").text
    assert "ויהי ערב ויהי בקר" in csv and "v:0; v:1; v:2" in csv
    r = client.get("/api/reader/c:0:1").json()
    assert [x["refrain_id"] for x in r["refrains"]] == [1, 2] and r["computed"]["refrains"]
    # v2 holds both; its first token keeps the stronger refrain
    assert r["verses"][2]["refrains"] == {"0": 0, "1": 0}


def test_refrains_in_db(built):
    _, db = built
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM refrain_verses").fetchone()[0] == 6
        meta = json.loads(
            conn.execute("SELECT value FROM meta WHERE key = 'refrains'").fetchone()[0]
        )
    assert meta["known_found"] == 1 and meta["known_share"] == 0.5
