import json
import math
import sqlite3

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.echoes import book_cycles, chapter_pairs, language_vote, orient, run_echoes
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder


def test_orient_takes_the_strongest_layer():
    assert orient(2, 0, -1.0) == (1, "cited")
    assert orient(0, -1, 1.0) == (-1, "borrowed")
    assert orient(1, -1, 0.0) == (0, "conflict")
    assert orient(0, 0, -1.0) == (-1, "language")
    assert orient(0, 0, 0.0) == (0, "none")
    assert orient(0, 0, math.nan) == (0, "none")


def test_language_vote():
    assert language_vote(0.4, 0.3) == 1 and language_vote(-0.31, 0.3) == -1
    assert language_vote(0.1, 0.3) == 0 and math.isnan(language_vote(math.nan, 0.3))


def test_chapter_pairs_orient_by_canon():
    chapter_of = np.array([0, 0, 1, 1, 2])
    # a span of chapter 1 drawing on chapter 0, and chapter 0 drawing on 2 (against the canon)
    pairs = chapter_pairs([(0, 1, 2, 3), (4, 4, 0, 0), (0, 0, 1, 1)], chapter_of)
    assert pairs == {(0, 1): 1, (0, 2): -1}
    assert chapter_pairs([(0, 0, 1, 1)], chapter_of) == {}  # inside one chapter


def test_book_cycles_from_explicit_layers_only():
    edges = pd.DataFrame(
        {
            "a_book": [0, 0, 1, 2],
            "b_book": [1, 1, 2, 3],
            "direction": [1, -1, 1, -1],
            "basis": ["borrowed", "cited", "language", "borrowed"],
        }
    )
    assert book_cycles(edges, 4) == [[0, 1]]
    assert book_cycles(edges[edges.basis != "cited"], 4) == []


@pytest.fixture
def toy(tmp_path):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(tmp_path), "artifacts": str(tmp_path)}
    chapters = [(f"c:{b}:1", b, 2 * b, 2 * b + 1) for b in range(4)]
    pd.DataFrame(
        {
            "unit_id": [c[0] for c in chapters],
            "unit_type": "chapter",
            "book_id": [c[1] for c in chapters],
            "start_verse_id": [c[2] for c in chapters],
            "end_verse_id": [c[3] for c in chapters],
        }
    ).to_parquet(tmp_path / "units.parquet")
    for d in ("network", "citations", "borrowing", "dating"):
        (tmp_path / d).mkdir()
    pd.DataFrame(
        [
            ("c:0:1", "c:1:1", 1.0, "chapter"),
            ("c:1:1", "c:2:1", 0.5, "chapter"),
            ("c:2:1", "c:3:1", 0.8, "chapter"),
            ("c:0:1", "c:3:1", 0.3, "chapter"),
            ("p:x", "p:y", 1.0, "pericope"),
        ],
        columns=["a", "b", "weight", "unit_type"],
    ).to_parquet(tmp_path / "network" / "edges.parquet")
    pd.DataFrame(
        {
            "verse_id": [3, 7, 6],
            "book_id": [1, 3, 3],
            "target_vid": [0, 1, 7],
            "target_book": [0, 0, 3],
            "resolved": [1, 1, 1],
        }
    ).to_parquet(tmp_path / "citations" / "citations.parquet")
    pd.DataFrame(
        {
            "a_start": [4, 0],
            "a_end": [5, 1],
            "b_start": [6, 6],
            "b_end": [7, 7],
            "spelling": [0.5, 1.0],
            "n_spelling": [5, 5],
            "direction": ["b_to_a", "b_to_a"],
        }
    ).to_parquet(tmp_path / "borrowing" / "sequences.parquet")
    pd.DataFrame(
        {
            "unit_id": [c[0] for c in chapters],
            "score": [0.1, 0.2, 0.9, 0.5],
            "out_of_domain": [False, False, False, True],
        }
    ).to_parquet(tmp_path / "dating" / "chapters.parquet")
    return cfg, tmp_path


def test_run_echoes(toy):
    cfg, tmp = toy
    out = run_echoes(cfg, log=lambda _: None)
    e = pd.read_parquet(out / "edges.parquet").set_index(["a", "b"])
    assert len(e) == 4  # cross-book chapter pairs only (the within-book citation is not one)
    assert tuple(e.loc[("c:0:1", "c:1:1"), ["direction", "basis"]]) == (1, "cited")
    assert tuple(e.loc[("c:1:1", "c:2:1"), ["direction", "basis"]]) == (1, "language")
    assert e.loc[("c:1:1", "c:2:1"), "gap"] == pytest.approx(0.7)
    assert tuple(e.loc[("c:2:1", "c:3:1"), ["direction", "basis"]]) == (-1, "borrowed")
    assert pd.isna(e.loc[("c:2:1", "c:3:1"), "language"])  # out of the profile's domain
    assert tuple(e.loc[("c:0:1", "c:3:1"), ["direction", "basis"]]) == (0, "conflict")
    books = pd.read_parquet(out / "books.parquet")
    assert books[["src_book", "dst_book"]].values.tolist() == [[0, 1], [1, 2], [3, 2]]
    ch = pd.read_parquet(out / "chapters.parquet").set_index("unit_id")
    assert ch.loc["c:3:1", "lends_explicit"] == 1 and ch.loc["c:2:1", "borrows"] == 2
    meta = json.loads((out / "echoes.meta.json").read_text("utf-8"))
    assert meta["bases"] == {"cited": 1, "borrowed": 1, "language": 1, "conflict": 1, "none": 0}
    assert meta["checks"]["cited"] == {"n": 0, "agree": 0, "p": 1.0, "underpowered": True}
    # the second sequence: book 0 against an out-of-domain chapter; the first likewise
    assert meta["checks"]["spelling"]["n"] == 0
    assert meta["language_forward"] == 1 and meta["cycles"] == []


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_echoes_api(client):
    r = client.get("/api/echoes").json()
    assert r["meta"]["language_backward"] == 1 and len(r["books"]) == 2
    assert r["sources"][0]["unit"]["unit_id"] == "c:0:1"  # the explicit source first
    assert client.get("/api/echoes?top=0").status_code == 422
    items = client.get("/api/echoes/list").json()["items"]
    assert [i["basis"] for i in items] == ["borrowed", "language"]
    assert items[0]["a"]["unit_id"] == "c:0:1" and items[0]["b"]["book_id"] == 1
    back = client.get("/api/echoes/list?backward=true").json()
    assert back["total"] == 1 and back["items"][0]["gap"] == -0.5
    assert client.get("/api/echoes/list?basis=cited").json()["total"] == 0
    assert client.get("/api/echoes/list?basis=nope").status_code == 422
    assert client.get("/api/echoes/list?unit=v:3").json()["total"] == 1
    assert client.get("/api/echoes/list?unit=v:99").status_code == 404
    assert client.get("/api/echoes/list?book=0&directed=false").json()["total"] == 0


def test_dossier_echoes(client):
    d = client.get("/api/dossier/v:5").json()
    assert next(e for e in d["entries"] if e["kind"] == "echoes")["count"] == 2


def test_echoes_in_db(built):
    _, db = built
    conn = sqlite3.connect(db)
    meta = json.loads(conn.execute("SELECT value FROM meta WHERE key = 'echoes'").fetchone()[0])
    assert meta["bases"]["borrowed"] == 1
    assert conn.execute("SELECT COUNT(*) FROM echo_chapters").fetchone()[0] == 3
