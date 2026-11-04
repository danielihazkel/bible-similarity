"""Other witnesses (`bsim witnesses`, DESIGN.md §16.78): the labels, the plus and omission rules,
the Text-Fabric readers and a run on made-up datasets; the API over the fixture DB."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.witnesses import (
    WWord,
    counts,
    label,
    letters_of,
    longest_plus,
    rate_ratio,
    run_witnesses,
    shifted,
    skeleton,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder


def test_labels_and_letters():
    assert letters_of("שׁנה") == "שנה"  # U+FB2A, the Samaritan's shin, decomposed
    assert letters_of("אלהים") == "אלהימ"  # finals folded
    assert skeleton("אלוהימ") == skeleton("אלהימ")
    assert skeleton("שמו") != skeleton("שמ") and skeleton("לו") == "לו"
    assert label("substitution", "ארצ", "הארצ") == "form"  # the article
    assert label("substitution", "שמו", "שמ") == "form"  # a suffix
    assert label("substitution", "השביעי", "הששי") == "substitution"
    assert label("added", "", "אור") == "added"


def test_plus_and_omission_rules():
    read, rec = WWord("א"), WWord("ב", read=False)
    # a reconstructed word inside a run of added words does not break it, nor count
    wit = [read, read, rec, read, read]
    ops = [("added", None, i) for i in range(5)]
    ok = counts(ops, wit)
    assert ok == [True, True, False, True, True]
    assert longest_plus(ops, ok) == 4
    assert longest_plus([("same", 0, 0), *ops[1:]], ok) == 3
    # an omission counts only between two read words
    ops = [("same", 0, 0), ("omitted", 1, None), ("same", 2, 1)]
    assert counts(ops, [read, read]) == [True, True, True]
    assert counts(ops, [read, rec]) == [True, False, False]
    assert counts([("omitted", 0, None), ("same", 1, 0)], [read]) == [False, True]


def test_shift_keeps_blocks():
    lab = np.array([True, True, False, False, False, True, False, False])
    books = np.array([0, 0, 0, 0, 0, 1, 1, 1])
    out = shifted(lab, books, np.random.default_rng(1))
    # each book's labels rotated as a whole: the block of two stays a block
    assert any(np.array_equal(out[:5], np.roll(lab[:5], k)) for k in range(5))
    assert any(np.array_equal(out[5:], np.roll(lab[5:], k)) for k in range(3))
    assert rate_ratio(np.array([1, 0, 0, 1]), np.array([True, True, False, False])) == 1.0
    assert np.isnan(rate_ratio(np.array([1, 1]), np.array([True, True])))


# --- a run on made-up Text-Fabric datasets -------------------------------------------------------

MT = {  # verse_id: (book_id, chapter, verse, WLC osis, words)
    0: (0, 1, 1, "Gen.1.1", ["בְּרֵאשִׁית", "בָּרָא", "אֱלֹהִים"]),
    1: (0, 1, 2, "Gen.1.2", ["וְהָאָרֶץ", "הָיְתָה", "תֹהוּ"]),
    2: (0, 5, 3, "Gen.5.3", ["וַיְחִי", "אָדָם", "שְׁלֹשִׁים", "וּמְאַת", "שָׁנָה"]),
    3: (11, 1, 1, "Isa.1.1", ["חֲזוֹן", "יְשַׁעְיָהוּ", "בֶּן", "אָמוֹץ"]),
}
# the Samaritan: (osis, [(units, trailer, lex, nu)]); a word's prefixes are units of their own
SP = [
    ("Gen.1.1", [("ב", "", "B", "NA"), ("ראשׁית", " ", "R>CJT/", "sg"), ("ברא", " ", "BR>[", "sg"),
                 ("אלוהים", " ", ">LHJM/", "pl")]),
    ("Gen.1.2", [("ו", "", "W", "NA"), ("ה", "", "H", "NA"), ("ארץ", " ", ">RY/", "sg"),
                 ("היתה", " ", "HJH[", "sg"), ("תהו", " ", "THW/", "sg"),
                 ("ויאמר", " ", "W", "NA"), ("אלהים", " ", ">LHJM/", "pl"),
                 ("יהי", " ", "HJH[", "sg"), ("אור", " ", ">WR/", "sg")]),
    ("Gen.5.3", [("ו", "", "W", "NA"), ("יחי", " ", "XJH[", "sg"), ("אדם", " ", ">DM/", "sg"),
                 ("שׁלשׁים", " ", "CLC/", "pl"), ("ו", "", "W", "NA"), ("מאת", " ", "M>H/", "sg"),
                 ("שׁנה", " ", "CNH/", "sg")]),
]  # fmt: skip
# a scroll: (osis, [(letters, after, reconstructed letters)])
DSS = [("Isa.1.1", [("חזון", " ", ""), ("ישעיה", " ", "יה"), ("בנ", " ", ""), ("אמוצ", " ", ""),
                    ("הנביא", " ", "")])]  # fmt: skip


def write_tf(path, feature, values, edge=False):
    lines = ["@edge" if edge else "@node", "@valueType=str", ""]
    lines += [f"{n}\t{v}" for n, v in sorted(values.items())]
    path.joinpath(f"{feature}.tf").write_text("\n".join(lines) + "\n", "utf-8")


def tf_dataset(path, verses, scroll=None):
    """A Text-Fabric dataset with letters as slots: words, verses (and a scroll or books)."""
    path.mkdir(parents=True)
    signs, words, verse_nodes = [], [], []
    for osis, ws in verses:
        first = len(signs) + 1
        for w in ws:
            start = len(signs) + 1
            signs.extend(w[0])
            words.append((start, len(signs), osis, w))
        verse_nodes.append((first, len(signs), osis))
    n = len(signs)
    nodes: dict[str, list] = {"sign": list(range(1, n + 1))}
    names_ = ("book", "chapter", "verse", "g_cons_utf8", "trailer", "lex", "nu", "glyph", "after",
              "rec", "unc", "scroll")  # fmt: skip
    slots, feats = {}, {k: {} for k in names_}
    nxt = n + 1
    if scroll is None:
        books = list(dict.fromkeys(o.split(".")[0] for o, _ in verses))
        names = {"Gen": "Genesis"}
        for b in books:
            vs = [v for v in verse_nodes if v[2].startswith(b + ".")]
            slots[nxt] = f"{vs[0][0]}-{vs[-1][1]}"
            feats["book"][nxt] = names[b]
            nodes.setdefault("book", []).append(nxt)
            nxt += 1
        for b, c in dict.fromkeys(tuple(v[2].split(".")[:2]) for v in verse_nodes):
            vs = [v for v in verse_nodes if v[2].startswith(f"{b}.{c}.")]
            slots[nxt] = f"{vs[0][0]}-{vs[-1][1]}"
            feats["chapter"][nxt] = c
            nodes.setdefault("chapter", []).append(nxt)
            nxt += 1
        for a, b, osis in verse_nodes:
            slots[nxt] = f"{a}-{b}"
            feats["verse"][nxt] = osis.split(".")[2]
            nodes.setdefault("verse", []).append(nxt)
            nxt += 1
    else:
        slots[nxt] = f"1-{n}"
        feats["scroll"][nxt] = scroll
        nodes["scroll"] = [nxt]
        nxt += 1
    for a, b, osis, w in words:
        slots[nxt] = f"{a}-{b}"
        nodes.setdefault("word", []).append(nxt)
        if scroll is None:
            _, trailer, lex, nu = w
            feats["g_cons_utf8"][nxt], feats["lex"][nxt], feats["nu"][nxt] = w[0], lex, nu
            if trailer:
                feats["trailer"][nxt] = trailer
        else:
            letters, after, rec = w
            bk, c, v = osis.split(".")
            feats["book"][nxt], feats["chapter"][nxt], feats["verse"][nxt] = "Is", c, v
            if after:
                feats["after"][nxt] = after
            for k, ch in enumerate(letters):
                feats["glyph"][a + k] = ch
                if ch in rec:
                    feats["rec"][a + k] = "1"
        nxt += 1
    lines = ["@node", "@valueType=str", ""]
    lines += [f"{v[0]}-{v[-1]}\t{k}" if len(v) > 1 else f"{v[0]}\t{k}" for k, v in nodes.items()]
    path.joinpath("otype.tf").write_text("\n".join(lines) + "\n", "utf-8")
    write_tf(path, "oslots", slots, edge=True)
    for k, v in feats.items():
        write_tf(path, k, v)


def corpus(tmp_path):
    proc, art, raw = (tmp_path / d for d in ("processed", "art", "raw"))
    for d in (proc, art / "sequences", art / "chronology"):
        d.mkdir(parents=True)
    pd.DataFrame(
        [(v, b, c, n, [o]) for v, (b, c, n, o, _) in MT.items()],
        columns=["verse_id", "book_id", "chapter", "verse", "oshb_osis"],
    ).to_parquet(proc / "verses.parquet")
    pd.DataFrame(
        [(v, i, w, i) for v, (*_, ws) in MT.items() for i, w in enumerate(ws)],
        columns=["verse_id", "idx", "surface", "display_idx"],
    ).to_parquet(proc / "words.parquet")
    pd.DataFrame([{"seq_id": 0, "q": 0.001, "same_chapter": False,
                   "pairs": json.dumps([[1, 2, 1.0]])}]).to_parquet(
        art / "sequences" / "verse.parquet")  # fmt: skip
    pd.DataFrame({"event": ["adam", "seth"], "year": [0, 130], "used": [True, True]}).to_parquet(
        art / "chronology" / "events.parquet"
    )
    tf_dataset(raw / "samaritan", SP)
    tf_dataset(raw / "scrolls", DSS, scroll="1Q1")
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art),
                    "data_raw": str(raw)}  # fmt: skip
    cfg["chronology"] = {
        **cfg["chronology"],
        "events": [["adam", None, None], ["seth", "adam", "Genesis 5:3", 1]],
    }
    cfg["witnesses"] = {
        **cfg["witnesses"], "shifts": 19,
        "known": [{"witness": "sp", "ref": "Genesis 1:2", "plus": 4},
                  {"witness": "sp", "ref": "Genesis 1:2", "reads": "אור"},
                  {"witness": "1Q1", "ref": "Isaiah 1:1", "plus": 1}],
        "chronology_known": {"seth": 130},
    }  # fmt: skip
    return cfg


def test_run_on_made_up_witnesses(tmp_path):
    cfg = corpus(tmp_path)
    out = run_witnesses(cfg, log=lambda _: None)
    v = pd.read_parquet(out / "verses.parquet").set_index(["witness", "verse_id"])
    # the Samaritan: prefixes joined into words; a spelling; a plus of four
    g1 = v.loc[("sp", 0)]
    assert [w["t"] for w in json.loads(g1.words)] == ["בראשית", "ברא", "אלוהימ"]
    assert (g1.same, g1.spelling, g1.variants) == (2, 1, 0)
    g2 = v.loc[("sp", 1)]
    assert (g2.added, g2.plus, g2.variants) == (4, 4, 4)
    # the scroll: ישעיה has reconstructed letters, so its spelling is no evidence
    i1 = v.loc[("1Q1", 3)]
    toks = json.loads(i1.words)
    assert [t["r"] for t in toks] == [True, False, True, True, True]
    assert (i1.n_read, i1.spelling, i1.added, i1.plus) == (4, 0, 1, 1)
    assert [t["mt"] for t in toks][:4] == [0, 1, 2, 3]
    ch = pd.read_parquet(out / "changes.parquet")
    assert ch[ch.witness == "1Q1"][["op", "w_text"]].values.tolist() == [["added", "הנביא"]]
    # the Samaritan chronology: Seth at Adam's 130, read from its own words
    c = pd.read_parquet(out / "chronology.parquet").set_index("event")
    assert (c.sp_year["seth"], c.mt_year["seth"], c.name["seth"]) == (130, 130, "שת")
    meta = json.loads((out / "witnesses.meta.json").read_text("utf-8"))
    assert [k["found"] for k in meta["known"]] == [True, True, True] and meta["known_holds"]
    assert meta["sp_pluses"] == 1 and meta["parallel_verses"] == 2
    assert meta["samaritan"]["verses"] == 3 and meta["scrolls"]["scrolls"] == 1
    s = pd.read_parquet(out / "scrolls.parquet")
    assert s[["scroll", "read", "pluses", "book_id"]].values.tolist() == [["1Q1", 4, 0, 11]]


def test_missing_datasets_fail_fast(tmp_path):
    cfg = corpus(tmp_path)
    (tmp_path / "raw" / "scrolls" / "rec.tf").unlink()
    with pytest.raises(FileNotFoundError, match="--only witnesses"):
        run_witnesses(cfg, log=lambda _: None)


# --- the API over the fixture DB -----------------------------------------------------------------


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_api_witnesses(client):
    r = client.get("/api/witnesses").json()
    assert (r["holds"], r["known_holds"], r["samaritan"]["added"]) == (False, True, 4)
    assert [k["verse"]["verse_id"] for k in r["known"]] == [1, 5]
    assert (r["chronology"][2]["sp_year"], r["chronology"][2]["mt_year"]) == (1307, 1656)
    assert r["chronology"][1]["ref"] and r["chronology"][0]["ref"] is None
    assert [s["scroll"] for s in r["scroll_rows"]] == ["1Qisaa", "4Q51"]
    assert {(b["kind"], b["book_id"]) for b in r["books"]} == {("sp", 0), ("scroll", 0),
                                                                ("scroll", 1)}  # fmt: skip


def test_api_witnesses_pluses(client):
    sp = client.get("/api/witnesses/pluses").json()
    assert (sp["kind"], sp["total"], sp["items"][0]["verse"]["verse_id"]) == ("sp", 1, 1)
    sc = client.get("/api/witnesses/pluses", params={"kind": "scroll"}).json()
    assert [(x["witness"], x["plus"]) for x in sc["items"]] == [("1Qisaa", 3)]
    one = client.get("/api/witnesses/pluses", params={"kind": "sp", "book": 1}).json()
    assert one["total"] == 0
    assert client.get("/api/witnesses/pluses", params={"kind": "x"}).status_code == 422


def test_api_witnesses_unit(client):
    r = client.get("/api/witnesses/unit", params={"unit": "c:0:1"}).json()
    assert (r["unit_id"], r["witnesses"], r["total"]) == ("c:0:1", ["sp", "4Q51"], 3)
    v2 = next(x for x in r["items"] if x["verse"]["verse_id"] == 2)
    assert [x["witness"] for x in v2["readings"]] == ["sp", "4Q51"]
    sp, scroll = v2["readings"]
    assert sp["missing"] == [2] and [w["op"] for w in sp["words"]] == ["same", "substitution"]
    assert scroll["words"][1]["r"] is False
    assert client.get("/api/witnesses/unit", params={"unit": "c:9:9"}).status_code == 404


def test_api_reader_and_dossier(client):
    r = client.get("/api/reader/c:0:1").json()
    assert r["computed"]["witnesses"] is True
    by = {v["verse_id"]: v["witnesses"] for v in r["verses"]}
    assert by[1] == {"sp": 4} and by[2] == {"sp": 2, "scrolls": 1, "scroll_variants": 0}
    assert by[0] == {"sp": 0}
    d = client.get("/api/dossier/c:0:1").json()
    (e,) = [x for x in d["entries"] if x["kind"] == "witnesses"]
    assert (e["computed"], e["count"], e["key"], e["total"]) == (True, 6, "sp", 3)


def test_api_findings(client):
    f = {x["key"]: x for x in client.get("/api/findings").json()["items"]}
    assert f["witnesses_parallel"]["verdict"] == "fails"
    assert f["witnesses_known"]["values"] == {"found": 2, "of": 2, "flood": 1307}
