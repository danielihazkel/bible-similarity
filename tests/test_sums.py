"""Do the sums add up (`bsim sums`, `/sums`, DESIGN.md §16.75); the number phrases it reads."""

import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.chronology import phrases, words_of
from bsim.analysis.sums import aligned, one_step, run_sums
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.data.canon import BY_OSIS
from bsim.fixture import fixture_encoder

NUMBERS = {str(k): int(v) for k, v in load_config()["chronology"]["numbers"].items()}


def value(*ws: tuple[str, str, str]) -> list[int]:
    """The values of the number phrases of (lemma, morph, surface) words."""
    return [
        p.value
        for p in phrases([words_of(lem, mo, i, s) for i, (lem, mo, s) in enumerate(ws)], NUMBERS)
    ]


def test_numbers_after_a_thousand():
    # Num 2:16: מאת אלף ואחד וחמשים אלף וארבע מאות וחמשים, 151,450 (the thousand multiplies
    # the groups since the last thousand, not the 100,000 before them)
    assert value(
        ("3967", "HAcbsc", "מְאַת"),
        ("505", "HAcbsa", "אֶלֶף"),
        ("c/259", "HC/Acmsa", "וְאֶחָד"),
        ("c/2572", "HC/Acbpa", "וַחֲמִשִּׁים"),
        ("505", "HAcbsa", "אֶלֶף"),
        ("c/702", "HC/Acfsa", "וְאַרְבַּע"),
        ("3967", "HAcbpa", "מֵאוֹת"),
        ("c/2572", "HC/Acbpa", "וַחֲמִשִּׁים"),
    ) == [151450]
    # Num 26:51: שש מאות אלף ואלף שבע מאות ושלשים, 601,730 (a smaller number after a thousand adds)
    assert value(
        ("8337", "HAcfsa", "שֵׁשׁ"),
        ("3967", "HAcbpa", "מֵאוֹת"),
        ("505", "HAcbsa", "אֶלֶף"),
        ("c/505", "HC/Acbsa", "וָאֶלֶף"),
        ("7651", "HAcfsa", "שְׁבַע"),
        ("3967", "HAcbpa", "מֵאוֹת"),
        ("c/7970", "HC/Acbpa", "וּשְׁלֹשִׁים"),
    ) == [601730]
    # 1 Chr 21:5: אלף אלפים ומאה אלף, 1,100,000
    assert value(
        ("505", "HAcbsa", "אֶלֶף"),
        ("505", "HAcbpa", "אֲלָפִים"),
        ("c/3967", "HC/Acbsa", "וּמֵאָה"),
        ("505", "HAcbsa", "אֶלֶף"),
    ) == [1100000]


def test_dual_and_as_one():
    # Ezra 2:64: כאחד ארבע רבוא אלפים שלש מאות ששים, 42,360: אַלְפַּיִם is a dual (OSHB: plural),
    # כאחד ("as one") not a number
    assert value(
        ("k/259", "HR/Acmsa", "כְּאֶחָד"),
        ("702", "HAcfsa", "אַרְבַּע"),
        ("7239", "HAcbsa", "רִבּוֹא"),
        ("505", "HAcbpa", "אַלְפַּיִם"),
        ("7969", "HAcfsa", "שְׁלֹשׁ"),
        ("3967", "HAcbpa", "מֵאוֹת"),
        ("8346", "HAcbpa", "שִׁשִּׁים"),
    ) == [42360]
    # Ezra 2:3: אלפים מאה שבעים ושנים, 2,172
    assert value(
        ("505", "HAcbpa", "אַלְפַּיִם"),
        ("3967", "HAcbsa", "מֵאָה"),
        ("7657", "HAcbpa", "שִׁבְעִים"),
        ("c/8147", "HC/Acmda", "וּשְׁנָיִם"),
    ) == [2172]


@pytest.mark.parametrize(
    ("x", "y", "step"),
    [
        (40000, 4000, True),  # a power of ten
        (18, 8, True),  # one decimal place
        (775, 652, False),
        (800000, 1100000, False),
        (12, 12, False),  # the same
        (500000, 470000, False),
    ],
)
def test_one_step(x, y, step):
    assert one_step(x, y) is step and one_step(y, x) is step


def test_aligned_by_unit():
    # 2 Kgs 24:8 (18 years, 3 months) against 2 Chr 36:9 (8 years, 3 months, 10 days)
    a = value(("8083", "HAcfsa", "שְׁמֹנֶה"), ("6240", "HAcfsa", "עֶשְׂרֵה"))
    assert a == [18]
    pa = phrases(
        [
            words_of("1121 a", "HNcmsc", 0),
            words_of("8083", "HAcfsa", 1),
            words_of("6240", "HAcfsa", 2),
            words_of("8141", "HNcfsa", 3),
            words_of("7969", "HAcfsa", 4),
            words_of("2320", "HNcmpa", 5),
        ],
        NUMBERS,
    )
    pb = phrases(
        [
            words_of("1121 a", "HNcmsc", 0),
            words_of("8083", "HAcfsa", 1),
            words_of("8141", "HNcfsa", 2),
            words_of("7969", "HAcfsa", 3),
            words_of("2320", "HNcmpa", 4),
            words_of("c/6235", "HC/Acmsa", 5),
            words_of("3117", "HNcmpa", 6),
        ],
        NUMBERS,
    )
    pairs = [(x.value, y.value, x.unit) for x, y in aligned(pa, pb)]
    assert pairs == [(18, 8, "year"), (3, 3, "month")]


def corpus(tmp_path):
    """Genesis 1:1–2 count 10 and 20 men of a town, 1:3 all of them, 30; 1 Chronicles 1:1–2 are
    their parallels (Sefaria verse links) with 100 and 35."""
    gen, chr_ = BY_OSIS["Gen"].book_id, BY_OSIS["1Chr"].book_id
    men = [("376", "HNcmpc", "אַנְשֵׁי", ["376"]), ("5892", "HNcfsa", "עִיר", ["5892"])]
    ten = [("6235", "HAcfsa", "עֲשָׂרָה", ["6235"])]
    twenty = [("6242", "HAcbpa", "עֶשְׂרִים", ["6242"])]
    thirty = [("3605", "HNcmsc", "כָּל", ["3605"]), ("7970", "HAcbpa", "שְׁלֹשִׁים", ["7970"])]
    hundred = [("3967", "HAcbsa", "מֵאָה", ["3967"])]
    thirty_five = [("7970", "HAcbpa", "שְׁלֹשִׁים", ["7970"]), ("c/2568", "HC/Acfsa", "וְחָמֵשׁ", ["2568"])]
    verses = [
        (gen, 1, 1, men + ten),
        (gen, 1, 2, men + twenty),
        (gen, 1, 3, thirty),
        (chr_, 1, 1, men + hundred),
        (chr_, 1, 2, men + thirty_five),
    ]
    proc = tmp_path / "processed"
    proc.mkdir()
    pd.DataFrame(
        {
            "verse_id": range(len(verses)),
            "book_id": [v[0] for v in verses],
            "chapter": [v[1] for v in verses],
            "verse": [v[2] for v in verses],
        }
    ).to_parquet(proc / "verses.parquet")
    rows = [
        (v, i, s, lem, mo, i, cl)
        for v, (*_, ws) in enumerate(verses)
        for i, (lem, mo, s, cl) in enumerate(ws)
    ]
    pd.DataFrame(
        rows,
        columns=["verse_id", "idx", "surface", "lemma", "morph", "display_idx", "content_lemmas"],
    ).to_parquet(proc / "words.parquet")
    pd.DataFrame({"src_vid": [0, 1], "tgt_vid": [3, 4], "level": ["verse", "verse"]}).to_parquet(
        proc / "links.parquet"
    )
    cfg = load_config()
    cfg["paths"] = {
        **cfg["paths"],
        "data_processed": str(proc),
        "artifacts": str(tmp_path / "artifacts"),
    }
    cfg["sums"] = {
        **cfg["sums"],
        "lists": {
            "men": [["Genesis 1:1-2"], "Genesis 1:3", 1, True],
            "chr": [["I Chronicles 1:1"], "I Chronicles 1:2", 1, True],
        },
        "parallels": {**cfg["sums"]["parallels"], "shuffles": 99},
        "known_parallels": [
            ["Genesis 1:1", "I Chronicles 1:1", 10, 100, True],
            ["Genesis 1:2", "I Chronicles 1:2", 20, 35, True],
        ],
    }
    return cfg


def test_run_sums(tmp_path):
    cfg = corpus(tmp_path)
    run_sums(cfg, log=lambda _: None)
    out = tmp_path / "artifacts" / "sums"
    lists = pd.read_parquet(out / "lists.parquet").set_index("key")
    assert (lists.loc["men", "sum"], lists.loc["men", "total"]) == (30, 30)
    assert lists.loc["men", "adds_up"] and lists.loc["men", "holds"]
    assert not lists.loc["chr", "adds_up"] and not lists.loc["chr", "holds"]  # 100, not 35
    items = pd.read_parquet(out / "items.parquet")
    assert items[items.key == "men"].value.tolist() == [10, 20]
    par = pd.read_parquet(out / "parallels.parquet")
    assert list(zip(par.a_value, par.b_value, par.one_step, strict=True)) == [
        (10, 100, True),
        (20, 35, False),
    ]
    meta = json.loads((out / "sums.meta.json").read_text("utf-8"))
    assert not meta["lists_holds"] and meta["lists_adding_up"] == 1
    assert meta["pairs"] == 2 and meta["pairs_used"] == 2
    assert meta["across"]["tested"] == 2 and meta["across"]["one_step"] == 1
    assert meta["across"]["share"] == 0.5 and meta["every"]["tested"] == 2
    # the first known pair one step apart as expected; the second not one step: it fails
    assert [k["holds"] for k in meta["known_parallels"]] == [True, False]
    assert not meta["known_holds"]


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_sums_endpoint(client):
    r = client.get("/api/sums").json()
    assert r["lists_holds"] and r["step_holds"] and r["known_holds"]
    assert [x["key"] for x in r["lists"]] == ["num1", "ezra2"]
    assert r["lists"][1]["sum"] == 5 and r["lists"][1]["total_verse"]["verse_id"] == 4
    assert r["across"]["share"] == 0.5 and r["known_parallels"][0]["b"]["verse_id"] == 5
    items = client.get("/api/sums/items", params={"key": "num1"}).json()["items"]
    assert [(i["verse"]["verse_id"], i["value"]) for i in items] == [(0, 10), (1, 20)]
    assert client.get("/api/sums/items", params={"key": "none"}).status_code == 404


def test_sums_parallels_endpoint(client):
    r = client.get("/api/sums/parallels").json()  # across books, differing: two
    assert r["total"] == 2 and [x["one_step"] for x in r["items"]] == [True, False]
    every = client.get("/api/sums/parallels", params={"across": False, "differ": False}).json()
    assert every["total"] == 3 and every["items"][0]["same"]
    step = client.get("/api/sums/parallels", params={"one_step": True}).json()
    assert [(x["a_value"], x["b_value"]) for x in step["items"]] == [(40, 4)]


def test_sums_findings(client):
    found = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    assert found["sums_lists"]["verdict"] == "holds"
    assert found["sums_lists"]["values"]["num1_sum"] == 30
    assert found["sums_lists"]["values"]["ezra2_total"] == 9
    assert found["sums_parallels"]["values"]["share"] == 0.5
