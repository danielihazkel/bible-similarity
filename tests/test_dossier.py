import sqlite3

import pytest
from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.fixture import fixture_encoder


def _client(cfg):
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


@pytest.fixture
def client(built):
    cfg, _ = built
    return _client(cfg)


def entries(client, unit_id):
    r = client.get(f"/api/dossier/{unit_id}")
    assert r.status_code == 200
    return {e["kind"]: e for e in r.json()["entries"]}


def test_dossier_of_a_verse(client):
    d = entries(client, "v:1")
    # counts agree with the list endpoints filtered to the unit
    for kind, path in (
        ("sequences", "/api/sequences?unit=v:1"),
        ("borrowing", None),
        ("phrases", "/api/phrases?unit=v:1&min_tokens=1"),
        ("wordplay", "/api/wordplay?unit=v:1"),
        ("rhymes", "/api/rhymes?unit=v:1"),
        ("discoveries", "/api/discoveries?unit=v:1"),
    ):
        if path:
            assert d[kind]["count"] == client.get(path).json()["total"], kind
    assert d["borrowing"]["count"] == 1  # the Genesis -> Exodus parallel starts at v:1
    assert d["speech"] == {
        **d["speech"], "count": 1, "key": "3068", "label": "יהוה", "computed": True,
    }  # fmt: skip
    assert d["voices"]["key"] == "divine" and d["voices"]["count"] == 1
    # a verse reads acrostic, dating and structure on its chapter
    for kind in ("acrostic", "dating", "structure"):
        assert (d[kind]["scope"], d[kind]["target_unit"]) == ("chapter", "c:0:1"), kind
    assert d["dating"]["value"] == pytest.approx(0.1)
    assert "network" not in d and d["labels"]["count"] == 0


def test_dossier_of_a_chapter(client):
    d = entries(client, "c:0:1")
    assert d["acrostic"]["scope"] == "unit" and d["structure"]["target_unit"] == "c:0:1"
    assert d["network"]["computed"] and d["network"]["count"] >= 1 and d["network"]["total"] >= 1
    assert d["changes"]["count"] == sum(
        client.get("/api/changes?unit=c:0:1").json()["totals"].values()
    )
    assert client.get("/api/dossier/c:9:9").status_code == 404


def test_dossier_labels_are_live(client):
    put = {"a_id": "v:0", "b_id": "v:3", "label": "real"}
    assert client.put("/api/labels", json=put).status_code == 200
    assert entries(client, "v:0")["labels"]["count"] == 1
    assert entries(client, "v:3")["labels"]["count"] == 1


def test_dossier_not_computed(built):
    cfg, db = built
    conn = sqlite3.connect(db)
    with conn:
        conn.execute("DELETE FROM voice_speakers")
        conn.execute("DELETE FROM borrowing_sequences")
    conn.close()
    d = entries(_client(cfg), "v:1")
    assert not d["voices"]["computed"] and not d["borrowing"]["computed"]
    assert d["phrases"]["computed"]


def test_unit_filters(client):
    assert client.get("/api/phrases?unit=v:5&min_tokens=1").json()["total"] == 1
    assert client.get("/api/phrases?unit=v:2&min_tokens=1").json()["total"] == 0
    ch = client.get("/api/changes?unit=v:3").json()
    assert ch["unit"] == "v:3" and sum(ch["totals"].values()) >= 1
    assert sum(client.get("/api/changes?unit=v:5").json()["totals"].values()) == 0
    disc = client.get("/api/discoveries?unit=v:3").json()
    assert disc["unit_type"] == "verse" and disc["total"] == 1
    assert client.get("/api/discoveries?unit=c:0:1").json()["unit_type"] == "chapter"
    b = client.get("/api/borrowing?unit=v:5").json()
    assert b["unit"] == "v:5" and [p["a_book"] for p in b["books"]] == [0]
    assert client.get("/api/borrowing?unit=v:3").json()["books"] == []
    assert len(client.get("/api/borrowing").json()["books"]) == 1
    for path in ("phrases", "changes", "rhymes", "discoveries", "borrowing", "typescenes"):
        assert client.get(f"/api/{path}?unit=v:99").status_code == 404, path
    # CSV export pages the same handlers, so the unit filter carries over
    csv = client.get("/api/export/phrases.csv?unit=v:2&min_tokens=1").text
    assert csv.strip().count("\n") == 0  # header only
