"""Your notebook: bookmarks, notes and collections (`store/notebook.py`, `/notebook`, §16.47)."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.config import resolve_path
from bsim.fixture import fixture_encoder
from bsim.store import labels
from bsim.store import notebook as store


def test_store(tmp_path):
    conn = store.connect(tmp_path / "x" / "labels.sqlite")
    e = store.put_entry(conn, "v:1", "a note")
    assert (e["unit_id"], e["note"], e["collections"]) == ("v:1", "a note", [])
    assert store.put_entry(conn, "v:1")["note"] == "a note"  # no note given: kept
    assert store.put_entry(conn, "v:1", "")["note"] == ""
    c = store.create_collection(conn, "Creation", "Genesis 1–2")
    with pytest.raises(store.Conflict):
        store.create_collection(conn, "Creation")
    # adding a unit to a collection keeps it as an entry
    cid = c["collection_id"]
    assert store.add_member(conn, cid, "c:0:1")["collections"] == [cid]
    store.add_member(conn, c["collection_id"], "v:1")
    store.add_member(conn, c["collection_id"], "v:1")  # twice: once
    assert store.collection(conn, c["collection_id"])["n_entries"] == 2
    assert {e["unit_id"] for e in store.entries(conn)} == {"v:1", "c:0:1"}
    assert store.remove_member(conn, c["collection_id"], "v:1")
    assert not store.remove_member(conn, c["collection_id"], "v:1")
    assert store.entry(conn, "v:1")["collections"] == []  # the entry stays
    store.add_member(conn, c["collection_id"], "v:1")
    assert store.delete_entry(conn, "v:1") and not store.delete_entry(conn, "v:1")
    assert store.collection(conn, c["collection_id"])["n_entries"] == 1  # taken out of it too
    other = store.create_collection(conn, "Other")
    with pytest.raises(store.Conflict):
        store.update_collection(conn, other["collection_id"], "Creation", "")
    assert store.update_collection(conn, 99, "x", "") is None
    assert store.delete_collection(conn, c["collection_id"])
    assert store.entry(conn, "c:0:1")["collections"] == []  # its entries stay
    assert [x["name"] for x in store.collections(conn)] == ["Other"]
    # the labels table lives alongside, untouched
    assert labels.all_labels(conn) == []
    conn.close()


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_notebook_api(client, built):
    cfg, _ = built
    assert client.get("/api/notebook").json() == {"writable": True, "entries": [],
                                                  "collections": [], "hidden": 0}  # fmt: skip
    r = client.put("/api/notebook/entries/v:3", json={"note": "the turn"})
    assert r.status_code == 200
    e = r.json()
    assert e["unit"]["unit_id"] == "v:3" and e["note"] == "the turn"
    assert e["verse"]["verse_id"] == 3 and e["collections"] == []
    c = client.post("/api/notebook/collections", json={"name": " Openings ", "description": ""})
    assert c.status_code == 201 and c.json()["name"] == "Openings"
    cid = c.json()["collection_id"]
    assert client.post("/api/notebook/collections", json={"name": "Openings"}).status_code == 409
    assert client.post("/api/notebook/collections", json={"name": "  "}).status_code == 422
    a = client.put(f"/api/notebook/collections/{cid}/entries/c:0:1")
    assert a.status_code == 200 and a.json()["verse"] is None and a.json()["collections"] == [cid]
    client.put(f"/api/notebook/collections/{cid}/entries/v:0")
    nb = client.get("/api/notebook")
    assert nb.headers["cache-control"] == "no-store"
    nb = nb.json()
    # canon order; a chapter before the verse it starts with
    assert [x["unit"]["unit_id"] for x in nb["entries"]] == ["c:0:1", "v:0", "v:3"]
    assert nb["collections"] == [
        {**c.json(), "n_entries": 2, "updated_at": nb["collections"][0]["updated_at"]}
    ]
    # the note kept when only the unit is put again
    assert client.put("/api/notebook/entries/v:3", json={}).json()["note"] == "the turn"
    long = "x" * (cfg["serve"]["notebook"]["max_note"] + 1)
    assert client.put("/api/notebook/entries/v:3", json={"note": long}).status_code == 422
    assert client.put("/api/notebook/entries/v:999", json={}).status_code == 404
    assert client.put("/api/notebook/collections/99/entries/v:0").status_code == 404
    body = {"name": "Beginnings", "description": "first verses"}
    ren = client.put(f"/api/notebook/collections/{cid}", json=body)
    assert ren.json()["name"] == "Beginnings" and ren.json()["description"] == "first verses"
    assert client.put("/api/notebook/collections/99", json={"name": "x"}).status_code == 404
    assert client.delete(f"/api/notebook/collections/{cid}/entries/v:0").status_code == 204
    assert client.delete(f"/api/notebook/collections/{cid}/entries/v:0").status_code == 404
    assert client.delete("/api/notebook/entries/c:0:1").status_code == 204
    assert client.delete("/api/notebook/entries/c:0:1").status_code == 404
    assert client.delete(f"/api/notebook/collections/{cid}").status_code == 204
    assert client.delete(f"/api/notebook/collections/{cid}").status_code == 404
    nb = client.get("/api/notebook").json()
    assert [x["unit"]["unit_id"] for x in nb["entries"]] == ["v:0", "v:3"]
    assert nb["collections"] == []
    # an entry whose unit this build lacks is kept and counted, not shown
    conn = store.connect(resolve_path(cfg, "labels"))
    store.put_entry(conn, "v:12345", "from an older build")
    conn.close()
    nb = client.get("/api/notebook").json()
    assert nb["hidden"] == 1 and len(nb["entries"]) == 2


def test_notebook_read_only(built):
    cfg, _ = built
    conn = store.connect(resolve_path(cfg, "labels"))
    store.put_entry(conn, "v:1", "kept")
    conn.close()
    cfg["serve"] = {**cfg["serve"], "labels_writable": False}
    c = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    nb = c.get("/api/notebook").json()
    assert nb["writable"] is False and nb["entries"][0]["note"] == "kept"
    assert c.put("/api/notebook/entries/v:2", json={}).status_code == 403
    assert c.post("/api/notebook/collections", json={"name": "x"}).status_code == 403
    assert c.delete("/api/notebook/entries/v:1").status_code == 403


def test_the_file_is_shared_with_the_labels(built, client):
    cfg, _ = built
    client.put("/api/labels", json={"a_id": "v:0", "b_id": "v:1", "label": "real"})
    client.put("/api/notebook/entries/v:0", json={"note": "n"})
    with sqlite3.connect(resolve_path(cfg, "labels")) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"labels", "notebook_entries", "notebook_collections", "notebook_members"} <= tables
