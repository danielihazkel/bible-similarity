"""Equidistant letter sequences against controls (`bsim els`, `/els`, §16.62)"""

import json
from itertools import permutations

import numpy as np
import pandas as pd
import pytest
import torch
from fastapi.testclient import TestClient

from bsim.analysis.els import (
    ALPHABET,
    count_hits,
    encode,
    expected_hits,
    find_at,
    ratio_stat,
    term_code,
    term_hits,
)
from bsim.api.app import create_app
from bsim.fixture import fixture_encoder


def brute(s: np.ndarray, term: list[int], lo: int, hi: int) -> int:
    L, n = len(term), len(s)
    return sum(
        all(s[i + k * d] == term[k] for k in range(L))
        for d in range(lo, hi + 1) for i in range(n - (L - 1) * d)
    )  # fmt: skip


def test_encode_and_terms():
    assert encode("שלום עולם!").tolist() == [20, 11, 5, 12, 15, 5, 11, 12]  # finals folded
    assert term_code("רמבם") == term_code("רמבמ")
    with pytest.raises(ValueError):
        term_code("א")


def test_count_matches_brute_force():
    rng = np.random.default_rng(0)
    s = rng.integers(0, 3, 400).astype(np.int8)  # three letters: many hits
    t = torch.from_numpy(s)
    for term in ([0, 1], [0, 1, 2], [2, 2, 0, 1]):
        assert count_hits(t, term, 2, 40) == brute(s, term, 2, 40)
    fwd, back = term_hits(t, [0, 1, 2], 2, 40)
    assert back == brute(s, [2, 1, 0], 2, 40)
    assert term_hits(t, [1, 0, 1], 2, 40)[1] == 0  # a palindrome counts once
    assert count_hits(t, [0, 1], 5, 4) == 0 and count_hits(t[:3], [0, 1, 2], 2, 9) == 0


def test_expected_is_exact():
    # every arrangement of these letters, equally likely: the mean count is the expectation
    letters = [0, 0, 1, 1, 2, 3]
    term, lo, hi = [0, 1], 2, 3
    counts = np.bincount(letters, minlength=len(ALPHABET))
    arrangements = set(permutations(letters))
    mean = np.mean([sum(term_hits(torch.tensor(a, dtype=torch.int8), term, lo, hi))
                    for a in arrangements])  # fmt: skip
    assert expected_hits(counts, len(letters), term, lo, hi) == pytest.approx(mean)
    want = 2 * (2 / 6) * (2 / 5) * (1 / 4)  # two placements, a palindrome counted once
    assert expected_hits(counts, 6, [0, 1, 0], 2, 2) == pytest.approx(want)
    assert expected_hits(counts, 6, [3, 3], 2, 2) == 0.0  # one ד: no two


def test_ratio_and_find():
    assert ratio_stat(np.array([10, 0]), np.array([10.0, 0.0]), 0.5) == pytest.approx(0.0)
    assert ratio_stat(np.array([20]), np.array([9.5]), 0.5) == pytest.approx(np.log(2.05))
    s = encode("אבגאבג")
    assert find_at(s, 0, 5, term_code("אא"), 3) == 0
    assert find_at(s, 1, 5, term_code("אא"), 3) is None


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_api_els(client):
    r = client.get("/api/els").json()
    assert r["meta"]["max_skip"] == 1000 and "scopes" not in r["meta"]
    (s,) = r["scopes"]
    assert (s["key"], s["label_en"], s["letters"], s["holds"]) == ("torah", "v:0–4", 120, True)
    assert s["controls"]["letters"]["values"] == [-0.05, 0.12, 0.01]
    assert s["controls"]["blocks"]["values"] == [0.04]
    assert s["blocks"] == [{"block": 1, "label_en": "v:5", "label_he": "v:5", "first_vid": 5,
                            "r": 0.04}]  # fmt: skip
    assert [(t["term"], t["hits"]) for t in s["terms"]] == [("משה", 78), ("אהרן", 4)]
    (k,) = r["known"]
    assert (k["term"], k["skip"], k["offset"], k["verse"]["verse_id"]) == ("תורה", 50, 5, 0)


def test_findings(client):
    items = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    c, k = items["els_counts"], items["els_known"]
    assert c["verdict"] == "holds" and c["values"]["torah_letters_p"] == 0.5
    assert c["values"]["torah_r"] == 0.09
    assert k["verdict"] == "holds" and k["values"] == {"n": 1, "found": 1}


def test_run_els(tmp_path, built):
    """The stage end to end on the fixture's corpus: a scope of Genesis, the rest as one block."""
    from bsim.analysis.els import run_els
    from bsim.config import resolve_path

    cfg, _ = built
    proc = resolve_path(cfg, "data_processed")
    verses = pd.read_parquet(proc / "verses.parquet")
    pairs_dir = tmp_path / "art" / "ketiv"
    pairs_dir.mkdir(parents=True)
    pd.DataFrame(columns=["verse_id", "pos", "n_ketiv", "n_qere", "ketiv", "qere"]).astype(
        {"verse_id": int, "pos": int, "n_ketiv": int, "n_qere": int}
    ).to_parquet(pairs_dir / "pairs.parquet")
    c = {**cfg, "paths": {**cfg["paths"], "artifacts": str(tmp_path / "art")}}
    c["els"] = {**cfg["els"], "device": "cpu", "shuffles": 9, "max_skip": 3,
                "scopes": {"torah": ["Gen"]}, "rest": ["Exod"], "terms": ["אמר", "את"],
                "known": [{"ref": "Genesis 1:1", "term": "בר", "skip": 2}]}  # fmt: skip
    out = run_els(c, log=lambda _: None)
    meta = json.loads((out / "els.meta.json").read_text("utf-8"))
    s = meta["scopes"]["torah"]
    assert s["verses"] == int((verses.book_id == 0).sum())
    assert set(s["controls"]) <= {"letters", "verses", "blocks"}
    assert s["controls"]["letters"]["n"] == 9
    terms = pd.read_parquet(out / "terms.parquet")
    assert terms.term.tolist() == ["אמר", "את"]
    assert (terms.hits == terms.forward + terms.backward).all()
    draws = pd.read_parquet(out / "draws.parquet")
    assert (draws.control == "letters").sum() == 9
    assert len(meta["known"]) == 1 and isinstance(meta["known"][0]["found"], bool)
