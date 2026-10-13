"""Who speaks to whom (`bsim dialogue`, `/dialogue`, DESIGN.md §16.44)."""

import json
import sqlite3

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.dialogue import (
    exchange_table,
    exchanges,
    pair_table,
    party_of,
    quotations,
    rank_of,
    run_dialogue,
    turn_checks,
    up_test,
    word_marks,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder

DIVINE = {"3068", "430"}
KINGS = {"4428"}


def test_word_marks():
    words = pd.DataFrame(
        {
            "verse_id": [0, 0, 0, 0, 1],
            "idx": [0, 1, 2, 3, 0],
            "morph": ["HVqv2ms", "HTe", "HNcmsc/Sp2ms", "HNcmsc/Sp1cs", "HTe"],
            "content_lemmas": [["1980"], ["4994"], ["5650"], ["5650"], ["4994"]],
        }
    )
    m = word_marks(words, {"5650"}, "4994")
    # לך נא: an imperative with נא; עבדך "your servant", not עבדי
    assert m.imperative.tolist() == [True, False, False, False, False]
    assert m.particle.tolist() == [True, False, False, False, False]
    assert m.deference.tolist() == [False, False, True, False, False]


def clauses(rows):
    return pd.DataFrame(
        rows,
        columns=["clause", "verse_id", "words", "txt", "speaker", "speaker_source", "quote",
                 "addressee", "addressee_source"],
    )  # fmt: skip


def test_quotations_extent_and_words():
    c = clauses([
        (1, 0, [0, 1], "N", None, None, -1, None, None),
        (2, 0, [2, 3], "NQ", "4872", "explicit", 2, "175", "explicit"),
        (3, 1, [0], "NQQ", "3068", "enclosing", 3, None, None),  # embedded: inside 2's extent
        (4, 1, [1, 2], "NQ", "4872", "explicit", 2, "175", "explicit"),
        (5, 2, [0], "N", None, None, -1, None, None),
        (6, 2, [1], "NQ", "175", "explicit", 6, "4872", "turn"),
    ])  # fmt: skip
    verses = pd.DataFrame({"verse_id": [0, 1, 2], "book_id": [0, 0, 0], "chapter": [1, 1, 1]})
    marks = pd.DataFrame({"verse_id": [0], "idx": [2], "deference": [True],
                          "imperative": [True], "particle": [True]})  # fmt: skip
    q = quotations(c, marks, verses)
    assert q.quote.tolist() == [2, 3, 6]
    assert q.n_words.tolist() == [4, 1, 1] and q.deference.tolist() == [1, 0, 0]
    assert q.start.tolist() == [1, 2, 5] and q.end.tolist() == [3, 2, 5]
    assert q.narrated.tolist() == [True, False, True]
    assert q.last_verse_id.tolist() == [1, 1, 2]


def test_ranks_and_parties():
    assert [rank_of(x, DIVINE, KINGS) for x in ("3068", "4428", "4872", None, "divine")] == [
        2, 1, 0, 0, 2,
    ]  # fmt: skip
    assert party_of("430", DIVINE) == "divine" and party_of("4872", DIVINE) == "4872"


def qrows(rows):
    """(speaker_party, addressee_party, start, end[, book, depth, narrated]) -> quotations."""
    full = [(*r, 0, 2, True)[:7] if len(r) == 4 else r for r in rows]
    q = pd.DataFrame(full, columns=["speaker_party", "addressee_party", "start", "end", "book_id",
                                    "depth", "narrated"])  # fmt: skip
    return q.assign(
        speaker=q.speaker_party, chapter=1, verse_id=q.start, last_verse_id=q.end,
        n_words=10,
    )  # fmt: skip


def test_exchanges():
    q = qrows([
        ("divine", "4872", 0, 3), ("4872", None, 5, 6), ("divine", "4872", 8, 9),
        ("175", "4872", 11, 12),  # a third speaker closes the run
        ("4872", "175", 13, 14),
        ("4872", "8193", 15, 16),  # still Moses, but to someone else: closes it
        ("8193", "4872", 30, 31),  # too far after
    ])  # fmt: skip
    assert exchanges(q, 4) == [[0, 1, 2], [3, 4]]
    # an unknown speaker breaks a run; turns the narrator does not introduce are left out
    q2 = qrows([("4872", "175", 0, 1), (None, None, 2, 3), ("175", "4872", 4, 5)])
    assert exchanges(q2, 4) == []
    q3 = qrows([("4872", "175", 0, 1, 0, 2, True), ("175", "4872", 2, 3, 0, 2, False)])
    assert exchanges(q3, 4) == []
    ex = exchange_table(q, 4, DIVINE, KINGS)
    assert ex[["a", "b", "turns", "a_turns", "last"]].values.tolist() == [
        ["divine", "4872", 3, 2, "divine"],
        ["175", "4872", 2, 1, "4872"],
    ]
    assert ex.a_rank.tolist() == [2, 0] and ex.a_words.tolist() == [20, 10]


def test_up_test_finds_a_planted_rate():
    rng = np.random.default_rng(0)
    n = 200
    up = np.arange(n) % 4 == 0
    words = np.full(n, 100)
    value = np.where(up, 3, 0)
    book = np.arange(n) % 2
    t = up_test(value, words, up, book, 199, rng, 1000.0)
    assert t["observed"] == pytest.approx(30.0) and t["p"] == pytest.approx(1 / 200)
    assert t["up"] == {"rate": 30.0, "count": 150, "of": 5000, "quotations": 50}
    flat = up_test(np.full(n, 1), words, up, book, 199, rng, 1000.0)
    assert flat["observed"] == 0 and flat["p"] > 0.5


def test_turn_checks():
    ex = pd.DataFrame(
        {
            "a": ["divine", "4872", "4428"],
            "b": ["4872", "divine", "175"],
            "a_rank": [2, 0, 1],
            "b_rank": [0, 2, 0],
            "turns": [2, 3, 4],
            "a_turns": [1, 2, 2],
            "a_words": [30, 10, 8],
            "b_words": [5, 40, 20],
            "last": ["4872", "4872", "175"],
        }
    )
    t = turn_checks(ex, 99, np.random.default_rng(0))
    # the higher one ends none of three; its share of the turns would give 0.5 + 1/3 + 0.5
    assert t["unequal"] == 3 and t["last_word"]["observed"] == 0
    assert t["last_word"]["expected"] == pytest.approx(1.33, abs=0.01)
    assert t["opener"]["observed"] == 2
    assert (t["lengths"]["longer"], t["lengths"]["shorter"]) == (2, 1)


def test_pair_table():
    q = pd.DataFrame(
        {
            "book_id": [0, 0, 0, 1],
            "speaker_party": ["divine", "divine", "4872", "4872"],
            "addressee_party": ["4872", "4872", "4872", None],
            "addressee_source": ["explicit", "turn", "explicit", None],
            "quote": [1, 2, 3, 4],
            "n_words": [5, 7, 2, 1],
        }
    )
    p = pair_table(q, ["explicit", "vocative"])
    assert p.values.tolist() == [[0, "divine", "4872", 2, 12, 1]]


def test_run_dialogue(tmp_path):
    cfg = load_config()
    proc, art = tmp_path / "processed", tmp_path / "artifacts"
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art)}
    cfg["dialogue"] = {**cfg["dialogue"], "shuffles": 19}
    proc.mkdir()
    clauses([
        (1, 0, [0], "N", None, None, -1, None, None),
        (2, 0, [1, 2], "NQ", "1732", "explicit", 2, "4428", "explicit"),
        (3, 1, [0], "N", None, None, -1, None, None),
        (4, 1, [1], "NQ", "4428", "explicit", 4, "1732", "turn"),
    ]).assign(speech=lambda d: d.txt.str.endswith("Q")).to_parquet(
        proc / "syntax_clauses.parquet"
    )  # fmt: skip
    pd.DataFrame(
        {
            "verse_id": [0, 0, 0, 1, 1],
            "idx": [0, 1, 2, 0, 1],
            "morph": ["HVqw3ms", "HNcmsc/Sp2ms", "HVqv2ms", "HVqw3ms", "HTe"],
            "content_lemmas": [["559"], ["5650"], ["1980"], ["559"], ["4994"]],
        }
    ).to_parquet(proc / "words.parquet")
    pd.DataFrame({"verse_id": [0, 1], "book_id": [8, 8], "chapter": [1, 1]}).to_parquet(
        proc / "verses.parquet"
    )
    meta = run_dialogue(cfg, log=lambda _: None)
    assert meta["quotations"] == 2 and meta["with_addressee"] == 2
    assert meta["addressee"] == {"explicit": 1, "vocative": 0, "pronoun": 0, "turn": 1}
    assert meta["exchanges"] == 1 and meta["unequal"] == 1
    assert meta["tests"]["deference"]["up"]["count"] == 1
    assert meta["tests"]["last_word"]["observed"] == 1  # the king answers last
    assert (art / "dialogue" / "exchanges.parquet").exists()
    saved = json.loads((art / "dialogue" / "dialogue.meta.json").read_text("utf-8"))
    assert saved["hand_check"]["explicit"] == [21, 21]


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_dialogue_endpoints(client):
    r = client.get("/api/dialogue").json()
    assert r["meta"]["tests"]["deference"]["holds"] is True
    assert r["books"] == [
        {"book_id": 0, "n_quotes": 3, "n_pairs": 2, "n_exchanges": 1},
        {"book_id": 1, "n_quotes": 1, "n_pairs": 1, "n_exchanges": 0},
    ]
    b = client.get("/api/dialogue/book/0").json()
    first = b["pairs"][0]
    assert first["speaker"] == {"key": "divine", "he": None, "rank": 2}
    assert first["addressee"]["key"] == "4872" and first["n_quotes"] == 2
    assert client.get("/api/dialogue/book/7").json()["pairs"] == []
    e = client.get("/api/dialogue/exchanges").json()
    assert e["total"] == 1
    (x,) = e["items"]
    assert x["unit_id"] == "c:0:1" and x["first"]["verse_id"] == 1
    assert x["last_verse"]["verse_id"] == 2 and x["last"] == "4872" and x["a"]["rank"] == 2
    assert client.get("/api/dialogue/exchanges?party=divine&unequal=true").json()["total"] == 1
    assert client.get("/api/dialogue/exchanges?party=175").json()["total"] == 0
    assert client.get("/api/dialogue/exchanges?book=1").json()["total"] == 0
    assert client.get("/api/dialogue/exchanges?limit=0").status_code == 422
    assert client.get("/api/dialogue/exchanges?party=").status_code == 422
    csv = client.get("/api/export/exchanges.csv").text.splitlines()
    assert "a.key" in csv[0] and len(csv) == 2


def test_dialogue_findings_and_dossier(client):
    f = {x["key"]: x for x in client.get("/api/findings").json()["items"]}
    assert f["dialogue_deference"]["verdict"] == "holds"
    assert f["dialogue_particle"]["verdict"] == "holds"
    assert f["dialogue_last_word"]["verdict"] == "fails"
    assert f["dialogue_deference"]["values"]["up"] == 13.1
    d = {e["kind"]: e for e in client.get("/api/dossier/c:0:1").json()["entries"]}
    assert d["dialogue"]["computed"] and d["dialogue"]["count"] == 1
    d2 = {e["kind"]: e for e in client.get("/api/dossier/c:1:1").json()["entries"]}
    assert d2["dialogue"]["count"] == 0


def test_without_the_stage(built):
    cfg, db = built
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM dialogue_pairs")
        conn.execute("DELETE FROM dialogue_exchanges")
        conn.execute("UPDATE meta SET value = '{}' WHERE key = 'dialogue'")
    c = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    assert c.get("/api/dialogue").json() == {"meta": {}, "books": []}
    assert c.get("/api/dialogue/exchanges").json()["total"] == 0
    keys = {x["key"] for x in c.get("/api/findings").json()["items"]}
    assert not keys & {"dialogue_deference", "dialogue_particle", "dialogue_last_word"}
    d = {e["kind"]: e for e in c.get("/api/dossier/c:0:1").json()["entries"]}
    assert not d["dialogue"]["computed"]
    assert c.get("/api/speech/book/0").json()["speakers"][0]["to"] == []
