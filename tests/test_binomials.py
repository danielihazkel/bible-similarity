"""Fixed word pairs (`bsim binomials`, `/binomials`, DESIGN.md §16.72)."""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.binomials import (
    construct,
    find_pairs,
    letters,
    n_prefixes,
    run_binomials,
    shorter_first,
    strip_prefixes,
    syllables,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.data.canon import BY_OSIS
from bsim.fixture import fixture_encoder

KINDS = {str(k): str(v) for k, v in load_config()["binomials"]["kinds"].items()}


@pytest.mark.parametrize(
    ("surface", "parts", "word", "n_letters", "n_syll"),
    [
        ("וְהָאָ֗רֶץ", ["c", "d", "776"], "אָ֗רֶץ", 3, 2),
        ("בַּשָּׁמַיִם", ["b", "d", "8064"], "שָּׁמַיִם", 4, 3),  # the article not written after ב
        ("וָבֹ֔הוּ", ["c", "922"], "בֹ֔הוּ", 3, 2),  # holam and shureq
        ("אִ֣ישׁ", ["376"], "אִ֣ישׁ", 3, 1),  # the yod a vowel letter
        ("וְאִמּֽוֹ", ["c", "517"], "אִמּֽוֹ", 3, 2),
    ],
)
def test_lengths(surface, parts, word, n_letters, n_syll):
    w = strip_prefixes(surface, n_prefixes(parts))
    assert w == word and letters(w) == n_letters and syllables(w) == n_syll


def test_construct():
    assert construct("Ncmpc") and not construct("Ncmpa") and not construct("Np")
    assert construct("Aamsc") and not construct("Ncbsa")


def words(*rows):
    """(verse, lemma, morph, surface) rows as a words frame."""
    return pd.DataFrame(
        [(v, i, s, lem, mo, i) for i, (v, lem, mo, s) in enumerate(rows)],
        columns=["verse_id", "idx", "surface", "lemma", "morph", "display_idx"],
    )


def test_find_pairs():
    w = words(
        (0, "d/8064", "HTd/Ncmpa", "הַשָּׁמַיִם"),
        (0, "c/d/776", "HC/Td/Ncbsa", "וְהָאָרֶץ"),  # a pair: שמים וארץ
        (0, "1121 a", "HNcmpc", "בְּנֵי"),
        (0, "c/3478", "HC/Np", "וְיִשְׂרָאֵל"),  # construct first, kinds differ: no pair
        (1, "4872", "HNp", "מֹשֶׁה"),
        (1, "c/175", "HC/Np", "וְאַהֲרֹן"),  # a pair of names
        (1, "c/175", "HC/Np", "וְאַהֲרֹן"),  # the same lemma twice: no pair
        (2, "3701", "HNcmsa", "כֶּסֶף"),  # verses do not run on
        (3, "c/2091", "HC/Ncmsa", "וְזָהָב"),
    )
    p = find_pairs(w, KINDS)
    assert list(zip(p.a, p.b, p.kind, strict=True)) == [("8064", "776", "noun"),
                                                         ("4872", "175", "name")]  # fmt: skip
    assert p.a_form.tolist() == ["שמים", "משה"] and p.b_len.tolist() == [3, 4]
    assert p.a_tok.tolist() == [0, 4] and p.b_tok.tolist() == [1, 5]


def test_shorter_first():
    r = shorter_first(np.array([3, 3, 3, 4, 5]), np.array([4, 4, 3, 5, 3]))
    assert (r["differ"], r["shorter_first"], r["share"]) == (4, 3, 0.75)
    assert shorter_first(np.array([3]), np.array([3]))["p"] == 1.0


def corpus(tmp_path):
    """Genesis (early) and Chronicles (late): כסף וזהב three times early, זהב וכסף twice late; שמים
    וארץ five times early; איש ואשה once (not a binomial)."""
    gen, chr_ = BY_OSIS["Gen"].book_id, BY_OSIS["1Chr"].book_id
    kesef = [("3701", "HNcmsa", "כֶּסֶף"), ("c/2091", "HC/Ncmsa", "וְזָהָב")]
    zahav = [("2091", "HNcmsa", "זָהָב"), ("c/3701", "HC/Ncmsa", "וָכֶסֶף")]
    shamayim = [("d/8064", "HTd/Ncmpa", "הַשָּׁמַיִם"), ("c/d/776", "HC/Td/Ncbsa", "וְהָאָרֶץ")]
    ish = [("376", "HNcmsa", "אִישׁ"), ("c/802", "HC/Ncfsa", "וְאִשָּׁה")]
    verses = [(gen, kesef)] * 3 + [(gen, shamayim)] * 5 + [(gen, ish)] + [(chr_, zahav)] * 2
    proc = tmp_path / "processed"
    proc.mkdir()
    pd.DataFrame({"verse_id": range(len(verses)), "book_id": [b for b, _ in verses]}).to_parquet(
        proc / "verses.parquet"
    )
    w = words(*[(v, lem, mo, s) for v, (_, ws) in enumerate(verses) for lem, mo, s in ws])
    w["idx"] = w.groupby("verse_id").cumcount()
    w["display_idx"] = w.idx
    w.to_parquet(proc / "words.parquet")
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc),
                    "artifacts": str(tmp_path / "artifacts")}  # fmt: skip
    cfg["binomials"] = {**cfg["binomials"], "shuffles": 99}
    return cfg


def test_run_binomials(tmp_path):
    cfg = corpus(tmp_path)
    run_binomials(cfg, log=lambda _: None)
    out = tmp_path / "artifacts" / "binomials"
    t = pd.read_parquet(out / "types.parquet").set_index("pair")
    assert sorted(t.index) == ["2091+3701", "776+8064"]  # איש ואשה once: not a binomial
    gold = t.loc["2091+3701"]
    assert (gold["first"], gold.n, gold.n_own, gold.fixed) == ("3701", 5, 3, 0.6)
    assert (gold.n_early, gold.rev_early, gold.n_late, gold.rev_late) == (3, 0, 2, 2)
    sky = t.loc["776+8064"]
    assert (sky.first_form, sky.second_form, sky.first_letters, sky.second_syll) == (
        "שמים", "ארץ", 4.0, 2.0)  # fmt: skip
    occ = pd.read_parquet(out / "occurrences.parquet")
    assert occ[occ.pair == "2091+3701"].own.tolist() == [True, True, True, False, False]
    meta = json.loads((out / "binomials.meta.json").read_text("utf-8"))
    assert meta["binomials"] == 2 and meta["both_ways"] == 1
    assert meta["rate_early"] == 0.0 and meta["rate_late"] == 1.0
    assert meta["known_late"]["share_early"] == 0.0 and meta["known_late"]["share_late"] == 1.0
    # שמים וארץ found and fixed; איש ואשה never a binomial: the known do not all hold
    assert meta["known"][0]["holds"] and not meta["known"][1]["holds"]
    assert not meta["known_holds"]


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_binomials_endpoint(client):
    r = client.get("/api/binomials").json()
    assert r["late_holds"] and not r["short_holds"] and r["known_holds"]
    assert [b["pair"] for b in r["items"]] == ["776+8064", "2091+3701"]
    assert r["items"][1]["rev_late"] == 2 and r["without_known"]["p"] == 1.0
    occ = client.get("/api/binomials/occurrences", params={"pair": "2091+3701"}).json()
    assert [o["own"] for o in occ["items"]] == [True, False]
    assert occ["items"][1]["verse"]["verse_id"] == 3 and occ["items"][1]["a_tok"] == 1
    assert client.get("/api/binomials/occurrences", params={"pair": "1+2"}).status_code == 404


def test_binomials_findings(client):
    found = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    assert found["binomials_short"]["verdict"] == "fails"
    assert found["binomials_late"]["values"]["without_p"] == 1.0
    assert found["binomials_known"]["values"]["gold_late"] == 1.0
