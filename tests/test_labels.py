import json

import pytest
from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.config import resolve_path
from bsim.data.canon import BOOKS
from bsim.eval.labels import ranks_from_lists, run_eval_labels, separation, verse_labels
from bsim.fixture import fixture_encoder
from bsim.store import labels as store


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_store_roundtrip(tmp_path):
    conn = store.connect(tmp_path / "x" / "labels.sqlite")
    store.put(conn, "verse", "v:0", "v:3", "real", mode="fused", score=0.5)
    store.put(conn, "verse", "v:0", "v:3", "not")  # replaces
    store.put(conn, "verse", "v:1", "v:2", "unsure")
    rows = store.all_labels(conn)
    assert sorted((r["a_id"], r["b_id"], r["label"]) for r in rows) == [
        ("v:0", "v:3", "not"),
        ("v:1", "v:2", "unsure"),
    ]
    with pytest.raises(ValueError):
        store.put(conn, "verse", "v:0", "v:1", "maybe")
    assert store.delete(conn, "v:1", "v:2") and not store.delete(conn, "v:1", "v:2")
    conn.close()
    assert len(store.read_labels(tmp_path / "x" / "labels.sqlite")) == 1
    assert store.read_labels(tmp_path / "none.sqlite") == []


def test_separation():
    labels = {("a", "b"): "real", ("a", "c"): "real", ("d", "e"): "not", ("f", "g"): "not"}
    ranks = {("a", "b"): 1, ("a", "c"): 30, ("d", "e"): 5}
    s = separation(ranks, labels, k=10, min_pairs=2)
    assert (s["n_real"], s["n_not"], s["found_real"], s["found_not"]) == (2, 2, 1, 1)
    assert s["recall"] == 0.5 and s["precision"] == 0.5
    # real scores 1, 1/30; not scores 1/5, 0 -> 3 of 4 orderings right
    assert s["auc"] == 0.75
    assert separation(ranks, labels, k=10, min_pairs=3)["auc"] is None
    empty = separation({}, {}, k=10, min_pairs=1)
    assert empty["recall"] is None and empty["precision"] is None


def test_ranks_and_verse_labels():
    ranked = {0: [3, 5], 5: [1, 0]}
    assert ranks_from_lists(ranked, [(0, 5), (0, 3), (1, 2)]) == {(0, 5): 2, (0, 3): 1}
    split_of_book = {0: "train", 1: "dev"}
    book = [0, 0, 1]
    df = verse_labels(
        [
            {"unit_type": "verse", "a_id": "v:0", "b_id": "v:2", "label": "real"},
            {"unit_type": "verse", "a_id": "v:0", "b_id": "v:1", "label": "not"},
            {"unit_type": "chapter", "a_id": "c:0:1", "b_id": "c:1:1", "label": "real"},
        ],
        book,
        split_of_book,
    )
    assert df.values.tolist() == [[0, 2, "real", "dev"], [0, 1, "not", "train"]]


def test_labels_api(client):
    empty = client.get("/api/labels")
    assert empty.json() == {
        "writable": True,
        "counts": {"real": 0, "not": 0, "unsure": 0},
        "items": [],
    }
    assert empty.headers["cache-control"] == "no-store"
    # either order: stored with the earlier unit first
    r = client.put(
        "/api/labels", json={"a_id": "v:3", "b_id": "v:0", "label": "real", "mode": "fused"}
    )
    assert r.status_code == 200, r.text
    assert (r.json()["a"]["unit_id"], r.json()["b"]["unit_id"]) == ("v:0", "v:3")
    client.put("/api/labels", json={"a_id": "v:0", "b_id": "v:3", "label": "not", "note": "chance"})
    client.put("/api/labels", json={"a_id": "c:0:1", "b_id": "c:0:2", "label": "unsure"})
    body = client.get("/api/labels").json()
    assert body["counts"] == {"real": 0, "not": 1, "unsure": 1}
    v = next(i for i in body["items"] if i["unit_type"] == "verse")
    assert v["note"] == "chance" and v["label"] == "not"
    bad = [
        {"a_id": "v:0", "b_id": "v:0", "label": "real"},
        {"a_id": "v:0", "b_id": "c:0:1", "label": "real"},
        {"a_id": "v:0", "b_id": "v:1", "label": "maybe"},
    ]
    for b in bad:
        assert client.put("/api/labels", json=b).status_code == 422
    assert (
        client.put("/api/labels", json={"a_id": "v:0", "b_id": "v:99", "label": "real"}).status_code
        == 404
    )

    ev = client.get("/api/labels/eval").json()
    assert ev["k"] == 10
    fused = next(r for r in ev["rows"] if r["unit_type"] == "verse" and r["mode"] == "fused")
    assert (fused["n_not"], fused["found_not"], fused["precision"]) == (1, 1, 0.0)

    assert client.delete("/api/labels/v:3/v:0").status_code == 204
    assert client.delete("/api/labels/v:3/v:0").status_code == 404
    assert client.get("/api/labels").json()["counts"]["not"] == 0


def test_labels_read_only(built):
    cfg, _ = built
    cfg["serve"] = {**cfg["serve"], "labels_writable": False}
    c = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    assert c.get("/api/labels").json()["writable"] is False
    assert (
        c.put("/api/labels", json={"a_id": "v:0", "b_id": "v:3", "label": "real"}).status_code
        == 403
    )


def test_run_eval_labels(built):
    cfg, _ = built
    proc = resolve_path(cfg, "data_processed")
    # book 0 (the fixture's first book) is dev, everything else train
    splits = {b.sefaria: "dev" if b.book_id == 0 else "train" for b in BOOKS}
    (proc / "splits.json").write_text(json.dumps({"books": splits}), "utf-8")
    with pytest.raises(RuntimeError, match="no labels"):
        run_eval_labels(cfg, log=lambda _: None)
    conn = store.connect(resolve_path(cfg, "labels"))
    store.put(conn, "verse", "v:0", "v:3", "real")
    store.put(conn, "verse", "v:0", "v:5", "not")
    store.put(conn, "verse", "v:1", "v:4", "unsure")
    conn.close()
    out = run_eval_labels(cfg, log=lambda _: None)
    assert out["counts"]["dev"] == {"real": 1, "not": 1, "unsure": 1}
    assert out["gold"]["real_pairs"] == 1
    fused = out["results"]["fused"]
    assert fused["retrieval"]["queries"] == 2  # both ends of the real pair are queries
    assert fused["separation"]["found_real"] == 1
    art = resolve_path(cfg, "artifacts") / "eval"
    assert (art / "labels.json").exists() and "Your labels" in (art / "labels.md").read_text(
        "utf-8"
    )
