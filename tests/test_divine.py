"""The divine names across the canon (`bsim divine`, `/divine`, DESIGN.md §16.65)."""

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.divine import (
    best_split,
    doubled_check,
    elohistic_check,
    name_of_lemma,
    sign_test,
    split_p,
    word_name,
)
from bsim.api.app import create_app
from bsim.fixture import fixture_encoder


def test_word_name():
    lookup = name_of_lemma({"yhwh": ["3068", "3069"], "elohim": ["430"], "elyon": ["5945b"]})
    assert word_name("3068", lookup) == "yhwh"
    assert word_name("c/3069", lookup) == "yhwh"  # a prefix before the name
    assert word_name("l/430", lookup) == "elohim"
    assert word_name("5945 b", lookup) == "elyon"  # OSHB writes a letter after a space
    assert word_name("5945 a", lookup) is None  # the adjective
    assert word_name("b/7225", lookup) is None


def test_best_split():
    # nine chapters: the middle three all אלהים, the rest all יהוה
    k = np.array([5, 5, 5, 0, 0, 0, 5, 5, 5])
    n = np.full(9, 5)
    i, j, gain = best_split(k, n, 3)
    assert (i, j) == (3, 6) and gain > 10
    # a constant mix gains nothing; a part shorter than min_segment is never cut
    assert best_split(np.full(9, 2), np.full(9, 4), 3)[2] == pytest.approx(0)
    i, j, _ = best_split(np.array([5, 0, 5, 5, 5, 5, 5, 5, 5]), np.full(9, 5), 2)
    assert i >= 2 and j - i >= 2 and 9 - j >= 2
    # the split against shuffles: in nine chapters the three together come by chance 1 time in 12;
    # in thirty, ten together almost never
    rng = np.random.default_rng(1)
    assert 0.02 < split_p(k, n, 3, gain, 199, rng) < 0.2
    k30, n30 = np.r_[np.full(10, 5), np.zeros(10), np.full(10, 5)], np.full(30, 5)
    assert split_p(k30, n30, 3, best_split(k30, n30, 3)[2], 199, rng) == 0.005
    assert split_p(np.full(9, 2), np.full(9, 4), 3, 0.0, 99, rng) == 1.0


def test_sign_test():
    assert sign_test(6, 7) == pytest.approx(8 / 128)  # the doubled psalms: 6 of 7
    assert sign_test(0, 0) == 1.0
    assert sign_test(3, 3) == pytest.approx(1 / 8)


def test_elohistic_check():
    books = pd.DataFrame(
        [
            {
                "book_id": 26,
                "split": True,
                "cut1": 43,
                "cut2": 85,
                "share1": 0.8,
                "share2": 0.2,
                "share3": 0.8,
                "gain": 50.0,
                "p": 0.001,
            }
        ]  # fmt: skip
    )
    el = {"book": "Psalms", "first": 42, "last": 83, "tolerance": 2}
    c = elohistic_check(books, el, 0.05)
    assert (c["first"], c["last"], c["found"], c["holds"]) == (43, 84, True, True)
    assert not elohistic_check(books.assign(cut2=90), el, 0.05)["found"]  # ends at 89
    assert not elohistic_check(books.assign(p=0.2), el, 0.05)["holds"]
    none = elohistic_check(books.assign(split=False), el, 0.05)
    assert none["found"] is None and not none["holds"] and none["p"] is None


def test_doubled_check():
    # Genesis 1:1 / 1:2 stand for a doubled psalm: the first has אלהים where the second has יהוה
    verses = pd.DataFrame(
        {"verse_id": [0, 1], "book_id": [0, 0], "chapter": [1, 1], "verse": [1, 2]}
    )
    rows = [
        (0, 0, "אָמַר", "559", ["559"], None),
        (0, 1, "אֱלֹהִים", "430", ["430"], "elohim"),
        (0, 2, "אֵל", "410", ["410"], "el"),
        (1, 0, "אָמַר", "559", ["559"], None),
        (1, 1, "יְהוָה", "3068", ["3068"], "yhwh"),
        (1, 2, "אֵל", "410", ["410"], "el"),
    ]
    words = pd.DataFrame(rows, columns=["verse_id", "idx", "surface", "lemma", "content_lemmas",
                                        "name"])  # fmt: skip
    words["name"] = words.name.astype(object).where(words.name.notna(), np.nan)  # as merged
    score = {"match": 2, "mismatch": 1, "gap": 1}
    pairs, c = doubled_check(
        verses, words, [{"e": "Genesis 1:1", "y": "Genesis 1:2"}, {"e": "Psalms 53:1-7",
                                                                    "y": "Psalms 14:1-7"}],
        ("yhwh", "elohim"), score, 0.05,
    )  # fmt: skip
    assert (c["e_ward"], c["y_ward"], c["missing"]) == (1, 0, ["Psalms 53:1-7"])
    assert c["pairs"] == [{"pair": 0, "e": "Genesis 1:1", "y": "Genesis 1:2", "e_ward": 1,
                           "y_ward": 0, "same": 1, "other": 0}]  # fmt: skip
    # only places with a name on either side: אמר is left out
    assert pairs.kind.tolist() == ["e_ward", "same"]
    assert pairs.e_word.tolist() == ["אלהים", "אל"] and pairs.y_name.tolist() == ["yhwh", "el"]
    assert c["p"] == 0.5 and not c["holds"]


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_divine_endpoints(client):
    r = client.get("/api/divine").json()
    assert r["names"][:2] == ["yhwh", "elohim"] and r["measure"] == ["yhwh", "elohim"]
    assert (r["totals"]["yhwh"], r["totals"]["elohim"], r["totals"]["shaddai"]) == (2, 2, 0)
    assert [c["unit_id"] for c in r["chapters"]] == ["c:0:1", "c:0:2", "c:1:1"]
    first = r["chapters"][0]
    assert (first["counts"], first["share"], first["part"]) == ({"yhwh": 2, "elohim": 2}, 0.5, None)
    assert r["chapters"][1]["counts"] == {} and r["chapters"][1]["share"] is None
    genesis = r["books"][0]
    assert (genesis["book_id"], genesis["split"], genesis["shares"]) == (0, False, [])
    assert r["elohistic"]["holds"] and r["doubled"]["pairs"][0]["same"] == 2
    pairs = client.get("/api/divine/pairs").json()["pairs"]
    assert [p["kind"] for p in pairs[0]["places"]] == ["same", "same"]
    assert pairs[0]["places"][0]["e_word"] == "אלהים" and pairs[0]["places"][1]["y_vid"] == 1


def test_divine_findings_dossier_reader(client):
    found = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    assert found["divine_elohistic"]["verdict"] == "holds"
    assert found["divine_elohistic"]["values"]["share2"] == 0.2
    assert found["divine_doubled"]["verdict"] == "fails"  # nothing differs in the fixture
    assert found["divine_doubled"]["values"]["pairs"] == 1
    entry = next(e for e in client.get("/api/dossier/v:0").json()["entries"]
                 if e["kind"] == "divine")  # fmt: skip
    assert (entry["computed"], entry["count"], entry["value"]) == (True, 2, 0.5)
    assert entry["key"] in ("yhwh", "elohim")
    none = next(e for e in client.get("/api/dossier/v:3").json()["entries"]
                if e["kind"] == "divine")  # fmt: skip
    assert (none["count"], none["value"], none["key"]) == (0, None, None)
    reader = client.get("/api/reader/c:0:1").json()
    assert reader["computed"]["divine"]
    assert reader["verses"][0]["divine"] == {"1": "elohim", "3": "yhwh"}
    assert reader["verses"][1]["divine"] == {"0": "elohim"}  # v1's יהוה has no display token
