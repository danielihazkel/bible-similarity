"""Names built on God's name (DESIGN.md §16.90, D152): the names from HebrewStrong, each
occurrence's form, the claim within names, the stage, the dating feature, the API."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from bsim.analysis.dating import model_features, word_flags
from bsim.analysis.theophoric import form_of, names, occurrences, run_theophoric, short_share
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.data.canon import BY_OSIS
from bsim.fixture import fixture_encoder


def _entry(lemma, pos, he, source):
    return f'<entry id="H{lemma}"><w pos="{pos}">{he}</w><source>{source}</source></entry>'


def _src(*keys):
    return " and ".join(f'<w src="H{k}">{k}</w>' for k in keys)


XML = "\n".join(
    [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<lexicon xmlns="http://openscriptures.github.com/morphhb/namespace">',
        _entry("3414", "n-pr-m", "יִרְמְיָה", f"or <w>יִרְמְיָהוּ</w>; from {_src('7311', '3050')};"),
        _entry("3088", "n-pr-m", "יְהוֹרָם", f"from {_src('3068', '7311')};"),
        _entry("3141", "n-pr-m", "יוֹרָם", f"a form of {_src('3088')};"),
        _entry("3458", "n-pr-m", "יִשְׁמָעֵאל", f"from {_src('8085', '410')};"),
        _entry("1008", "n-pr-loc", "בֵּית־אֵל", f"from {_src('1004', '410')};"),
        _entry("8020", "n-pr-m", "שַׁלְמַן", "of foreign derivation;"),
        "</lexicon>",
    ]
)


def lexicon(tmp_path):
    p = tmp_path / "raw" / "lexicon"
    p.mkdir(parents=True)
    (p / "HebrewStrong.xml").write_text(XML, encoding="utf-8")
    return p / "HebrewStrong.xml"


def test_names(tmp_path):
    theo = names(lexicon(tmp_path)).set_index("lemma")
    assert theo.divine.to_dict() == {"3414": "yah", "3088": "yah", "3458": "el", "3141": "yah"}
    # a place (Bethel) and a name of foreign derivation are not names built on God's name


def test_form_of():
    assert form_of("ירמיהו", "yah") == "yahu" and form_of("ירמיה", "yah") == "yah"
    assert form_of("יהורם", "yah") == "yeho" and form_of("יורם", "yah") == "yo"
    assert form_of("ישמעאל", "el") == "el_last" and form_of("אלישע", "el") == "el_first"
    assert form_of("רם", "yah") is None


def test_occurrences_and_the_claim(tmp_path):
    theo = names(lexicon(tmp_path))
    words = pd.DataFrame(
        {
            "verse_id": [0, 1, 2, 3, 4, 5],
            "lemma": ["3414", "l/3414", "3414", "3088", "3141", "1961"],
            "surface": ["יִרְמְיָהוּ", "לְיִרְמְיָה", "יִרְמְיָה", "יְהוֹרָם", "יוֹרָם", "וַיְהִי"],
            "morph": ["HNp", "HR/Np", "HNp", "HNp", "HNp", "HVqw3ms"],
        }
    )
    occ = occurrences(words, theo)
    assert occ.form.tolist() == ["yahu", "yah", "yah", "yeho", "yo"]  # the prefix ל stripped
    late = np.array([False, True, True, False, False])
    assert short_share(occ, late) == 1.0  # late: 2 of 2 short; early: 0 of 1


def test_run(tmp_path):
    lexicon(tmp_path)
    proc = tmp_path / "processed"
    proc.mkdir()
    # Genesis (early) spells Jeremiah long, Ezra (late) short
    gen, ezra = BY_OSIS["Gen"].book_id, BY_OSIS["Ezra"].book_id
    words = pd.DataFrame(
        {
            "verse_id": [0, 1, 2, 3],
            "lemma": ["3414", "3414", "3414", "3458"],
            "surface": ["יִרְמְיָהוּ", "יִרְמְיָהוּ", "יִרְמְיָה", "יִשְׁמָעֵאל"],
            "morph": ["HNp"] * 4,
        }
    )
    words.to_parquet(proc / "words.parquet")
    pd.DataFrame({"verse_id": [0, 1, 2, 3], "book_id": [gen, gen, ezra, gen]}).to_parquet(
        proc / "verses.parquet"
    )
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "data_raw": str(tmp_path / "raw"),
                    "artifacts": str(tmp_path / "artifacts")}  # fmt: skip
    cfg["theophoric"] = {**cfg["theophoric"], "shuffles": 99,
                         "known": [{"books": ["Gen"], "side": "long"},
                                   {"books": ["Ezra"], "side": "short"}]}  # fmt: skip
    run_theophoric(cfg, log=lambda _: None)
    out = tmp_path / "artifacts" / "theophoric"
    meta = json.loads((out / "theophoric.meta.json").read_text("utf-8"))
    assert (meta["forms"]["yahu"], meta["forms"]["yah"], meta["forms"]["el_last"]) == (2, 1, 1)
    c = meta["claim"]
    assert (c["early_short"], c["late_short"], c["names"]) == (0.0, 1.0, 1)
    assert [k["holds"] for k in meta["known"]] == [True, True] and meta["known_holds"]
    n = pd.read_parquet(out / "names.parquet").set_index("lemma")
    assert (n.loc["3414", "n"], n.loc["3414", "yahu"], n.loc["3414", "yah"]) == (3, 2, 1)
    b = pd.read_parquet(out / "books.parquet").set_index("book_id")
    assert b.loc[ezra, "yah"] == 1 and b.loc[gen, "yahu"] == 2


def test_the_dating_feature():
    words = pd.DataFrame(
        {
            "verse_id": [0, 1, 2],
            "lemma": ["3414", "3414", "1961"],
            "surface": ["יִרְמְיָהוּ", "יִרְמְיָה", "וַיְהִי"],
            "morph": ["HNp", "HNp", "HVqw3ms"],
        }
    )
    f = word_flags(words, set(), {"3414"})
    assert f.yah_end.tolist() == [1, 1, 0] and f.yah_short.tolist() == [0, 1, 0]
    assert word_flags(words, set()).yah_end.sum() == 0  # no names given: the feature at its prior
    feats, gram = model_features({"features": ["lbh_lexemes", "anokhi"]})
    assert (feats, gram) == (["lbh_lexemes", "anokhi"], ["anokhi"])
    try:
        model_features({"features": ["nothing"]})
    except RuntimeError as e:
        assert "unknown" in str(e)
    else:
        raise AssertionError("an unknown feature should be refused")
    assert "yah_short" not in load_config()["dating"]["features"]  # measured, not adopted (D152)


def test_api(built):
    cfg, _ = built  # the fixture's made-up run
    c = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    r = c.get("/api/theophoric").json()
    assert (r["names_total"], r["occurrences"]) == (2, 5)
    assert r["claim"]["holds"] is False and [k["holds"] for k in r["known"]] == [True, False]
    assert [b["book_id"] for b in r["books"]] == [0, 1] and r["names"][0]["lemma"] == "3414"
    assert c.get("/api/theophoric", params={"names": 100000}).status_code == 422
    f = {x["key"]: x for x in c.get("/api/findings").json()["items"]}
    assert f["theophoric"]["verdict"] == "fails" and f["theophoric"]["values"]["names"] == 1
    pub = {**cfg, "serve": {**cfg["serve"], "personal": False}}
    p = TestClient(create_app(pub, encoder=fixture_encoder, log=lambda _: None))
    assert p.get("/api/theophoric").status_code == 200
