import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.stylometry import feature_counts, feature_matrix
from bsim.analysis.voices import (
    DIVINE,
    author_check,
    distinctiveness,
    group_sums,
    permute_within,
    proper_names,
    speaker_key,
    verdict,
    word_clauses,
)
from bsim.api.app import create_app
from bsim.fixture import fixture_encoder

WORDS = pd.DataFrame(
    {
        "verse_id": [0, 0, 1, 1],
        "content_lemmas": [["559"], ["430"], ["559"], []],
        "morph": ["HC/Vqw3ms", "HNcmpa", "HVqp3ms", "HTo"],
    }
)


def test_feature_counts_matches_feature_matrix():
    rel, n, names = feature_matrix(WORDS, np.array([0, 1]), 2, ["559", "430"])
    counts, n2, names2 = feature_counts(WORDS, np.array([0, 0, 1, 1]), 2, ["559", "430"])
    assert names == names2 and n.tolist() == n2.tolist() == [2, 2]
    assert np.allclose(rel, counts / n[:, None])
    # a word left out (-1) and words of one verse split over two units
    counts, n, _ = feature_counts(WORDS, np.array([0, 1, -1, 1]), 2, ["559"])
    assert n.tolist() == [1, 2]


def test_word_clauses_last_clause_wins():
    clauses = pd.DataFrame({"verse_id": [0, 0, 1], "words": [[0, 1], [1, 2], [0]]})
    wc = word_clauses(clauses)
    assert wc.values.tolist() == [[0, 0, 0], [0, 1, 1], [0, 2, 1], [1, 0, 2]]


def test_speaker_keys_and_proper_names():
    divine = {"3068", "430"}
    assert speaker_key("3068", divine) == speaker_key("430", divine) == DIVINE
    assert speaker_key("1732", divine) == "1732"
    assert speaker_key(None, divine) is None and speaker_key(float("nan"), divine) is None
    words = pd.DataFrame(
        {
            "lemma": ["1732", "1732", "c/5971 a", "5971 a", "5971 a", "5971 a"],
            "morph": ["HNpm", "HNpm", "HC/Npm", "HNcmsa", "HNcmsa", "HNcmsa"],
        }
    )
    assert proper_names(words) == {"1732"}  # עם tagged Np once in four: not a name


def test_permute_within_keeps_each_group():
    rng = np.random.default_rng(0)
    lab = np.array([0, 1, 2, 3, 4, 5, 6, 7])
    group = np.array([1, 0, 1, 0, 1, 0, 1, 0])
    for _ in range(5):
        out = permute_within(lab, group, rng)
        assert sorted(out[group == 0]) == [1, 3, 5, 7] and sorted(out[group == 1]) == [0, 2, 4, 6]


def test_group_sums_skips_unlabelled():
    x = np.array([[1.0, 0.0], [0.0, 2.0], [5.0, 5.0]])
    s, w = group_sums(np.array([0, 1, -1]), 2, x, np.array([1.0, 2.0, 9.0]))
    assert s.tolist() == [[1.0, 0.0], [0.0, 2.0]] and w.tolist() == [1.0, 2.0]


def _corpus(rng, planted: bool):
    """Two books of clauses (10 words each, two features); speaker 0 in book 0 uses feature 0
    twice as often when `planted`, speaker 1 in book 1 speaks like everyone else."""
    rows, books, labs = [], [], []
    for b in (0, 1):
        for i in range(120):
            lab = (0 if b == 0 else 1) if i < 30 else 2
            rate = 0.6 if planted and lab == 0 else 0.3
            rows.append([rng.binomial(10, rate), rng.binomial(10, 0.3)])
            books.append(b)
            labs.append(lab)
    return np.array(rows, dtype=float), np.full(len(rows), 10.0), np.array(books), np.array(labs)


def test_distinctiveness_finds_planted_speaker_only():
    rng = np.random.default_rng(1)
    x, nw, book, lab = _corpus(rng, planted=True)
    res = distinctiveness(x, nw, book, lab, 2, np.array([0.1, 0.1]), 199, rng)
    assert res["q"][0] < 0.05 and res["q"][1] > 0.05
    assert res["effect"][0] > res["effect"][1]
    x, nw, book, lab = _corpus(np.random.default_rng(2), planted=False)
    res = distinctiveness(x, nw, book, lab, 2, np.array([0.1, 0.1]), 199, rng)
    assert (res["q"] > 0.05).all() and (res["q_calibration"] > 0.05).all()


def test_author_check_and_verdict():
    rng = np.random.default_rng(3)
    n = 60
    # narrators of A and B differ in feature 0; the speaker follows each side's narrator
    side_a = np.r_[np.ones(n, bool), np.zeros(3 * n, bool)]
    side_b = np.r_[np.zeros(n, bool), np.ones(n, bool), np.zeros(2 * n, bool)]
    narr_a = np.r_[np.zeros(2 * n, bool), np.ones(n, bool), np.zeros(n, bool)]
    narr_b = np.r_[np.zeros(3 * n, bool), np.ones(n, bool)]
    rate = np.where(side_a | narr_a, 0.6, 0.2)
    x = np.c_[rng.binomial(10, rate), rng.binomial(10, 0.3, size=4 * n)].astype(float)
    nw = np.full(4 * n, 10.0)
    c = author_check(x, nw, side_a, side_b, narr_a, narr_b, np.array([0.1, 0.1]), 199, rng)
    assert c["cross"] > 0 and c["p_cross"] < 0.05 and c["words_a"] == 600
    assert verdict(c, 300) == "author"
    assert verdict(c, 1000) == "underpowered"
    assert verdict({**c, "p_cross": 0.5, "p_ab": 0.01}, 300) == "differs"
    assert verdict({**c, "p_cross": 0.5, "p_ab": 0.5}, 300) == "same"


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_voices_api(client):
    v = client.get("/api/voices").json()
    assert [s["key"] for s in v["speakers"]] == ["divine", "4872"]
    assert v["speakers"][0]["he"] is None and v["speakers"][0]["books"] == [0]
    assert v["meta"]["checks"]["author"][0]["verdict"] == "author"
    assert len(v["pairs"]) == 3
    d = client.get("/api/voices/divine").json()
    assert [f["side"] for f in d["features"]] == ["over", "under"]
    assert [p["b"] for p in d["nearest"]] == ["4872", "narrator"]
    assert d["chapters"] == [{"unit_id": "c:0:1", "book_id": 0, "chapter": 1, "n_clauses": 1}]
    m = client.get("/api/voices/4872").json()
    assert [p["b"] for p in m["nearest"]] == ["narrator", "divine"]
    assert m["chapters"][0]["unit_id"] == "c:1:1"
    assert client.get("/api/voices/9999").status_code == 404


def test_voices_meta_in_db(built):
    import sqlite3

    _, db = built
    conn = sqlite3.connect(db)
    meta = json.loads(conn.execute("SELECT value FROM meta WHERE key = 'voices'").fetchone()[0])
    assert meta["calibration"] == {"significant": 0, "of": 2}
    assert conn.execute("SELECT books FROM voice_speakers WHERE key = '4872'").fetchone() == (
        "[1]",
    )
