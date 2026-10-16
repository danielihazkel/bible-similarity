"""Are the place lists ordered on the ground? (`bsim place-lists`, `/place-lists`, §16.58)"""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.place_lists import (
    distances,
    path_km,
    run_place_lists,
    score_districts,
    short_path,
    shuffled_paths,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder


def test_distances():
    # Jerusalem to Jericho, about 23 km; a degree of latitude, about 111 km
    d = distances(np.array([31.778, 31.871, 32.778]), np.array([35.235, 35.444, 35.235]))
    assert d[0, 1] == pytest.approx(22.1, abs=0.5)
    assert d[0, 2] == pytest.approx(111.2, abs=0.1)
    assert np.allclose(d, d.T) and np.allclose(np.diag(d), 0)


def test_short_path_and_shuffles():
    rng = np.random.default_rng(0)
    lon = rng.permutation(np.linspace(34, 36, 12))
    d = distances(np.full(12, 31.0), lon)
    short = short_path(d)
    assert sorted(short) == list(range(12))
    # points on a line: the short path runs along it, end to end (a parallel of latitude bows a
    # little from the great circle)
    assert path_km(d, short) == pytest.approx(d.max(), rel=1e-3)
    null = shuffled_paths(d, 500, rng)
    assert null.shape == (500,) and null.min() >= path_km(d, short) - 1e-6
    assert short_path(d[:3, :3]).tolist() == [0, 1, 2]


def test_districts_cluster():
    rng = np.random.default_rng(1)
    pts = pd.DataFrame({
        "lat": [31.0, 31.01, 31.02, 32.0, 32.01, 32.02],
        "lon": [35.0, 35.01, 35.0, 35.0, 35.01, 35.0],
        "district": [1, 1, 1, 2, 2, 2],
    })  # fmt: skip
    summary, per = score_districts(pts, 199, rng)
    assert summary["n"] == 6 and summary["districts"] == 2 and summary["nearest_same"] == 1.0
    assert summary["within_km"] < 3 and summary["null_mean"] > 30
    assert summary["p"] < 0.2  # 20 ways to label six towns three and three: 2 as tight
    assert [(d["district"], d["n"]) for d in per] == [(1, 3), (2, 3)]


def corpus(tmp_path):
    """Genesis 1:1-6: six towns on a line west to east (places 1-6), named in that order, and a
    region; 1, 3 and 5 sure sites."""
    proc, art = tmp_path / "processed", tmp_path / "art"
    for d in (proc, art / "places"):
        d.mkdir(parents=True)
    pd.DataFrame(
        [(i, 0, 1, i + 1) for i in range(6)], columns=["verse_id", "book_id", "chapter", "verse"]
    ).to_parquet(proc / "verses.parquet")
    pd.DataFrame(
        [(i, "town", 31.0, 34.0 + 0.2 * (i - 1), 600 if i % 2 else 100, "openbible")
         for i in range(1, 7)] + [(7, "region", 31.5, 35.0, 500, "openbible")],
        columns=["place_id", "kind", "lat", "lon", "score", "coord_source"],
    ).astype({"score": "Int64"}).to_parquet(art / "places" / "places.parquet")  # fmt: skip
    # v0 names 2 before 1 by place id but 1 first by word; v3 names 1 again
    mentions = [("b", 0, 2), ("a", 0, 1), ("c", 1, 3), ("d", 2, 4), ("r", 2, 7), ("e", 3, 5),
                ("a", 3, 1), ("f", 4, 6)]  # fmt: skip
    pd.DataFrame(mentions, columns=["lemma", "verse_id", "place_id"]).to_parquet(
        art / "places" / "mentions.parquet"
    )
    words = [(0, 0, ["x"]), (0, 1, ["a"]), (0, 2, None), (0, 3, ["b"]), (1, 0, ["c"]),
             (2, 0, ["r"]), (2, 1, ["d"]), (3, 0, ["e"]), (3, 1, ["a"]), (4, 0, ["f"])]  # fmt: skip
    pd.DataFrame(words, columns=["verse_id", "idx", "content_lemmas"]).to_parquet(
        proc / "words.parquet"
    )
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art)}
    cfg["place_lists"] = {
        **cfg["place_lists"], "shuffles": 199, "min_places": 3,
        "lists": [{"key": "line", "ref": "Genesis 1:1-5", "kind": "itinerary",
                   "places": ["town"]}],
        "districts": [{"key": "g", "places": ["town"],
                       "groups": ["Genesis 1:1-2", "Genesis 1:4-5"]}],
    }  # fmt: skip
    return cfg


def test_run_place_lists(tmp_path):
    cfg = corpus(tmp_path)
    out = run_place_lists(cfg, log=lambda _: None)
    steps = pd.read_parquet(out / "steps.parquet")
    # word order within a verse; the region left out; a place named again keeps its first place
    assert steps.place_id.tolist() == [1, 2, 3, 4, 5, 6]
    assert steps.verse_id.tolist() == [0, 0, 1, 2, 3, 4]
    assert np.isnan(steps.km[0]) and steps.km[1:].tolist() == pytest.approx([19.1] * 5, abs=0.1)
    assert steps.sure.tolist() == [True, False, True, False, True, False]
    assert sorted(steps.short_pos) == [1, 2, 3, 4, 5, 6]
    lists = pd.read_parquet(out / "lists.parquet").set_index("variant")
    a, s = lists.loc["all"], lists.loc["sure"]
    assert (a.n_named, a.n, s.n) == (6, 6, 3)
    assert a.path_km == pytest.approx(95.4, abs=0.2) and a.short_km == pytest.approx(a.path_km)
    assert a.order_score == pytest.approx(1.0) and a.p < 0.05 and a.null_mean > a.path_km
    hist = json.loads(a["hist"])
    assert sum(hist["counts"]) == 199 and hist["lo"] <= a.path_km
    d = pd.read_parquet(out / "districts.parquet")
    al = d[d.variant == "all"]
    rows = al[["district", "n", "first_vid", "last_vid"]].values.tolist()
    assert rows == [[1, 3, 0, 1], [2, 2, 3, 4]]
    assert al.within_km.tolist() == pytest.approx([25.4, 19.1], abs=0.1)
    members = pd.read_parquet(out / "members.parquet")
    assert members.groupby("district").place_id.apply(list).to_dict() == {1: [1, 2, 3],
                                                                         2: [5, 6]}  # fmt: skip
    meta = json.loads((out / "place_lists.meta.json").read_text("utf-8"))
    assert meta["order"]["all"] == {"n": 1, "held": 1}
    assert meta["districts"]["g"]["all"]["within_km"] == pytest.approx(23.8, abs=0.1)
    sure = meta["districts"]["g"]["sure"]
    assert (sure["n"], sure["districts"]) == (3, 2)  # 1 and 3, then 5
    first = (out / "lists.parquet").read_bytes()
    run_place_lists(cfg, log=lambda _: None)
    assert (out / "lists.parquet").read_bytes() == first


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_api_lists(client):
    r = client.get("/api/place-lists").json()
    assert r["meta"]["shuffles"] == 999 and "districts" not in r["meta"]
    (li,) = r["lists"]
    assert (li["key"], li["kind"], li["label_en"], li["n_named"]) == ("trek", "itinerary",
                                                                       "v:0–5", 2)  # fmt: skip
    assert li["all"]["p"] == 0.002 and li["all"]["hist"]["counts"] == [1, 3, 5, 2]
    assert li["sure"]["n"] == 1 and li["sure"]["path_km"] is None and li["sure"]["hist"] is None
    (g,) = r["groupings"]
    assert g["key"] == "halves" and g["all"]["districts"] == 2 and g["sure"] == {
        "n": 1, "districts": None, "within_km": None, "null_mean": None, "p": None,
        "all_km": None, "nearest_same": None,
    }  # fmt: skip
    assert [(d["district"], d["all"]["n"], d["sure"] is None) for d in g["districts"]] == [
        (1, 1, False), (2, 1, True),
    ]  # fmt: skip


def test_api_list_and_districts(client):
    d = client.get("/api/place-lists/trek").json()
    assert d["list"]["key"] == "trek"
    assert [(s["pos"], s["place"]["he"], s["km"], s["sure"]) for s in d["steps"]] == [
        (1, "אמר", None, True), (2, "ראשית", 441.2, False),
    ]  # fmt: skip
    assert d["steps"][1]["verse"] == {"verse_id": 5, "label_en": "v:5", "label_he": "v:5"}
    assert client.get("/api/place-lists/nope").status_code == 404
    g = client.get("/api/place-districts/halves").json()
    assert g["grouping"]["key"] == "halves"
    assert [(t["district"], t["place"]["place_id"], t["sure"]) for t in g["towns"]] == [
        (1, 1, True), (2, 2, False),
    ]  # fmt: skip
    assert client.get("/api/place-districts/nope").status_code == 404


def test_findings(client):
    items = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    o, d = items["place_lists_order"], items["place_lists_districts"]
    assert o["verdict"] == "holds" and o["values"] == {
        "n": 1, "held": 1, "sure_n": 0, "sure_held": 0, "max_p": 0.002,
    }  # fmt: skip
    assert d["verdict"] == "fails" and d["values"]["held"] == 0 and d["values"]["max_p"] == 0.5
