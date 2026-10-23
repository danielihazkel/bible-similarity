"""Naming etiologies (`bsim etiologies`, `/etiologies`, DESIGN.md §16.66)."""

import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.etiologies import (
    Word,
    echo,
    explanation,
    find_namings,
    lcs,
    run_etiologies,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder

EC = load_config()["etiologies"]


def w(i, surface, lemma, morph, content=True):
    return Word(i, surface, lemma, morph, content, i)


# Gen 29:32, cut: ותקרא שמו ראובן כי ראה יהוה בעניי
REUBEN = [
    w(0, "וַתִּקְרָא", "c/7121", "HC/Vqw3fs"),
    w(1, "שְׁמוֹ", "8034", "HNcmsc/Sp3ms"),
    w(2, "רְאוּבֵן", "7205", "HNp"),
    w(3, "כִּי", "3588 a", "HC"),
    w(4, "רָאָה", "7200", "HVqp3ms"),
    w(5, "יְהוָה", "3068", "HNp"),
    w(6, "בְּעָנְיִי", "b/6040", "HR/Ncmsc/Sp1cs"),
]


def test_lcs_and_echo():
    assert lcs("ראובנ", "ראה") == 2 and lcs("נח", "ינחמנו") == 2 and lcs("גד", "שמע") == 0
    # the most of a name word's letters in order in one word; ties: the word closest to the name
    assert echo(["ראובנ"], ["ראה", "ענני"], 2) == (pytest.approx(0.4), 0)
    assert echo(["שת"], ["אשתו", "שת"], 2) == (1.0, 1)
    assert echo(["גד"], ["שמע"], 2) == (0.0, -1)
    # a multi-word name: its best word
    assert echo(["באר", "שבע"], ["נשבעו"], 2) == (1.0, 0)


def test_find_namings():
    (n,) = find_namings(REUBEN, 7, EC)
    assert (n.verse_id, n.call, n.span, n.kind, n.name) == (7, 0, [2], "person", ["ראובנ"])
    assert n.written == ["ראובן"]
    # the explanation: content words outside the formula, no proper noun (יהוה)
    assert [REUBEN[k].idx for k in explanation(REUBEN, n, EC)] == [4, 6]


def test_find_namings_forms():
    # על כן קרא למקום ההוא באר שבע: a place, a two-word name whole
    beersheba = [
        w(0, "קָרָא", "7121", "HVqp3ms"),
        w(1, "לַמָּקוֹם", "l/4725", "HRd/Ncmsa"),
        w(2, "הַהוּא", "d/1931", "HTd/Pp3ms"),
        w(3, "בְּאֵר", "884+", "HNp"),
        w(4, "שָׁבַע", "884", "HNp"),
        w(5, "נִשְׁבְּעוּ", "7650", "HVNp3cp"),
    ]
    (n,) = find_namings(beersheba, 1, EC)
    assert (n.kind, n.span, n.name) == ("place", [3, 4], ["באר", "שבע"])
    # not namings: קרא בשם יהוה (a preposition, God's name), לא יקרא שמך, שמי (1st person)
    in_name = [w(0, "וַיִּקְרָא", "c/7121", "HC/Vqw3ms"), w(1, "בְּשֵׁם", "b/8034", "HR/Ncmsc"),
               w(2, "יְהוָה", "3068", "HNp")]  # fmt: skip
    assert find_namings(in_name, 2, EC) == []
    negated = [w(0, "לֹא", "3808", "HTn"), w(1, "יִקָּרֵא", "7121", "HVNi3ms"),
               w(2, "שִׁמְךָ", "8034", "HNcmsc/Sp2ms"), w(3, "אַבְרָם", "87", "HNp")]  # fmt: skip
    assert find_namings(negated, 3, EC) == []
    mine = [w(0, "וְיִקָּרֵא", "c/7121", "HC/VNj3ms"), w(1, "שְׁמִי", "8034", "HNcmsc/Sp1cs"),
            w(2, "אַבְרָהָם", "85", "HNp")]  # fmt: skip
    assert find_namings(mine, 4, EC) == []
    # a pronoun object right before the name: ואביו קרא לו בנימין
    to_him = [w(0, "קָרָא", "7121", "HVqp3ms"), w(1, "לוֹ", "l", "HR/Sp3ms", False),
              w(2, "בִנְיָמִין", "1144", "HNp")]  # fmt: skip
    assert [n.name for n in find_namings(to_him, 5, EC)] == [["בנימינ"]]


def corpus(tmp_path):
    """Four namings (each name echoed by its own verse) and four verses without one."""
    rows = []

    def naming(vid, name, lemma, expl):
        rows.extend([(vid, 0, "וַיִּקְרָא", "c/7121", ["7121"], "HC/Vqw3ms"),
                     (vid, 1, "שְׁמוֹ", "8034", ["8034"], "HNcmsc/Sp3ms"),
                     (vid, 2, name, lemma, [lemma], "HNp")])  # fmt: skip
        rows.extend(
            (vid, 3 + k, e, f"9{k}{vid}", [f"9{k}{vid}"], "HNcmsa") for k, e in enumerate(expl)
        )

    naming(0, "גָּד", "1410", ["בָּגַד", "טוֹב"])
    naming(1, "נֹחַ", "5146", ["יְנַחֲמֵנוּ", "אֶרֶץ"])
    naming(2, "שֵׁת", "8352", ["שָׁת", "זֶרַע"])
    naming(3, "דָּן", "1835", ["דָּנַנִּי", "קוֹל"])
    for vid in range(4, 8):
        rows.extend((vid, k, x, f"8{k}{vid}", [f"8{k}{vid}"], "HNcmsa")
                    for k, x in enumerate(["מַיִם", "יוֹם", "עֵץ"]))  # fmt: skip
    words = pd.DataFrame(rows, columns=["verse_id", "idx", "surface", "lemma", "content_lemmas",
                                        "morph"])  # fmt: skip
    words["display_idx"] = words.idx
    proc = tmp_path / "processed"
    proc.mkdir()
    words.to_parquet(proc / "words.parquet")
    pd.DataFrame({"verse_id": range(8), "book_id": 0, "chapter": 1,
                  "verse": range(1, 9)}).to_parquet(proc / "verses.parquet")  # fmt: skip
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc),
                    "artifacts": str(tmp_path / "artifacts")}  # fmt: skip
    cfg["etiologies"] = {**EC, "shuffles": 99, "verse_draws": 4,
                         "known": [{"ref": "Genesis 1:1", "name": "גד"},
                                   {"ref": "Genesis 1:2", "name": "שת"}]}  # fmt: skip
    return cfg


def test_run_etiologies(tmp_path):
    cfg = corpus(tmp_path)
    run_etiologies(cfg, log=lambda _: None)
    out = tmp_path / "artifacts" / "etiologies"
    d = pd.read_parquet(out / "namings.parquet")
    assert d.name.tolist() == ["גד", "נח", "שת", "דן"]
    assert d.score.tolist() == [1.0, 1.0, 1.0, 1.0]
    assert d.echo_word.tolist() == ["בגד", "ינחמנו", "שת", "דנני"]
    assert d.echo_disp.tolist() == [3, 3, 3, 3]
    # no other explanation echoes another name: each ranks first, and beats the random verses
    assert d.chance.tolist() == [0.0, 0.0, 0.0, 0.0]
    assert d.rank_p.tolist() == [0.25] * 4 and d.p.tolist() == [0.2] * 4
    meta = json.loads((out / "etiologies.meta.json").read_text("utf-8"))
    assert meta["mean_own"] == 1.0 and meta["mean_null"] < 1.0 and meta["p"] < 0.2
    assert meta["verse_draws"] == 4
    # the known: גד found at its verse; שת is not at Genesis 1:2
    assert [k["found"] for k in meta["known"]] == [True, False] and not meta["known_holds"]
    assert d.known.tolist() == [True, False, False, False]


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_etiologies_endpoint(client):
    r = client.get("/api/etiologies").json()
    assert [n["name"] for n in r["namings"]] == ["דגן", "חכמה"]
    first = r["namings"][0]
    assert (first["unit_id"], first["verse"]["verse_id"], first["echo_disp"]) == ("c:0:2", 3, 0)
    assert first["known"] and r["namings"][1]["echo_word"] is None
    assert r["holds"] and not r["known_holds"] and r["leads"] == 1
    assert [k["found"] for k in r["known"]] == [True, False]


def test_etiologies_findings(client):
    found = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    assert found["etiology_echo"]["verdict"] == "holds"
    assert found["etiology_echo"]["values"]["mean_own"] == 0.25
    assert found["etiology_known"]["verdict"] == "fails"
    assert found["etiology_known"]["values"]["known"] == 2
