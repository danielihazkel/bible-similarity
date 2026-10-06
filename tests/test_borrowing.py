import math

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.borrowing import (
    agreement,
    cross_check,
    direction,
    expansion_sign,
    known_direction,
    language_sign,
    select_signs,
    smoothing_sign,
    spelling_sign,
    vote,
    votes,
)
from bsim.api.app import create_app
from bsim.fixture import fixture_encoder


def ops(rows):
    return pd.DataFrame(rows, columns=["op", "a_form", "b_form", "a_key", "b_key"])


def test_diff_signs():
    o = ops(
        [
            ("spelling", "דוד", "דויד", "1732", "1732"),  # B fuller
            ("spelling", "קול", "קל", "6963", "6963"),  # A fuller
            ("spelling", "לא", "לוא", "3808", "3808"),
            ("substitution", "", "", "8199", "7760"),  # rare -> common
            ("substitution", "", "", "~l", "7760"),  # no content lemma: left out
            ("added", None, "", None, "1"),
            ("added", None, "", None, "2"),
            ("omitted", "", None, "3", None),
        ]
    )
    assert spelling_sign(o, 2) == (pytest.approx(1 / 3), 3)
    assert math.isnan(spelling_sign(o, 4)[0])
    s, n = smoothing_sign(o, {"8199": 1, "7760": 500}, 1)
    assert (s, n) == (1.0, 1)
    assert math.isnan(smoothing_sign(o, {}, 2)[0])
    assert expansion_sign(o, 10, 2) == pytest.approx(0.1)
    assert math.isnan(expansion_sign(o, 10, 4))


def test_language_sign():
    cols = ["lex", "word", "anokhi", "pron_1cs", "inf_abs", "verb", "et_suffix", "verb_suffix",
            "directional_he", "way1cs_h", "way1cs", "david_plene", "david"]  # fmt: skip
    a = pd.Series(dict.fromkeys(cols, 0) | {"word": 100, "verb": 20, "inf_abs": 4})
    b = pd.Series(dict.fromkeys(cols, 0) | {"word": 100, "verb": 20, "lex": 3})
    prior = dict.fromkeys(["lbh_lexemes", "anokhi", "inf_abs", "et_suffix", "directional_he",
                           "cohortative_wayyiqtol", "david_plene"], 0.1)  # fmt: skip
    sd = pd.Series(1.0, index=list(prior))
    signs = {"lbh_lexemes": 1, "inf_abs": -1}
    # B has more late words and fewer infinitive absolutes: later
    assert language_sign(a, b, prior, 0.0, sd, signs) > 0
    assert language_sign(b, a, prior, 0.0, sd, signs) < 0


def test_known_and_agreement():
    known = [{"source": "1Sam", "target": "1Chr"}]
    assert known_direction(7, 37, known) == "a_to_b"  # I Samuel (7) before I Chronicles (37)
    assert known_direction(37, 7, known) == "b_to_a"
    assert known_direction(0, 1, known) is None
    truth = pd.Series(["a_to_b", "a_to_b", "b_to_a", "a_to_b"])
    c = agreement(pd.Series([0.5, -1.0, -2.0, 0.0]), truth)
    assert (c["agree"], c["n"]) == (2, 3)
    assert vote(float("nan")) == 0 and vote(-0.2) == -1


def test_select_and_cross_check():
    # "good" always points the known way; "noise" alternates
    rows = []
    for g in range(4):
        for i in range(6):
            rows.append((g, 100 + g, "a_to_b", 1.0, 1.0 if i % 2 else -1.0))
    known = pd.DataFrame(rows, columns=["a_book", "b_book", "known", "good", "noise"])
    known = known.assign(language=known.good, spelling=known.noise, smoothing=None, expansion=None)
    assert select_signs(known, 0.05) == ["language"]
    held = cross_check(known, 0.05)
    assert (held["agree"], held["n"], held["unclear"]) == (24, 24, 0)
    v = votes(known, ["language", "spelling"])
    assert list(direction(v[:2])) == ["unclear", "a_to_b"]


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_borrowing_api(client):
    r = client.get("/api/borrowing").json()
    assert r["used_signs"] == ["language", "spelling"] and r["held_out"]["unclear"] == 3
    (pair,) = r["books"]
    assert (pair["a_book"], pair["b_book"], pair["direction"]) == (0, 1, "a_to_b")
    (s,) = pair["items"]
    assert (s["a_label"], s["b_label"], s["smoothing"]) == ("v:1–2", "v:5", None)
    assert client.get("/api/borrowing/sequence/2").json()["votes"] == 2
    assert client.get("/api/borrowing/sequence/1").json() is None  # same book: not scored
    assert len(client.get("/api/borrowing/between?a=c:1:1&b=c:0:1").json()) == 1
    assert client.get("/api/borrowing/between?a=c:0:2&b=c:1:1").json() == []
    assert client.get("/api/borrowing/between?a=c:0:2&b=v:99").status_code == 404
