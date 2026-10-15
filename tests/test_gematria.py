"""Letter values (`text/gematria.py`, `bsim gematria`, `/gematria`, DESIGN.md §16.53)."""

import json
import sqlite3

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.gematria import check_known
from bsim.api.app import create_app
from bsim.config import load_config, resolve_path
from bsim.fixture import fixture_encoder
from bsim.text.gematria import FINALS, LETTERS, TABLES, letters, value, values

GEN_1_1 = "בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים אֵ֥ת הַשָּׁמַ֖יִם וְאֵ֥ת הָאָֽרֶץ׃"
# the fixture's first verse: בראשית 913, אלהים 86, ויאמר 257, יהוה 26
V0 = [913, 86, 257, 26]


def test_tables():
    std = TABLES["standard"]
    assert [std[c] for c in "אטיצקת"] == [1, 9, 10, 90, 100, 400]
    assert [std[f] for f in FINALS] == [20, 40, 50, 80, 90]  # a final form as its letter
    assert [TABLES["gadol"][f] for f in FINALS] == [500, 600, 700, 800, 900]
    assert TABLES["gadol"]["כ"] == 20
    assert [TABLES["ordinal"][c] for c in "אית"] == [1, 10, 22] and TABLES["ordinal"]["ץ"] == 18
    assert [TABLES["katan"][c] for c in "יקרת"] == [1, 1, 2, 4]
    assert all(len(t) == len(LETTERS) + len(FINALS) for t in TABLES.values())


def test_values_ignore_points_accents_and_maqaf():
    assert letters("כׇּל־הָאָֽרֶץ׃") == "כלהארץ"
    assert value(GEN_1_1) == 2701  # Genesis 1:1: 7 words, 28 letters
    assert len(letters(GEN_1_1)) == 28
    assert values("יין") == {"standard": 70, "gadol": 720, "ordinal": 34, "katan": 7}
    assert value("abc 123") == 0


def test_known_values_of_the_config():
    known = load_config()["gematria"]["known"]
    assert check_known(known) == [{"text": k["text"], "value": k["value"]} for k in known]
    assert value("אליעזר") == 318 and value("נחש") == value("משיח") == value("יבא שילה") == 358
    with pytest.raises(RuntimeError, match="is 318, not 319"):
        check_known([{"text": "אליעזר", "value": 319}])


def test_run_gematria(built):
    cfg, db = built
    out = resolve_path(cfg, "artifacts")
    forms = pd.read_parquet(out / "gematria" / "forms.parquet").set_index("form")
    # ראשית opens v2-v5; בראשית (with its prefix) is another form
    assert forms.loc["ראשית", ["standard", "n_words", "n_verses"]].tolist() == [911, 4, 4]
    assert json.loads(forms.loc["ראשית", "verses"]) == [2, 3, 4, 5]
    assert forms.loc["בראשית", "standard"] == 913
    verses = pd.read_parquet(out / "gematria" / "verses.parquet").set_index("verse_id")
    assert verses.loc[0, ["standard", "n_letters", "n_words"]].tolist() == [sum(V0), 20, 4]
    # no HebrewStrong.xml in the fixture: lemmas valued by their commonest form
    lemmas = pd.read_parquet(out / "gematria" / "lemmas.parquet").set_index("lemma")
    assert lemmas.loc["430", ["he", "source", "standard"]].tolist() == ["אלהים", "form", 86]
    meta = json.loads((out / "gematria" / "gematria.meta.json").read_text("utf-8"))
    assert meta["verses"] == 6 and meta["lemmas_by_headword"] == 0 and len(meta["known"]) == 8
    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM gematria_verses").fetchone()[0] == 6
    assert json.loads(con.execute("SELECT value FROM meta WHERE key = 'gematria'").fetchone()[0])[
        "forms"
    ] == len(forms)


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_api_value(client):
    r = client.get("/api/gematria/value", params={"text": "אֱלֹהִים"}).json()
    assert r == {
        "text": "אֱלֹהִים",
        "letters": "אלהים",
        "values": {"standard": 86, "gadol": 646, "ordinal": 41, "katan": 14},
    }
    assert client.get("/api/gematria/value", params={"text": "abc"}).status_code == 422
    assert client.get("/api/gematria/value", params={"text": "א" * 501}).status_code == 422


def test_api_lists(client):
    r = client.get("/api/gematria", params={"value": 911}).json()
    assert r["computed"] and r["system"] == "standard"
    assert (r["forms"], r["words"], r["lemmas"], r["verses"]) == (1, 4, 1, 0)
    assert r["known"][0] == {"text": "אליעזר", "value": 318}
    forms = client.get("/api/gematria/forms", params={"value": 911}).json()
    (f,) = forms["items"]
    assert f["form"] == "ראשית" and f["n_words"] == 4
    assert [v["verse_id"] for v in f["verses"]] == [2, 3, 4, 5]
    lemmas = client.get("/api/gematria/lemmas", params={"value": 86}).json()
    assert [(x["lemma"], x["he"]) for x in lemmas["items"]] == [("430", "אלהים")]
    verses = client.get("/api/gematria/verses", params={"value": sum(V0)}).json()
    assert verses["total"] == 1 and verses["items"][0]["verse"]["verse_id"] == 0
    assert verses["items"][0]["n_letters"] == 20
    # ראשית חכמה (v5, book 1) by ordinal; the book filter
    v5 = client.get("/api/gematria/value", params={"text": "ראשית חכמה"}).json()["values"]
    by = {"value": v5["ordinal"], "system": "ordinal"}
    assert [i["verse"]["verse_id"] for i in client.get("/api/gematria/verses", params=by).json()[
        "items"
    ]] == [5]
    assert client.get("/api/gematria/verses", params={**by, "book": 0}).json()["total"] == 0


def test_api_bad_parameters(client):
    for path, params in [
        ("/api/gematria", {"value": -1}),
        ("/api/gematria/forms", {"value": 1, "system": "atbash"}),
        ("/api/gematria/lemmas", {"value": 1, "limit": 0}),
        ("/api/gematria/verses", {"value": "x"}),
    ]:
        assert client.get(path, params=params).status_code == 422


def test_reader_layer(client):
    r = client.get("/api/reader/c:0:1").json()
    assert r["verses"][0]["gematria"] == V0
    assert r["verses"][2]["gematria"] == [911, 360]  # ראשית השנה
