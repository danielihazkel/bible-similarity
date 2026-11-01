"""Errors the viewer can tell apart (M107): a stage that did not run (503 `stage_missing`), an
unknown book (404), and a table an older DB lacks (503 `stage_missing`, not a bare 500)."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.api.routes._common import STAGE_TABLES
from test_api import fake_encoder


@pytest.fixture
def app_of(built):
    cfg, db = built

    def make(**meta):
        app = create_app(cfg, encoder=fake_encoder, log=lambda _: None)
        app.state.serve.meta.update(meta)
        return TestClient(app), db

    return make


def test_the_fixture_ran_these_stages(app_of):
    client, _ = app_of()
    ran = client.app.state.serve.meta["stages_run"]
    assert {"ketiv", "typescenes", "mirrors"} <= set(ran)
    assert set(ran) <= set(STAGE_TABLES)


@pytest.mark.parametrize(
    ("stage", "path"),
    [("ketiv", "/api/ketiv"), ("mirrors", "/api/mirrors/verses"), ("sequences", "/api/sequences"),
     ("typescenes", "/api/typescenes")],
)  # fmt: skip
def test_a_stage_not_run_is_told_apart(app_of, stage, path):
    client, _ = app_of()
    assert client.get(path).status_code == 200
    ran = [s for s in client.app.state.serve.meta["stages_run"] if s != stage]
    client, _ = app_of(stages_run=ran)
    r = client.get(path)
    assert r.status_code == 503
    detail = r.json()["detail"]
    assert detail["code"] == "stage_missing" and detail["stage"] == stage
    assert f"bsim {stage}" in detail["message"]


def test_a_stage_that_found_nothing_is_not_missing(app_of):
    """typescenes runs on the fixture and finds no pair: an empty list, not "not computed"."""
    client, _ = app_of()
    body = client.get("/api/typescenes?max_q=1&hide_textual=false").json()
    assert body["total"] == len(body["items"])


def test_an_older_db_without_stages_run(app_of):
    """No `stages_run`: a stage counts as run by its meta entry or its table's rows."""
    client, _ = app_of()
    del client.app.state.serve.meta["stages_run"]
    assert client.get("/api/ketiv").status_code == 200


def test_a_missing_table_is_stage_missing(app_of):
    client, db = app_of()
    conn = sqlite3.connect(db)
    conn.execute("DROP TABLE kq_letters")
    conn.commit()
    conn.close()
    client, _ = app_of()
    r = client.get("/api/ketiv")
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "stage_missing"
    assert r.json()["detail"]["stage"] == "ketiv"


@pytest.mark.parametrize(
    "path",
    ["/api/discoveries?unit_type=verse&mode=fused&book=99", "/api/ketiv/pairs?book=99",
     "/api/phrases?book=99", "/api/changes?a_book=99", "/api/dating/book/99",
     "/api/segments/book/99", "/api/affinity/0/99", "/api/export/discoveries.csv?book=99"],
)  # fmt: skip
def test_an_unknown_book_is_404(app_of, path):
    client, _ = app_of()
    r = client.get(path)
    assert r.status_code == 404
    assert r.json()["detail"] == "unknown book 99"


def test_a_known_book_without_rows_is_empty(app_of):
    client, _ = app_of()
    assert client.get("/api/ketiv/pairs?book=30").status_code == 200
    assert client.get("/api/phrases?book=abc").status_code == 422
