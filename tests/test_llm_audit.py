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
