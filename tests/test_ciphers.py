"""Atbash and albam (`text/ciphers.py`, `bsim ciphers`, `/ciphers`, DESIGN.md §16.54)."""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.ciphers import name_forms, run_ciphers, spans
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder
from bsim.text.ciphers import LETTERS, SWAPS, apply, key, random_swap


def test_swaps():
    at, al = SWAPS["atbash"], SWAPS["albam"]
    assert (at["א"], at["ת"], at["כ"], at["ל"]) == ("ת", "א", "ל", "כ")
    assert (al["א"], al["ל"], al["כ"], al["ת"]) == ("ל", "א", "ת", "כ")
    for s in (at, al, random_swap(np.random.default_rng(0))):
        assert sorted(s) == sorted(LETTERS)
        assert all(s[s[c]] == c and s[c] != c for c in LETTERS)  # pairs, no letter left alone


def test_known_readings():
    assert apply("שֵׁשַׁךְ", "atbash") == "בבל"  # Jeremiah 25:26, 51:41
    assert apply("בָּבֶל", "atbash") == "ששך"  # the last letter written final
    assert key("לֵב קָמָי").translate(str.maketrans(SWAPS["atbash"])) == "כשדימ"
    assert apply("כשדים", "atbash") == "לבקמי"
    assert apply("טָבְאַל", "albam") == "רמלא"  # Isaiah 7:6, Rashi's Remaliah
    assert apply("לב קמי", "atbash") == "כש דים"  # word by word


def corpus(tmp_path):
    """Genesis 1:1-3 and 2:1-2: Babel named, then written ששך; לב קמי, and the Chaldeans named."""
    proc = tmp_path / "processed"
    proc.mkdir()
    verses = [
        (0, 1, 1, ["בָּבֶל", "עִיר"]),
        (1, 1, 2, ["וּמֶלֶךְ", "שֵׁשַׁךְ", "׀", "יִשְׁתֶּה"]),
        (2, 1, 3, ["יֹשְׁבֵי", "לֵב", "קָמָי"]),
        (3, 2, 1, ["כַּשְׂדִּים"]),
        (4, 2, 2, ["מָה", "זֶּה"]),
    ]
    pd.DataFrame(
        {
            "verse_id": [v[0] for v in verses],
            "book_id": 0,
            "chapter": [v[1] for v in verses],
            "verse": [v[2] for v in verses],
            "display_tokens": [v[3] for v in verses],
        }
    ).to_parquet(proc / "verses.parquet")
    pd.DataFrame(
        [("בָּבֶל", "894", "HNp"), ("כַּשְׂדִּים", "3778", "HNp"), ("וּ/מֶלֶךְ", "c/4428", "HC/Ncmsa"),
         ("יְהוָה", "3068", "HNp"), ("לְ/אַבְרָם", "l/87", "HR/Np")],
        columns=["surface", "lemma", "morph"],
    ).to_parquet(proc / "words.parquet")  # fmt: skip
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(tmp_path / "art")}
    cfg["ciphers"] = {
        **cfg["ciphers"],
        "shuffles": 49,
        "known": [{"ref": "Genesis 1:2", "cipher": "atbash", "text": "ששך", "name": "בבל"},
                  {"ref": "Genesis 1:3", "cipher": "atbash", "text": "לב קמי", "name": "כשדים"}],
        "chapters": ["Genesis 1"],
    }  # fmt: skip
    return cfg, proc


def test_names_and_spans(tmp_path):
    _, proc = corpus(tmp_path)
    words = pd.read_parquet(proc / "words.parquet")
    names = name_forms(words, {"3068"}, 3)
    # the name part of a prefixed word; the divine name left out
    assert names == {"בבל": ("בבל", "894"), "כשדימ": ("כשדים", "3778"), "אברמ": ("אברם", "87")}
    sp = spans(pd.read_parquet(proc / "verses.parquet"), 2, 3, 5)
    rows = set(zip(sp.verse_id, sp.first_tok, sp.last_tok, sp.letters, strict=True))
    assert (1, 1, 1, "ששכ") in rows  # a rare word
    assert (2, 1, 2, "לבקמי") in rows  # two words read as one
    assert (1, 1, 3, "ששכישתה") not in rows  # over the longest name; the paseq skipped


def test_run_ciphers(tmp_path):
    cfg, _ = corpus(tmp_path)
    out = run_ciphers(cfg, log=lambda _: None)
    hits = pd.read_parquet(out / "hits.parquet")
    at = hits[hits.cipher == "atbash"]
    assert list(zip(at.verse_id, at.span, at.reads, at.known, strict=True)) == [
        (1, "ששך", "בבל", "Genesis 1:2"),
        (2, "לב קמי", "כשדים", "Genesis 1:3"),
    ]
    meta = json.loads((out / "ciphers.meta.json").read_text("utf-8"))
    assert meta["known_found"] == 2 and all(k["found"] for k in meta["known"])
    t = meta["tests"]
    assert t["jeremiah"]["observed"] == 2 and t["elsewhere"]["observed"] == 0
    assert 0 < t["jeremiah"]["p"] <= 1 and t["jeremiah"]["expected"] >= 0
    chap = pd.read_parquet(out / "chapters.parquet")
    assert chap[chap.cipher == "atbash"].unit_id.tolist() == ["c:0:1"]
    # the same seed, the same file
    first = (out / "chapters.parquet").read_bytes()
    run_ciphers(cfg, log=lambda _: None)
    assert (out / "chapters.parquet").read_bytes() == first


def test_unknown_ref_fails_fast(tmp_path):
    cfg, _ = corpus(tmp_path)
    cfg["ciphers"] = {**cfg["ciphers"], "chapters": ["Genesis 9"]}
    with pytest.raises(ValueError, match="Genesis 9"):
        run_ciphers(cfg, log=lambda _: None)


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_api(client):
    r = client.get("/api/ciphers").json()
    assert r["meta"]["tests"]["jeremiah"]["p"] == 0.04 and "known" not in r["meta"]
    assert r["known"] == [
        {"verse": {"verse_id": 0, "label_en": "v:0", "label_he": "v:0"}, "cipher": "atbash",
         "text": "יהוה", "name": "מצפץ", "found": True}
    ]  # fmt: skip
    assert [(c["cipher"], c["unit_id"], c["label_en"]) for c in r["chapters"]] == [
        ("albam", "c:1:1", "c:1:1"),
        ("atbash", "c:0:1", "c:0:1"),
    ]
    hits = client.get("/api/ciphers/hits").json()
    assert hits["total"] == 2 and hits["items"][0]["unit_id"] == "c:0:1"
    assert hits["items"][0]["verse"]["verse_id"] == 0 and hits["items"][0]["first_tok"] == 3
    assert client.get("/api/ciphers/hits", params={"cipher": "albam"}).json()["total"] == 1
    assert client.get("/api/ciphers/hits", params={"known": "true"}).json()["total"] == 1
    assert client.get("/api/ciphers/hits", params={"unit": "c:1:1"}).json()["total"] == 1
    assert client.get("/api/ciphers/hits", params={"cipher": "rot13"}).status_code == 422
    assert client.get("/api/ciphers/hits", params={"unit": "c:9:9"}).status_code == 404


def test_api_value(client):
    # ראשית is written in the fixture (4 times); its atbash form is not
    r = client.get("/api/ciphers/value", params={"text": "גךאבזת"}).json()
    assert r["atbash"]["form"] == apply("גךאבזת", "atbash")
    v = client.get("/api/ciphers/value", params={"text": apply("ראשית", "atbash")}).json()
    assert v["atbash"] == {"form": "ראשית", "n_words": 4}
    assert client.get("/api/ciphers/value", params={"text": "abc"}).status_code == 422


def test_findings(client):
    items = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    assert items["ciphers_known"]["verdict"] == "holds"
    assert items["ciphers_jeremiah"]["verdict"] == "holds"
    assert items["ciphers_elsewhere"]["verdict"] == "fails"
    assert items["ciphers_albam"]["verdict"] == "fails"
    assert items["ciphers_albam"]["values"]["random_hits"] == 0.7
