"""The forms of prophetic speech (DESIGN.md §16.92, D154): the morph parts, the cover of a
passage, the joining of findings, every form on a toy corpus, the API, the reader and Findings."""

from __future__ import annotations

import json

import pandas as pd
from fastapi.testclient import TestClient

from bsim.analysis.prophetic import cover, is_kind, merge, morph_parts, run_prophetic
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.data.canon import BY_OSIS
from bsim.fixture import fixture_encoder

PC = load_config()["prophetic"]
ISA = BY_OSIS["Isa"].book_id


def test_morph_parts():
    assert morph_parts("HC/Vqw3ms") == ("Vqw3ms", "")
    assert morph_parts("HR/Ncmsc/Sp2mp") == ("Ncmsc", "Sp2mp")
    assert morph_parts("HTd/Ncbsa") == ("Ncbsa", "")
    assert morph_parts("HR/Ti") == ("Ti", "")  # במה: the interrogative after the preposition
    assert morph_parts("HTo/Sp2ms") == ("To", "Sp2ms")
    assert morph_parts(None) == ("", "")


def test_is_kind():
    assert is_kind("Vhrmpc", "V-participle") and is_kind("Vqsmsa", "V-participle")
    assert is_kind("Vqv2mp", "V-imperative") and not is_kind("Vqp3cp", "V-imperative")
    assert is_kind("Ncmsa", "N") and is_kind("Aamsa", "A") and not is_kind("Tj", "N")


def test_cover():
    assert cover(10, 19, [(8, 11), (15, 15)]) == 0.3
    assert cover(10, 19, []) == 0.0


def test_merge():
    book = {v: 0 for v in range(10)} | {v: 1 for v in range(10, 20)}
    spans = [
        (3, 5, {"dispute": True, "witnesses": False, "words": [(3, 0)]}),
        (5, 6, {"dispute": False, "witnesses": True, "words": [(6, 2), (3, 0)]}),
        (8, 9, {"dispute": True, "witnesses": False, "words": [(8, 1)]}),
        (10, 11, {"dispute": True, "witnesses": False, "words": [(10, 1)]}),
    ]
    out = merge(spans, book)
    # 3-5 and 5-6 overlap: one finding, its flags or-ed; 8-9 is apart; 10-11 is another book
    assert [(a, b) for a, b, _ in out] == [(3, 6), (8, 9), (10, 11)]
    assert out[0][2]["dispute"] and out[0][2]["witnesses"]
    assert out[0][2]["words"] == [(3, 0), (6, 2)]


def toy(tmp_path):
    """Isaiah 1:1-6, one form a verse: כה אמר יהוה; הוי מגיעי; משא בבל; שמעו שמים … ארץ; לך
    ואמרת (God speaking); אהה (the one sent)."""
    proc = tmp_path / "processed"
    proc.mkdir()
    words = [
        (0, 0, ["3541"], "HD"), (0, 1, ["559"], "HVqp3ms"), (0, 2, ["3068"], "HNp"),
        (1, 0, ["1945"], "HTj"), (1, 1, ["5060"], "HVhrmpc"), (1, 2, ["1004b"], "HNcmsa"),
        (2, 0, ["4853b"], "HNcmsc"), (2, 1, ["894"], "HNp"),
        (3, 0, ["8085"], "HVqv2mp"), (3, 1, ["8064"], "HNcmpa"), (3, 2, ["776"], "HNcbsa"),
        (4, 0, ["3212"], "HVqv2ms"), (4, 1, ["559"], "HC/Vqq2ms"),
        (5, 0, ["559"], "HC/Vqw1cs"), (5, 1, ["162"], "HTj"),
    ]  # fmt: skip
    pd.DataFrame(words, columns=["verse_id", "idx", "content_lemmas", "morph"]).to_parquet(
        proc / "words.parquet"
    )
    clauses = [
        (1, 0, [0, 1, 2], "xQt0", None), (2, 1, [0, 1, 2], "Ptcp", None),
        (3, 2, [0, 1], "Ellp", None), (4, 3, [0, 1, 2], "ZIm0", None),
        (5, 4, [0, 1], "ZIm0", "3068"), (6, 5, [0], "Way0", None), (7, 5, [1], "Voct", None),
    ]  # fmt: skip
    pd.DataFrame(clauses, columns=["clause", "verse_id", "words", "typ", "speaker"]).to_parquet(
        proc / "syntax_clauses.parquet"
    )
    pd.DataFrame(
        {"verse_id": range(6), "book_id": ISA, "chapter": 1, "verse": range(1, 7),
         "ref": [f"Isaiah 1:{i}" for i in range(1, 7)]}
    ).to_parquet(proc / "verses.parquet")  # fmt: skip
    pd.DataFrame(
        {"unit_id": ["s:0", "s:1", "s:2"], "unit_type": "pericope", "label_en": "",
         "label_he": "", "book_id": ISA, "start_verse_id": [0, 2, 4], "end_verse_id": [1, 3, 5],
         "n_verses": 2, "marker": None}
    ).to_parquet(proc / "units.parquet")  # fmt: skip
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "data_raw": str(tmp_path / "raw"),
                    "artifacts": str(tmp_path / "artifacts")}  # fmt: skip
    known = {"woe": ["Isaiah 1:2"], "nations": ["Isaiah 1:3-4"], "call": ["Isaiah 1:5-6"],
             "lawsuit": ["Isaiah 1:1"]}  # fmt: skip
    cfg["prophetic"] = {**PC, "known": known}
    return cfg


def test_run(tmp_path):
    cfg = toy(tmp_path)
    run_prophetic(cfg, log=lambda _: None)
    out = tmp_path / "artifacts" / "prophetic"
    it = pd.read_parquet(out / "items.parquet")
    spans = {f: (a, b) for f, a, b in zip(it.form, it.first_vid, it.last_vid, strict=True)}
    assert spans == {"messenger": (0, 0), "woe": (1, 1), "nations": (2, 3), "lawsuit": (3, 3),
                     "call": (4, 5)}  # fmt: skip
    d = {f: json.loads(x) for f, x in zip(it.form, it.detail, strict=True)}
    assert d["messenger"] == {"kind": "thus"} and d["woe"] == {"next": "5060"}
    assert d["nations"]["heading"] and d["nations"]["names"] == [{"lemma": "894", "he": "", "n": 1}]
    assert d["lawsuit"] == {"dispute": False, "witnesses": True}
    assert d["call"] == {"objection": True, "reassurance": False}
    assert it.unit_id.tolist() == ["s:0", "s:0", "s:1", "s:1", "s:2"]
    meta = json.loads((out / "prophetic.meta.json").read_text("utf-8"))
    k = meta["known"]
    assert k["woe"]["holds"] and k["nations"]["holds"] and k["call"]["holds"]
    assert not k["lawsuit"]["holds"] and not meta["known_holds"]  # Isaiah 1:1 has no lawsuit
    assert (meta["known_found"], meta["known_total"]) == (3, 4)
    assert set(it.form[it.known]) == {"woe", "nations", "call"}
    marks = pd.read_parquet(out / "words.parquet")
    assert marks[marks.verse_id == 4].idx.tolist() == [0, 1]  # לך ואמרת
    assert set(marks.form) == {"messenger", "woe", "nations", "lawsuit", "call"}


def test_rules_hold_back(tmp_path):
    """הוי אחי is mourning; a commission said by a man BHSA names is not God's; a call to hear
    with nothing else is no lawsuit."""
    cfg = toy(tmp_path)
    proc = tmp_path / "processed"
    w = pd.read_parquet(proc / "words.parquet")
    swap = {(1, 1): (["251"], "HNcmsc"), (3, 1): (["1"], "HNcmsa"), (3, 2): (["2"], "HNcmsa")}
    for (v, i), (lem, morph) in swap.items():  # הוי אחי; שמעו with neither heaven nor earth
        k = w.index[(w.verse_id == v) & (w.idx == i)][0]
        w.at[k, "content_lemmas"], w.at[k, "morph"] = lem, morph
    w.to_parquet(proc / "words.parquet")
    c = pd.read_parquet(proc / "syntax_clauses.parquet")
    c.loc[c.verse_id == 4, "speaker"] = "4872"  # Moses
    c.to_parquet(proc / "syntax_clauses.parquet")
    run_prophetic(cfg, log=lambda _: None)
    it = pd.read_parquet(tmp_path / "artifacts" / "prophetic" / "items.parquet")
    assert set(it.form) == {"messenger", "nations"}


def test_api_reader_and_findings(built):
    cfg, _ = built  # the fixture's made-up run
    c = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    r = c.get("/api/prophetic").json()
    assert r["counts"]["woe"] == 1 and r["known_total"] == 3 and not r["known_holds"]
    assert r["books"] == [{"book_id": 0, "counts": {"messenger": 1, "nations": 1, "woe": 1}}]
    p = c.get("/api/prophetic/items").json()
    assert p["total"] == 3 and [x["form"] for x in p["items"]] == ["nations", "woe", "messenger"]
    nat = p["items"][0]
    assert nat["detail"]["names"][0]["he"] == "בָּבֶל" and nat["detail"]["heading"]
    assert [v["verse_id"] for v in nat["verses"]] == [0, 1, 2] and nat["marks"] == {}
    woe = c.get("/api/prophetic/items", params={"form": "woe"}).json()["items"]
    assert len(woe) == 1 and woe[0]["known"] and woe[0]["marks"] == {"1": [0, 1]}
    assert c.get("/api/prophetic/items", params={"known": True}).json()["total"] == 1
    assert c.get("/api/prophetic/items", params={"form": "nope"}).status_code == 422
    rd = c.get("/api/reader/c:0:1").json()
    assert rd["computed"]["prophetic"] is True
    marks = {v["verse_id"]: v["prophetic"] for v in rd["verses"]}
    assert set(marks[1].values()) == {"woe"} and set(marks[2].values()) == {"messenger"}
    assert marks[0] == {}
    f = {x["key"]: x for x in c.get("/api/findings").json()["items"]}
    assert f["prophetic"]["verdict"] == "fails" and f["prophetic"]["values"]["known"] == 2
    pub = {**cfg, "serve": {**cfg["serve"], "personal": False}}
    assert (
        TestClient(create_app(pub, encoder=fixture_encoder, log=lambda _: None))
        .get("/api/prophetic")
        .status_code
        == 200
    )
