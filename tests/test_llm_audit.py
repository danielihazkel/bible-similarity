"""Detector precision by Claude's reading (series L5, §16.86): the claims, the draw, the Wilson
interval, the calibration gate and a run with a fake batch client."""

from __future__ import annotations

import json
import sqlite3

import pandas as pd
import pytest

from bsim.config import load_config, resolve_path
from bsim.eval import llm_audit as la
from llm_fakes import fake_client


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    tokens = [["וַיִּקְרָא", "שְׁמוֹ", "נֹחַ", "לֵאמֹר", "זֶה", "יְנַחֲמֵנוּ"], ["צֹאן", "וּבָקָר"]]
    pd.DataFrame(
        {"verse_id": [0, 1], "ref": ["Genesis 5:29", "Genesis 12:16"],
         "display_tokens": [json.dumps(t, ensure_ascii=False) for t in tokens]}
    ).to_sql("verses", c, index=False)  # fmt: skip
    pd.DataFrame(
        {"naming": [0, 1], "verse_id": [0, 0], "name": ["נח", "נח"], "kind": ["person"] * 2,
         "name_first": [2, 2], "name_last": [2, 2], "echo_disp": [5, None], "p": [0.01, 0.5],
         "score": [1.0, 0.5], "known": [1, None]}
    ).to_sql("etiologies", c, index=False)  # fmt: skip
    pd.DataFrame(
        {"pair": ["a+b"], "first_form": ["צאן"], "second_form": ["בקר"], "n": [32], "fixed": [0.75]}
    ).to_sql("binomials", c, index=False)
    pd.DataFrame({"pair": ["a+b", "a+b"], "verse_id": [1, 0]}).to_sql(
        "binomial_occurrences", c, index=False
    )
    yield c
    c.close()


def test_claims(conn):
    src = la.Source(conn)
    et = la.findings(conn, "etiologies", src, 8)
    assert et.key.tolist() == ["naming 0", "naming 1"]  # the stronger first
    assert et.claim[0] == "This verse names נֹחַ (person) and explains the name, playing on the" \
        " word יְנַחֲמֵנוּ."  # fmt: skip
    assert "playing" not in et.claim[1] and et.known.tolist() == [True, False]
    bi = la.findings(conn, "binomials", src, 8)
    assert bi.claim[0].startswith("צאן ובקר is a fixed pair") and bi.vids[0] == [0, 1]
    with pytest.raises(RuntimeError, match="unknown detector"):
        la.findings(conn, "nothing", src, 8)
    assert set(la.DEFINITIONS) >= set(load_config()["llm_audit"]["detectors"]) | {"places"}


def test_prophetic_claims(conn):
    """The messenger formula is not judged; each other form has its own claim (§16.92)."""
    names = [{"lemma": "894", "he": "בָּבֶל", "n": 2}]
    pd.DataFrame(
        {"item_id": [1, 2, 3], "form": ["messenger", "nations", "woe"], "first_vid": [0, 0, 1],
         "last_vid": [0, 1, 1], "detail": ["{}", json.dumps({"names": names}), "{}"],
         "known": [0, 1, 0]}
    ).to_sql("prophetic_items", conn, index=False)  # fmt: skip
    f = la.findings(conn, "prophetic", la.Source(conn), 8)
    assert f.key.tolist() == ["nations 2", "woe 3"] and f.known.tolist() == [True, False]
    assert "against a foreign nation (בָּבֶל)" in f.claim[0] and f.vids[0] == [0, 1]
    assert f.claim[1].startswith("In Genesis 12:16 a woe saying begins")


def test_known():
    assert la._known(1) and la._known("כי לעולם חסדו")
    assert not any(la._known(x) for x in (0, None, float("nan"), "", False))


def test_draw():
    df = pd.DataFrame(
        {"key": [f"k{i}" for i in range(10)], "known": [i in (1, 8, 9) for i in range(10)]}
    )
    d = la.draw(df, top=5, n=3, known_max=1, seed=0)
    s = d[d.set == "sample"]
    assert len(s) == 3 and s.key.isin([f"k{i}" for i in range(5)]).all()
    k = d[d.set == "known"]
    assert len(k) == 1 and k.key.iloc[0] not in s.key.tolist()
    assert d.equals(la.draw(df, top=5, n=3, known_max=1, seed=0))


def test_wilson_and_precision():
    lo, hi = la.wilson(45, 50)
    assert lo < 0.9 < hi and lo > 0.75 and hi < 0.97
    assert la.wilson(0, 0) == (None, None)
    x = pd.DataFrame({"status": ["ok"] * 4 + ["errored"], "verdict": ["right", "right", "wrong",
                      "unsure", None]})  # fmt: skip
    p = la.precision(x)
    assert (p["judged"], p["right"], p["wrong"], p["unsure"], p["precision"]) == (4, 2, 1, 1, 0.667)


def _ans(v, p=0.9):
    return {"verdict": v, "p_right": p, "rationale": "השם נח"}


def test_a_run(tmp_path, monkeypatch):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "artifacts": str(tmp_path / "artifacts")}
    cfg["llm_audit"] = {**cfg["llm_audit"], "min_places": 0.5, "min_known": 0.5}
    items = pd.DataFrame(
        {
            "set": ["sample", "sample", "known", "calibration", "calibration"],
            "detector": ["etiologies", "etiologies", "etiologies", "places", "places"],
            "custom_id": [f"aud-{i}" for i in range(5)],
            "key": ["naming 0", "naming 1", "naming 2", "place 0 1", "place 1 2"],
            "claim": ["c0", "c1", "c2", "c3", "c4"],
            "vids": [[0], [0], [1], [0], [1]],
            "known": [True, False, True, True, True],
            "prompt": ["p"] * 5,
        }
    )
    monkeypatch.setattr(la, "build_items", lambda cfg, log: items)
    client, batches = fake_client({})
    dry = la.run_llm_audit(cfg, log=lambda s: None, dry_run=True, client=client)
    assert dry["requests"] == 5 and batches.created == []
    answers = {"aud-0": _ans("right"), "aud-1": _ans("wrong", 0.1), "aud-2": _ans("right"),
               "aud-3": _ans("right"), "aud-4": "not json"}  # fmt: skip
    client, _ = fake_client(answers)
    meta = la.run_llm_audit(cfg, log=lambda s: None, client=client, sleep=lambda s: None)
    c = meta["calibration"]
    assert (c["places_right"], c["known_right"], c["holds"]) == ("1 / 1", "2 / 2", True)
    d = meta["detectors"]["etiologies"]
    assert (d["judged"], d["right"], d["wrong"], d["precision"]) == (2, 1, 1, 0.5)
    assert "places" not in meta["detectors"]
    report = (resolve_path(cfg, "artifacts") / "eval" / "llm_audit.md").read_text("utf-8")
    assert "naming 1: c1" in report and "holds" in report


# --- the `pages` run (M158, D147) ----------------------------------------------------------------


def test_findings_where(conn):
    src = la.Source(conn)
    assert la.findings(conn, "etiologies", src, 8, "p <= 0.05").key.tolist() == ["naming 0"]
    assert len(la.findings(conn, "etiologies", src, 8)) == 2


def test_draw_pages():
    full = pd.DataFrame(
        {"key": [f"k{i}" for i in range(10)], "known": [i in (1, 8, 9) for i in range(10)]}
    )
    lists = {"shown": full, "marked": full.iloc[[0, 1]]}
    d = la.draw_pages(full, lists, n=4, known_max=5, seed=0)
    s, m, k = (d[d.set == x] for x in ("shown", "marked", "known"))
    assert len(s) == 4 and s.population.unique().tolist() == [10]
    assert m.key.tolist() == ["k0", "k1"] and m.population.unique().tolist() == [2]  # all of it
    assert not k.key.isin(set(s.key) | set(m.key)).any() and k.known.all()
    assert d.equals(la.draw_pages(full, lists, n=4, known_max=5, seed=0))
    assert len(la.draw_pages(full, lists, n=4, known_max=5, seed=1).merge(s, on="key")) < 4


def test_out_dir():
    cfg = load_config()
    assert la.out_dir(cfg) == "llm_audit"  # M152's run, as it was
    cfg["llm_audit"] = {**cfg["llm_audit"], "population": "pages"}
    assert la.out_dir(cfg) == "llm_audit_pages"
    cfg["llm_audit"]["population"] = "all"
    with pytest.raises(RuntimeError, match="one of strongest, pages"):
        la.out_dir(cfg)


def test_a_pages_run(tmp_path, monkeypatch):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "artifacts": str(tmp_path / "artifacts")}
    cfg["llm_audit"] = {**cfg["llm_audit"], "population": "pages", "min_places": 0.5,
                        "min_known": 0.5}  # fmt: skip
    items = pd.DataFrame(
        {
            "set": ["shown", "shown", "marked", "known", "calibration"],
            "detector": ["etiologies"] * 4 + ["places"],
            "custom_id": [f"aud-{i}" for i in range(5)],
            "key": ["naming 0", "naming 1", "naming 0", "naming 2", "place 0 1"],
            "claim": ["c0", "c1", "c0", "c2", "c3"],
            "vids": [[0], [0], [0], [1], [0]],
            "known": [False, False, False, True, True],
            "population": [111, 111, 8, 16, 50],
            "prompt": ["p"] * 5,
        }
    )
    monkeypatch.setattr(la, "build_items", lambda cfg, log: items)
    answers = {"aud-0": _ans("right"), "aud-1": _ans("wrong", 0.1), "aud-2": _ans("right"),
               "aud-3": _ans("right"), "aud-4": _ans("right")}  # fmt: skip
    client, _ = fake_client(answers)
    meta = la.run_llm_audit(cfg, log=lambda s: None, client=client, sleep=lambda s: None)
    d = meta["detectors"]["etiologies"]
    assert (d["shown"]["precision"], d["shown"]["population"]) == (0.5, 111)
    assert (d["marked"]["right"], d["marked"]["population"]) == (1, 8)
    assert d["known"]["right"] == 1 and meta["population"] == "pages"
    art = resolve_path(cfg, "artifacts")
    assert (art / "llm_audit_pages" / "llm_audit.meta.json").exists()
    assert not (art / "llm_audit").exists()  # M152's run untouched
    report = (art / "eval" / "llm_audit_pages.md").read_text("utf-8")
    assert "| etiologies | marked | 8 |" in report and report.count("naming 1: c1") == 1
    got = la.read_precision(cfg)
    assert [r["population"] for r in got["runs"]] == ["pages"]
    assert [(r["set"], r["population"]) for r in got["detectors"]["etiologies"]] == [
        ("shown", 111), ("marked", 8)
    ]  # fmt: skip


def test_read_precision_skips_failed_calibration(tmp_path):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "artifacts": str(tmp_path)}
    (tmp_path / "llm_audit").mkdir()
    calibration = {"places_right": "1 / 50", "known_right": "0 / 1", "holds": False}
    meta = {"model": "m", "collected_at": "t", "detectors": {}, "calibration": calibration}
    (tmp_path / "llm_audit" / "llm_audit.meta.json").write_text(json.dumps(meta), "utf-8")
    assert la.read_precision(cfg) == {"runs": [], "detectors": {}}


def test_detector_precision_api(built):
    from fastapi.testclient import TestClient

    from bsim.api.app import create_app
    from bsim.fixture import fixture_encoder

    cfg, _ = built  # the fixture's two made-up runs
    c = TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))
    r = c.get("/api/detector-precision").json()
    assert sorted(x["population"] for x in r["runs"]) == ["pages", "strongest"]
    ety = {x["set"]: x for x in r["detectors"]["etiologies"]}
    assert set(ety) == {"strongest", "shown", "marked"}
    assert (ety["shown"]["population"], ety["strongest"]["population"]) == (111, None)
    assert ety["marked"]["precision"] == 0.875
    pub = {**cfg, "serve": {**cfg["serve"], "personal": False}}
    p = TestClient(create_app(pub, encoder=fixture_encoder, log=lambda _: None))
    assert p.get("/api/detector-precision").status_code == 404


def test_a_tagged_run_and_the_runs_shown(tmp_path):
    """M164: a run of some detectors writes its own folder; the pages show the runs of
    `shown_runs` in order, a later run replacing an earlier one's rows for its detectors."""
    cfg = load_config()
    cfg["llm_audit"] = {**cfg["llm_audit"], "population": "pages", "tag": "m164"}
    assert la.out_dir(cfg) == "llm_audit_pages_m164"
    cfg["paths"] = {**cfg["paths"], "artifacts": str(tmp_path)}
    cfg["llm_audit"]["shown_runs"] = ["llm_audit_pages", "llm_audit_pages_m164"]
    cal = {"places_right": "47 / 50", "known_right": "9 / 10", "holds": True}

    def row(right, population):
        return {"judged": right + 1, "right": right, "wrong": 1, "unsure": 0, "precision": 0.5,
                "lo": 0.1, "hi": 0.9, "population": population}  # fmt: skip

    for folder, detectors in [
        ("llm_audit_pages", {"seams": {"shown": row(30, 159), "known": row(0, 0)},
                             "mainline": {"shown": row(1, 10), "known": row(0, 0)}}),
        ("llm_audit_pages_m164", {"mainline": {"shown": row(40, 1250), "known": row(5, 5)}}),
    ]:  # fmt: skip
        (tmp_path / folder).mkdir()
        meta = {"model": "m", "collected_at": "2026-11-10T00:00:00", "population": "pages",
                "calibration": cal, "detectors": detectors}  # fmt: skip
        (tmp_path / folder / "llm_audit.meta.json").write_text(json.dumps(meta), "utf-8")
    got = la.read_precision(cfg)
    assert [r["run"] for r in got["runs"]] == ["llm_audit_pages", "llm_audit_pages_m164"]
    assert [r["right"] for r in got["detectors"]["mainline"]] == [40]  # the later run's
    assert [r["right"] for r in got["detectors"]["seams"]] == [30]  # kept from the earlier
