"""The workbench: sets contrasted and checked (`api/workbench.py`, `/workbench`, §16.64)."""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.stats import g2_table
from bsim.api.app import create_app
from bsim.api.workbench import SetError, check, parse_set
from bsim.fixture import fixture_encoder


@pytest.mark.parametrize(
    ("spec", "code", "item"),
    [
        ("", "empty", 0),
        (" ; ;", "empty", 0),
        ("book", "bad_item", 0),
        ("book:", "bad_item", 0),
        ("book:1; volume:2", "unknown_kind", 1),
        ("book:x", "bad_range", 0),
        ("book:1-2-3", "bad_range", 0),
        ("collection:1-2", "bad_range", 0),
        ("chapters:1", "bad_range", 0),
        ("chapters:a:1", "bad_range", 0),
        ("section:law", "bad_item", 0),
        ("only:poetry", "bad_item", 0),
        ("book:1;book:2;book:3", "too_long", 2),
    ],
)
def test_parse_set_errors(spec, code, item):
    with pytest.raises(SetError) as e:
        parse_set(spec, 2, 100)
    assert (e.value.code, e.value.item) == (code, item)


def test_parse_set():
    spec = " Book:1-3 ; chapters:27:42-83;SECTION:Torah; unit:p:Noach ;"
    items = parse_set(spec + " pattern:[lemma=430] ..2 [lemma=3068]; only:Speech", 8, 500)
    assert [(i.kind, i.value, i.at) for i in items] == [
        ("book", "1-3", 0), ("chapters", "27:42-83", 1), ("section", "torah", 2),
        ("unit", "p:Noach", 3), ("pattern", "[lemma=430] ..2 [lemma=3068]", 4),
        ("only", "speech", 5),
    ]  # fmt: skip
    with pytest.raises(SetError) as e:
        parse_set("book:1", 8, 3)
    assert e.value.code == "too_long"


def test_check():
    # two books of ten verses, ten words each; the pattern only in the set's five verses
    groups = np.repeat([0, 1], 10)
    words = np.full(20, 10)
    in_set = np.arange(20) < 5
    matches = in_set.astype(int)
    c = check(matches, words, in_set, groups, 999, seed=1)
    assert c.testable and (c.matches, c.words, c.rate) == (5, 50, 100.0)
    assert (c.rest_matches, c.rest_words, c.groups, c.fixed_verses) == (0, 50, 1, 0)
    # the five set verses drawn again among book 0's ten: all five only 1 time in 252
    assert c.p_high < 0.02 and c.p_low == 1.0
    assert c.null_mean == pytest.approx(50, abs=3) and c.null_low < c.null_mean < c.null_high
    assert check(matches, words, in_set, groups, 999, seed=1) == c  # one answer per seed
    # the whole corpus as one group: the same set against all twenty verses
    one = check(matches, words, in_set, np.zeros(20, dtype=int), 999, seed=1)
    assert one.testable and one.null_mean == pytest.approx(25, abs=2) and one.p_high < 0.01
    # a set that is a whole group does not move
    whole = check(matches, words, groups == 0, groups, 999, seed=1)
    assert not whole.testable and (whole.groups, whole.fixed_verses) == (0, 10)
    # a set that fills one group and shares another: only the shared one moves
    part = check(matches, words, (groups == 0) | (np.arange(20) == 10), groups, 999, seed=1)
    assert part.testable and (part.groups, part.fixed_verses) == (1, 10)
    assert part.null_low == part.null_high == part.rate == pytest.approx(1000 * 5 / 110)


@pytest.fixture
def client(built):
    cfg, _ = built
    cfg["serve"] = {**cfg["serve"], "workbench": {**cfg["serve"]["workbench"], "min_count": 1}}
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def contrast(client, **params):
    return client.get("/api/workbench/contrast", params=params).json()


def test_contrast(client):
    # chapter 0:1 (v0-v2: ראשית ×2, אלהים ×2, אמר ×2, יהוה ×2) against the rest (ראשית ×3)
    r = contrast(client, a="chapters:0:1")
    assert r["error"] is None
    assert r["a"] == {"spec": "chapters:0:1", "verses": 3, "words": 8, "books": [0],
                      "filtered": False}  # fmt: skip
    assert r["b"] == {"spec": "", "verses": 3, "words": 3, "books": [0, 1], "filtered": False}
    assert (r["total_a"], r["total_b"], r["tested"], r["overlap"]) == (8, 3, 4, 0)
    assert [x["key"] for x in r["over_a"]] == ["430", "559", "3068"]
    first = r["over_a"][0]
    assert first["label"] == "אלהים" and (first["a"], first["b"]) == (2, 0)
    assert first["g2"] == pytest.approx(g2_table(2, 8, 2, 11))
    assert first["rate_a"] == 250 and first["rate_b"] == 0
    assert first["log_ratio"] == pytest.approx(np.log2((2.5 / 8.5) / (0.5 / 3.5)))
    assert [e["verse_id"] for e in first["examples"]] == [0, 1]
    assert [x["key"] for x in r["over_b"]] == ["7225"]
    assert [e["verse_id"] for e in r["over_b"][0]["examples"]] == [3, 4, 5]
    assert r["significant_a"] == r["significant_b"] == 0  # six verses prove nothing
    # an explicit B overlapping A: the shared words count for A only
    r = contrast(client, a="chapters:0:1", b="book:0")
    assert r["overlap"] == 8 and r["b"]["words"] == 2 and r["b"]["books"] == [0]
    # rows per side
    assert len(contrast(client, a="chapters:0:1", rows=1)["over_a"]) == 1
    bad = client.get("/api/workbench/contrast", params={"a": "book:0", "rows": 0})
    assert bad.status_code == 422


def test_contrast_features(client):
    r = contrast(client, a="chapters:0:1", feature="domain")
    assert [(x["key"], x["label"], x["a"]) for x in r["over_a"]] == [("001001002", "Deities", 4.0)]
    assert [(x["key"], x["a"], x["b"]) for x in r["over_b"]] == [("002001001", 2.0, 3.0)]
    # syntax: the fixture's phrase functions
    r = contrast(client, a="unit:v:0", feature="function")
    assert r["total_a"] == 4  # v0's four words, one of them in two phrases (Conj, Pred)
    assert "time" in {x["key"] for x in r["over_a"]} and "prec" in {x["key"] for x in r["over_b"]}
    assert client.get("/api/workbench/contrast", params={"a": "book:0", "feature": "colour"}
                      ).status_code == 422  # fmt: skip


def test_sets(client):
    # direct speech: v1 (three words) and v3 (one) of book 0
    r = contrast(client, a="book:0; only:speech")
    assert (r["a"]["verses"], r["a"]["words"], r["a"]["filtered"]) == (2, 4, True)
    assert contrast(client, a="book:0; only:narration")["a"]["words"] == 6
    assert contrast(client, a="book:0; only:speech; only:narration")["a"]["words"] == 10
    assert contrast(client, a="section:torah")["error"]["code"] == "no_words"  # B is empty
    assert contrast(client, a="book:1")["a"]["verses"] == 1
    assert contrast(client, a="unit:c:0:2; unit:v:5")["a"]["verses"] == 3
    r = contrast(client, a="pattern:[lemma=430] [lemma=559]")
    assert (r["a"]["verses"], r["a"]["books"]) == (2, [0])
    problems = {
        "book:99": ("unknown_book", 0, "99"),
        "book:7": ("no_words", 0, ""),  # a book of the canon without verses here
        "book:1-0": ("bad_range", 0, "1-0"),
        "chapters:0:2-3": ("bad_range", 0, "0:2-3"),
        "book:0; unit:c:9:9": ("unknown_unit", 1, "c:9:9"),
        "collection:5": ("unknown_collection", 0, "5"),
        "only:speech": ("empty", 0, ""),
    }
    for spec, (code, item, token) in problems.items():
        e = contrast(client, a=spec)["error"]
        assert (e["set"], e["code"], e["item"], e["token"]) == ("a", code, item, token), spec
    e = contrast(client, a="book:0", b="pattern:[lemma=430")["error"]
    assert (e["set"], e["code"]) == ("b", "pattern")
    assert e["pattern"] == {"code": "unclosed", "at": 0, "token": "[lemma=430"}


def test_collection_set(client):
    cid = client.post("/api/notebook/collections", json={"name": "Mine"}).json()["collection_id"]
    client.put(f"/api/notebook/collections/{cid}/entries/v:5")
    assert contrast(client, a=f"collection:{cid}")["a"]["books"] == [1]
    # read live: a unit added shows in the next contrast
    client.put(f"/api/notebook/collections/{cid}/entries/c:0:2")
    assert contrast(client, a=f"collection:{cid}")["a"]["verses"] == 3


def test_check_endpoint(client):
    def check_(**params):
        return client.get("/api/workbench/check", params=params).json()

    r = check_(q="[lemma=430]", set="chapters:0:1", within="corpus", draws=199)
    assert r["error"] is None and r["pattern_error"] is None and r["testable"]
    assert (r["matches"], r["words"], r["rest_matches"], r["rest_words"]) == (2, 8, 0, 3)
    assert r["rate"] == 250 and r["groups"] == 1 and r["draws"] == 199
    assert r["books"] == [{"book_id": 0, "matches": 2, "words": 8}]
    assert 0 < r["p_high"] <= 1 and r["null_low"] <= r["null_mean"] <= r["null_high"]
    assert check_(q="[lemma=430]", set="chapters:0:1", within="corpus", draws=199) == r
    whole = check_(q="[lemma=430]", set="chapters:0:1", within="chapter")
    assert not whole["testable"] and whole["fixed_verses"] == 3
    assert check_(q="[lemma=430", set="book:0")["pattern_error"]["code"] == "unclosed"
    assert check_(q="", set="book:0")["pattern_error"]["code"] == "empty"
    e = check_(q="[lemma=430]", set="book:0; only:speech")["error"]
    assert (e["set"], e["code"], e["item"]) == ("set", "filter_in_check", 1)
    assert client.get("/api/workbench/check", params={"q": "[]", "set": "book:0", "draws": 5}
                      ).status_code == 422  # fmt: skip
