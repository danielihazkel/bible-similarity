"""A unit's neighbourhood graph (DESIGN.md §11.1, D149): the walk, the kinds, the layout, the
limits, a public server."""

from __future__ import annotations

from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.api.neighbourhood import KINDS
from bsim.fixture import fixture_encoder


def client(cfg):
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_the_graph(built):
    cfg, _ = built
    c = client(cfg)
    r = c.get("/api/neighbourhood/v:0").json()
    nodes = {n["unit"]["unit_id"]: n for n in r["nodes"]}
    assert r["unit"]["unit_id"] == "v:0" and (r["k"], r["hops"]) == (6, 2)
    assert nodes["v:0"]["hop"] == 0 and (nodes["v:0"]["x"], nodes["v:0"]["y"]) == (0.5, 0.5)
    assert len(nodes) > 1 and all(0 <= n["x"] <= 1 and 0 <= n["y"] <= 1 for n in nodes.values())
    assert {n["hop"] for n in nodes.values()} <= {0, 1, 2}
    for e in r["edges"]:
        assert e["a"] < e["b"] and {e["a"], e["b"]} <= set(nodes)
        assert e["kinds"] and e["kinds"] == [k for k in KINDS if k in e["kinds"]]  # colour first
    hits = {e["b"] if e["a"] == "v:0" else e["a"] for e in r["edges"] if "v:0" in (e["a"], e["b"])}
    own = c.get("/api/similar/v:0", params={"mode": "fused", "k": 6, "exclude": "neighbors"}).json()
    assert {h["unit"]["unit_id"] for h in own["hits"]} <= hits  # the unit's own list, every hit
    assert c.get("/api/neighbourhood/v:0").json() == r  # the same layout every time


def test_one_hop_and_the_cap(built):
    cfg, _ = built
    one = client(cfg).get("/api/neighbourhood/v:0", params={"hops": 1, "k": 2}).json()
    assert {n["hop"] for n in one["nodes"]} <= {0, 1} and len(one["nodes"]) <= 3
    nc = {**cfg["serve"]["neighbourhood"], "max_nodes": 2}
    small = {**cfg, "serve": {**cfg["serve"], "neighbourhood": nc}}
    r = client(small).get("/api/neighbourhood/v:0").json()
    assert len(r["nodes"]) == 2 and r["truncated"]


def test_limits_and_a_public_server(built):
    cfg, _ = built
    c = client(cfg)
    assert c.get("/api/neighbourhood/v:999999").status_code == 404
    assert c.get("/api/neighbourhood/v:0", params={"k": 0}).status_code == 422
    assert c.get("/api/neighbourhood/v:0", params={"k": 11}).status_code == 422
    assert c.get("/api/neighbourhood/v:0", params={"hops": 3}).status_code == 422
    pub = {**cfg, "serve": {**cfg["serve"], "personal": False}}
    assert client(pub).get("/api/neighbourhood/c:0:1").status_code == 200  # stored lists only
