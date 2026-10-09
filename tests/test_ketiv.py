import json
import sqlite3

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.ketiv import (
    _check_positions,
    feature_diffs,
    grammar_class,
    late_fuller,
    letter_class,
    letter_pairs,
    letters_of,
    lookalike_test,
    morph_features,
    parallel_readings,
)
from bsim.api.app import create_app
from bsim.fixture import fixture_encoder


@pytest.mark.parametrize(
    ("k", "q", "n", "expected"),
    [
        ("ידו", "ידיו", (1, 1), ("vowel_letter", "qere", None)),
        ("דויד", "דוד", (1, 1), ("vowel_letter", "ketiv", None)),
        ("הוא", "היא", (1, 1), ("swap", None, "ו>י")),
        ("הלוכ", "הולכ", (1, 1), ("vowel_position", None, None)),
        ("בעברות", "בערבות", (1, 1), ("metathesis", None, None)),
        ("עפלימ", "טחרימ", (1, 1), ("other", None, None)),
        ("אשדת", "אשדת", (1, 2), ("division", None, None)),
        ("", "אלי", (0, 1), ("qere_only", None, None)),
        ("אמ", "", (1, 0), ("ketiv_only", None, None)),
        ("לא", "לא", (1, 1), ("same_letters", None, None)),
    ],
)
def test_letter_class(k, q, n, expected):
    assert letter_class(n[0], n[1], k, q) == expected


def test_letters_fold_finals_and_join():
    assert letters_of(["מִן", "הַסְּעָרָה"]) == "מנהסערה"


def test_morph_features():
    assert morph_features("HC/Vqw3ms") == {
        "pos": "V", "stem": "q", "conj": "w", "person": "3", "gender": "m", "number": "s",
    }  # fmt: skip
    assert morph_features("HNcbdc/Sp3ms") == {
        "pos": "N", "type": "c", "gender": "b", "number": "d", "state": "c", "suffix": "3ms",
    }  # fmt: skip
    assert morph_features("HVqrmsa")["state"] == "a"  # a participle has no person
    assert morph_features("HR/Sp1cs") == {"pos": "R", "suffix": "1cs"}


def test_feature_diffs_and_grammar():
    assert feature_diffs("b/899", "b/899", "HR/Ncmsc/Sp3ms", "HR/Ncmpc/Sp3ms") == ["number s>p"]
    assert feature_diffs("b/5927", "k/5927", "HR/Vqc", "HR/Vqc") == ["prefix b>k"]
    assert grammar_class("b/5927", "k/5927", "HR/Vqc", "HR/Vqc") == "form"
    assert grammar_class("7693", "7901", "HVqi3fp", "HVqi3fp") == "word"
    assert grammar_class("5869 a", "5869 a", "HNcbdc", "HNcbdc") == "spelling"


FREQ = {c: 1 / 22 for c in "אבגדהוזחטיכלמנסעפצקרשת"}


def test_letter_pairs_and_lookalikes():
    swaps = pd.Series(["ו>י"] * 8 + ["י>ו"] * 2 + ["ב>כ", "א>ע"])
    df = letter_pairs(swaps, FREQ, {"וי", "בכ"})
    top = df.iloc[0]
    assert top.pair == "וי" and top.n == 10 and top.lookalike and top.q < 0.001
    assert len(df) == 231 and df.n.sum() == 12
    t = lookalike_test(swaps, FREQ, {"וי", "בכ"})
    assert t["all"]["lookalike"] == 11 and t["all"]["p"] < 0.001
    assert t["without_wy"]["n"] == 2 and t["without_wy"]["lookalike"] == 1


def test_late_fuller_permutes_books():
    rows = []
    for book, late_k in ((0, 9), (1, 8), (2, 2), (3, 1), (4, 2), (5, 1)):
        rows += [{"book_id": book, "cls": "vowel_letter", "fuller": "ketiv"}] * late_k
        rows += [{"book_id": book, "cls": "vowel_letter", "fuller": "qere"}] * (10 - late_k)
    res = late_fuller(pd.DataFrame(rows), {0, 1}, 999, np.random.default_rng(0))
    assert res["late"] == pytest.approx(0.85) and res["other"] == pytest.approx(0.15)
    assert res["p"] < 0.1 and res["books"] == 6  # only 15 ways to pick 2 of 6 books
    none = late_fuller(pd.DataFrame(rows), {9}, 9, np.random.default_rng(0))
    assert none["p"] is None


def test_parallel_readings_compare_the_written_partner():
    words = pd.DataFrame(
        {
            "verse_id": [0, 0, 1, 1, 2, 2],
            "idx": [0, 1, 0, 1, 0, 1],
            "surface": ["דָּוִד", "מֶלֶךְ", "דָּוִד", "מֶלֶךְ", "שָׁלוֹם", "מֶלֶךְ"],
            "lemma": ["1732", "4428", "1732", "4428", "8010", "4428"],
            "content_lemmas": [["1732"], ["4428"], ["1732"], ["4428"], ["8010"], ["4428"]],
        }
    )
    pairs = pd.DataFrame(
        {
            "verse_id": [0, 2],
            "pos": [0, 1],
            "n_ketiv": [1, 1],
            "n_qere": [1, 1],
            "ketiv_c": ["דויד", "מלכ"],
        }
    )
    seqs = pd.DataFrame(
        {"q": [0.0, 0.0], "same_chapter": [0, 0], "pairs": ["[[0, 1, 1.0]]", "[[1, 2, 1.0]]"]}
    )
    cfg = {"diffs": {"max_q": 0.05, "same_chapter": False, "match": 2, "mismatch": 1, "gap": 1,
                     "min_shared": 0.5}}  # fmt: skip
    out = parallel_readings(pairs, words, seqs, cfg)
    # v0 reads דוד, writes דויד; its parallel v1 writes דוד: the qere's spelling
    assert out.iloc[0].tolist() == ["qere", 1, "דוד"]
    # v2's ketiv is written exactly as its partner writes it
    assert out.iloc[1].tolist() == ["ketiv", 1, "מלכ"]


def test_positions_must_match_the_corpus():
    words = pd.DataFrame({"verse_id": [0, 0], "idx": [0, 1], "kq": [None, "q"]})
    _check_positions(pd.DataFrame({"verse_id": [0], "pos": [1], "n_qere": [1]}), words)
    with pytest.raises(RuntimeError):
        _check_positions(pd.DataFrame({"verse_id": [0], "pos": [0], "n_qere": [1]}), words)


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_ketiv_api(client):
    k = client.get("/api/ketiv").json()
    assert k["meta"]["checks"]["parallel"]["qere"] == 1
    assert [b["book_id"] for b in k["books"]] == [0, 1]
    assert [x["pair"] for x in k["letters"]] == ["וי"] and k["letters"][0]["lookalike"] is True
    p = client.get("/api/ketiv/pairs").json()
    assert p["total"] == 3 and [i["kq_id"] for i in p["items"]] == [1, 2, 3]
    full = p["items"][1]
    assert full["parallel"] == "qere" and full["partner_vid"] == 5
    assert full["partner_label"] and full["display"] == [0] and full["verse"]["verse_id"] == 4
    swap = client.get("/api/ketiv/pairs?cls=swap").json()["items"][0]
    assert swap["features"] == ["number s>p"] and swap["euphemism"] is True
    assert client.get("/api/ketiv/pairs?euphemism=false").json()["total"] == 2
    assert client.get("/api/ketiv/pairs?parallel=qere&book=0").json()["total"] == 1
    assert client.get("/api/ketiv/pairs?unit=c:0:2").json()["total"] == 1
    assert client.get("/api/ketiv/pairs?cls=nope").status_code == 422
    assert client.get("/api/ketiv/pairs?unit=v:99").status_code == 404


def test_dossier_ketiv(client):
    d = client.get("/api/dossier/v:4").json()
    e = next(e for e in d["entries"] if e["kind"] == "ketiv")
    assert e["computed"] and e["count"] == 1


def test_ketiv_in_db(built):
    _, db = built
    conn = sqlite3.connect(db)
    meta = json.loads(conn.execute("SELECT value FROM meta WHERE key = 'ketiv'").fetchone()[0])
    assert meta["checks"]["plural_suffix"] == {"plural": 1, "waw_yw": 0}
    assert conn.execute("SELECT lookalike FROM kq_letters WHERE pair = 'וי'").fetchone() == (1,)
