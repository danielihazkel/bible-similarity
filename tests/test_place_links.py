"""Do places named together lie together? (`bsim place-links`, `/place-links`, §16.61)"""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.place_links import decay_bins, decay_test, link_pairs, rho_ranks, run_place_links
from bsim.analysis.stats import g2_table
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder


def test_link_pairs():
    m = pd.DataFrame({"verse_id": [0, 0, 1, 1, 2, 2, 3, 4], "place_id": [1, 2, 1, 2, 1, 3, 3, 3]})
    pairs = link_pairs(m, 10, 2)
    # 1-2 share two verses; 1-3 one; places twice in a verse count once
    assert pairs[["a", "b", "n_together", "n_a", "n_b"]].values.tolist() == [[1, 2, 2, 3, 2]]
    assert pairs.expected[0] == pytest.approx(0.6)
    assert pairs.g2[0] == pytest.approx(g2_table(2, 3, 2, 10))
    # a pair together less often than independence expects is no link
    common = pd.DataFrame({"verse_id": [0, 1, 2, 0, 1, 2], "place_id": [1, 1, 1, 2, 2, 2]})
    assert link_pairs(common, 3, 2).empty


def test_rho_ranks():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    r = rho_ranks(x, np.array([[1.0, 2.0, 3.0, 4.0], [4.0, 3.0, 2.0, 1.0]]))
    assert r == pytest.approx([1.0, -1.0])


def line(n: int) -> tuple[dict[int, float], dict[int, float]]:
    """Places 1..n on a line west to east, 0.3° apart."""
    return {i: 31.0 for i in range(1, n + 1)}, {i: 34.0 + 0.3 * (i - 1) for i in range(1, n + 1)}


def test_decay_test_and_bins():
    rng = np.random.default_rng(0)
    lat, lon = line(8)
    # neighbours strongly linked, far pairs weakly
    pairs = pd.DataFrame(
        [(i, j, 50.0 / (j - i)) for i in range(1, 9) for j in range(i + 1, 9) if (i + j) % 2],
        columns=["a", "b", "g2"],
    )
    res, km = decay_test(pairs, lat, lon, 999, rng)
    # ties in km fall apart by float noise, so not quite -1
    assert res["rho"] < -0.9 and res["p"] < 0.01 and res["places"] == 8
    assert km[0] == pytest.approx(28.6, abs=0.1)
    n_verses = pd.Series(3, index=range(1, 9))
    bins = decay_bins(pairs, n_verses, lat, lon, [0.0, 50.0, 100.0], 2)
    assert [b["pairs"] for b in bins] == [7, 11, 10]
    assert [b["linked"] for b in bins] == [7, 5, 4]
    assert bins[0]["share"] == 1.0 and bins[2]["hi_km"] is None
    assert bins[0]["median_g2"] == 50.0


def corpus(tmp_path):
    """Genesis 1:1-30 (verses 0-29): places 1-6 on a line; neighbours named together in pairs of
    verses, 1 and 6 named together in two verses, place 7 (no point) with 1; Genesis 1:12 is a
    "list" verse naming 2 and 5."""
    proc, art = tmp_path / "processed", tmp_path / "art"
    for d in (proc, art / "places"):
        d.mkdir(parents=True)
    pd.DataFrame(
        [(i, 0, 1, i + 1) for i in range(30)], columns=["verse_id", "book_id", "chapter", "verse"]
    ).to_parquet(proc / "verses.parquet")
    lat, lon = line(6)
    pd.DataFrame(
        [(i, "דן" if i == 1 else "באר שבע" if i == 6 else f"p{i}", lat[i], lon[i],
          600 if i <= 3 else 100, "openbible") for i in range(1, 7)]
        + [(7, "x", None, None, None, None)],
        columns=["place_id", "he", "lat", "lon", "score", "coord_source"],
    ).astype({"score": "Int64"}).to_parquet(art / "places" / "places.parquet")  # fmt: skip
    m = [(0, 1), (0, 2), (1, 1), (1, 2), (2, 2), (2, 3), (3, 2), (3, 3), (4, 3), (4, 4),
         (5, 3), (5, 4), (6, 4), (6, 5), (7, 4), (7, 5), (8, 1), (8, 6), (9, 1), (9, 6),
         (10, 1), (10, 7), (11, 2), (11, 5)]  # fmt: skip
    pd.DataFrame(m, columns=["verse_id", "place_id"]).assign(lemma="x").to_parquet(
        art / "places" / "mentions.parquet"
    )
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art)}
    cfg["place_links"] = {
        **cfg["place_links"], "shuffles": 199, "lists": ["Genesis 1:12"], "far_km": 100.0,
        "bins": [0, 50], "known": [["דן", "באר שבע"], ["p2", "p9"]], "top": 1,
    }  # fmt: skip
    return cfg


def test_run_place_links(tmp_path):
    cfg = corpus(tmp_path)
    out = run_place_links(cfg, log=lambda _: None)
    pairs = pd.read_parquet(out / "pairs.parquet")
    assert pairs[["a", "b"]].values.tolist() == [[1, 2], [1, 6], [2, 3], [3, 4], [4, 5]]
    assert pairs.km.tolist() == pytest.approx([28.6, 142.9, 28.6, 28.6, 28.6], abs=0.2)
    assert pairs.lead_rank.tolist() == [pd.NA, 1, pd.NA, pd.NA, pd.NA]
    meta = json.loads((out / "place_links.meta.json").read_text("utf-8"))
    t = meta["tests"]
    assert (t["all"]["pairs"], t["all"]["places"], t["all"]["verses"]) == (5, 6, 30)
    assert t["no_lists"]["verses"] == 29 and t["sure"] == {"pairs": 2}
    k1, k2 = meta["known"]
    assert (k1["rank"], k1["holds"], k1["a_id"], k1["b_id"]) == (1, True, 1, 6)
    assert (k2["found"], k2["rank"], k2["holds"]) == (False, None, False)
    bins = pd.read_parquet(out / "bins.parquet")
    a = bins[bins.variant == "all"]
    assert a.pairs.tolist() == [5, 10] and a.linked.tolist() == [4, 1]
    assert set(bins.variant) == {"all", "no_lists"}
    first = (out / "pairs.parquet").read_bytes()
    run_place_links(cfg, log=lambda _: None)
    assert (out / "pairs.parquet").read_bytes() == first


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_api_links(client):
    r = client.get("/api/place-links").json()
    assert r["meta"]["far_km"] == 150.0 and r["lists_en"] == ["Exodus 1"]
    assert r["lists_he"] == ["שמות א"]
    assert [(v["variant"], v["test"]["pairs"], len(v["bins"])) for v in r["variants"]] == [
        ("all", 1, 2), ("sure", 0, 0), ("no_lists", 1, 2),
    ]  # fmt: skip
    assert r["variants"][0]["bins"][1] == {"bin": 2, "lo_km": 100.0, "hi_km": None, "pairs": 2,
                                           "linked": 1, "share": 0.5, "median_g2": 9.3}  # fmt: skip
    (k,) = r["known"]
    assert (k["rank"], k["holds"], k["pair"]["a"]["he"], k["pair"]["b"]["he"]) == (
        1, True, "אמר", "ראשית",
    )  # fmt: skip
    (lead,) = r["leads"]
    assert (lead["g2"], lead["km"], lead["lead_rank"], lead["a"]["lat"]) == (9.3, 441.2, 1, 31.78)
    assert r["scatter"] == [{"km": 441.2, "g2": 9.3, "far": True}]


def test_api_pairs(client):
    d = client.get("/api/place-links/pairs", params={"place": 2, "sort": "km"}).json()
    assert (d["total"], d["place"], d["sort"]) == (1, 2, "km")
    assert d["items"][0]["b"]["kind"] == "region"
    assert client.get("/api/place-links/pairs", params={"place": 9}).json()["total"] == 0
    assert client.get("/api/place-links/pairs", params={"far": True}).json()["total"] == 1
    assert client.get("/api/place-links/pairs", params={"sort": "x"}).status_code == 422
    assert client.get("/api/place-links/pairs", params={"limit": 0}).status_code == 422


def test_findings(client):
    items = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    d, k = items["place_links_decay"], items["place_links_known"]
    assert d["verdict"] == "holds" and d["values"]["rho"] == -0.5
    assert d["values"]["sure_rho"] is None and d["values"]["no_lists_p"] == 0.4
    assert k["verdict"] == "holds" and k["values"] == {"n": 1, "held": 1, "top": 10, "rank": 1,
                                                       "km": 441.2}  # fmt: skip
