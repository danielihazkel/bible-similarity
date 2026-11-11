"""The label queue (`GET /labels/queue`, DESIGN.md §16.79, D132) and your labels as training
pairs (`train.supervised.extra_pairs: [labels]`): ranking, the train-book rule, the API, the
positives and the labelled hard negatives."""

from __future__ import annotations

import json
import sqlite3

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.api.label_queue import rank_queue, unlabelled
from bsim.config import load_config, resolve_path
from bsim.fixture import fixture_encoder
from bsim.store import labels as store
from bsim.train.negatives import mine_hard_negatives
from bsim.train.pairs import extra_links, label_negatives, training_pairs
from bsim.train.supervised import with_overrides

K1 = 51  # retrieval.k + 1: a rank beyond the lists


def test_rank_queue_orders_by_disagreement():
    rows = [
        # a, b, fused score, tie, lex a->b, sem a->b, lex b->a, sem b->a
        ("v:1", "v:9", 0.03, 0.5, 2, 3, None, None),  # both modes agree: 1
        ("v:2", "v:8", 0.02, 0.1, 1, None, None, None),  # lexical first, semantic beyond: 50
        ("v:3", "v:7", 0.01, 0.9, None, None, None, 4),  # semantic 4 (b->a), lexical beyond: 47
        ("v:4", "v:6", 0.04, 0.2, 9, None, None, 1),  # the best rank of either direction: 8
        ("v:5", "v:10", 0.025, 0.1, None, 1, None, None),  # semantic first: 50, a stronger pair
        # equal to v:5 in disagreement and fused score: the sides take turns, semantic ones in
        # their own order (v:13's semantic score is higher)
        ("v:11", "v:12", 0.025, 0.0, 1, None, None, None),
        ("v:13", "v:14", 0.025, 0.9, None, 1, None, None),
    ]
    q = rank_queue(rows, K1)
    assert [(p.a_id, p.disagreement, p.side) for p in q] == [
        ("v:11", 50, "lexical"),
        ("v:13", 50, "semantic"),
        ("v:5", 50, "semantic"),
        ("v:2", 50, "lexical"),
        ("v:3", 47, "semantic"),
        ("v:4", 8, "semantic"),
        ("v:1", 1, "lexical"),
    ]
    assert (q[5].lex_rank, q[5].sem_rank) == (9, 1)
    q = [p for p in q if p.a_id not in ("v:11", "v:13")]
    done = {("v:5", "v:10"), ("v:3", "v:7")}
    assert [p.a_id for p in unlabelled(q, done, "all")] == ["v:2", "v:4", "v:1"]
    assert [p.a_id for p in unlabelled(q, done, "semantic")] == ["v:4"]
    assert [p.a_id for p in unlabelled(q, set(), "lexical")] == ["v:2", "v:1"]


# --- the API over the fixture DB -----------------------------------------------------------------


@pytest.fixture
def client(built):
    cfg, db = built
    # the fixture's one fused discovery between train-book verses, v:0 -> v:3 (rank 2): lexical
    # ranks it first, semantic does not list it
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE matches SET lex_rank = 1, sem_rank = NULL WHERE unit_type = 'verse'"
            " AND mode = 'fused' AND src_id = 'v:0' AND tgt_id = 'v:3'"
        )
    return cfg, TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_api_queue(client):
    cfg, c = client
    r = c.get("/api/labels/queue")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    body = r.json()
    assert (body["split"], body["k"], body["pool"], body["labelled"], body["total"]) == (
        "train",
        cfg["retrieval"]["k"],
        1,
        0,
        1,
    )
    (item,) = body["items"]
    assert (item["a_id"], item["b_id"], item["lex_rank"], item["sem_rank"]) == (
        "v:0",
        "v:3",
        1,
        None,
    )
    assert (item["disagreement"], item["side"]) == (cfg["retrieval"]["k"], "lexical")
    assert item["a"]["ref"] and item["b"]["display_tokens"]
    assert c.get("/api/labels/queue?side=semantic").json()["total"] == 0
    # a labelled pair leaves the queue (in either order), and is counted
    c.put("/api/labels", json={"a_id": "v:3", "b_id": "v:0", "label": "not", "mode": "queue"})
    after = c.get("/api/labels/queue").json()
    assert (after["labelled"], after["total"], after["items"]) == (1, 0, [])
    # your real pairs between train books count towards training (v:5 is in a dev book)
    assert (after["train_real"], after["min_train"]) == (0, cfg["labels"]["min_train"])
    c.put("/api/labels", json={"a_id": "v:0", "b_id": "v:2", "label": "real"})
    c.put("/api/labels", json={"a_id": "v:1", "b_id": "v:5", "label": "real"})
    assert c.get("/api/labels/queue").json()["train_real"] == 1
    assert c.get("/api/labels/queue?side=other").status_code == 422
    assert c.get("/api/labels/queue?limit=0").status_code == 422


def test_api_queue_without_splits(built):
    cfg, _ = built
    # no preload: its thread reads splits.json at start, and Windows will not delete an open file
    queue = {**cfg["labels"]["queue"], "preload": False}
    cfg = {**cfg, "labels": {**cfg["labels"], "queue": queue}}
    c = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    (resolve_path(cfg, "data_processed") / "splits.json").unlink()
    r = c.get("/api/labels/queue")
    assert r.status_code == 503 and r.json()["detail"]["code"] == "splits_missing"


# --- your labels as training pairs --------------------------------------------------------------


def _labels_cfg(tmp_path, labels, min_train=2):
    """A config whose processed data is 15 verses in Genesis (0-4), Exodus (5-9), Joshua (10-14)."""
    cfg = load_config()
    proc = tmp_path / "processed"
    proc.mkdir()
    cfg["paths"] = {
        **cfg["paths"],
        "data_processed": str(proc),
        "labels": str(tmp_path / "labels.sqlite"),
    }
    cfg["labels"] = {**cfg["labels"], "min_train": min_train}
    verses = pd.DataFrame({"verse_id": range(15), "book_id": np.repeat([0, 1, 5], 5)})
    verses.to_parquet(proc / "verses.parquet")
    books = {"Genesis": "train", "Exodus": "train", "Joshua": "dev"}
    (proc / "splits.json").write_text(json.dumps({"books": books}), "utf-8")
    conn = store.connect(resolve_path(cfg, "labels"))
    for a, b, lab in labels:
        store.put(conn, "verse", f"v:{a}", f"v:{b}", lab)
    store.put(conn, "chapter", "c:0:1", "c:1:1", "real")  # not a verse pair: never trains
    conn.close()
    return cfg


def test_label_pairs_train_only_between_train_books(tmp_path):
    labels = [(0, 6, "real"), (1, 7, "real"), (2, 11, "real"), (3, 8, "not"), (4, 12, "not")]
    labels += [(0, 9, "unsure")]
    cfg = _labels_cfg(tmp_path, labels)
    df = extra_links(cfg, "labels")
    # both directions of every real pair, each with its split; unsure and not left out
    got = {(a, b, s) for a, b, s in zip(df.src_vid, df.tgt_vid, df.split, strict=True)}
    assert got == {(0, 6, "train"), (6, 0, "train"), (1, 7, "train"), (7, 1, "train")} | {
        (2, 11, "dev"),
        (11, 2, "dev"),
    }
    # only the train pair of the not labels becomes a negative
    assert label_negatives(cfg) == {3: {8}, 8: {3}}
    # as an extra source: the train pairs added after Sefaria's, every real pair kept from being
    # drawn as a negative
    pd.DataFrame(
        {"src_vid": [5, 10], "tgt_vid": [10, 5], "split": "dev", "level": "verse"}
    ).to_parquet(resolve_path(cfg, "data_processed") / "links.parquet")
    pairs, linked = training_pairs(with_overrides(cfg, extra_pairs=["labels"]))
    assert pairs.source.tolist() == ["labels"] * 4
    assert {(2, 11), (0, 6)} <= set(zip(linked.src_vid, linked.tgt_vid, strict=True))


def test_label_pairs_need_enough_labels(tmp_path):
    cfg = _labels_cfg(tmp_path, [(0, 6, "real"), (2, 11, "real")], min_train=2)
    with pytest.raises(
        RuntimeError, match="needs 2 real verse pairs between train books, there are 1"
    ):
        extra_links(cfg, "labels")


def test_labelled_not_is_the_negative_when_eligible():
    book = np.repeat([0, 1, 2], 5)
    train_book = np.array([True, True, False])
    cand = pd.DataFrame({"src": 0, "tgt": [6, 7], "rank": [2, 3]})

    def mine(labelled_not, anchors=(0,), positives=(8,), linked=None):
        return mine_hard_negatives(
            np.array(anchors), np.array(positives), cand, book, train_book, linked or {},
            np.arange(15), (2, 10), 1, 0, labelled_not,
        )  # fmt: skip

    df = mine({0: {3}})
    assert (df.negative_vid[0], df.negative_rank[0], df.from_label[0]) == (3, -1, True)
    # not eligible (a neighbour of the positive, or linked to the anchor): BM25 as before
    for labelled, linked in (({0: {9}}, None), ({0: {3}}, {0: {3}})):
        df = mine(labelled, linked=linked)
        assert not df.from_label[0] and df.negative_vid[0] in (6, 7)
    assert not mine(None).from_label.any()
