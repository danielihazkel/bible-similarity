import json
import sqlite3

import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp
from fastapi.testclient import TestClient

from bsim.analysis.allusions import rare_lemmas, suppress, window_matrix, window_pairs
from bsim.api.app import create_app
from bsim.fixture import fixture_encoder


def test_rare_lemmas_drop_names_aramaic_and_sense_letters():
    words = pd.DataFrame(
        {
            "verse_id": [0, 1, 1, 2, 3, 4],
            "content_lemmas": [["3939a"], ["3939b"], ["1732"], ["1732"], ["3939"], ["2000"]],
            "morph": ["HNcfsa", "HNcfsa", "HNp", "HNp", "ANcfsa", "HNcmsa"],
        }
    )
    r = rare_lemmas(words, 5)
    # 3939 in verses 0 and 1 (senses merged; the Aramaic verse 3 left out); names and a lemma of
    # one verse are not rare words
    assert r.values.tolist() == [[0, "3939"], [1, "3939"]]
    assert rare_lemmas(words, 1).empty


def test_window_matrix_stays_in_its_chapter():
    x = sp.csr_matrix(np.eye(5))
    chap = np.array([1, 1, 1, 2, 2])
    m = window_matrix(x, np.arange(5), chap, 2).toarray()
    assert m[0].tolist() == [1, 1, 0, 0, 0]
    assert m[2].sum() == 0  # verses 2 and 3 are in different chapters
    assert m[3].tolist() == [0, 0, 0, 1, 1] and m[4].sum() == 0


def test_window_pairs_and_suppression():
    # lemmas 0-2 in verses 0-1 (chapter 1) and again in verses 4-5 (chapter 2), spread out
    x = sp.lil_matrix((6, 4))
    for v, lem in [(0, 0), (1, 1), (1, 2), (4, 0), (5, 1), (5, 2), (3, 3)]:
        x[v, lem] = 1
    x = sp.csr_matrix(x)
    chap = np.array([1, 1, 1, 2, 2, 2])
    idf = np.array([1.0, 2.0, 3.0, 1.0])
    pairs = window_pairs(x, idf, np.arange(6), chap, 2, 3)
    assert pairs.iloc[0][["i", "j", "n_shared", "score"]].tolist() == [0, 4, 3, 6.0]
    kept = suppress(pairs, 2)
    assert len(kept) == 1
    # no pair inside one chapter, however much it shares
    same = window_pairs(x, idf, np.arange(6), np.ones(6, dtype=int), 2, 3)
    assert same.empty


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_allusions_api(client):
    a = client.get("/api/allusions").json()
    assert a["meta"]["best_new_q"] == 0.8 and a["total"] == 2
    first = a["items"][0]
    assert first["known"] and [x["form"] for x in first["lemmas"]] == ["ראשית", "אלהים"]
    assert [v["verse_id"] for v in first["a_verses"]] == [0, 1]
    assert first["a_marks"]["0"] == [0, 1] and first["b_marks"]["3"] == [0]
    assert "–" in first["a_label"]
    assert client.get("/api/allusions?known=false").json()["total"] == 1
    assert client.get("/api/allusions?book=1").json()["total"] == 1
    assert client.get("/api/allusions?unit=v:2").json()["items"][0]["allusion_id"] == 2
    assert client.get("/api/allusions?unit=v:99").status_code == 404


def test_dossier_allusions(client):
    d = client.get("/api/dossier/c:0:2").json()
    assert next(e for e in d["entries"] if e["kind"] == "allusions")["count"] == 1


def test_allusions_in_db(built):
    _, db = built
    conn = sqlite3.connect(db)
    meta = json.loads(conn.execute("SELECT value FROM meta WHERE key = 'allusions'").fetchone()[0])
    assert meta["strong_known"] == 1
