import json
import sqlite3

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.meter import chapter_rates, group_test, lines, main_pause, stresses
from bsim.api.app import create_app
from bsim.fixture import fixture_encoder

ETNAHTA, ZAQEF, TIPEHA, REVIA = "֑", "֔", "֖", "֗"


def test_stresses_maqaf_and_marks():
    # a word joined by maqaf shares the next word's stress; paseq and sof pasuq carry none
    assert stresses(["מֶה־", "הָיָה", "׀", "לָנוּ", "׃"]) == [0, 1, 0, 1, 0]


def test_main_pause_first_of_equals():
    levels = [0, 2, 3, 2, 0]
    assert main_pause(levels, 0, 4) == 1  # two level-2 pauses: the first divides
    assert main_pause(levels, 2, 4) == 3
    assert main_pause([0, 0, 0], 0, 2) is None


def test_lines_qinah_verse():
    # Lam 3:1: אני הגבר ראה עני (zaqef) | בשבט (tipeha) עברתו -> one line, 4:2
    toks = ["אֲנִי", "הַגֶּבֶר", "רָאָה", "עֳנִי" + ZAQEF, "בְּשֵׁבֶט" + TIPEHA, "עֶבְרָתוֹ"]
    assert lines(toks, False, 7) == [(0, 5, 6, 4, 2)]


def test_lines_cut_at_etnahta_and_maqaf():
    # 9 stresses: cut at the etnahta into two lines; the maqaf pair counts once
    first = ["א", "ב" + REVIA, "ג", "ד" + ETNAHTA]
    second = ["ה", "ו־", "ז", "ח" + TIPEHA, "ט", "י"]
    out = lines(first + second, False, 7)
    assert out == [(0, 3, 4, 2, 2), (4, 9, 5, 3, 2)]
    # a line no pause divides is kept whole, without members
    assert lines(["א", "ב"], False, 7) == [(0, 1, 2, None, None)]


def test_chapter_rates():
    df = pd.DataFrame(
        {
            "verse_id": [0, 0, 1, 2],
            "stresses": [5, 5, 4, 9],
            "a": pd.array([3, 2, 2, 5], dtype="Int64"),
            "b": pd.array([2, 3, 2, 4], dtype="Int64"),
        }
    )
    chapter_of = pd.Series({0: "x", 1: "x", 2: "y"})
    r = chapter_rates(df, chapter_of, 4, 7)
    assert list(r.index) == ["x"]  # the 9-stress line is not measured
    assert r.loc["x", "n_lines"] == 3
    assert r.loc["x", "fall"] == pytest.approx(1 / 3) and r.loc["x", "net"] == pytest.approx(0)
    assert r.loc["x", "share32"] == pytest.approx(1 / 3)


def test_group_test():
    rng = np.random.default_rng(0)
    net = pd.Series({**{f"p{i}": 0.1 + 0.01 * i for i in range(40)}, "t1": 0.9, "t2": 0.8})
    pool = [f"p{i}" for i in range(40)]
    high = group_test(net, ["t1", "t2"], pool, 999, rng)
    assert high["mean"] == pytest.approx(0.85) and high["p"] < 0.01
    low = group_test(net, ["p0", "p1"], pool[2:], 999, rng)
    assert low["p"] > 0.5
    assert group_test(net, ["missing"], pool, 9, rng)["p"] is None


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_meter_api(client):
    r = client.get("/api/meter").json()
    assert r["meta"]["test"]["p"] == 0.04 and "chapters" not in r["meta"]["named"]
    assert [c["unit"]["unit_id"] for c in r["items"]] == ["c:0:1", "c:0:2", "c:1:1"]
    assert [c["unit"]["unit_id"] for c in r["test_chapters"]] == ["c:0:1"]
    assert [c["unit"]["unit_id"] for c in r["control_chapters"]] == ["c:1:1"]
    assert [c["unit"]["unit_id"] for c in r["named_chapters"]] == ["c:0:2"]
    assert client.get("/api/meter?group=pool").json()["total"] == 1
    assert client.get("/api/meter?book=1").json()["items"][0]["group"] == "control"
    assert client.get("/api/meter?group=other").status_code == 422
    assert client.get("/api/meter?limit=0").status_code == 422


def test_unit_meter(client):
    u = client.get("/api/meter/c:0:1").json()
    assert u["chapter"]["group"] == "test" and u["max_stresses"] == 7
    assert [v["verse_id"] for v in u["verses"]] == [0, 1, 2]
    assert u["verses"][0]["lines"] == [{"first": 0, "last": 3, "stresses": 4, "a": 3, "b": 1}]
    assert u["verses"][2]["lines"][0]["a"] is None
    assert client.get("/api/meter/v:4").json()["chapter"]["unit"]["unit_id"] == "c:0:2"
    assert client.get("/api/meter/c:9:9").status_code == 404


def test_meter_dossier_and_findings(client):
    def entry(unit):
        d = client.get(f"/api/dossier/{unit}").json()
        return next(e for e in d["entries"] if e["kind"] == "meter")

    e = entry("v:1")
    assert e["scope"] == "chapter" and e["target_unit"] == "c:0:1"
    assert e["value"] == 1.0 and e["count"] == 1
    assert entry("c:0:2")["count"] == 0
    f = {x["key"]: x for x in client.get("/api/findings").json()["items"]}
    assert f["meter"]["verdict"] == "holds" and f["meter"]["values"]["control_pct"] == 0.0
    assert f["laments"]["verdict"] == "fails"


def test_meter_in_db(built):
    _, db = built
    conn = sqlite3.connect(db)
    meta = json.loads(conn.execute("SELECT value FROM meta WHERE key = 'meter'").fetchone()[0])
    assert meta["split"] == 4
    assert conn.execute("SELECT COUNT(*) FROM meter_lines WHERE a IS NULL").fetchone()[0] == 2
    assert conn.execute("SELECT grp FROM meter_chapters WHERE book_id = 1").fetchone()[0] == (
        "control"
    )
