"""Graded numerical sayings and lists (`bsim forms`, `/forms`, DESIGN.md §16.45)."""

import json
import sqlite3

import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp
from fastapi.testclient import TestClient

from bsim.analysis.forms import (
    candidate_pairs,
    free_numbers,
    likeness,
    list_runs,
    number_words,
    run_forms,
    step_table,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder

NUMBERS = {"259": 1, "8147": 2, "7969": 3, "702": 4, "7970": 30, "6240": 0, "3967": 100}
STEPS = {(1, 2), (2, 3), (3, 4)}


def words(rows):
    """(verse_id, idx, lemma, morph) -> a words table, each word its own display token."""
    w = pd.DataFrame(rows, columns=["verse_id", "idx", "lemma", "morph"])
    return w.assign(display_idx=w.idx)


def test_number_words():
    w = words([
        (0, 0, "7969", "HAcmsa"),       # שלשה
        (0, 1, "c/702", "HC/Acmsa"),    # וארבעה: the number is the second morpheme
        (0, 2, "702", "HNp"),           # a name is not a number
        (0, 3, "1697", "HNcmsa"),
        (1, 0, "8147 a", "HAcmda"),     # not a lemma in the table ("8147a")
    ])  # fmt: skip
    n = number_words(w, NUMBERS)
    assert n[["verse_id", "idx", "value"]].values.tolist() == [[0, 0, 3], [0, 1, 4]]


def test_free_numbers():
    nums = pd.DataFrame(
        [
            (0, 0, 0, 30), (0, 1, 1, 2),        # שלשים ושנים: one compound number
            (0, 5, 5, 3),                        # alone
            (1, 0, 0, 2), (1, 1, 1, 3),          # שנים שלשה: two side by side a step apart
            (1, 4, 4, 3), (1, 5, 5, 0),          # שלש עשרה: a teen
            (2, 0, 0, 3), (2, 1, 1, 100),        # שלש מאות
            (3, 2, 2, 1), (3, 3, 3, 2), (3, 4, 4, 3),   # three side by side
        ],
        columns=["verse_id", "idx", "display_idx", "value"],
    )  # fmt: skip
    f = free_numbers(nums, STEPS)
    assert list(zip(f.verse_id, f.idx, strict=True)) == [(0, 5), (1, 0), (1, 1)]


def test_candidate_pairs_and_steps():
    free = pd.DataFrame(
        {"verse_id": [0, 0, 0, 1], "idx": [0, 3, 20, 0], "value": [3, 4, 4, 3]}
    )
    a, b = candidate_pairs(free, 8)
    assert list(zip(a, b, strict=True)) == [(0, 1)]  # 20 is too far; verse 1 is another verse
    codes, ok = step_table(free.value.to_numpy(), STEPS)
    assert ok[codes[0], codes[1]] and not ok[codes[1], codes[0]]
    assert candidate_pairs(free.iloc[:1], 8)[0].size == 0


def test_likeness_and_runs():
    # verses 1-3 share a shape, 0 and 4 do not; verse 5 is another book
    x = sp.csr_matrix(np.array([[1, 0, 0], [0, 1, 0], [0, 1, 0], [0, 1, 0], [0, 0, 1], [0, 1, 0]],
                               dtype=float))  # fmt: skip
    book = np.array([0, 0, 0, 0, 0, 1])
    like = likeness(x, np.arange(6), book, 1)
    assert like.tolist() == [0, 1, 1, 1, 0, 0]  # verse 5 is not compared across the book
    assert list_runs(like >= 0.5, book, 3, 0) == [(1, 3, 3)]
    assert list_runs(like >= 0.5, book, 4, 0) == []
    gap = np.array([False, True, True, False, True, True])
    assert list_runs(gap, np.zeros(6, dtype=int), 4, 1) == [(1, 5, 4)]
    assert list_runs(gap, np.zeros(6, dtype=int), 4, 0) == []


def toy(tmp_path):
    """A book of 120 verses of mixed shapes with a saying (v3), a compound number (v5), a run of
    eight stations (v40-v47) and a second book."""
    cfg = load_config()
    proc, art = tmp_path / "processed", tmp_path / "artifacts"
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art)}
    cfg["forms"] = {
        **cfg["forms"],
        "shuffles": 99,
        "list_shuffles": 5,
        "known": [["three … four", ["B0 1:4"]], ["one … two", ["B0 1:7"]]],
        "lists": {**cfg["forms"]["lists"], "quantile": 0.95,
                  "known": [["the stations", "B0 1:41", "B0 1:48"],
                            ["the kings", "B0 1:90", "B0 1:99"]]},
    }  # fmt: skip
    proc.mkdir()
    rng = np.random.default_rng(3)
    pool = ["HNcmsa", "HVqp3ms", "HC/Vqw3ms", "HR/Ncmsa", "HTd/Ncmpa", "HAamsa", "HD", "HTo"]
    rows = []
    n = 130
    for v in range(n):
        if v == 3:
            seq = [("7969", "HAcmsa"), ("1697", "HNcmsa"), ("c/702", "HC/Acmsa")]
        elif v == 5:
            seq = [("7970", "HAcmpa"), ("c/8147", "HC/Acmda"), ("8141", "HNcfsa")]
        elif 40 <= v <= 47:
            seq = [("c/5265", "HC/Vqw3mp"), ("m/9000", "HR/Np"), ("c/2583", "HC/Vqw3mp"),
                   ("b/9001", "HR/Np")]  # fmt: skip
        else:
            seq = [("1", m) for m in rng.choice(pool, int(rng.integers(5, 12)))]
        rows += [(v, i, lem, m) for i, (lem, m) in enumerate(seq)]
    words(rows).to_parquet(proc / "words.parquet")
    book = [0] * 120 + [1] * 10
    pd.DataFrame(
        {
            "verse_id": range(n),
            "book_id": book,
            "ref": [f"B{b} 1:{v + 1 if b == 0 else v - 119}" for v, b in enumerate(book)],
        }
    ).to_parquet(proc / "verses.parquet")
    par = art / "parallelism"
    par.mkdir(parents=True)
    pd.DataFrame({"verse_id": range(n), "prob": [0.9 if v == 3 else 0.1 for v in range(n)]}).assign(
        prob=lambda d: d.prob.where(d.verse_id != 7)  # a verse the stage could not split
    ).to_parquet(par / "verses.parquet")
    return cfg, art


def test_run_forms(tmp_path):
    cfg, art = toy(tmp_path)
    run_forms(cfg, log=lambda _: None)
    out = art / "forms"
    meta = json.loads((out / "forms.meta.json").read_text("utf-8"))
    say = pd.read_parquet(out / "sayings.parquet")
    assert say.verse_id.tolist() == [3]
    assert say.steps.tolist() == ["3 / 4"] and say.known.tolist() == ["three … four"]
    pairs = pd.read_parquet(out / "pairs.parquet")
    assert pairs[["a_tok", "b_tok", "a_value", "b_value"]].values.tolist() == [[0, 2, 3, 4]]
    assert meta["numbers"] == 4 and meta["free"] == 2  # שלשים ושנים is one number
    assert meta["known_found"] == 1 and [k["found"] for k in meta["known"]] == [True, False]
    assert meta["chance"]["observed"] == 1
    assert meta["parallel"] is None  # no other verse holds two free numbers
    lists = pd.read_parquet(out / "lists.parquet")
    assert lists[["first_vid", "last_vid", "kind"]].values.tolist() == [[40, 47, "itinerary"]]
    assert lists.known.tolist() == ["the stations"]
    li = meta["lists"]
    assert li["known_found"] == 1 and li["observed"] == 1 and li["verses"] == 8
    books = pd.read_parquet(out / "books.parquet")
    assert books.set_index("book_id").loc[0, "list_verses"] == 8


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_forms_endpoints(client):
    r = client.get("/api/forms").json()
    assert r["meta"]["chance"]["p"] == 0.196 and "known" not in r["meta"]["lists"]
    assert [(k["first"]["verse_id"], k["hits"], k["found"]) for k in r["known"]] == [
        (0, 1, True), (3, 0, False)
    ]  # fmt: skip
    (adam, _) = r["known_lists"]
    assert adam["n_verses"] == 3 and adam["covered"] == 3 and adam["last_verse"]["verse_id"] == 3
    assert [b["book_id"] for b in r["books"]] == [0, 1]
    s = client.get("/api/forms/sayings").json()
    assert s["total"] == 2
    first = s["items"][0]
    assert first["unit_id"] == "c:0:1" and first["verse"]["verse_id"] == 0
    assert first["pairs"] == [{"a_tok": 1, "b_tok": 3, "a_value": 3, "b_value": 4}]
    assert s["items"][1]["pairs"][0]["b_tok"] is None
    assert client.get("/api/forms/sayings?known=true").json()["total"] == 1
    assert client.get("/api/forms/sayings?unit=c:0:2").json()["total"] == 1
    assert client.get("/api/forms/sayings?book=1").json()["total"] == 0
    li = client.get("/api/forms/lists").json()
    assert li["total"] == 2
    gen = li["items"][0]
    assert gen["kind"] == "genealogy" and gen["n_verses"] == 3
    assert [v["verse_id"] for v in gen["verses"]] == [1, 2, 3]  # serve.list_verses = 3
    assert client.get("/api/forms/lists?kind=names").json()["total"] == 1
    assert client.get("/api/forms/lists?unit=c:0:2").json()["total"] == 1
    assert client.get("/api/forms/lists?limit=0").status_code == 422
    assert client.get("/api/forms/sayings?unit=nope").status_code == 404
    csv = client.get("/api/export/sayings.csv").text.splitlines()
    assert "steps" in csv[0] and len(csv) == 3
    assert len(client.get("/api/export/lists.csv").text.splitlines()) == 3


def test_forms_map_findings_and_dossier(client):
    m = client.get("/api/map/chapter").json()
    assert m["lists"] is True
    share = {p["unit_id"]: p["list_verses"] for p in m["points"]}
    assert share.get("c:0:1") == 2 and share.get("c:1:1") == 1
    f = {x["key"]: x for x in client.get("/api/findings").json()["items"]}
    assert f["forms_known"]["verdict"] == "fails"  # 1 of 2 in the fixture
    assert f["forms_chance"]["verdict"] == "fails"
    assert f["forms_parallel"]["verdict"] == "holds"
    assert f["forms_lists"]["verdict"] == "holds"
    assert f["forms_chance"]["values"]["without_p"] == 0.037
    d = {e["kind"]: e for e in client.get("/api/dossier/c:0:1").json()["entries"]}
    assert d["forms"]["computed"] and d["forms"]["count"] == 2  # a saying and a list


def test_without_the_stage(built):
    cfg, db = built
    with sqlite3.connect(db) as conn:
        for t in ("forms_sayings", "forms_pairs", "forms_lists", "forms_books"):
            conn.execute(f"DELETE FROM {t}")
        conn.execute("UPDATE meta SET value = '{}' WHERE key = 'forms'")
    c = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    assert c.get("/api/forms").json() == {"meta": {"lists": {}}, "known": [], "known_lists": [],
                                         "books": []}  # fmt: skip
    assert c.get("/api/forms/sayings").json()["total"] == 0
    keys = {x["key"] for x in c.get("/api/findings").json()["items"]}
    assert not keys & {"forms_known", "forms_chance", "forms_parallel", "forms_lists"}
    d = {e["kind"]: e for e in c.get("/api/dossier/c:0:1").json()["entries"]}
    assert not d["forms"]["computed"]
    m = c.get("/api/map/chapter").json()
    assert m["lists"] is False and all(p["list_verses"] == 0 for p in m["points"])
