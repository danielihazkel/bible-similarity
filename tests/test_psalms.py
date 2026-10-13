"""Psalms: the form of each psalm, Gunkel's genres, the lament's turn (`bsim psalms`, `/psalms`,
DESIGN.md §16.42)."""

import json
import sqlite3

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.psalms import (
    find_turn,
    morph_counts,
    poisson_binomial_sf,
    profile_check,
    run_psalms,
    split_stats,
    strongs,
    title_mask,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.data.canon import BY_SEFARIA
from bsim.fixture import fixture_encoder

GRIEVE, PRAISE = "002001002013", "002004001009009"


def test_morph_counts():
    # הושיעני: an imperative (2ms) with a 1cs suffix
    assert morph_counts("HVhv2ms/Sp1cs") == {
        "first_singular": 1, "first_plural": 0, "second": 1, "imperative": 1,
        "imperative_plural": 0, "question": 0,
    }  # fmt: skip
    c = morph_counts("HVpv2mp")  # הללו
    assert c["imperative_plural"] == 1 and c["second"] == 1
    assert morph_counts("HVqp1cp")["first_plural"] == 1
    assert morph_counts("HTi")["question"] == 1 and morph_counts("HPi")["question"] == 1
    # a participle and an infinitive have no person
    assert sum(morph_counts("HVqrmsa").values()) == 0 and sum(morph_counts("HVqc").values()) == 0
    assert sum(morph_counts(None).values()) == 0


def test_strongs_and_titles():
    assert strongs("l/1732") == ["1732"] and strongs("1254 a") == ["1254"] and strongs("c") == []
    title = {"4210", "1732"}
    w = pd.DataFrame(
        {
            "chapter": [1, 1, 1, 1, 2, 2, 2, 3],
            "verse": [1, 1, 1, 2, 1, 2, 2, 1],
            # 1: מזמור לדוד then the psalm; 2: all title in verse 1, so verse 2 too; 3: no title
            "lemma": ["4210", "l/1732", "3068", "4210", "4210", "1732", "7225", "4210 x"],
        }
    )
    w.loc[7, "lemma"] = "7225"
    assert title_mask(w, title).tolist() == [True, True, False, False, True, True, False, False]


def test_turns():
    # distress, distress | praise, praise: the rate (pooled over words) rises most at the middle
    mood, words = np.array([-2.0, -1, 2, 2]), np.array([4.0, 4, 4, 4])
    assert split_stats(mood, words, 2)[0].tolist() == [pytest.approx(4 / 8 + 3 / 8)]
    assert split_stats(mood, words, 1)[0].argmax() == 1
    rng = np.random.default_rng(0)
    long_mood = np.array([-2.0] * 6 + [2.0] * 6)
    t = find_turn(long_mood, np.full(12, 4.0), 2, 199, rng)
    assert t["split"] == 6 and t["p"] <= 0.05 and t["before"] < 0 < t["after"]
    assert find_turn(mood[:3], words[:3], 2, 10, rng) is None


def test_poisson_binomial_and_profiles():
    assert poisson_binomial_sf([0.5, 0.5], 2) == pytest.approx(0.25)
    assert poisson_binomial_sf([0.5, 0.5], 0) == pytest.approx(1.0)
    rng = np.random.default_rng(0)
    vals = np.array([0.9, 0.8, 0.85, 0.1, 0.2, 0.15, 0.1, 0.2])
    lab = np.array(["a"] * 3 + ["b"] * 5)
    hi = profile_check(vals, lab, "a", True, 199, rng)
    assert hi["mean"] > hi["rest"] and hi["p"] <= 0.05
    assert profile_check(vals, lab, "a", False, 199, rng)["p"] > 0.5


def write_toy(tmp_path):
    """Twelve psalms of eight verses: 1-6 hymns (plural imperatives, praise), 7-12 laments (first
    person singular, distress, then praise from verse 5)."""
    ps = BY_SEFARIA["Psalms"].book_id
    verses, words, senses = [], [], []
    vid = 0
    for ch in range(1, 13):
        lament = ch > 6
        for v in range(1, 9):
            toks = [("1000", "HNcmsa")] * 4
            if ch == 1 and v == 1:
                toks = [("4210", "HNcmsa"), ("l/1732", "HR/Np")] + toks  # the superscription
            if lament:
                toks += [("2000", "HVqp1cs")]
                dom = GRIEVE if v < 5 else PRAISE
            else:
                toks += [("3000", "HVpv2mp")]
                dom = PRAISE
            toks += [("4000", "HNcmsa")]
            verses.append((vid, ps, ch, v, f"Psalms {ch}:{v}"))
            for i, (lem, morph) in enumerate(toks):
                words.append((vid, i, lem, morph))
            senses.append((vid, len(toks) - 1, [dom]))
            vid += 1
    proc = tmp_path / "processed"
    proc.mkdir()
    pd.DataFrame(verses, columns=["verse_id", "book_id", "chapter", "verse", "ref"]).to_parquet(
        proc / "verses.parquet"
    )
    pd.DataFrame(words, columns=["verse_id", "idx", "lemma", "morph"]).to_parquet(
        proc / "words.parquet"
    )
    pd.DataFrame(senses, columns=["verse_id", "idx", "domains"]).to_parquet(
        proc / "word_senses.parquet"
    )
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc),
                    "artifacts": str(tmp_path / "artifacts")}  # fmt: skip
    cfg["psalms"] = {
        **cfg["psalms"],
        "genres": {"hymn": [1, 2, 3, 4, 5, 6], "lament_individual": [7, 8, 9, 10, 11, 12]},
        "checks": [["lament_individual", "first_singular", "higher"],
                   ["hymn", "imperative_plural", "higher"]],  # fmt: skip
        "known_turns": ["Psalms 7:5", "Psalms 8:5"],
        "tolerance": 0,  # with 8 verses, 1 either side would be 3 of the 5 splits
        "draws": 199,
    }
    return cfg


def test_stage_on_a_toy_psalter(tmp_path):
    cfg = write_toy(tmp_path)
    out = run_psalms(cfg, log=lambda _: None)
    meta = json.loads((out / "psalms.meta.json").read_text("utf-8"))
    assert meta["psalms"] == 12 and meta["labelled"] == 12 and meta["title_words"] == 2
    # the two forms are two clusters, exactly the two genres
    assert meta["genre_test"]["nmi"] == pytest.approx(1.0) and meta["genre_test"]["p"] <= 0.05
    assert meta["checks_held"] == 2
    # every lament turns at verse 5, the hymns never do
    assert meta["known_turns"]["found"] == 2 and meta["known_turns"]["p"] <= 0.05
    lvh = meta["laments_vs_hymns"]
    assert (lvh["laments"], lvh["hymns"]) == (6, 0) and lvh["p"] <= 0.05
    ps = pd.read_parquet(out / "psalms.parquet")
    assert ps.unit_id.tolist()[0] == f"c:{BY_SEFARIA['Psalms'].book_id}:1"
    assert (ps[ps.genre == "lament_individual"].turn_verse == 5).all()
    assert ps.loc[0, "words"] == 48  # the superscription left out
    v = pd.read_parquet(out / "verses.parquet")
    assert len(v) == 96 and v.distress.sum() == 24 and v.praise.sum() == 72


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_psalms_endpoints(client):
    r = client.get("/api/psalms").json()
    assert r["meta"]["genre_test"]["nmi"] == 0.4
    k0, k1 = r["known"]
    assert k0["found"] and k0["turn_vid"] == 2 and k1["found"] is None and k1["turn_label"] is None
    page = client.get("/api/psalms/list").json()
    assert page["total"] == 2 and [p["unit_id"] for p in page["items"]] == ["c:0:1", "c:0:2"]
    p0 = page["items"][0]
    assert p0["genre"] == "lament_individual" and p0["features"]["first_singular"] == 0.3
    assert p0["turn"]["verse_id"] == 2 and p0["turn"]["p"] == 0.01
    assert [m["praise"] for m in p0["mood"]] == [0, 0, 2]
    assert page["items"][1]["turn"] is None
    assert client.get("/api/psalms/list?turned=true").json()["total"] == 1
    assert client.get("/api/psalms/list?genre=hymn").json()["items"][0]["unit_id"] == "c:0:2"
    assert client.get("/api/psalms/list?cluster=1").json()["total"] == 1
    assert client.get("/api/psalms/list?unit=v:3").json()["items"][0]["unit_id"] == "c:0:2"
    assert client.get("/api/psalms/list?unit=c:1:1").json()["total"] == 0
    assert client.get("/api/psalms/list?sort=x").status_code == 422
    assert client.get("/api/psalms/list?limit=0").status_code == 422
    csv = client.get("/api/export/psalms.csv").text
    assert "features.first_singular" in csv.splitlines()[0] and "mood" not in csv.splitlines()[0]


def test_psalms_findings_and_dossier(client):
    f = {x["key"]: x for x in client.get("/api/findings").json()["items"]}
    assert f["psalm_genres"]["verdict"] == "holds"
    assert f["psalm_forms"]["verdict"] == "fails" and f["psalm_forms"]["values"]["held"] == 1
    assert f["lament_turn"]["verdict"] == "holds"
    assert f["lament_turns"]["verdict"] == "fails"
    d = {e["kind"]: e for e in client.get("/api/dossier/c:0:1").json()["entries"]}
    assert d["psalms"]["computed"] and d["psalms"]["count"] == 1
    d = {e["kind"]: e for e in client.get("/api/dossier/c:1:1").json()["entries"]}
    assert d["psalms"]["count"] == 0


def test_without_the_stage(built):
    cfg, db = built
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM psalms")
        conn.execute("UPDATE meta SET value = '{}' WHERE key = 'psalms'")
    c = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    assert c.get("/api/psalms/list").json()["total"] == 0
    assert c.get("/api/psalms").json()["known"] == []
    keys = {x["key"] for x in c.get("/api/findings").json()["items"]}
    assert not keys & {"psalm_genres", "psalm_forms", "lament_turn", "lament_turns"}
    d = {e["kind"]: e for e in c.get("/api/dossier/c:0:1").json()["entries"]}
    assert not d["psalms"]["computed"]
