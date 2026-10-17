"""The gazetteer (`data/geo.py`, `bsim places`, `/places`, DESIGN.md §16.56)."""

import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.places import (
    ob_base,
    openbible_match,
    resolve_mentions,
    run_places,
    tipnr_key,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.data.geo import (
    AncientPlace,
    Identification,
    TipnrName,
    TipnrRecord,
    read_openbible,
    read_tipnr,
    step_ref,
)
from bsim.fixture import fixture_encoder

TIPNR = "\t".join(["TIPNR header", "", ">"]) + "\n" + "\n".join(
    [
        "$========== PLACE\t",
        "Abel@1Sa.6.18=H0059G\tWord sometimes translated as a place\t\t\thttps://www.google.com/maps/@,14z",
        "– Named\tstone|Abel@1Sa.6.18\tH0059G«H0059=אָבֵל\tstone =ESV\t1Sa.6.18\t\t",
        "– Total\tAbel\tAbel\tH0059G\t1Sa.6.18;\t1",
        "$========== PLACE\t",
        "Abel-beth-maacah@2Sa.20.14-2Ch=H0062\tAbel-beth-maacah\t\t\t"
        "https://www.google.com/maps/@33.268526,35.578046,14z\t>\t#A location\tPlace",
        "– Named\tAbel-beth-maacah@2Sa.20.14-2Ch\tH0062«H0062=אָבֵל בֵּית מַעֲכָה, אָבֵל מַעֲכָה\tAbel\t"
        "2Sa.20.14; 2Sa.20.15; 1Ki.15.20\t\t",
        "– Named\tAbel|Abel-beth-maacah@2Sa.20.14-2Ch\tH0059H«H0059=אָבֵל\tAbel\t2Sa.20.18\t",
        "– Named\tAram-zobah|Abel@x\tH0760«H0760=אֲרַם צוֹבָה\tAram-zobah\tPsa.60.0; LXX.Num.1.1\t",
        "$========== PERSON(s)\t",
        "Tekoa@1Ch.2.24=H8620\tson of Ashhur\t\t",
        "– Named\tTekoa@1Ch.2.24\tH8620«H8620=תְּקוֹעַ\tTekoa\t1Ch.2.24\t",
    ]
)  # fmt: skip


def test_read_tipnr(tmp_path):
    path = tmp_path / "tipnr.txt"
    path.write_text(TIPNR, encoding="utf-8")
    recs = read_tipnr(path)
    assert [(r.uid, r.category) for r in recs] == [
        ("Abel@1Sa.6.18", "PLACE"),
        ("Abel-beth-maacah@2Sa.20.14-2Ch", "PLACE"),
        ("Tekoa@1Ch.2.24", "PERSON"),
    ]
    abel, abm, _ = recs
    assert abel.lonlat is None and abm.lonlat == (35.578046, 33.268526)
    assert abm.openbible == "Abel-beth-maacah"
    assert [(n.strong, n.dstrong, n.refs) for n in abm.names] == [
        (62, "H0062", [(8, 20, 14), (8, 20, 15), (9, 15, 20)]),
        (59, "H0059H", [(8, 20, 18)]),
        (760, "H0760", [(26, 60, 1)]),  # a psalm title's verse 0; the Septuagint left out
    ]
    assert abm.names[0].hebrew == "אָבֵל בֵּית מַעֲכָה"


def test_step_ref():
    assert step_ref("Jdg.7.22") == (6, 7, 22) and step_ref("Psa.3.0") == (26, 3, 1)
    assert step_ref("Mat.1.1") is None and step_ref("LXX.Num.1.1") is None


def test_read_openbible(tmp_path):
    def ident(lonlat, votes):
        return {"class": "settlement", "score": {"vote_total": votes},
                "resolutions": [{"lonlat": lonlat}]}  # fmt: skip

    rows = [
        {"id": "a1", "friendly_id": "Aroer 2", "types": ["settlement"],
         "linked_data": {"s3b25cf": {"id": "Aroer@Num.32.34"}},
         "verses": [{"osis": "Num.32.34"}, {"osis": "Matt.1.1"}],
         "identifications": [ident("35.8,31.9", 48), ident("35.9,31.92", 50),
                             {"class": "x", "score": {"vote_total": 900}, "resolutions": []}]},
        {"id": "a2", "friendly_id": "Bethel 1", "types": [],
         "linked_data": {"s3b25cf": {"ids": ["Bethel@Gen.12.8", "Bethel@Jos.12.16"]}},
         "identifications": []},
    ]  # fmt: skip
    path = tmp_path / "ancient.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    a, b = read_openbible(path)
    assert a.tipnr == ["Aroer@Num.32.34"] and a.refs == [(3, 32, 34)]
    assert [(i.lon, i.score) for i in a.identifications] == [(35.9, 50), (35.8, 48)]  # best first
    assert b.tipnr == ["Bethel@Gen.12.8", "Bethel@Jos.12.16"] and b.best is None


def rec(uid, category, strong, refs):
    return TipnrRecord(uid, category, names=[TipnrName(strong, f"H{strong}", "", refs)])


def test_resolve_mentions():
    vid_of = {(0, 1, v): v - 1 for v in range(1, 31)} | {(0, 2, 1): 30}
    records = [
        rec("Abel-stone", "PLACE", 59, [(0, 1, 2)]),
        rec("Abel-city", "PLACE", 59, [(0, 1, 20), (0, 1, 21)]),
        rec("Tekoa-person", "PERSON", 8620, [(0, 1, 5)]),
        rec("Tekoa", "PLACE", 8620, [(0, 1, 25)]),
        rec("Dan", "PLACE", 1835, [(0, 1, 3)]),
    ]
    mentions = pd.DataFrame(
        [("59", 1), ("59", 21), ("59", 10), ("8620", 4), ("8620", 24), ("1835", 29), ("9", 0)],
        columns=["lemma", "verse_id"],
    )
    r = resolve_mentions(mentions, records, vid_of, max_shift=3)
    assert list(zip(r.place, r.how, strict=True)) == [
        ("Abel-stone", "exact"),
        ("Abel-city", "shifted"),  # verse 21 against 1:21 (vid 20)
        (None, "none"),  # far from both Abels
        (None, "person"),
        ("Tekoa", "exact"),
        ("Dan", "only"),  # its only place, no person of that number
        (None, "none"),  # no TIPNR record
    ]


def test_openbible_match():
    assert tipnr_key("Babylon@Gen.10.10-Rev") == "Babylon@Gen.10.10"
    assert tipnr_key("Abel-beth-maacah@2Sa.20.14-2Ch") == "Abel-beth-maacah@2Sa.20.14"
    assert ob_base("Bethel 2") == "Bethel" and ob_base("Abel-beth-maacah") == "Abel-beth-maacah"

    def ob(id_, name, tipnr, refs, score):
        return AncientPlace(id_, name, ["settlement"], tipnr, refs,
                            [Identification(35.0, 31.0, score, "settlement")])  # fmt: skip

    b1 = ob("b1", "Bethel 1", ["Bethel@Gen.12.8"], [(0, 12, 8), (0, 28, 19)], 800)
    b2 = ob("b2", "Bethel 2", ["Bethel@Jos.12.16"], [(5, 12, 16)], 900)
    by_base = {"Bethel": [b1, b2]}
    by_tipnr = {"Bethel@Gen.12.8": [b1], "Bethel@Jos.12.16": [b2]}
    r = TipnrRecord("Bethel@Gen.12.8-Zec", "PLACE", openbible="Bethel_1",
                    names=[TipnrName(1008, "H1008", "", [(0, 12, 8), (0, 28, 19)])])  # fmt: skip
    assert openbible_match(r, by_base, by_tipnr) is b1  # the verses shared decide
    stray = TipnrRecord("Bethel@Jdg.1.1", "PLACE", openbible="Elsewhere",
                        names=[TipnrName(1008, "H1008", "", [(6, 1, 1)])])  # fmt: skip
    assert openbible_match(stray, by_base, by_tipnr) is None


def corpus(tmp_path):
    """Genesis 1:1-3: Abel (a place) in 1:1, Abel and Tekoa (a person) in 1:2, a sea in 1:3."""
    proc, art, raw = tmp_path / "processed", tmp_path / "art", tmp_path / "raw"
    for d in (proc, art / "entities", raw / "geo"):
        d.mkdir(parents=True)
    pd.DataFrame(
        [(0, 0, 1, 1), (1, 0, 1, 2), (2, 0, 1, 3)],
        columns=["verse_id", "book_id", "chapter", "verse"],
    ).to_parquet(proc / "verses.parquet")
    pd.DataFrame(
        [("59", "אבל"), ("8620", "תקוע"), ("3220", "ים")], columns=["lemma", "he"]
    ).to_parquet(art / "entities" / "entities.parquet")
    pd.DataFrame(
        [("59", 0), ("59", 1), ("8620", 1), ("3220", 2)], columns=["lemma", "verse_id"]
    ).to_parquet(art / "entities" / "mentions.parquet")
    pd.DataFrame(
        [(0, "59", ["003001010"], [1.0]), (1, "59", ["003001010"], [1.0]),
         (1, "8620", ["003001007"], [1.0]), (2, "3220", ["003001015", "001"], [0.5, 0.5]),
         (2, "x", ["003001015"], [1.0])],
        columns=["verse_id", "strong", "domains", "weights"],
    ).to_parquet(proc / "word_senses.parquet")  # fmt: skip
    tipnr = "\n".join([
        "header",
        "$========== PLACE\t",
        "Abel@Gen.1.1=H0059\tAbel 1\t\t\thttps://www.google.com/maps/@33.0,35.5,14z",
        "– Named\tAbel@Gen.1.1\tH0059«H0059=אָבֵל\tAbel\tGen.1.1; Gen.1.2\t",
        "– Named\tAbel@Gen.1.1\tH0063«H0063=אָבֵל הַשִּׁטִּים\tAbel-shittim\tGen.1.2\t",
        "$========== PLACE\t",
        "Sea@Gen.1.3=H3220\tGreat Sea\t\t\thttps://www.google.com/maps/@32.0,34.0,14z",
        "– Named\tSea@Gen.1.3\tH3220«H3220=הַיָּם\tSea\tGen.1.3\t",
        "– Named\tSea@Gen.1.3\tH3220«H3220=יָם\tSea\tGen.1.3\t",
        "$========== PERSON(s)\t",
        "Tekoa@Gen.1.2=H8620\tson\t\t",
        "– Named\tTekoa@Gen.1.2\tH8620«H8620=תְּקוֹעַ\tTekoa\tGen.1.2\t",
    ])  # fmt: skip
    cfg = load_config()
    (raw / "geo" / cfg["sources"]["tipnr"]["files"][0].split("/")[-1]).write_text(tipnr, "utf-8")
    ob = {"id": "a1", "friendly_id": "Abel 1", "types": ["settlement"],
          "linked_data": {"s3b25cf": {"id": "Abel@Gen.1.1"}},
          "verses": [{"osis": "Gen.1.1"}],
          "identifications": [{"class": "settlement", "score": {"vote_total": 700},
                               "resolutions": [{"lonlat": "35.6,33.1"}]},
                              {"class": "settlement", "score": {"vote_total": 350},
                               "resolutions": [{"lonlat": "35.7,33.2"}]}]}  # fmt: skip
    (raw / "geo" / "ancient.jsonl").write_text(json.dumps(ob), "utf-8")
    square = [[34, 30], [36, 30], [36, 34], [34, 34], [34, 30]]

    def fc(*features):
        return json.dumps({"type": "FeatureCollection", "features": list(features)})

    def feature(kind, coords, **props):
        return {"type": "Feature", "properties": props, "geometry": {"type": kind,
                                                                     "coordinates": coords}}

    (raw / "geo" / "ne_10m_land.geojson").write_text(fc(feature("Polygon", [square])), "utf-8")
    (raw / "geo" / "ne_10m_lakes.geojson").write_text(
        fc(feature("Polygon", [[[35.4, 31.2], [35.6, 31.2], [35.6, 31.8], [35.4, 31.2]]],
                   name="Dead Sea", scalerank=3)), "utf-8")  # fmt: skip
    (raw / "geo" / "ne_10m_rivers_lake_centerlines.geojson").write_text(
        fc(feature("LineString", [[35.5, 32.7], [35.55, 31.8]], name="Jordan", scalerank=6),
           feature("LineString", [[30, 30], [31, 31]], name="Far", scalerank=1),
           feature("LineString", [[35, 31], [35.1, 31]], name="Small", scalerank=9)),
        "utf-8")  # fmt: skip
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art),
                    "data_raw": str(raw)}  # fmt: skip
    cfg["places"] = {**cfg["places"], "sample": 2,
                     "map": {**cfg["places"]["map"], "box": [33, 29, 37, 35]}}  # fmt: skip
    return cfg


def test_run_places(tmp_path):
    cfg = corpus(tmp_path)
    out = run_places(cfg, log=lambda _: None)
    p = pd.read_parquet(out / "places.parquet")
    assert p[["place_id", "tipnr", "he", "kind", "n_verses"]].values.tolist() == [
        [1, "Abel@Gen.1.1", "אבל", "town", 2],
        [2, "Sea@Gen.1.3", "הים", "water", 1],  # SDBH's waterbody, though OpenBible has none
    ]
    abel, sea = p.to_dict("records")
    # the names the text uses for it, its own first: not Abel-shittim, whose number it never uses
    assert (json.loads(abel["names"]), json.loads(sea["names"])) == (["אבל"], ["הים", "ים"])
    assert (abel["lat"], abel["lon"], abel["score"], abel["runner_up"]) == (33.1, 35.6, 700, 0.5)
    assert (sea["coord_source"], sea["lat"], sea["score"]) == ("tipnr", 32.0, None)
    m = pd.read_parquet(out / "mentions.parquet")
    assert list(zip(m.lemma, m.verse_id, m.place_id, m.how, strict=True)) == [
        ("59", 0, 1, "exact"), ("59", 1, 1, "exact"), ("3220", 2, 2, "exact"),
    ]  # fmt: skip
    nk = pd.read_parquet(out / "name_kinds.parquet").set_index("lemma")
    assert nk.kind.to_dict() == {"3220": "water", "59": "location", "8620": "person"}
    meta = json.loads((out / "places.meta.json").read_text("utf-8"))
    assert meta["how"]["person"] == 1 and meta["places"] == 2 and meta["located_openbible"] == 1
    assert len(json.loads((out / "sample.json").read_text("utf-8"))) == 2
    bm = pd.read_parquet(out / "basemap.parquet")
    # the river outside the box and the minor one are left out
    assert bm[["layer", "name"]].values.tolist() == [
        ["land", ""], ["lakes", "Dead Sea"], ["rivers", "Jordan"],
    ]  # fmt: skip
    assert json.loads(bm.rings[2]) == [[[35.5, 32.7], [35.55, 31.8]]]
    assert meta["map"]["shapes"] == {"land": 1, "lakes": 1, "rivers": 1}
    first = (out / "places.parquet").read_bytes()
    run_places(cfg, log=lambda _: None)
    assert (out / "places.parquet").read_bytes() == first


def test_missing_sources_fail_fast(tmp_path):
    cfg = corpus(tmp_path)
    (tmp_path / "raw" / "geo" / "ancient.jsonl").unlink()
    with pytest.raises(FileNotFoundError, match="--only geo"):
        run_places(cfg, log=lambda _: None)


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_api(client):
    r = client.get("/api/places").json()
    assert r["meta"]["hand_check"] == {"site": [49, 50], "low_score": 4}
    assert [(p["place_id"], p["he"], p["n_here"]) for p in r["items"]] == [
        (1, "אמר", None), (2, "ראשית", None),
    ]  # fmt: skip
    assert r["items"][0]["lemmas"] == ["559"] and "tipnr" not in r["items"][0]
    assert [p["place_id"] for p in client.get("/api/places?kind=region").json()["items"]] == [2]
    book = client.get("/api/places?book=0").json()["items"]
    assert [(p["place_id"], p["n_here"]) for p in book] == [(1, 2)]
    assert client.get("/api/places?unit=c:1:1").json()["items"][0]["place_id"] == 2
    assert client.get("/api/places?kind=city").status_code == 422
    assert client.get("/api/places?unit=c:9:9").status_code == 404


def test_entity_sites(client):
    e = client.get("/api/entities/559").json()
    assert e["name_kind"] == "location"
    assert [(s["place_id"], s["n_here"], s["kind"]) for s in e["sites"]] == [(1, 2, "town")]
    p = client.get("/api/entities/430").json()
    assert p["name_kind"] == "person" and p["sites"] == []


def test_api_basemap_and_place(client):
    bm = client.get("/api/places/basemap").json()
    assert bm["box"] == [33, 28, 38, 35]
    assert [s["layer"] for s in bm["shapes"]] == ["land", "lakes", "rivers"]
    assert bm["shapes"][2]["rings"] == [[[35.5, 32.7], [35.55, 31.8]]]
    d = client.get("/api/places/1").json()
    assert d["place"]["he"] == "אמר" and d["first_label"] == "v:0"
    assert d["names"] == [{"lemma": "559", "he": "אמר", "n_verses": 2}]
    assert d["by_book"] == [{"book_id": 0, "n_verses": 2}] and d["partners"] == []
    assert client.get("/api/places/99").status_code == 404
    v = client.get("/api/places/1/verses").json()
    assert v["total"] == 2 and [i["verse"]["verse_id"] for i in v["items"]] == [0, 1]
    assert v["items"][0]["tokens"] == [2] and v["items"][1]["tokens"] == [1]
    assert client.get("/api/places/1/verses", params={"limit": 0}).status_code == 422


def test_api_lookup(client):
    def look(q):
        r = client.get("/api/places/lookup", params={"q": q}).json()
        assert r["query"] == q
        return [(p["place_id"], p["exact"]) for p in r["items"]]

    assert look("אמר") == [(1, True)]
    assert look("וְאָמַר") == [(1, True)]  # pointing ignored, a prefix dropped
    assert look("אמרה") == [(1, True)]  # another of its names
    assert look("אמ") == [(1, False)]  # a name starts with it
    assert look("ראשיתה") == [] and look("ראשת") == [(2, True)]  # ו and י ignored
    assert look("H7225") == [(2, True)] and look("9999") == []
    one = client.get("/api/places/lookup", params={"q": "אמר"}).json()["items"][0]
    assert (one["he"], one["first_label"], one["kind"]) == ("אמר", "v:0", "town")
    assert client.get("/api/places/lookup", params={"q": "אמר", "limit": 0}).status_code == 422


def test_reader_places(client):
    r = client.get("/api/reader/c:0:1").json()
    assert r["computed"]["places"] is True
    assert r["places"] == [{"place_id": 1, "he": "אמר", "kind": "town"}]
    assert [v["places"] for v in r["verses"]] == [{"2": 1}, {"1": 1}, {}]
