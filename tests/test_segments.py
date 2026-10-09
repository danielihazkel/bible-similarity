import json
import sqlite3

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from scipy import sparse

from bsim.analysis.segments import (
    agreement,
    book_scores,
    contrast,
    depth_scores,
    gap_labels,
    group_tests,
    kinds,
    lemma_matrix,
    local_peak,
    near,
    pk_windowdiff,
    window_cosines,
)
from bsim.api.app import create_app
from bsim.fixture import fixture_encoder

SC = {"turn_min": 0.9, "turn_peak": 1, "cut_max": 0.25, "quiet_max": 0.05}


def _naive_cos(m, w):
    m = np.asarray(m.todense()) if sparse.issparse(m) else m
    out = []
    for k in range(1, len(m)):
        a, b = m[max(0, k - w) : k].sum(0), m[k : k + w].sum(0)
        den = np.linalg.norm(a) * np.linalg.norm(b)
        out.append(a @ b / den if den else 0.0)
    return np.array(out)


@pytest.mark.parametrize("w", [1, 2, 4])
def test_window_cosines_match_the_windows(w):
    rng = np.random.default_rng(0)
    dense = rng.random((9, 5))
    np.testing.assert_allclose(window_cosines(dense, w), _naive_cos(dense, w))
    sp = sparse.random(9, 30, density=0.15, random_state=1, format="csr")
    np.testing.assert_allclose(window_cosines(sp, w), _naive_cos(sp, w))
    assert len(window_cosines(dense[:1], w)) == 0


def _naive_depth(s):
    out = []
    for k in range(len(s)):
        lft, i = s[k], k
        while i > 0 and s[i - 1] >= lft:
            lft, i = s[i - 1], i - 1
        rgt, j = s[k], k
        while j < len(s) - 1 and s[j + 1] >= rgt:
            rgt, j = s[j + 1], j + 1
        out.append(lft - s[k] + rgt - s[k])
    return np.array(out)


def test_depth_climbs_both_sides():
    s = np.array([0.9, 0.5, 0.2, 0.6, 0.8, 0.8, 0.3, 0.7])
    np.testing.assert_allclose(depth_scores(s), _naive_depth(s))
    assert depth_scores(s)[2] == pytest.approx(0.7 + 0.6)  # climbs to 0.9 and to 0.8
    rng = np.random.default_rng(3)
    for _ in range(20):
        r = rng.random(30).round(1)  # with ties
        np.testing.assert_allclose(depth_scores(r), _naive_depth(r))


def test_book_scores_rank_the_drop_highest_and_break_ties():
    lex = np.array([0.8, 0.8, 0.1, 0.8, 0.8])
    sem = np.array([0.9, 0.85, 0.2, 0.9, 0.9])
    dl, _, score = book_scores(lex, sem)
    assert score.argmax() == 2 and score[1] > score[0]  # 1 is a dip of the semantic curve
    assert score[0] == score[3] == score[4]  # equal cohesion stays tied
    assert dl[0] > 0 and dl[0] < 1e-5  # a peak's depth 0 + the tie-break


def test_pk_and_windowdiff():
    ref = np.array([0, 0, 1, 0, 0, 1, 0, 0], dtype=bool)
    assert pk_windowdiff(ref, ref, 2) == (0.0, 0.0)
    off = np.roll(ref, 1)
    pk, wd = pk_windowdiff(ref, off, 2)
    assert 0 < pk <= wd
    assert np.isnan(pk_windowdiff(ref[:1], ref[:1], 2)[0])


def test_agreement_beats_random_gaps_when_the_score_finds_the_breaks():
    rng = np.random.default_rng(0)
    ref = np.zeros(200, dtype=bool)
    ref[::20] = True
    score = rng.random(200) * 0.5 + ref
    res = agreement(score, ref, 199, rng)
    assert res["pk"] == 0 and res["pk_p"] <= 0.01 and res["pk_null"] > 0.2
    noise = agreement(rng.random(200), ref, 199, rng)
    assert noise["pk_p"] > 0.01
    assert agreement(score, np.zeros(200, dtype=bool), 9, rng) is None


def test_group_tests_and_contrast_against_within_book_shuffles():
    rng = np.random.default_rng(1)
    book = np.repeat([0, 1], 300)
    score = rng.random(600)
    planted = np.zeros(600, dtype=bool)
    planted[rng.choice(600, 60, replace=False)] = True
    score[planted] = 0.9 + 0.1 * rng.random(60)
    other = ~planted & (rng.random(600) < 0.1)
    res = group_tests(score, book, {"planted": planted, "other": other}, 199, rng)
    assert res["planted"]["p"] <= 0.01 and res["planted"]["null"] == pytest.approx(0.5, abs=0.05)
    assert res["other"]["p"] > 0.05
    c = contrast(score, book, planted, other, 199, rng)
    assert c["diff"] > 0.3 and c["p"] <= 0.01
    flat = contrast(score, book, other, ~planted & ~other, 199, rng)
    assert flat["p"] > 0.05


def test_gap_labels_place_breaks_on_the_verse_after():
    verses = pd.DataFrame(
        {
            "verse_id": range(6),
            "book_id": [0, 0, 0, 0, 1, 1],
            "chapter": [1, 1, 2, 2, 1, 1],
            "break_after": [None, "pe", None, "samekh", None, None],  # 3's break ends book 0
            "oshb_break": [None, "samekh", None, None, np.nan, None],
        }
    )
    units = pd.DataFrame({"unit_type": ["parasha"], "start_verse_id": [2]})
    g = gap_labels(verses, units, {5})
    assert g.verse_id.tolist() == [1, 2, 3, 5]  # no gap across the book boundary
    assert g.mam.fillna("").tolist() == ["", "pe", "", ""]
    assert g.oshb.fillna("").tolist() == ["", "samekh", "", ""]
    assert g.chapter.tolist() == [0, 1, 0, 0] and g.parasha.tolist() == [0, 1, 0, 0]
    assert g.seam.tolist() == [0, 0, 0, 1]


def test_peaks_and_neighbourhoods_stay_in_their_book():
    book = np.array([0, 0, 0, 1, 1])
    assert local_peak(np.array([0.1, 0.5, 0.4, 0.9, 0.2]), book, 1).tolist() == [
        False, True, False, True, False,
    ]  # fmt: skip
    assert near(np.array([0, 0, 1, 0, 0], dtype=bool), book, 1).tolist() == [
        False, True, True, False, False,
    ]  # fmt: skip


def test_kinds():
    gaps = pd.DataFrame(
        {
            "book_id": 0,
            "verse_id": range(1, 9),
            "score": [0.5, 0.95, 0.5, 0.3, 0.97, 0.1, 0.02, 0.5],
            "mam": [None, None, None, None, None, None, "pe", None],
            "oshb": [None] * 8,
            "chapter": [0, 0, 0, 0, 0, 1, 0, 0],
            "parasha": 0,
            "seam": 0,
        }
    )
    # 0.95 is an unmarked peak; 0.97 lies next to the chapter start (not a turn); the chapter
    # start at 0.1 has no paragraph break (cut); the pe at 0.02 is quiet
    assert kinds(gaps, SC).tolist() == [None, "turn", None, None, None, "cut", "quiet", None]


def test_lemma_matrix_weights_rare_lemmas():
    words = pd.DataFrame({"verse_id": [0, 0, 1, 2], "content_lemmas": [["a"], ["b"], ["a"], []]})
    x = lemma_matrix(words, 3).toarray()
    assert x.shape == (3, 2) and x[2].sum() == 0
    assert x[0, 1] > x[0, 0] > 0  # b (one verse) outweighs a (two)


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_segments_api(client):
    s = client.get("/api/segments").json()
    assert s["meta"]["window"] == 4 and s["meta"]["kinds"] == {"turn": 1, "cut": 1, "quiet": 1}
    assert s["books"][0]["ref"] == "mam"
    turns = client.get("/api/segments/gaps?kind=turn").json()
    assert turns["total"] == 1 and turns["items"][0]["verse_id"] == 2
    assert [v["verse_id"] for v in turns["items"][0]["verses"]] == [1, 2]
    any_kind = client.get("/api/segments/gaps").json()
    assert [g["kind"] for g in any_kind["items"]] == ["quiet", "turn", "cut"]
    cut = client.get("/api/segments/gaps?unit=c:0:2").json()
    assert cut["unit"] == "c:0:2" and [g["kind"] for g in cut["items"]] == ["cut"]
    assert cut["items"][0]["chapter"] and cut["items"][0]["seam"]
    assert client.get("/api/segments/gaps?book=1").json()["total"] == 0
    assert client.get("/api/segments/gaps?kind=bad").status_code == 422
    assert client.get("/api/segments/gaps?unit=v:99").status_code == 404
    b = client.get("/api/segments/book/0").json()
    assert [p["verse_id"] for p in b["points"]] == [1, 2, 3, 4]
    assert b["points"][2]["chapter_start"] and b["points"][3]["mam"] == "pe"
    assert b["agreement"][0]["pk"] == 0.3
    assert client.get("/api/segments/book/1").json()["points"] == []
    assert client.get("/api/segments/book/77").status_code == 404


def test_dossier_divisions(client):
    def entry(unit):
        d = client.get(f"/api/dossier/{unit}").json()
        return next(e for e in d["entries"] if e["kind"] == "divisions")

    chapter = entry("c:0:2")
    assert chapter["computed"] and chapter["count"] == 1
    assert chapter["key"] == "cut" and chapter["value"] == 0.1
    first = entry("v:0")  # a book's first verse opens no gap
    assert first["count"] == 0 and first["value"] is None


def test_segments_in_db(built):
    _, db = built
    conn = sqlite3.connect(db)
    meta = json.loads(conn.execute("SELECT value FROM meta WHERE key = 'segments'").fetchone()[0])
    assert meta["agreement"]["mam"]["better"] == 1
    assert conn.execute("SELECT COUNT(*) FROM segment_gaps WHERE kind IS NULL").fetchone() == (1,)
