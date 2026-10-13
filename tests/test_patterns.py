"""Pattern search (`api/patterns.py`, `/patterns`, DESIGN.md §16.46)."""

import sqlite3

import numpy as np
import pytest
from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.api.patterns import PatternError, WordTable, describe, parse
from bsim.fixture import fixture_encoder


def test_describe():
    w = describe("c/559", "HC/Vqw3ms")  # ויאמר
    assert (w["lemma"], w["pos"], w["stem"], w["form"]) == ("559", "verb", "qal", "wayyiqtol")
    assert (w["person"], w["gender"], w["number"], w["prefix_bits"]) == ("3", "m", "s", 1 << 1)
    w = describe("1121", "HNcmsc/Sp3ms")  # בנו
    assert (w["pos"], w["type"], w["state"], w["suffix"]) == ("noun", "common", "c", "3ms")
    w = describe("l", "HR/Sp3ms")  # לו: the preposition is the word, not a prefix
    assert (w["lemma"], w["pos"], w["suffix"], w["prefix_bits"]) == ("l", "preposition", "3ms", 0)
    w = describe("b/d/1004", "HR/Td/Ncmsa")  # בבית: two prefixes
    assert w["lemma"] == "1004" and w["prefix_bits"] == (1 << 2) | (1 << 0)
    assert describe("4191", "HVqa")["form"] == "infabs"
    assert describe("1254 a", "HVqrmsa")["lemma"] == "1254a"
    a = describe("1980", "AVhp3ms")
    assert (a["lang"], a["stem"]) == ("aramaic", "haphel")
    assert describe("7969", "HAcmsa")["pos"] == "number"
    assert describe("5704", "HNp")["pos"] == "name"
    assert describe("b/7225", None) == {"lemma": "7225"}  # no morphology: the lemma alone


@pytest.mark.parametrize(
    ("query", "code", "at"),
    [
        ("", "empty", 0),
        ("pos=verb", "expected_pattern", 0),
        ("[pos=verb", "unclosed", 0),
        ("[pos]", "bad_condition", 1),
        ("[pos=]", "bad_condition", 1),
        ("[colour=red]", "unknown_key", 1),
        ("[pos=verb] ..0 []", "bad_gap", 11),
        ("[pos=verb] ..99 []", "bad_gap", 11),
        ("[pos=verb] ..", "expected_pattern", 13),
        (".. [pos=verb]", "expected_pattern", 0),
        ("[] .. .. []", "expected_pattern", 6),
        ("[pos=@x]", "variable", 1),
        ("[] [] [] []", "too_many", 9),
    ],
)
def test_parse_errors(query, code, at):
    with pytest.raises(PatternError) as e:
        parse(query, 3, 40)
    assert (e.value.code, e.value.at) == (code, at)


def test_parse():
    terms = parse("[form=infabs root=@r]  [root=@r form!=infabs] ..3 [] .. [pos=verb|noun]", 8, 40)
    assert [t.gap for t in terms] == [1, 1, 3, 40]
    c = terms[1].conds
    assert (c[0].key, c[0].variable, c[1].negate, c[1].values) == ("root", "r", True, ["infabs"])
    assert terms[3].conds[0].values == ["verb", "noun"] and terms[2].conds == []


@pytest.fixture
def table(tmp_path):
    """Three verses: מות יומת; שמעו בני (a command and a vocative, in speech by משה); מות … then
    יומת five words on."""
    db = tmp_path / "w.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE words (verse_id, idx, display_idx, surface, lemma, morph);
        CREATE TABLE lemma_roots (lemma, root, root_he, link);
        CREATE TABLE lemma_gloss (lemma, he_lemma);
        CREATE TABLE syntax_phrases (verse_id, words, function);
        CREATE TABLE clauses (verse_id, words, typ, txt, speaker);
        """
    )
    conn.executemany(
        "INSERT INTO words VALUES (?, ?, ?, ?, ?, ?)",
        [
            (0, 0, 0, "מ֥וֹת", "4191", "HVqa"),
            (0, 1, 1, "יוּמָֽת", "4191", "HVHi3ms"),
            (1, 0, 0, "שִׁמְע֣וּ", "8085", "HVqv2mp"),
            (1, 1, 1, "בָנַ֗י", "1121", "HNcmpc/Sp1cs"),
            (1, 2, None, "וְהַקְשִׁ֣יבוּ", "c/7181", "HC/Vhv2mp"),
            (2, 0, 0, "מ֥וֹת", "4191", "HVqa"),
            (2, 1, 1, "לֹא", "3808", "HTn"),
            (2, 2, 2, "לֹא", "3808", "HTn"),
            (2, 3, 3, "לֹא", "3808", "HTn"),
            (2, 4, 4, "לֹא", "3808", "HTn"),
            (2, 5, 5, "תָּמֻת", "4191", "HVqi2ms"),
            (2, 6, 6, "מִיתָה", "4194", "HNcfsa"),
        ],
    )
    conn.executemany(
        "INSERT INTO lemma_roots VALUES (?, ?, ?, ?)",
        [("4191", "4191", "מוּת", None), ("4194", "4191", "מוּת", "from"),
         ("8085", "8085", "שָׁמַע", None)],
    )  # fmt: skip
    conn.executemany(
        "INSERT INTO lemma_gloss VALUES (?, ?)",
        [("4191", "מות"), ("1121", "בני"), ("8085", "שמע"), ("3808", "לא")],
    )
    conn.executemany(
        "INSERT INTO syntax_phrases VALUES (?, ?, ?)",
        [(1, "[0]", "Pred"), (1, "[1]", "Voct"), (1, "[2]", "Pred")],
    )
    conn.execute("INSERT INTO clauses VALUES (1, '[0, 1, 2]', 'ZIm0', 'Q', '4872')")
    conn.commit()
    t = WordTable.load(conn)
    conn.close()
    return t


def found(t: WordTable, q: str, limit: int = 1000) -> list[list[tuple[int, int]]]:
    rows = t.match(parse(q, 8, t.max_words), limit)
    return [[(int(t.verse[i]), int(t.idx[i])) for i in r] for r in rows]


def test_match(table):
    t = table
    assert t.max_words == 7
    # מות יומת: the next word, of the same root, not itself an infinitive absolute
    assert found(t, "[form=infabs root=@r] [root=@r form!=infabs]") == [[(0, 0), (0, 1)]]
    # ..N reaches N words on; .. the rest of the verse; never into the next verse
    assert found(t, "[form=infabs root=@r] ..4 [root=@r form=finite]") == [[(0, 0), (0, 1)]]
    assert found(t, "[form=infabs root=@r] ..5 [root=@r form=finite]") == [
        [(0, 0), (0, 1)], [(2, 0), (2, 5)]
    ]  # fmt: skip
    assert found(t, "[form=infabs root=@r] .. [root=@r]") == [
        [(0, 0), (0, 1)], [(2, 0), (2, 5)], [(2, 0), (2, 6)]
    ]  # fmt: skip
    # lemma differs, root the same: the noun of the family
    assert found(t, "[lemma=@l form=infabs] .. [root=מות lemma!=@l]") == [[(2, 0), (2, 6)]]
    assert found(t, "[form=imperative] [function=voct suffix=1cs]") == [[(1, 0), (1, 1)]]
    assert found(t, "[prefix=ו stem=hiphil]") == [[(1, 2)]]
    assert found(t, "[speech=yes speaker=4872 form=imperative]") == [[(1, 0)], [(1, 2)]]
    assert found(t, "[speaker=4872 suffix=yes]") == [[(1, 1)]]
    assert len(found(t, "[prefix=none suffix=no]")) == 10
    assert found(t, "[lemma=בני]") == [[(1, 1)]]  # its commonest form
    assert found(t, "[word=יומת]") == [[(0, 1)]]  # the consonants, final letters folded
    assert found(t, "[clause=zim0 function=pred]") == [[(1, 0)], [(1, 2)]]
    assert found(t, "[function=Subj]") == []  # a function the text lacks: nothing
    assert found(t, "[pos=noun] []") == [[(1, 1), (1, 2)]]  # the last word has no next word
    with pytest.raises(PatternError) as e:
        found(t, "[lemma=אבגד]")
    assert e.value.code == "unknown_value"
    with pytest.raises(PatternError) as e:
        found(t, "[] .. []", limit=10)
    assert e.value.code == "too_broad"
    with pytest.raises(PatternError) as e:
        found(t, "[lemma=@x] [root=@x]")
    assert e.value.code == "variable"
    with pytest.raises(PatternError) as e:
        found(t, "[speech=maybe]")
    assert e.value.code == "bad_value"


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_patterns_endpoint(client):
    # the fixture's verses 0 and 1 both hold אלהים ויאמר יהוה
    r = client.get("/api/patterns", params={"q": "[lemma=430] [lemma=559] ..2 [lemma=3068]"}).json()
    assert r["error"] is None and r["patterns"] == 3
    assert (r["total"], r["matches"]) == (2, 2)
    assert r["books"] == [{"book_id": 0, "matches": 2, "verses": 2}]
    first = r["items"][0]
    assert first["verse_id"] == 0 and first["unit_id"] == "c:0:1"
    assert first["matches"] == [{"words": [1, 2, 3], "tokens": [1, 2, 3]}]
    assert first["text"] == "אֱלֹהִים … וַיֹּאמֶר … יְהוָה"
    assert r["items"][1]["matches"][0]["tokens"] == [0, 1, None]  # v1's last word has no token
    assert client.get("/api/patterns", params={"q": "[lemma=430]", "unit": "v:1"}).json()[
        "total"
    ] == 1
    assert client.get("/api/patterns", params={"q": "[lemma=430]", "book": 1}).json()["total"] == 0
    paged = client.get("/api/patterns", params={"q": "[lemma=7225]", "limit": 2, "offset": 2})
    assert paged.json()["total"] == 5 and [i["verse_id"] for i in paged.json()["items"]] == [3, 4]
    bad = client.get("/api/patterns", params={"q": "[lemma=430"}).json()
    assert bad["error"] == {"code": "unclosed", "at": 0, "token": "[lemma=430"}
    assert bad["items"] == [] and bad["total"] == 0
    assert client.get("/api/patterns").json()["error"]["code"] == "empty"
    assert client.get("/api/patterns", params={"q": "[]", "limit": 0}).status_code == 422
    csv = client.get("/api/export/patterns.csv", params={"q": "[lemma=430]"}).text.splitlines()
    assert csv[0].lstrip("﻿") == "verse_id,label,label_he,unit_id,text" and len(csv) == 3


def test_word_table_built_once(built):
    cfg, _ = built
    cfg["serve"] = {**cfg["serve"], "patterns": {**cfg["serve"]["patterns"], "preload": False}}
    app = create_app(cfg, encoder=fixture_encoder, log=lambda _: None)
    state = app.state.serve
    assert state._words is None
    t = state.word_table()
    assert state.word_table() is t and len(t) == len(np.unique(t.verse * 100 + t.idx))
