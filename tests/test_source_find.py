"""The source finder (`POST /source-find`, DESIGN.md §11.1): the keys, seeds, alignment and
choosing on a small corpus of verses; the API over the fixture DB."""

from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.api.source_find import Normaliser, build_index, source_find
from bsim.config import load_config
from bsim.fixture import fixture_encoder

SF = load_config()["source_find"]

# a small corpus: the priestly blessing, the Shema's two "when you lie down", and others
VERSES = [
    "יְבָרֶכְךָ יְהוָה וְיִשְׁמְרֶךָ",  # 0 Num 6:24
    "יָאֵר יְהוָה פָּנָיו אֵלֶיךָ וִיחֻנֶּךָּ",  # 1 Num 6:25
    "יִשָּׂא יְהוָה פָּנָיו אֵלֶיךָ וְיָשֵׂם לְךָ שָׁלוֹם",  # 2 Num 6:26
    "וְשִׁנַּנְתָּם לְבָנֶיךָ וְדִבַּרְתָּ בָּם בְּשִׁבְתְּךָ בְּבֵיתֶךָ וּבְלֶכְתְּךָ בַדֶּרֶךְ וּבְשָׁכְבְּךָ וּבְקוּמֶךָ",  # 3
    "וְלִמַּדְתֶּם אֹתָם אֶת בְּנֵיכֶם לְדַבֵּר בָּם בְּשִׁבְתְּךָ בְּבֵיתֶךָ וּבְלֶכְתְּךָ בַדֶּרֶךְ וּבְשָׁכְבְּךָ וּבְקוּמֶךָ",  # 4
    "וַיְדַבֵּר יְהוָה אֶל מֹשֶׁה לֵּאמֹר",  # 5
    "וַיְדַבֵּר יְהוָה אֶל מֹשֶׁה לֵּאמֹר",  # 6
    "וַיֹּאמֶר אֱלֹהִים יְהִי אוֹר וַיְהִי אוֹר",  # 7
]  # fmt: skip
LOW = {**SF, "min_score": 2.5}  # the corpus is small, so its words weigh little (1.4-2.1)


@pytest.fixture(scope="module")
def index():
    return build_index(VERSES, Normaliser(SF))


def test_keys():
    n = Normaliser(SF)
    assert n.key("ה׳") == n.key("יי") == n.key("יְהוָה")  # the divine name as liturgy writes it
    assert n.key("אלקינו") == n.key("אֱלֹהֵינוּ") and n.key("אלקים") == n.key("אלהים")
    assert n.key("אלקנה") != n.key("אלהנה")  # Elkanah is no אלקים
    assert n.key("אלוהי") == n.key("אֱלֹהֵי")  # fuller spelling, one key
    assert n.key("שׁלום") == n.key("שלם") and n.key("׃") == ""


def test_priestly_blessing_one_passage(index):
    text = "יברכך ה׳ וישמרך. יאר ה׳ פניו אליך ויחנך. ישא ה׳ פניו אליך וישם לך שלום."
    tokens, at, ps = source_find(text, index, Normaliser(SF), LOW)
    assert [[h.verse_id for h in p.hits] for p in ps] == [[0, 1, 2]]
    assert (at[ps[0].q_first], at[ps[0].q_last]) == (0, len(tokens) - 1)


def test_a_verse_quoted_twice_and_its_alternative(index):
    text = "שנאמר ובשכבך ובקומך. ובית הלל אומרים שנאמר ובלכתך בדרך. למה נאמר ובשכבך ובקומך"
    tokens, at, ps = source_find(text, index, Normaliser(SF), LOW)
    # "when you lie down", "when you walk on the way", "when you lie down" again
    assert [tokens[at[p.q_first]] for p in ps] == ["ובשכבך", "ובלכתך", "ובשכבך"]
    for p in ps:  # Deut 6:7, with Deut 11:19 the same words
        (h,) = p.hits
        assert {h.verse_id, *h.alternatives} == {3, 4}


def test_nothing_in_other_hebrew_and_formulae_seed_nothing(index):
    assert source_find("אני הולך מחר לחנות לקנות לחם", index, Normaliser(SF), LOW)[2] == []
    # "וידבר יהוה אל משה" is in two verses: with seed_max 1 it seeds nothing
    strict = {**LOW, "seed_max": 1}
    assert source_find("וידבר ה׳ אל משה לאמר", index, Normaliser(SF), strict)[2] == []
    found = source_find("וידבר ה׳ אל משה לאמר", index, Normaliser(SF), LOW)[2]
    assert len(found) == 1 and {found[0].hits[0].verse_id, *found[0].hits[0].alternatives} == {5, 6}


# --- the API over the fixture DB -----------------------------------------------------------------


@pytest.fixture
def client(built):
    cfg, _ = built
    cfg = copy.deepcopy(cfg)
    cfg["source_find"] = {**cfg["source_find"], "min_score": 1.0, "max_chars": 60}
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_api_examples(client):
    r = client.get("/api/source-find/examples").json()
    assert r["max_chars"] == 60
    assert [e["key"] for e in r["examples"]] == ["ashrei", "aleinu", "priestly", "mishnah"]


def test_api_source_find(client):
    r = client.post("/api/source-find", json={"text": "שלום. אלהים ויאמר ה׳ עוד"}).json()
    assert r["tokens"] == ["שלום.", "אלהים", "ויאמר", "ה׳", "עוד"]
    (p,) = r["passages"]
    assert (p["first"], p["last"], p["matched"]) == (1, 3, 3)
    (v,) = p["verses"]
    # fixture v0 has these three words after בראשית, and v1 is them: a tie, the first verse taken
    assert v["verse"]["verse_id"] == 0 and v["tokens"] == [1, 2, 3]
    assert v["text_tokens"] == [1, 2, 3]
    assert [a["verse_id"] for a in p["alternatives"]] == [1]
    assert client.post("/api/source-find", json={"text": ""}).json()["passages"] == []


def test_api_source_find_too_long(client):
    r = client.post("/api/source-find", json={"text": "א" * 61})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "too_long"
