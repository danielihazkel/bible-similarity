"""Claude's notes on verse pairs (series L7, §16.88): the runs gathered, the strongest pairs,
`/pair-note` and the discoveries' notes over the fixture DB, personal only."""

from __future__ import annotations

import json
import sqlite3

import pandas as pd
from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.config import resolve_path
from bsim.eval import llm_notes as ln
from bsim.fixture import fixture_encoder


def _run(cfg, folder, meta_file, rows_file, rows, ids=True, holds=True, rationale="hebrew"):
    out = resolve_path(cfg, "artifacts") / folder
    out.mkdir(parents=True, exist_ok=True)
    cols = ("a_id", "b_id") if ids else ("a", "b")
    pd.DataFrame(
        [
            {cols[0]: f"v:{a}" if ids else a, cols[1]: f"v:{b}" if ids else b, "status": "ok",
             "verdict": v, "p_real": p, "kind": "allusion", "rationale": r}
            for a, b, v, p, r in rows
        ]
    ).to_parquet(out / rows_file)  # fmt: skip
    meta = {"model": "claude-sonnet-5-5", "rationale": rationale,
            "calibration": {"holds": holds, "auc": 0.95 if holds else 0.5}}  # fmt: skip
    (out / meta_file).write_text(json.dumps(meta), "utf-8")


def test_read_notes(tmp_path):
    from bsim.config import load_config

    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "artifacts": str(tmp_path)}
    assert ln.read_notes(cfg) == ({}, {})
    _run(cfg, "llm", "llm_triage.meta.json", "triage.parquet",
         [(3, 0, "real", 0.8, "ויאמר יהוה"), (5, 6, "not", 0.1, "אין")])  # fmt: skip
    _run(cfg, "llm_pool", "llm_pool.meta.json", "judged.parquet",
         [(0, 3, "not", 0.2, "שונים")], ids=False)  # fmt: skip
    _run(cfg, "llm_rerank", "llm_rerank.meta.json", "judged.parquet",
         [(7, 8, "real", 0.9, "x")], holds=False)  # fmt: skip
    runs, notes = ln.read_notes(cfg)
    assert set(runs) == {"llm", "llm_pool"}  # the failed calibration left out
    assert notes[(0, 3)]["run"] == "llm_pool" and notes[(0, 3)]["verdict"] == "not"
    assert notes[(5, 6)]["run"] == "llm" and (7, 8) not in notes
    # a triage whose rationale is in English gives no notes
    _run(cfg, "llm", "llm_triage.meta.json", "triage.parquet",
         [(5, 6, "not", 0.1, "none")], rationale="english")  # fmt: skip
    assert (5, 6) not in ln.read_notes(cfg)[1]


def test_strongest():
    conn = sqlite3.connect(":memory:")
    pd.DataFrame(
        {"unit_type": "verse", "mode": ["fused"] * 4 + ["semantic"],
         "a_id": ["v:0", "v:1", "v:2", "v:3", "v:9"], "b_id": ["v:5", "v:6", "v:7", "v:8", "v:4"],
         "rank_ab": [3, 1, 1, 2, 1], "rank_ba": [None, 1, 4, 2, 1],
         "tie": [0.99, 0.5, 0.6, 0.7, 0.9]}
    ).to_sql("discoveries", conn, index=False)  # fmt: skip
    top = ln.strongest(conn, 10, skip=set())
    # first both ways, then first one way, then the semantic score; other modes left out
    assert list(zip(top.a, top.b, strict=True)) == [(1, 6), (2, 7), (0, 5), (3, 8)]
    assert list(zip(*ln.strongest(conn, 2, skip={(1, 6)}).values.T, strict=True)) == [
        (2, 7),
        (0, 5),
    ]


def test_pair_note(built):
    cfg, _ = built  # the fixture's made-up `llm-notes` run: v:0 / v:3
    c = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    r = c.get("/api/pair-note", params={"a": 3, "b": 0}).json()
    assert (r["note"]["verdict"], r["note"]["run"]) == ("real", "llm_notes")
    assert r["note"]["rationale"] == "שתיהן פותחות בראשית" and r["runs"]["llm_notes"]["pairs"] == 1
    assert c.get("/api/pair-note", params={"a": 1, "b": 2}).json()["note"] is None
    disc = c.get("/api/discoveries", params={"unit_type": "verse", "mode": "fused"}).json()
    noted = [i for i in disc["items"] if i["note"]]
    assert len(noted) == 1
    assert {noted[0]["a"]["unit_id"], noted[0]["b"]["unit_id"]} == {"v:0", "v:3"}
    # a public server: no notes, the route answers 404
    pub = {**cfg, "serve": {**cfg["serve"], "personal": False}}
    p = TestClient(create_app(pub, encoder=fixture_encoder, log=lambda _: None))
    assert p.get("/api/pair-note", params={"a": 3, "b": 0}).status_code == 404
    items = p.get("/api/discoveries", params={"unit_type": "verse", "mode": "fused"}).json()
    assert all(i["note"] is None for i in items["items"])
