"""The layered reader's word-level layers (`/api/reader/{unit}`, DESIGN.md §16.39)."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.fixture import fixture_encoder


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_reader_layers(client):
    r = client.get("/api/reader/c:0:1").json()
    assert r["unit"]["unit_id"] == "c:0:1" and r["rare_verses"] == 3
    assert all(r["computed"].values())
    assert r["speakers"] == [
        {"lemma": "3068", "he": "יהוה", "divine": True, "n_words": 2, "to": ["4872"]}
    ]
    v0, v1, v2 = r["verses"]
    # Genesis 1:2 is spoken by יהוה (its last word has no display token)
    assert v0["speech"] == {} and v1["speech"] == {"0": 0, "1": 0}
    # v0 words 0-1 share a phrase with v5; יהוה is in two verses, the names are left out
    assert v0["phrases"] == {"0": 1, "1": 1}
    assert v0["rare"] == {"3": 2}
    # mood (the fixture's domains): ראשית counts as distress, אלהים and יהוה as praise
    assert v0["mood"] == {"0": "distress", "1": "praise", "3": "praise"}
    # a sound-alike pair inside v0: each word gets the other as its partner
    assert [(w["display"], w["partner_display"], w["partner_form"]) for w in v0["wordplay"]] == [
        (1, 3, "יהוה"),
        (3, 1, "אלהים"),
    ]
    assert v2["ketiv"] == [{"display": [0], "ketiv": "", "qere": "רֵאשִׁית", "cls": "qere_only"}]
    # a quiet samekh before v1, an unmarked turn before v2, nothing before the chapter's first
    assert v0["gap"] is None
    assert v1["gap"] == {"score": 0.03, "kind": "quiet", "mam": "samekh", "chapter": False}
    assert v2["gap"]["kind"] == "turn" and v2["gap"]["mam"] is None


def test_reader_across_units(client):
    v3, v4 = client.get("/api/reader/c:0:2").json()["verses"]
    # the pair v3 ~ v4 lies inside the chapter; the partner label names the other verse
    assert v3["wordplay"][0]["partner_vid"] == 4 and v4["wordplay"][0]["partner_vid"] == 3
    assert v3["gap"]["chapter"] and v4["gap"]["mam"] == "pe"
    assert v4["ketiv"][0]["cls"] == "vowel_letter"
    assert client.get("/api/reader/v:0").json()["verses"][0]["verse_id"] == 0
    assert client.get("/api/reader/c:9:9").status_code == 404


def test_reader_too_long(built):
    cfg, _ = built
    cfg["serve"]["max_compare_verses"] = 2
    c = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    assert c.get("/api/reader/c:0:1").status_code == 422


def test_reader_without_stages(built):
    cfg, db = built
    with sqlite3.connect(db) as conn:
        for t in ("clauses", "phrases", "wordplay", "kq_pairs", "segment_gaps", "refrains"):
            conn.execute(f"DELETE FROM {t}")
        conn.execute("DELETE FROM domains")
        conn.execute("DELETE FROM pentateuch_verses")
        conn.execute("DELETE FROM places")
        conn.execute("DELETE FROM place_mentions")
        conn.execute("UPDATE words SET domains = NULL")
    c = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    r = c.get("/api/reader/c:0:1").json()
    assert not any(r["computed"].values()) and r["speakers"] == []
    assert all(
        not v["speech"] and not v["wordplay"] and v["gap"] is None and not v["mood"]
        and not v["places"]
        for v in r["verses"]
    ) and r["places"] == []
