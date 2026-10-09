import json
import sqlite3

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.mirrors import (
    chapter_interval,
    clause_pairs,
    genre_permutation,
    order_counts,
    sign_test,
)
from bsim.api.app import create_app
from bsim.fixture import fixture_encoder


@pytest.mark.parametrize(
    ("seq", "expected"),
    [
        ("x y y x", (1, 0, 0)),  # mirrored
        ("x y z x y", (0, 0, 1)),  # a repeated two-word phrase
        ("x y z x w y", (0, 1, 0)),  # repeated order, spread
        ("x y z x y z", (0, 1, 2)),  # a repeated phrase: x-y and y-z are bigrams, x-z spread
        ("x x y y", (0, 0, 0)),  # no overlap
        ("a b c c b a", (3, 0, 0)),  # a full mirror
        ("x y y x x", (0, 0, 0)),  # x thrice: only lemmas used exactly twice count
    ],
)
def test_order_counts(seq, expected):
    assert order_counts(seq.split())[:3] == expected


def test_sign_test_and_interval():
    chi = np.array([2, 0, 0, 0, 1, 0])
    par = np.array([0, 1, 2, 1, 0, 3])
    t = sign_test(chi, par)
    assert (t["verses_chiastic"], t["verses_parallel"]) == (2, 4)
    assert t["share"] == pytest.approx(3 / 10) and 0 < t["p"] <= 1
    lo, hi = chapter_interval(chi, par, np.array([1, 1, 2, 2, 3, 3]), 200, np.random.default_rng(0))
    assert 0 <= lo <= 0.3 <= hi <= 1


def test_clause_pairs_compare_consecutive_clauses_of_a_verse():
    phrases = pd.DataFrame(
        {
            "clause": [1, 1, 2, 2, 3, 3, 3, 4, 4],
            "verse_id": [0, 0, 0, 0, 1, 1, 1, 1, 1],
            "words": [[0], [1], [2], [3], [0], [1], [2], [3], [4]],
            "function": ["Pred", "Objc", "Objc", "Pred", "Pred", "Objc", "Conj", "Pred", "Objc"],
        }
    )
    cp = clause_pairs(phrases, {"Pred", "Objc"})
    assert cp[["verse_id", "pair", "first", "second", "mirrored"]].values.tolist() == [
        [0, "Objc-Pred", "Pred", "Objc", 1],
        [1, "Objc-Pred", "Pred", "Objc", 0],
    ]
    assert json.loads(cp.a_words[0]) == {"Pred": [0], "Objc": [1]}


def test_genre_permutation_by_chapter():
    rng = np.random.default_rng(0)
    chapters = np.repeat(np.arange(20), 10)
    poetic = chapters < 5
    mirrored = np.where(poetic, rng.random(200) < 0.6, rng.random(200) < 0.1).astype(float)
    res = genre_permutation(mirrored, poetic, chapters, 999, rng)
    assert res["poetry"] > res["prose"] and res["p"] < 0.01
    flat = genre_permutation(rng.random(200) < 0.2, poetic, chapters, 999, rng)
    assert flat["p"] > 0.01


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_mirrors_api(client):
    m = client.get("/api/mirrors").json()["meta"]
    assert m["words"]["all"]["verses_parallel"] == 3 and m["clauses"]["pairs"] == 2
    v = client.get("/api/mirrors/verses").json()
    assert v["total"] == 1 and v["items"][0]["marks"] == {"0": 0, "1": 1, "2": 1, "3": 0}
    c = client.get("/api/mirrors/clauses").json()
    assert [i["mirrored"] for i in c["items"]] == [True, False]
    assert c["items"][0]["marks"] == {"0": 1, "1": 0}  # Objc of the first clause: the second slot
    assert client.get("/api/mirrors/clauses?mirrored=true").json()["total"] == 1
    assert client.get("/api/mirrors/clauses?poetic=true&pair=Objc-Pred").json()["total"] == 1
    assert client.get("/api/mirrors/clauses?book=1").json()["total"] == 0
    assert client.get("/api/mirrors/verses?unit=c:0:2").json()["total"] == 0


def test_dossier_mirrors(client):
    def count(unit):
        d = client.get(f"/api/dossier/{unit}").json()
        return next(e for e in d["entries"] if e["kind"] == "mirrors")["count"]

    assert count("c:0:1") == 2 and count("v:4") == 0


def test_mirrors_in_db(built):
    _, db = built
    conn = sqlite3.connect(db)
    meta = json.loads(conn.execute("SELECT value FROM meta WHERE key = 'mirrors'").fetchone()[0])
    assert meta["full_mirrors"] == 1
    rows = conn.execute("SELECT pair_id, poetic FROM mirror_clauses ORDER BY pair_id").fetchall()
    assert rows == [(1, 0), (2, 1)]
