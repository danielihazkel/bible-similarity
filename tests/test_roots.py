import json
import sqlite3

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.roots import (
    count_pairs,
    families,
    find_pairs,
    holds,
    radicals,
    read_derivations,
    tokens,
)
from bsim.api.app import create_app
from bsim.fixture import fixture_encoder

STRONG = """<?xml version="1.0" encoding="utf-8"?>
<lexicon xmlns="http://openscriptures.github.com/morphhb/namespace">
<entry id="H1288"><w pos="v">בָּרַךְ</w>
  <source>a primitive root;</source></entry>
<entry id="H1293"><w pos="n-f">בְּרָכָה</w>
  <source>from <w src="H1288">1288</w>;</source></entry>
<entry id="H1129"><w pos="v">בָּנָה</w>
  <source>a primitive root;</source></entry>
<entry id="H1004"><w pos="n-m">בַּיִת</w>
  <source>probably from <w src="H1129">1129</w>;</source></entry>
<entry id="H1121"><w pos="n-m">בֵּן</w>
  <source>from <w src="H1129">1129</w>;</source></entry>
<entry id="H3458"><w pos="n-pr-m">יִשְׁמָעֵאל</w>
  <source>from <w src="H8085">8085</w>;</source></entry>
<entry id="H8085"><w pos="v">שָׁמַע</w>
  <source>a primitive root;</source></entry>
<entry id="H1419"><w pos="a n-pr-m">גָּדוֹל</w>
  <source>or <w>גָּדֹל</w>; (shortened) from <w src="H1431">1431</w>;</source></entry>
<entry id="H1431"><w pos="v">גָּדַל</w>
  <source>a primitive root;</source></entry>
<entry id="H6965"><w pos="v">קוּם</w>
  <source>a primitive root;</source></entry>
<entry id="H8676"><w pos="a">קְהָתִי</w>
  <source>patronymically from <w src="H6955">6955</w>;</source></entry>
<entry id="H6955"><w pos="n-pr-m">קְהָת</w>
  <source>from an unused root;</source></entry>
<entry id="H7009"><w pos="n-m">קִים</w>
  <source>(Aramaic) corresponding to <w src="H6965">6965</w>;</source></entry>
<entry id="H9001"><w pos="n-f">גְּדֻלָּה</w>
  <source>from <w src="H9002">9002</w>;</source></entry>
<entry id="H9002"><w pos="n-f">גְּדֵלָה</w>
  <source>feminine of <w src="H9003">9003</w>;</source></entry>
<entry id="H9003"><w pos="n-m">גִּדּוּל</w>
  <source>from <w src="H1431">1431</w>;</source></entry>
</lexicon>
"""


@pytest.fixture
def derivations(tmp_path):
    path = tmp_path / "HebrewStrong.xml"
    path.write_text(STRONG, encoding="utf-8")
    return read_derivations(path)


def test_radicals_and_shapes():
    assert radicals("בָּרַךְ") == ["ב", "ר", "כ"]
    assert radicals("נָתַן") == ["ת", "נ"]  # a first נ is weak, a last one is not
    assert radicals("רָאָה") == ["ר", "א"]  # א stays
    assert radicals("סָבַב") == ["ס", "ב"]  # a doubled radical once
    assert holds("בְּרָכָה", ["ב", "ר", "כ"]) and holds("מִשְׁמַעַת", ["ש", "מ", "ע"])
    assert holds("גַּלְגַּל", ["ג", "ל"])  # the radicals twice over
    assert holds("פָּנִים", ["פ", "נ"])  # a final form folded before the ending
    assert not holds("בַּיִת", ["ב", "נ"]) and not holds("תְּבוּאָה", ["ב", "ר", "כ"])


def test_derivations(derivations):
    d = derivations.set_index("strong")
    assert d.loc["1293", "parent"] == "1288" and d.loc["1293", "link"] == "from"
    assert d.loc["1419", "parent"] == "1431"  # a variant spelling before the link
    assert pd.isna(d.loc["7009", "parent"]) and bool(d.loc["7009", "aramaic"])
    assert pd.isna(d.loc["8676", "parent"])  # a patronymic is not a word of the root


def test_families(derivations):
    fam = families(derivations, 2)
    assert fam["1293"] == "1288"
    assert fam["1121"] == "1129"  # בן: ב and נ
    assert "1004" not in fam  # בית "from" בנה lacks the נ
    assert "3458" not in fam  # a name never joins a family
    assert fam["1419"] == "1431"  # an adjective Strong also lists as a name
    assert fam["9003"] == "1431" and fam["9002"] == "1431"  # one and two links up
    assert "9001" not in fam  # three links up: not followed at max_depth 2
    assert families(derivations, 2, max_depth=3)["9001"] == "1431"
    assert "1293" not in families(derivations, 2, exclude=frozenset({"1293"}))
    assert "1121" not in families(derivations, 3)  # בנה has two strong radicals only


def _words(rows):
    return pd.DataFrame(rows, columns=["verse_id", "idx", "lemma", "morph"])


def test_tokens_and_pairs():
    fam = {"2472": "2492"}
    w = _words(
        [
            (0, 0, "c/2492", "HC/Vqw3ms"),  # ויחלם
            (0, 1, "3130", "HNpm"),  # יוסף: a name
            (0, 2, "2472", "HNcmsa"),  # חלום: a cognate pair at distance 2
            (1, 0, "4191", "HVqa"),  # מות
            (1, 1, "4191", "HVHi3ms"),  # יומת: infinitive absolute + finite
            (2, 0, "2472", "HNcmsa"),
            (2, 4, "2492", "HVqp3ms"),  # too far apart
            (3, 0, "7308", "AVqp3ms"),  # Aramaic: left out
        ]
    )
    t = tokens(w, fam)
    assert len(t) == 7 and set(t.root[t.lemma == "2472"]) == {"2492"}
    assert t[t.lemma == "3130"].pos.iloc[0] == "p"
    p = find_pairs(t, 3)
    assert list(zip(p.verse_id, p.kind, strict=True)) == [(0, "cognate"), (1, "inf_abs")]
    assert (p.a_idx.iloc[0], p.b_idx.iloc[0]) == (0, 2)


def test_count_pairs_matches_find_pairs():
    rng = np.random.default_rng(0)
    n = 400
    t = pd.DataFrame(
        {
            "verse_id": np.repeat(np.arange(40), 10),
            "idx": np.tile(np.arange(10), 40),
            "lemma": rng.choice(["a", "b", "c", "d", "e"], n),
            "pos": rng.choice(["V", "N", "A", "R"], n),
            "conj": "",
        }
    )
    t["root"] = t.lemma.map({"a": "x", "b": "x", "c": "y", "d": "y", "e": "e"})
    p = find_pairs(t, 3)
    codes = {c: pd.factorize(t[c])[0] for c in ("root", "lemma")}
    got = count_pairs(t.verse_id.to_numpy(), t.idx.to_numpy(), codes["root"], codes["lemma"],
                      t.pos.to_numpy(), 3, np.zeros(n, dtype=int), 1)  # fmt: skip
    assert got["cognate"][0] == (p.kind == "cognate").sum()
    assert got["other"][0] == (p.kind == "other").sum()


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_roots_api(client):
    r = client.get("/api/roots").json()
    assert r["meta"]["tests"]["cognate"]["ratio"] == 2.0 and "known" not in r["meta"]
    assert r["known"][0]["unit"]["unit_id"] == "c:0:1" and r["known"][0]["root_rank"] == 1
    assert [b["book_id"] for b in r["books"]] == [0, 1]
    p = client.get("/api/roots/pairs").json()
    assert p["total"] == 2 and p["items"][0]["root_he"] == "רֹאשׁ"
    assert p["items"][0]["marks"] == {"0": 0, "2": 1}
    assert client.get("/api/roots/pairs?kind=inf_abs").json()["items"][0]["verse_id"] == 1
    assert client.get("/api/roots/pairs?unit=c:0:2").json()["total"] == 0
    assert client.get("/api/roots/pairs?kind=other").json()["total"] == 0
    assert client.get("/api/roots/pairs?kind=nope").status_code == 422
    h = client.get("/api/roots/hidden").json()
    assert h["total"] == 1 and h["items"][0]["unit"]["unit_id"] == "c:0:1"
    assert [m["lemma"] for m in h["items"][0]["lemmas"]] == ["7225"]
    assert client.get("/api/roots/hidden?unit=v:1").json()["total"] == 1
    assert client.get("/api/roots/hidden?unit=c:1:1").json()["total"] == 0
    assert client.get("/api/roots/hidden?unit=c:9:9").status_code == 404


def test_root_family(client):
    f = client.get("/api/root/7218").json()
    assert f["root_he"] == "רֹאשׁ" and [m["lemma"] for m in f["members"]] == ["7225"]
    assert f["links"] == {"7225": "from"} and f["n_verses"] == 5
    assert f["items"][0]["display_idxs"] == [0]
    assert client.get("/api/root/7218?book=1").json()["total"] == 1
    assert client.get("/api/root/430").status_code == 404  # a word alone has no family page
    assert client.get("/api/root/123456").status_code == 404


def test_words_carry_roots(client):
    w = client.get("/api/words/0").json()
    assert w[0]["roots"] == [{"lemma": "7225", "root": "7218", "root_he": "רֹאשׁ"}]
    assert w[1]["roots"] == []


def test_roots_dossier_findings_export(client):
    d = client.get("/api/dossier/c:0:1").json()
    assert next(e for e in d["entries"] if e["kind"] == "roots")["count"] == 2
    f = {x["key"]: x for x in client.get("/api/findings").json()["items"]}
    assert f["cognate"]["verdict"] == "holds"
    lw = f["root_leitworte"]
    assert lw["verdict"] == "holds" and lw["values"]["better"] == 1
    csv = client.get("/api/export/root-pairs.csv").text
    assert csv.splitlines()[0].lstrip("﻿").split(",")[:5] == [
        "pair_id", "verse_id", "label", "label_he", "kind",
    ]  # fmt: skip
    assert "marks" not in csv.splitlines()[0]


def test_roots_in_db(built):
    _, db = built
    conn = sqlite3.connect(db)
    meta = json.loads(conn.execute("SELECT value FROM meta WHERE key = 'roots'").fetchone()[0])
    assert meta["families"] == 1
    assert conn.execute("SELECT book_id FROM root_pairs WHERE pair_id = 2").fetchone()[0] == 0
    assert conn.execute("SELECT SUM(hidden) FROM root_leitworte").fetchone()[0] == 1
