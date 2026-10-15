"""The Masorah's counts (`bsim masorah`, `/masorah`, DESIGN.md §16.55)."""

import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.masorah import book_span, run_masorah, texts
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder


def corpus(tmp_path):
    """Genesis 1:1-3, 2:1 and Exodus 1:1. Ketiv / qere: MAM shows the written היתה (read
    הייתה), the read אור (written אר); את is written, not read; ואלה is read, not written."""
    proc, art = tmp_path / "processed", tmp_path / "art"
    (art / "ketiv").mkdir(parents=True)
    proc.mkdir()
    verses = [
        (0, 0, 1, 1, ["בְּרֵאשִׁית", "בָּרָא", "אֱלֹהִים"]),
        (1, 0, 1, 2, ["וְהָאָרֶץ", "הָיְתָה", "׀", "תֹהוּ"]),
        (2, 0, 1, 3, ["וַיֹּאמֶר", "אֱלֹהִים", "יְהִי־", "אוֹר"]),
        (3, 0, 2, 1, ["וַיְכֻלּוּ", "הַשָּׁמַיִם"]),
        (4, 1, 1, 1, ["וְאֵלֶּה", "שְׁמוֹת"]),
    ]
    pd.DataFrame(
        verses, columns=["verse_id", "book_id", "chapter", "verse", "display_tokens"]
    ).to_parquet(proc / "verses.parquet")
    # OSHB words: one per display token (the paseq is none)
    words = [
        (v, i, d)
        for v, *_, ts in verses
        for i, d in enumerate(j for j, t in enumerate(ts) if t != "׀")
    ]
    pd.DataFrame(words, columns=["verse_id", "idx", "display_idx"]).astype(
        {"display_idx": "Int32"}
    ).to_parquet(proc / "words.parquet")
    pd.DataFrame(
        [(1, 1, 1, 1, "היתה", "הָיְיתָה"), (2, 3, 1, 1, "אר", "אוֹר"), (3, 1, 1, 0, "את", ""),
         (4, 0, 0, 1, "", "וְאֵלֶּה")],
        columns=["verse_id", "pos", "n_ketiv", "n_qere", "ketiv", "qere"],
    ).to_parquet(art / "ketiv" / "pairs.parquet")  # fmt: skip
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art)}
    cfg["masorah"] = {
        **cfg["masorah"],
        "middles": [
            {"span": "Torah", "unit": "letter", "ref": "Genesis 1:3", "word": "יהי", "letter": 1,
             "source": "talmud"},
            {"span": "Torah", "unit": "word", "ref": "Genesis 1:3", "word": "אלהים",
             "source": "talmud"},
            {"span": "Torah", "unit": "verse", "ref": "Genesis 1:3", "source": "masorah"},
            {"span": "Genesis", "unit": "verse", "ref": "Genesis 2:1", "source": "masorah"},
        ],
        "books": [{"books": ["Genesis"], "verses": 5, "reason": "split", "ref": "Genesis 1:2"},
                  {"books": ["Exodus"], "verses": 1, "also": [2]}],
        "sections": [
            {"books": ["Genesis", "Exodus"], "name": "torah", "unit": "verses", "value": 5,
             "source": "masorah"},
            {"books": ["Genesis", "Exodus"], "name": "torah", "unit": "letters", "value": 57,
             "source": "printed"},
        ],
    }  # fmt: skip
    return cfg, proc, art


def test_book_span():
    assert book_span("Torah") == (0, 4) and book_span("Psalms") == (26, 26)
    assert book_span(["Hosea", "Malachi"]) == (14, 25)
    with pytest.raises(ValueError, match="Tobit"):
        book_span(["Tobit"])


def test_texts(tmp_path):
    _, proc, art = corpus(tmp_path)
    t, applied = texts(
        pd.read_parquet(proc / "verses.parquet"),
        pd.read_parquet(proc / "words.parquet"),
        pd.read_parquet(art / "ketiv" / "pairs.parquet"),
    )
    words = {k: [" ".join(g.word) for _, g in d.groupby("verse_id")] for k, d in t.items()}
    assert words["ketiv"] == ["בראשית ברא אלהים", "והארץ היתה תהו", "ויאמר אלהים יהי אר",
                              "ויכלו את השמים", "שמות"]  # fmt: skip
    assert words["qere"] == ["בראשית ברא אלהים", "והארץ הייתה תהו", "ויאמר אלהים יהי אור",
                             "ויכלו השמים", "ואלה שמות"]  # fmt: skip
    # a written word MAM does not show stands for no display token; a replaced one for its own
    k = t["ketiv"]
    assert k[k.word == "את"].tok.tolist() == [-1] and k[k.word == "אר"].tok.tolist() == [3]
    assert applied == {"pairs": 4, "changed": {"ketiv": 3, "qere": 1}, "unaligned": 0}


def test_run_masorah(tmp_path):
    cfg, _, _ = corpus(tmp_path)
    out = run_masorah(cfg, log=lambda _: None)
    m = pd.read_parquet(out / "middles.parquet")
    row = {(r.claim, r.text): r for r in m.itertuples()}
    # written: 57 letters, the middle (28) is the 3rd letter of ויאמר; יהי's first letter is 36
    lk = row[(0, "ketiv")]
    assert (lk.n, lk.mid_pos, lk.mid_word, lk.mid_letter, lk.trad_pos) == (57, 28, "ויאמר", 3, 36)
    assert lk.distance == 8 and lk.verses_apart == 0 and not lk.holds
    lq = row[(0, "qere")]
    assert (lq.n, lq.mid_letter, lq.distance) == (61, 4, 7)
    # 14 written words: the middle falls between ויאמר and אלהים, and אלהים is half a word on
    wk = row[(1, "ketiv")]
    assert (wk.n, wk.mid_pos, wk.trad_pos, wk.distance, wk.trad_tok) == (14, 6.5, 7, 0.5, 1)
    assert wk.holds
    verse = m[m.unit == "verse"]
    assert verse.text.isna().all()
    assert verse.distance.tolist() == [0.0, 1.5] and verse.holds.tolist() == [True, False]

    t = pd.read_parquet(out / "totals.parquet")
    books = t[t.scope == "book"]
    assert books.ours.tolist() == [4, 1] and books["diff"].tolist() == [-1, 0]
    assert books.reason.tolist()[0] == "split" and books.ref_first.tolist()[0] == 1
    assert json.loads(books.also.tolist()[1]) == [2]
    sec = t[t.scope == "section"]
    assert sec[sec.unit == "verses"].book_sum.tolist() == [6]
    letters = sec[sec.unit == "letters"]
    assert letters.text.tolist() == ["ketiv", "qere"] and letters["diff"].tolist() == [0, 4]

    b = pd.read_parquet(out / "books.parquet")
    assert b.to_dict("records")[1] == {
        "book_id": 1, "verses": 1, "words_ketiv": 1, "words_qere": 2, "letters_ketiv": 4,
        "letters_qere": 8,
    }  # fmt: skip
    meta = json.loads((out / "masorah.meta.json").read_text("utf-8"))
    c = meta["checks"]
    assert c["letter"]["distance"] == 8 and c["word"]["holds"] and c["verse"]["holds"]
    assert c["books"] == {"n": 2, "agree": 1, "max_diff": 1, "reasoned": 1}
    assert meta["torah"]["letters_ketiv"] == 57 and meta["torah"]["words_qere"] == 14
    # the same input, the same files
    first = (out / "middles.parquet").read_bytes()
    run_masorah(cfg, log=lambda _: None)
    assert (out / "middles.parquet").read_bytes() == first


def test_bad_claims_fail_fast(tmp_path):
    cfg, _, _ = corpus(tmp_path)
    bad = {**cfg["masorah"]["middles"][1], "word": "גחון"}
    with pytest.raises(ValueError, match="גחון"):
        run_masorah({**cfg, "masorah": {**cfg["masorah"], "middles": [bad]}}, log=lambda _: None)
    bad = {**cfg["masorah"]["middles"][0], "letter": 4}
    with pytest.raises(ValueError, match="no letter 4"):
        run_masorah({**cfg, "masorah": {**cfg["masorah"], "middles": [bad]}}, log=lambda _: None)
    bad = {**cfg["masorah"]["middles"][3], "span": "Exodus"}
    with pytest.raises(ValueError, match="Genesis 2:1 is not in Exodus"):
        run_masorah({**cfg, "masorah": {**cfg["masorah"], "middles": [bad]}}, log=lambda _: None)


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_api(client):
    r = client.get("/api/masorah").json()
    assert r["meta"]["checks"]["letter"]["distance"] == 4.5 and r["meta"]["text"] == "ketiv"
    mid = r["middles"]
    assert [(x["claim"], x["text"]) for x in mid] == [
        (0, "ketiv"), (0, "qere"), (1, "ketiv"), (1, "qere"), (2, None), (3, None)
    ]  # fmt: skip
    assert mid[0]["trad_verse"]["verse_id"] == 2 and mid[0]["mid_verse"]["verse_id"] == 0
    assert mid[0]["trad_verse"]["display_tokens"][0] == "רֵאשִׁית" and mid[4]["trad_tok"] is None
    t = r["totals"]
    assert t[0]["reason"] == "split" and t[0]["ref_first"]["label_en"] == "v:2"
    assert t[1]["also"] == [2] and t[1]["ref_first"] is None
    assert t[2]["book_sum"] == 7 and t[3]["text"] == "ketiv"
    assert r["books"][0] == {"book_id": 0, "verses": 5, "words_ketiv": 13, "words_qere": 13,
                             "letters_ketiv": 52, "letters_qere": 53}  # fmt: skip


def test_findings(client):
    items = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    assert items["masorah_letter"]["verdict"] == "fails"
    assert items["masorah_letter"]["values"] == {"n": 52, "distance": 4.5, "verses_apart": 2}
    assert items["masorah_words"]["verdict"] == "holds"
    assert items["masorah_verse"]["verdict"] == "holds"
    assert items["masorah_books"]["verdict"] == "fails"
    assert items["masorah_books"]["values"]["agree"] == 1
