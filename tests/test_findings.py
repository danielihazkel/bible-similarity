import sqlite3

import pytest
from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.api.routes import findings as f
from bsim.fixture import fixture_encoder


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE acrostics (q REAL)")
    c.executemany("INSERT INTO acrostics VALUES (?)", [(0.01,), (0.04,), (0.5,)])
    return c


def test_verdicts_follow_the_numbers(conn):
    meta = {
        "acrostics": {"known_recall": 0.9},
        "leitwort_numbers": {
            "leitworte": 9,
            "6": {"multiples": 12, "expected": 10},
            "7": {"multiples": 11, "expected": 10},
            "10": {"multiples": 15, "expected": 10},
        },
        "mirrors": {
            "words": {
                "all": {"verses_chiastic": 4, "verses_parallel": 6, "share": 0.4, "p": 0.001}
            },
            "clauses": {"poetry": 0.3, "prose": 0.2, "poetry_n": 5, "prose_n": 9, "p": 0.2},
        },
        "allusions": {"pairs": 5, "known": 4, "strong": 1, "strong_known": 1, "best_new_q": 0.04},
    }
    got = {x.key: x for b in f.BUILDERS if (x := b(meta, conn, 0.05)) is not None}
    assert set(got) == {"acrostics", "sevens", "chiasm", "clauses", "allusions"}
    assert got["acrostics"].verdict == "holds" and got["acrostics"].values["found"] == 2
    # 7 is not the divisor with the largest excess: nothing singles it out
    assert got["sevens"].verdict == "fails" and got["sevens"].values["largest"] == 10
    assert got["sevens"].values["smallest"] == 7
    assert got["chiasm"].verdict == "fails"  # the repeated order wins
    assert got["clauses"].verdict == "fails"  # the right way, but p 0.2
    assert got["allusions"].verdict == "holds"  # a new pair beat the shuffles
    meta["allusions"]["best_new_q"] = 0.8
    meta["mirrors"]["clauses"]["p"] = 0.01
    assert f._allusions(meta, conn, 0.05).verdict == "lead"
    assert f._clauses(meta, conn, 0.05).verdict == "holds"
    meta["leitwort_numbers"]["7"]["multiples"] = 20
    assert f._sevens(meta, conn, 0.05).verdict == "holds"


def test_missing_stages_are_left_out(conn):
    assert all(b({}, conn, 0.05) is None for b in f.BUILDERS if b is not f._acrostics)
    assert f._echoes({"echoes": {"checks": {}}}, conn, 0.05) is None


def test_findings_api(built):
    cfg, _ = built
    client = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    r = client.get("/api/findings").json()
    assert r["alpha"] == cfg["serve"]["findings"]["alpha"]
    by_key = {i["key"]: i for i in r["items"]}
    # the fixture's citations: "as commanded" never resolves, so the family is left out
    assert "citations" not in by_key
    assert by_key["echoes"]["verdict"] == "fails"  # one spelling case: too few
    assert by_key["allusions"]["verdict"] == "lead" and by_key["allusions"]["values"]["pairs"] == 2
    assert by_key["chiasm"]["values"]["verses_chiastic"] == 1
