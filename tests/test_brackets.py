"""Resumptive repetition (`bsim brackets`, `/brackets`, DESIGN.md §16.67)."""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from scipy import sparse

from bsim.analysis.brackets import (
    Tok,
    candidates,
    insertion,
    mutual_best,
    prefix_sums,
    run_brackets,
)
from bsim.analysis.structure import embeddings_path
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder


def test_tok_matches_by_lemma_or_form():
    # Ezra 4:5 / 4:24: Hebrew and Aramaic lemmas differ, the forms agree
    assert Tok("4428", "מלכ") == Tok("4430", "מלכ")
    assert Tok("559", "ויאמר") == Tok("559", "אמר")
    assert Tok("559", "אמר") != Tok("1696", "דבר")


def test_candidates():
    # five verses of one book, then one of another; verse 0 and 3 share two lemmas and a form
    lem = sparse.csr_matrix(np.array([[1, 1, 0], [0, 0, 1], [0, 0, 1], [1, 1, 0], [0, 0, 0],
                                      [1, 1, 0]]))  # fmt: skip
    form = sparse.csr_matrix(np.array([[1], [0], [0], [1], [0], [1]]))
    book = np.array([0, 0, 0, 0, 0, 1])
    assert candidates(lem, form, book, 2, 4, 3).tolist() == [[0, 3]]
    # verse 5 shares as much with 3 but lies in another book; 2 apart is too near
    assert candidates(lem, form, book, 1, 4, 1).tolist() == [[1, 2], [0, 3]]


def test_mutual_best():
    pairs = pd.DataFrame({"a": [0, 0, 5], "b": [9, 12, 12], "score": [20.0, 15.0, 30.0]})
    # 0's best is 9 and 9's is 0; 12's best is 5, so 0 / 12 goes
    assert mutual_best(pairs)[["a", "b"]].values.tolist() == [[0, 9], [5, 12]]


def test_insertion():
    # before (0-1) and after (5-6) alike, the block (3) apart: high; a block like them: low
    m = np.array([[1, 0], [1, 0], [9, 9], [0, 1], [9, 9], [1, 0], [1, 0]], dtype=float)
    p = prefix_sums(m)
    a, b = np.array([2]), np.array([4])
    assert insertion(p, a, b, 2)[0] == pytest.approx(1.0)
    m[3] = [1, 0]
    assert insertion(prefix_sums(m), a, b, 2)[0] == pytest.approx(0.0)


def corpus(tmp_path):
    """One book of 100 verses: 10 and 20 share a clause of rare words, the block between them
    talks of other things than the verses around it."""
    rows = []
    letters = str.maketrans("0123456789", "אבגדהוזחטי")  # a form of its own for each lemma

    def verse(vid, lemmas):
        rows.extend((vid, k, x.translate(letters), x, [x], "HNcmsa") for k, x in enumerate(lemmas))

    for v in range(100):
        inside = 11 <= v <= 19
        verse(v, [f"{'9' if inside else '8'}{v % 3}", f"{'9' if inside else '8'}{(v + 1) % 3}"])
    rows = [r for r in rows if r[0] not in (10, 20)]
    for v in (10, 20):
        verse(v, ["501", "502", "503", "504"])
    words = pd.DataFrame(rows, columns=["verse_id", "idx", "surface", "lemma", "content_lemmas",
                                        "morph"])  # fmt: skip
    words["display_idx"] = words.idx
    proc = tmp_path / "processed"
    proc.mkdir()
    words.to_parquet(proc / "words.parquet")
    pd.DataFrame({"verse_id": range(100), "book_id": 0, "chapter": 1,
                  "verse": range(1, 101)}).to_parquet(proc / "verses.parquet")  # fmt: skip
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc),
                    "artifacts": str(tmp_path / "artifacts")}  # fmt: skip
    emb = np.zeros((100, 4))
    emb[:, 0] = 1
    emb[11:20, 0], emb[11:20, 1] = 0, 1
    path = embeddings_path(cfg)
    path.parent.mkdir(parents=True)
    np.save(path, emb)
    cfg["brackets"] = {**cfg["brackets"], "draws": 99, "lex_dims": 64, "min_score": 5,
                       "known": [{"a": "Genesis 1:11", "b": "Genesis 1:21"},
                                 {"a": "Genesis 1:1", "b": "Genesis 1:5"}]}  # fmt: skip
    return cfg


def test_run_brackets(tmp_path):
    cfg = corpus(tmp_path)
    run_brackets(cfg, log=lambda _: None)
    out = tmp_path / "artifacts" / "brackets"
    d = pd.read_parquet(out / "brackets.parquet")
    assert d[["a", "b", "n_between", "n_tokens"]].values.tolist() == [[10, 20, 9, 4]]
    assert json.loads(d.a_disp[0]) == [0, 1, 2, 3]
    row = d.iloc[0]
    # the block shares neither words nor meaning with the verses around it
    assert row["sem"] == pytest.approx(1.0) and row["lex"] > 0.8
    assert row.p < 0.05 and bool(row.known)
    meta = json.loads((out / "brackets.meta.json").read_text("utf-8"))
    # one bracket: the claim is its own test
    assert meta["mean"] == pytest.approx(row.insertion, abs=1e-4) and meta["p"] == row.p
    # the known: the first found and beyond chance, the second not found
    assert [(k["found"], k["beats"]) for k in meta["known"]] == [(True, True), (False, False)]
    assert not meta["known_holds"]


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_brackets_endpoints(client):
    r = client.get("/api/brackets").json()
    assert r["holds"] and not r["known_holds"] and r["strong"] == 1
    assert r["books"] == [{"book_id": 0, "brackets": 2, "strong": 1}]
    page = client.get("/api/brackets/items").json()
    assert page["total"] == 2 and [i["bracket"] for i in page["items"]] == [0, 1]
    first = page["items"][0]
    assert (first["a"]["verse_id"], first["b"]["verse_id"], first["a_disp"]) == (0, 4, [1, 2])
    assert first["unit_id"] == "c:0:1" and first["known"]
    strong = client.get("/api/brackets/items?show=strong").json()
    assert [i["bracket"] for i in strong["items"]] == [0]
    assert client.get("/api/brackets/items?show=known&book=1").json()["total"] == 0
    weakest = client.get("/api/brackets/items?order=strongest&limit=1&offset=1").json()
    assert [i["bracket"] for i in weakest["items"]] == [1]
    assert client.get("/api/brackets/items?show=nope").status_code == 422


def test_brackets_findings(client):
    found = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    assert found["brackets_insertion"]["verdict"] == "holds"
    assert found["brackets_known"]["verdict"] == "fails"
    assert found["brackets_known"]["values"] == {"known_found": 1, "known_beat": 1, "known": 2}
