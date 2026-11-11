"""The law codes side by side (DESIGN.md §16.93, D155): a verb's person, a law's form, the links
and the matching, the stage on a toy corpus, the API, the export, the dossier and Findings."""

from __future__ import annotations

import json

import pandas as pd
from fastapi.testclient import TestClient

from bsim.analysis.laws import law_form, link_laws, match_laws, run_laws, verb_person
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.data.canon import BY_OSIS
from bsim.fixture import fixture_encoder

LC = load_config()["laws"]


def test_verb_person():
    assert verb_person("Vqi2ms") == "2ms" and verb_person("Vqv2mp") == "2mp"
    assert verb_person("VNi3ms") == "3" and verb_person("Vqw3fs") == "3"
    assert verb_person("Vqrmsa") is None  # a participle has no person
    assert verb_person("Vqi1cs") is None and verb_person("Ncmsa") is None


def words(rows):
    return pd.DataFrame(rows, columns=["verse_id", "idx", "lemma", "main"])


def test_law_form():
    opens = {(0, 0), (1, 0)}
    # כי תקנה עבד: casuistic; its 2ms verb is the address
    w = words([(0, 0, "3588a", "C"), (0, 1, "7069", "Vqi2ms"), (0, 2, "5650", "Ncmsa")])
    f = law_form(w, opens, 0, LC["form"])
    assert f["form"] == "casuistic" and f["address"] == "2ms" and f["v2ms"] == 1
    # כי נורא הוא: no yiqtol after it, so not a protasis; לא תגנב: apodictic
    w = words([(0, 0, "3588a", "C"), (0, 1, "3372", "Vnrmsa"), (1, 0, "3808", "Tn"),
               (1, 1, "1589", "Vqi2ms")])  # fmt: skip
    assert law_form(w, opens, 0, LC["form"])["form"] == "apodictic"
    # מות יומת
    w = words([(0, 0, "5221", "Vhrmsa"), (0, 1, "4191", "Vqa"), (0, 2, "4191", "VHi3ms")])
    f = law_form(w, opens, 0, LC["form"])
    assert f["form"] == "apodictic" and not f["casuistic"] and f["address"] == "3"
    # a כי opening a clause past the first `opening` verses is not the law's protasis
    w = words([(5, 0, "3588a", "C"), (5, 1, "7069", "Vqi2ms")])
    assert law_form(w, {(5, 0)}, 0, LC["form"])["form"] == "other"


def test_link_and_match():
    topk = pd.DataFrame({
        "src_id": ["v:0", "v:2", "v:1", "v:0", "v:4", "v:4"],
        "rank": [1, 1, 1, 30, 1, 2],
        "tgt_id": ["v:2", "v:0", "v:3", "v:3", "v:0", "v:1"],
        "score": [0.03, 0.02, 0.01, 0.5, 0.01, 0.01],
    })  # fmt: skip
    law_of = {0: 1, 1: 1, 2: 2, 3: 2, 4: 3}
    code_of = {1: "covenant", 2: "deuteronomic", 3: "deuteronomic"}
    links = link_laws(topk, law_of, code_of, 20)
    # both directions of v0-v2 one link (the higher score); rank 30 left out
    assert links[(1, 2)] == {(0, 2): 0.03, (1, 3): 0.01}
    assert links[(1, 3)] == {(0, 4): 0.01, (1, 4): 0.01}
    matched = match_laws(links, {1: 2, 2: 2, 3: 1}, code_of, {**LC, "best": 1})
    # law 1's best in Deuteronomy is law 3 (0.02 / √2), and law 2's best in the Covenant Code is
    # law 1: both pairs matched
    assert set(matched) == {(1, 2), (1, 3)}
    assert set(match_laws(links, {1: 2, 2: 2, 3: 1}, code_of, {**LC, "min_links": 3})) == set()


def toy(tmp_path):
    """Exod 21:2-3 and Deut 15:12-13, the release of a slave twice over."""
    proc, art = tmp_path / "processed", tmp_path / "artifacts"
    proc.mkdir()
    (art / "topk" / "verse").mkdir(parents=True)
    ex, dt = BY_OSIS["Exod"].book_id, BY_OSIS["Deut"].book_id
    pd.DataFrame(
        {"verse_id": range(4), "book_id": [ex, ex, dt, dt], "chapter": [21, 21, 15, 15],
         "verse": [2, 3, 12, 13],
         "ref": ["Exodus 21:2", "Exodus 21:3", "Deuteronomy 15:12", "Deuteronomy 15:13"]}
    ).to_parquet(proc / "verses.parquet")  # fmt: skip
    pd.DataFrame(
        {"unit_id": ["s:0", "s:1"], "unit_type": "pericope", "label_en": "", "label_he": "",
         "book_id": [ex, dt], "start_verse_id": [0, 2], "end_verse_id": [1, 3], "n_verses": 2,
         "marker": None}
    ).to_parquet(proc / "units.parquet")  # fmt: skip
    rows = [
        (0, 0, "כִּי", "3588 a", ["3588a"], "HC"), (0, 1, "תִקְנֶה", "7069", ["7069"], "HVqi2ms"),
        (0, 2, "עֶבֶד", "5650", ["5650"], "HNcmsa"), (0, 3, "עִבְרִי", "5680", ["5680"], "HAgmsa"),
        (1, 0, "אִם", "518", ["518"], "HC"), (1, 1, "בְּגַפּוֹ", "b/1610", ["1610"], "HR/Ncmsc/Sp3ms"),
        (1, 2, "יָבֹא", "935", ["935"], "HVqi3ms"),
        (2, 0, "כִּי", "3588 a", ["3588a"], "HC"), (2, 1, "יִמָּכֵר", "4376", ["4376"], "HVNi3ms"),
        (2, 2, "אָחִיךָ", "251", ["251"], "HNcmsc/Sp2ms"),
        (2, 3, "הָעִבְרִי", "d/5680", ["5680"], "HTd/Agmsa"),
        (3, 0, "לֹא", "3808", ["3808"], "HTn"),
        (3, 1, "תְשַׁלְּחֶנּוּ", "7971", ["7971"], "HVpi2ms/Sp3ms"),
    ]  # fmt: skip
    w = pd.DataFrame(
        rows, columns=["verse_id", "idx", "surface", "lemma", "content_lemmas", "morph"]
    )
    w["display_idx"] = w.idx
    w.to_parquet(proc / "words.parquet")
    pd.DataFrame(
        {"clause": range(1, 5), "verse_id": range(4), "words": [[0, 1, 2, 3], [0, 1, 2],
                                                                [0, 1, 2, 3], [0, 1]]}
    ).to_parquet(proc / "syntax_clauses.parquet")  # fmt: skip
    pd.DataFrame(
        {"unit_type": "verse", "src_id": ["v:0", "v:1", "v:2"], "rank": 1,
         "tgt_id": ["v:2", "v:3", "v:0"], "score": [0.03, 0.02, 0.03]}
    ).to_parquet(art / "topk" / "verse" / "fused.parquet")  # fmt: skip
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art)}
    cfg["laws"] = {**LC, "codes": {"covenant": ["Exodus 21:2-3"],
                                   "deuteronomic": ["Deuteronomy 15:12-13"]},
                   "known": {"slave release": ["Exodus 21:2", "Deuteronomy 15:12"]}}  # fmt: skip
    return cfg


def test_run(tmp_path):
    cfg = toy(tmp_path)
    run_laws(cfg, log=lambda _: None)
    out = tmp_path / "artifacts" / "laws"
    laws = pd.read_parquet(out / "laws.parquet")
    assert laws[["code", "first_vid", "last_vid", "form"]].values.tolist() == [
        ["covenant", 0, 1, "casuistic"], ["deuteronomic", 2, 3, "casuistic"]]  # fmt: skip
    assert bool(laws.apodictic[1]) and laws.address.tolist() == ["mixed", "mixed"]
    p = pd.read_parquet(out / "pairs.parquet")
    assert p[["a", "b", "links", "a_first", "a_last", "b_first", "b_last"]].values.tolist() == [
        [1, 2, 2, 0, 1, 2, 3]]  # fmt: skip
    assert p.known[0] == "slave release" and p.same[0] == 1 and 0 < p.kept[0] < 1  # כי = כי
    marks = pd.read_parquet(out / "marks.parquet")
    assert set(marks.side) == {"a", "b"} and "same" not in set(marks.op)
    meta = json.loads((out / "laws.meta.json").read_text("utf-8"))
    assert (meta["known_found"], meta["known_total"], meta["known_holds"]) == (1, 1, True)
    codes = pd.read_parquet(out / "codes.parquet")
    assert codes.code.tolist() == ["covenant", "deuteronomic"] and codes.casuistic.tolist() == [
        1,
        1,
    ]


def test_api_export_dossier_findings(built):
    cfg, _ = built  # the fixture's made-up run
    c = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    r = c.get("/api/laws").json()
    assert (r["laws"], r["pairs"], r["known_found"], r["known_holds"]) == (2, 1, 1, True)
    assert [x["code"] for x in r["codes"]] == ["covenant", "deuteronomic"]
    ls = c.get("/api/laws/list", params={"code": "covenant"}).json()
    assert (
        ls["total"] == 1 and ls["items"][0]["form"] == "apodictic" and ls["items"][0]["pairs"] == 1
    )
    assert c.get("/api/laws/list", params={"code": "nope"}).status_code == 422
    p = c.get("/api/laws/pairs").json()
    item = p["items"][0]
    assert (
        p["total"] == 1 and item["known"] == "slave release" and item["a"]["code"] == "deuteronomic"
    )
    assert item["ops"]["same"] == 4 and item["a_span"] == item["a"]["first_label"]
    assert c.get("/api/laws/pairs", params={"code": "holiness"}).json()["total"] == 0
    assert c.get("/api/laws/pairs", params={"law": 2, "known": True}).json()["total"] == 1
    s = c.get("/api/laws/pair/1").json()
    assert [x["verse"]["verse_id"] for x in s["a"]] == [3] and s["a"][0]["marks"] == {
        "0": "substitution"
    }
    assert s["b"][0]["marks"] == {"1": "added"}
    assert c.get("/api/laws/pair/99").status_code == 404
    csv = c.get("/api/export/law-pairs.csv").text
    assert "slave release" in csv and c.get("/api/export/laws.csv").status_code == 200
    d = c.get("/api/dossier/c:0:2").json()
    assert next(e for e in d["entries"] if e["kind"] == "laws")["count"] == 1
    f = {x["key"]: x for x in c.get("/api/findings").json()["items"]}
    assert f["laws"]["verdict"] == "holds" and f["laws"]["values"]["known"] == 1
    pub = {**cfg, "serve": {**cfg["serve"], "personal": False}}
    assert (
        TestClient(create_app(pub, encoder=fixture_encoder, log=lambda _: None))
        .get("/api/laws/pair/1")
        .status_code
        == 200
    )
