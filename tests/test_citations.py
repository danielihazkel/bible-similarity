import json
import sqlite3

import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp
from fastapi.testclient import TestClient

from bsim.analysis.citations import (
    TORAH,
    allowed,
    best_sources,
    find_formulas,
    gold_rank,
    gold_targets,
)
from bsim.api.app import create_app
from bsim.fixture import fixture_encoder
from bsim.lexical.bm25 import Bm25Index

FAMILIES = {
    "written": {"pattern": "ככתוב|כתוב בספר", "target": "torah"},
    "word": {"pattern": "(דבר יהוה)( הוא)? אשר (דבר|קרא)", "target": "earlier"},
}


def test_find_formulas_keeps_the_first_family():
    verses = pd.DataFrame(
        {
            "verse_id": [0, 1, 2],
            "book_id": [0, 9, 9],
            "text_plain": [
                "ויאמר אלהים",
                "ככתוב בספר תורת משה",
                "כדבר יהוה אשר דבר ביד עבדו",
            ],
        }
    )
    f = find_formulas(verses, FAMILIES)
    assert f.values.tolist() == [[1, 9, "written", "ככתוב"], [2, 9, "word", "דבר יהוה אשר דבר"]]


def test_allowed_sources():
    book_of = np.array([0, 0, 4, 5, 5, 5])
    assert 0 in TORAH and 5 not in TORAH
    assert allowed("torah", 5, book_of, 2).tolist() == [True, True, True, False, False, False]
    assert allowed("earlier", 5, book_of, 2).tolist() == [True, True, True, True, False, False]


def _index(rows: list[list[float]]) -> Bm25Index:
    m = sp.csr_matrix(np.array(rows, dtype=np.float32))
    return Bm25Index(doc=m, query=m, vocab=[str(i) for i in range(m.shape[1])])


def test_best_sources_and_agreement():
    # verse 4 shares its words and its meaning with verse 0; verse 5 with nothing
    lex = [[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 1, 1], [1, 0, 0], [0, 0, 0]]
    emb = np.array([[1, 0], [0, 1], [0.6, 0.8], [0.7, 0.7], [1, 0], [0.6, 0.8]], dtype=np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    masks = [np.array([1, 1, 1, 1, 0, 0], dtype=bool)] * 2
    (c4, s4, a4), (c5, _, a5) = best_sources([4, 5], masks, _index(lex), emb, 2, 0)
    assert c4[0] == 0 and s4[0] > s4[1] and a4
    assert not a5  # no shared word: BM25 picks verse 0 by order, cosine picks verse 2
    assert best_sources([4], [np.zeros(6, dtype=bool)], _index(lex), emb, 2, 0) == [([], [], False)]


def test_gold():
    key = {(9, 21, 19): 100, (9, 22, 38): 140, (5, 6, 26): 7, (5, 6, 27): 8}
    gold = gold_targets([["I Kings 22:38", "I Kings 21:19", "Joshua 6:26-27"]], key)
    assert gold == {140: [(100, 100), (7, 8)]}
    assert gold_rank([50, 102, 7], gold[140], 2) == 2
    assert gold_rank([50, 60], gold[140], 2) is None


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_citations_api(client):
    c = client.get("/api/citations").json()
    assert c["meta"]["gold"]["resolved_right"] == 1
    assert c["books"] == [{"book_id": 0, "target_book": 0, "n": 1}]
    lst = client.get("/api/citations/list").json()
    assert lst["total"] == 2
    first = lst["items"][0]
    assert first["family"] == "word" and first["resolved"] and first["named"]
    assert first["target"]["verse_id"] == 0 and first["target_label"]
    assert [x["verse_id"] for x in first["candidates"]] == [0, 1]
    assert lst["items"][1]["resolved"] is False and lst["items"][1]["gold_rank"] is None
    assert client.get("/api/citations/list?resolved=true").json()["total"] == 1
    assert client.get("/api/citations/list?family=written&book=1").json()["total"] == 1
    # a unit holds the citing verse, or the source of a resolved citation
    assert client.get("/api/citations/list?unit=v:0").json()["total"] == 1
    assert client.get("/api/citations/list?unit=v:1").json()["total"] == 0
    assert client.get("/api/citations/list?family=x").status_code == 422


def test_dossier_citations(client):
    def count(unit):
        d = client.get(f"/api/dossier/{unit}").json()
        return next(e for e in d["entries"] if e["kind"] == "citations")["count"]

    assert count("v:0") == 1 and count("v:3") == 1 and count("v:2") == 0


def test_citations_in_db(built):
    _, db = built
    conn = sqlite3.connect(db)
    meta = json.loads(conn.execute("SELECT value FROM meta WHERE key = 'citations'").fetchone()[0])
    assert meta["families"]["word"]["resolved"] == 1
