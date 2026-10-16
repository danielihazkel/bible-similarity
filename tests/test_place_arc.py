"""The geographic arc (`bsim place-arc`, `/place-arc`, §16.60)"""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.place_arc import centre, km_to, label_test, place_spans, run_place_arc
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder

STEP = 0.3 * 111.195 * np.cos(np.radians(31))  # km between two neighbours on the line below


def test_centre_and_km():
    lat, lon = centre(np.array([31.0, 31.0]), np.array([34.0, 36.0]))
    assert lon == pytest.approx(35.0) and lat == pytest.approx(31.0, abs=0.01)
    assert centre(np.array([10.0]), np.array([20.0])) == pytest.approx((10.0, 20.0))
    d = km_to(np.array([31.778, 32.778]), np.array([35.235, 35.235]), 31.778, 35.235)
    assert d == pytest.approx([0.0, 111.2], abs=0.1)


def test_place_spans():
    pts = pd.DataFrame({"place_id": [3, 1, 1], "lat": [31.0, 31.0, 31.0],
                        "lon": [34.0, 35.0, 35.0]})  # fmt: skip
    s = place_spans(pts)
    assert (s["n_mentions"], s["n_places"], s["top_place"]) == (3, 2, 1)
    # the centre is two thirds of the way east; the spread the mean km from it
    assert s["lon"] == pytest.approx(34.667, abs=0.01)
    assert s["spread_km"] == pytest.approx(4 / 9 * 95.3, abs=0.5)


def test_label_test():
    rng = np.random.default_rng(0)
    values = np.array([10.0, 12.0, 11.0, 50.0, 60.0])
    r = label_test(values, np.array([False, False, False, True, True]), 999, rng)
    assert (r["n"], r["n_other"], r["observed"], r["other"]) == (2, 3, 55.0, 11.0)
    assert r["p"] < 0.15  # 1 labelling of 10 is as high
    low = label_test(values, np.array([True, True, False, False, False]), 999, rng)
    assert low["p"] > 0.5


def corpus(tmp_path):
    """Genesis 1-8 (two verses each) name places 1-8 on a line west to east, chapter by chapter,
    but Genesis 3 names its place once; Exodus 1 names the line's two ends; Isaiah 1-3 near the
    west end, Isaiah 2 (an oracle) at both ends; place 9 is of no kind."""
    proc, art = tmp_path / "processed", tmp_path / "art"
    for d in (proc, art / "places"):
        d.mkdir(parents=True)
    rows = [(0, c, v) for c in range(1, 9) for v in (1, 2)]
    rows += [(1, 1, 1), (1, 1, 2)] + [(11, c, v) for c in (1, 2, 3) for v in (1, 2)]
    verses = pd.DataFrame(rows, columns=["book_id", "chapter", "verse"])
    verses.insert(0, "verse_id", range(len(verses)))
    verses.to_parquet(proc / "verses.parquet")
    pd.DataFrame(
        [(i, "town", 31.0, 34.0 + 0.3 * (i - 1)) for i in range(1, 9)] + [(9, None, 33.0, 40.0)],
        columns=["place_id", "kind", "lat", "lon"],
    ).to_parquet(art / "places" / "places.parquet")
    vid = {(b, c, v): i for i, (b, c, v) in enumerate(rows)}
    m = [("a", vid[(0, 1, 1)], 1), ("b", vid[(0, 1, 1)], 1)]  # one place twice in a verse
    m += [("x", vid[(0, c, v)], c) for c in range(1, 9) for v in (1, 2) if (c, v) != (3, 2)]
    m += [("x", vid[(1, 1, 1)], 1), ("x", vid[(1, 1, 2)], 8)]
    m += [("x", vid[(11, 1, 1)], 2), ("x", vid[(11, 1, 2)], 2), ("x", vid[(11, 2, 1)], 1),
          ("x", vid[(11, 2, 2)], 8), ("x", vid[(11, 3, 1)], 3), ("x", vid[(11, 3, 2)], 3),
          ("x", vid[(11, 3, 2)], 9)]  # fmt: skip
    pd.DataFrame(m, columns=["lemma", "verse_id", "place_id"]).to_parquet(
        art / "places" / "mentions.parquet"
    )
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art)}
    cfg["place_arc"] = {
        **cfg["place_arc"], "shuffles": 999,
        "regions": {"canaan": {"lat": 31.0, "lon": 34.0}, "east": {"lat": 31.0, "lon": 36.1}},
        "moves": [
            {"key": "out", "from": "Genesis 1-2", "to": "Genesis 7-8", "from_region": "canaan",
             "to_region": "east"},
            {"key": "back", "from": "Genesis 7-8", "to": "Genesis 1-2", "from_region": "canaan",
             "to_region": "east"},
            {"key": "thin", "from": "Genesis 3", "to": "Genesis 4", "from_region": "canaan",
             "to_region": "east"},
        ],
        "oracles": ["Isaiah 2"], "prophets": ["Isa"],
    }  # fmt: skip
    return cfg


def test_run_place_arc(tmp_path):
    cfg = corpus(tmp_path)
    out = run_place_arc(cfg, log=lambda _: None)
    ch = pd.read_parquet(out / "chapters.parquet")
    assert len(ch) == 12
    gen = ch[ch.book_id == 0].set_index("chapter")
    # a place twice in one verse is one mention; Genesis 3's single mention leaves it unplaced
    assert gen.n_mentions.tolist() == [2, 2, 1, 2, 2, 2, 2, 2]
    assert np.isnan(gen.lat[3]) and gen.n_places.isna()[3]
    assert gen.lon[1] == pytest.approx(34.0) and gen.spread_km[1] == 0.0
    # steps join placed chapters: Genesis 4 steps from Genesis 2
    assert gen.prev_chapter[4] == 2 and gen.step_km[4] == pytest.approx(2 * STEP, abs=0.2)
    assert gen.step_km[5] == pytest.approx(STEP, abs=0.2) and np.isnan(gen.step_km[1])
    assert gen.reach_km[8] == pytest.approx(7 * STEP, abs=0.5)
    ex = ch[ch.book_id == 1].iloc[0]
    assert ex.lon == pytest.approx(35.05, abs=0.01)
    assert ex.spread_km == pytest.approx(3.5 * STEP, abs=0.5)
    isa = ch[ch.book_id == 11].set_index("chapter")
    assert isa.oracle.tolist() == [False, True, False] and isa.prophetic.all()
    assert isa.n_mentions[3] == 2  # place 9 has no kind
    books = pd.read_parquet(out / "books.parquet").set_index("book_id")
    assert books.n.to_dict() == {0: 7, 1: 1, 11: 3}
    g = books.loc[0]
    assert g.mean_step == pytest.approx(7 * STEP / 6, abs=0.2) and g.mean_step < g.null_mean
    assert g.p < 0.01  # 2 of 5,040 orders run along the line
    assert np.isnan(books.p[1])
    meta = json.loads((out / "place_arc.meta.json").read_text("utf-8"))
    arc = meta["arc"]
    assert (arc["chapters"], arc["placed"], arc["books"], arc["steps"]) == (12, 11, 2, 8)
    moves = {m["key"]: m for m in meta["moves"]}
    assert moves["out"]["holds"] is True and moves["back"]["holds"] is False
    assert moves["thin"]["holds"] is None and "km" not in moves["thin"]
    o = moves["out"]
    assert o["from"]["nearest"] == "canaan" and o["to"]["nearest"] == "east"
    assert o["km"] == pytest.approx(6 * STEP, abs=0.5) and o["from_vids"] == [0, 3]
    ora = meta["oracles"]
    assert (ora["chapters"], ora["placed"], ora["alpha"]) == (1, 1, 0.025)
    assert ora["spread"]["observed"] == pytest.approx(3.5 * STEP, abs=0.5)
    assert ora["spread"]["n_other"] == 2 and ora["spread"]["other"] == 0.0
    first = (out / "books.parquet").read_bytes()
    run_place_arc(cfg, log=lambda _: None)
    assert (out / "books.parquet").read_bytes() == first


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_api_arc(client):
    r = client.get("/api/place-arc").json()
    assert r["meta"]["shuffles"] == 999 and r["meta"]["regions"]["egypt"]["lon"] == 31.31
    assert r["arc"]["placed"] == 3 and r["arc"]["p"] == 0.5
    assert [(b["name"], b["he_name"], b["n"], b["p"]) for b in r["books"]] == [
        ("Genesis", "בראשית", 2, 0.5), ("Exodus", "שמות", 1, None),
    ]  # fmt: skip
    (mv,) = r["moves"]
    assert (mv["key"], mv["holds"], mv["km"]) == ("descent", True, 270.2)
    assert (mv["start"]["label_en"], mv["start"]["label_he"], mv["start"]["unit_id"]) == (
        "Genesis 1", "בראשית א", "c:0:1",
    )  # fmt: skip
    assert mv["end"]["top_place"] == {"place_id": 2, "he": "ראשית", "kind": "region"}
    o = r["oracles"]
    assert (o["labels_en"], o["labels_he"], o["holds"]) == (["Exodus 1"], ["שמות א"], True)
    assert [c["unit_id"] for c in o["items"]] == ["c:1:1"]


def test_api_book(client):
    d = client.get("/api/place-arc/0").json()
    assert d["book"]["name"] == "Genesis"
    assert [(c["chapter"], c["label_en"], c["step_km"], c["prev_chapter"]) for c in d["items"]] == [
        (1, "Genesis 1", None, None), (2, "Genesis 2", 270.2, 1),
    ]  # fmt: skip
    assert d["items"][1]["top_place"]["he"] == "ראשית" and d["items"][0]["oracle"] is False
    assert client.get("/api/place-arc/7").status_code == 404


def test_findings(client):
    items = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    o, m, n = items["place_arc_order"], items["place_arc_moves"], items["place_arc_oracles"]
    assert o["verdict"] == "fails" and o["values"]["mean_step"] == 270.2
    assert m["verdict"] == "holds" and m["values"] == {"n": 1, "held": 1, "descent_km": 270.2}
    assert n["verdict"] == "holds" and n["values"]["reach_p"] == 0.01
