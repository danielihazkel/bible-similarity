"""The P / non-P split of Genesis-Numbers (`bsim pentateuch`, `/pentateuch`, DESIGN.md §16.43)."""

import json
import sqlite3

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.pentateuch import (
    choice_matrix,
    chunk_ids,
    circular,
    first_component,
    kappa,
    name_gap,
    run_pentateuch,
    smooth_within,
    verse_tokens,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.data.canon import BY_SEFARIA
from bsim.fixture import fixture_encoder


def test_tokens_hold_out_the_names():
    words = pd.DataFrame(
        {
            "verse_id": [0, 0, 0, 1],
            "lemma": ["c/1696", "3068", "l/430", "3205"],
            "morph": ["HC/Vpw3ms", "HNp", "HR/Ncmpa", "HVhw3ms"],
        }
    )
    toks, n_words, names, func = verse_tokens(words, {"3068", "430"}, {"C", "R"})
    assert toks[0] == {"p:c": 1, "1696": 1, "1696@p": 1, "p:l": 1}
    assert toks[1] == {"3205": 1, "3205@h": 1}
    assert n_words == {0: 3, 1: 1} and names == {0: (1, 1)}
    assert func == {"p:c": 1, "p:l": 1}


def test_chunks_choices_and_component():
    assert chunk_ids(np.array([0, 0, 0, 1, 1]), 2).tolist() == [0, 0, 1, 2, 2]
    # two sets of two members; row 0 picks the first of each, row 1 the second, row 2 neither
    counts = np.array([[3, 0, 2, 0], [0, 3, 0, 2], [0, 0, 0, 0]], float)
    x = choice_matrix(counts, [[0, 1], [2, 3]])
    assert x[0, 0] == pytest.approx(0.5) and x[1, 0] == pytest.approx(-0.5)
    assert (x[2] == 0).all()
    s = first_component(x)
    assert np.sign(s[0]) == -np.sign(s[1]) and abs(s[2]) < abs(s[0])


def test_kappa_names_and_shifts():
    a = np.array([1, 1, 0, 0], bool)
    assert kappa(a, a) == pytest.approx(1.0) and kappa(a, ~a) == pytest.approx(-1.0)
    side = np.array([True, True, False, False])
    # P-like side: 0 of 4 names are יהוה, the other side 2 of 2
    assert name_gap(side, np.array([0.0, 0, 1, 1]), np.array([2.0, 2, 0, 0])) == pytest.approx(1)
    rng = np.random.default_rng(0)
    book = np.array([0, 0, 0, 1, 1, 1])
    s = np.array([1, 0, 0, 1, 1, 0], bool)
    shifted = circular(s, book, rng)
    assert shifted[:3].sum() == 1 and shifted[3:].sum() == 2  # the runs stay in their book
    p = np.array([0.0, 1, 0, 1])
    assert smooth_within(p, np.array([0, 0, 1, 1]), 1).tolist() == [0.5, 0.5, 0.5, 0.5]
    assert smooth_within(p, np.array([0, 0, 1, 1]), 0).tolist() == p.tolist()


P_WORDS = [("589", "HPp1cs"), ("5712", "HNcfsc"), ("854", "HR"), ("430", "HNcmpa")]
NON_WORDS = [("595", "HPp1cs"), ("6951", "HNcmsc"), ("5973", "HR"), ("3068", "HNp")]


def write_toy(tmp_path):
    """Four books of 60 verses; P verses say אני, עדה, את (with) and אלהים, the others אנכי, קהל,
    עם and יהוה. P: Genesis 1-20, Exodus 1-30, all of Leviticus, Numbers 1-40."""
    p_until = {"Genesis": 20, "Exodus": 30, "Leviticus": 60, "Numbers": 40}
    rng = np.random.default_rng(3)
    verses, words = [], []
    vid = 0
    for name, cut in p_until.items():
        b = BY_SEFARIA[name].book_id
        for v in range(1, 61):
            marks = P_WORDS if v <= cut else NON_WORDS
            toks = [(str(9000 + int(rng.integers(0, 50))), "HNcmsa") for _ in range(6)]
            toks += [marks[i] for i in rng.choice(4, 2, replace=False)]
            verses.append((vid, b, 1, v))
            for i, (lem, morph) in enumerate(toks):
                words.append((vid, i, lem, morph))
            vid += 1
    proc = tmp_path / "processed"
    proc.mkdir()
    pd.DataFrame(verses, columns=["verse_id", "book_id", "chapter", "verse"]).to_parquet(
        proc / "verses.parquet"
    )
    pd.DataFrame(words, columns=["verse_id", "idx", "lemma", "morph"]).to_parquet(
        proc / "words.parquet"
    )
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc),
                    "artifacts": str(tmp_path / "artifacts")}  # fmt: skip
    cfg["pentateuch"] = {
        **cfg["pentateuch"],
        "synonyms": [["I", ["589", "595"]], ["congregation", ["5712", "6951"]],
                     ["with", ["854", "5973"]]],  # fmt: skip
        "n_function": 5,
        "p": [f"{n} 1:1-1:{c}" for n, c in p_until.items()],
        "unassigned": ["Numbers 1:41"],
        "names_window": ["Genesis 1:1-1:60", "Exodus 1:1-1:10"],
        "grid": {"chunk_verses": [10], "smooth": [2]},
        "draws": 199,
    }
    return cfg


def test_stage_on_a_toy_pentateuch(tmp_path):
    out = run_pentateuch(write_toy(tmp_path), log=lambda _: None)
    meta = json.loads((out / "pentateuch.meta.json").read_text("utf-8"))
    assert meta["verses"] == 240 and meta["assigned"] == 239 and meta["reference_p"] == 150
    t = meta["tests"]
    assert t["kappa"]["observed"] > 0.8 and t["kappa"]["p"] <= 0.05
    assert t["kappa_genesis"]["observed"] > 0.8 and t["kappa_genesis"]["p"] <= 0.05
    # the names were never features, yet the P-like side avoids יהוה
    assert meta["names"]["p_like"]["share"] < 0.1 < 0.9 < meta["names"]["non_p"]["share"]
    assert t["names"]["p"] <= 0.05
    assert {f["token"] for f in meta["features"]["p_like"][:3]} <= {"589", "5712", "854"}
    assert all(f["token"] not in ("430", "3068") for s in meta["features"].values() for f in s)
    assert len(meta["grid"]) == 1
    v = pd.read_parquet(out / "verses.parquet")
    lev = v[v.book_id == BY_SEFARIA["Leviticus"].book_id]
    assert (lev.side == "P").mean() > 0.9  # the side holding most of Leviticus is P-like
    assert v.reference.isna().sum() == 1
    ch = pd.read_parquet(out / "chapters.parquet")
    lev_id = BY_SEFARIA["Leviticus"].book_id
    assert len(ch) == 4 and ch.loc[ch.book_id == lev_id, "p_ref"].item() == 1


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_pentateuch_endpoints(client):
    r = client.get("/api/pentateuch").json()
    assert r["meta"]["tests"]["kappa"]["observed"] == 0.6 and "features" not in r["meta"]
    assert [w["token"] for w in r["p_like"]] == ["7225", "p:l"]
    assert r["p_like"][1]["he"] == "ל" and r["p_like"][0]["he"] is not None
    assert r["synonyms"][0]["he"][1] is not None  # 3068@q: the stem marker dropped for the lemma
    page = client.get("/api/pentateuch/chapters").json()
    assert page["total"] == 3 and page["items"][0]["unit_id"] == "c:0:1"
    assert page["items"][2]["p_ref"] is None
    assert client.get("/api/pentateuch/chapters?book=1").json()["total"] == 1
    assert client.get("/api/pentateuch/chapters?limit=0").status_code == 422
    csv = client.get("/api/export/pentateuch.csv").text
    assert "p_like" in csv.splitlines()[0] and len(csv.splitlines()) == 4


def test_pentateuch_reader_findings_and_dossier(client):
    v0, v1, v2 = client.get("/api/reader/c:0:1").json()["verses"]
    assert v0["source"] == {"side": "P", "prob": 0.9, "reference": "P"}
    assert v1["source"]["reference"] == "nonP"
    assert client.get("/api/reader/c:1:1").json()["verses"][0]["source"]["reference"] is None
    f = {x["key"]: x for x in client.get("/api/findings").json()["items"]}
    assert f["pentateuch_split"]["verdict"] == "holds"
    assert f["pentateuch_genesis"]["verdict"] == "holds"
    assert f["pentateuch_names"]["verdict"] == "fails"
    assert f["pentateuch_names"]["values"]["p_like"] == 0.25
    d = {e["kind"]: e for e in client.get("/api/dossier/c:0:1").json()["entries"]}
    assert d["pentateuch"]["computed"] and d["pentateuch"]["count"] == 3


def test_without_the_stage(built):
    cfg, db = built
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM pentateuch_verses")
        conn.execute("DELETE FROM pentateuch_chapters")
        conn.execute("UPDATE meta SET value = '{}' WHERE key = 'pentateuch'")
    c = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    assert c.get("/api/pentateuch/chapters").json()["total"] == 0
    assert c.get("/api/pentateuch").json()["p_like"] == []
    keys = {x["key"] for x in c.get("/api/findings").json()["items"]}
    assert not keys & {"pentateuch_split", "pentateuch_genesis", "pentateuch_names"}
    assert all(v["source"] is None for v in c.get("/api/reader/c:0:1").json()["verses"])
