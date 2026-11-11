"""The narrative main line and its pauses (DESIGN.md §16.91, D153): the narrator's clauses, the
runs inside the chain, the opening share, the stage on a toy corpus, the API and the reader."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from bsim.analysis.mainline import narrator_clauses, opening_excess, run_mainline, runs
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder

MC = load_config()["mainline"]


def test_narrator_clauses():
    c = pd.DataFrame(
        {
            "clause": [4, 1, 2, 3, 5],
            "typ": ["NmCl", "Way0", "WayX", "xQt0", "Way0"],
            "domain": ["N", "N", "Q", "?", "N"],
            "rela": ["NA", "NA", "NA", "NA", "Attr"],
            "speech": [False, False, True, False, False],
        }
    )
    n = narrator_clauses(c, MC)
    # in text order; quoted speech and a subordinate clause left out
    assert n.clause.tolist() == [1, 3, 4] and n.main.tolist() == [True, False, False]


def test_runs():
    f = np.array([False, True, True, False, True, False, True, True, True])
    assert runs(f, 2) == [(1, 2), (6, 8)]
    assert runs(f, 2, inside=True) == [(1, 2)]  # the last run is not followed by the chain
    assert runs(np.array([True, True, False]), 2, inside=True) == []  # nor is one at the start


def test_opening_excess():
    bg = np.array([1, 1, 0, 0, 1, 0, 0, 0], dtype=bool)
    groups = [np.arange(0, 4), np.arange(4, 8)]
    # first two of each: 3 of 4 background; the rest: 0 of 4
    assert opening_excess(bg, groups, 2) == 0.75
    assert opening_excess(bg, [np.arange(0, 2)], 2) == 0.0  # too short to have a rest


def test_run(tmp_path):
    proc = tmp_path / "processed"
    proc.mkdir()
    # Genesis 1:1-6 (verse ids 0-5): the chain, a pause of two at verses 2-3, the chain again
    typ = ["Way0", "Way0", "NmCl", "Ptcp", "WayX", "Way0", "NmCl"]
    vid = [0, 1, 2, 3, 4, 5, 5]
    pd.DataFrame(
        {
            "clause": range(1, 8),
            "verse_id": vid,
            "words": [[0]] * 7,
            "typ": typ,
            "kind": "VC",
            "domain": "N",
            "txt": "N",
            "rela": "NA",
            "speech": False,
        }
    ).to_parquet(proc / "syntax_clauses.parquet")
    pd.DataFrame(
        {"verse_id": range(6), "book_id": 0, "chapter": 1, "verse": range(1, 7),
         "ref": [f"Genesis 1:{i}" for i in range(1, 7)]}
    ).to_parquet(proc / "verses.parquet")  # fmt: skip
    pd.DataFrame(
        {"unit_id": ["s:0", "s:1"], "unit_type": "pericope", "label_en": "", "label_he": "",
         "book_id": 0, "start_verse_id": [0, 4], "end_verse_id": [3, 5], "n_verses": [4, 2],
         "marker": None}
    ).to_parquet(proc / "units.parquet")  # fmt: skip
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc),
                    "artifacts": str(tmp_path / "artifacts")}  # fmt: skip
    cfg["mainline"] = {**MC, "shuffles": 99, "known": ["Genesis 1:3"]}
    run_mainline(cfg, log=lambda _: None)
    out = tmp_path / "artifacts" / "mainline"
    p = pd.read_parquet(out / "pauses.parquet")
    assert p[["first_vid", "last_vid", "n_clauses"]].values.tolist() == [[2, 3, 2]]
    assert json.loads(p.types[0]) == ["NmCl", "Ptcp"] and bool(p.known[0])
    meta = json.loads((out / "mainline.meta.json").read_text("utf-8"))
    assert (meta["clauses"], meta["main"], meta["background"], meta["known_found"]) == (7, 4, 3, 1)
    per = pd.read_parquet(out / "pericopes.parquet").set_index("unit_id")
    assert (per.loc["s:0", "main"], per.loc["s:0", "background"]) == (2, 2)
    roles = pd.read_parquet(out / "clauses.parquet")
    assert roles.role.tolist() == ["main", "main", "background", "background", "main", "main",
                                   "background"]  # fmt: skip


def test_api_and_reader(built):
    cfg, _ = built  # the fixture's made-up run
    c = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    r = c.get("/api/mainline").json()
    assert (r["clauses"], r["pauses"], r["claim"]["holds"]) == (4, 1, False)
    assert r["books"][0]["share"] == 0.5 and r["max_run"] == MC["max_run"]
    p = c.get("/api/mainline/pauses").json()
    assert p["total"] == 1 and p["items"][0]["types"] == ["NmCl", "Ptcp"] and p["items"][0]["known"]
    assert [v["verse_id"] for v in p["items"][0]["verses"]] == [1]
    assert c.get("/api/mainline/pauses", params={"order": "nope"}).status_code == 422
    rd = c.get("/api/reader/c:0:1").json()
    assert rd["computed"]["mainline"] is True
    marks = {v["verse_id"]: v["mainline"] for v in rd["verses"]}
    assert set(marks[1].values()) == {"background"} and set(marks[0].values()) == {"main"}
    f = {x["key"]: x for x in c.get("/api/findings").json()["items"]}
    assert f["mainline"]["verdict"] == "fails" and f["mainline"]["values"]["known"] == 1
    pub = {**cfg, "serve": {**cfg["serve"], "personal": False}}
    assert (
        TestClient(create_app(pub, encoder=fixture_encoder, log=lambda _: None))
        .get("/api/mainline")
        .status_code
        == 200
    )
