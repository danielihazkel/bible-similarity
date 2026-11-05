"""The cross-encoder's negatives judged by Claude (series L4, §16.85): the sample, the soft
targets (calibrated runs only), the extra queue rows, a run with a fake batch client."""

from __future__ import annotations

import json

import pandas as pd

from bsim.config import load_config, resolve_path
from bsim.eval import llm_rerank as lr
from llm_fakes import fake_client


def test_negative_sample():
    data = pd.DataFrame(
        {"a": [0, 0, 1, 2, 3, 5], "b": [1, 5, 0, 7, 8, 0], "label": [1.0, 0, 0, 0, 0, 0]}
    )
    s = lr.negative_sample(data, 10, 0)
    # the positive left out; (5, 0) is (0, 5) again; the draw keeps the order
    assert list(zip(s.a, s.b, strict=True)) == [(0, 5), (1, 0), (2, 7), (3, 8)]
    assert len(lr.negative_sample(data, 2, 0)) == 2
    assert lr.negative_sample(data, 2, 0).equals(lr.negative_sample(data, 2, 0))


def test_apply_soft_labels():
    data = pd.DataFrame({"a": [0, 0, 1, 2], "b": [1, 5, 4, 7], "label": [1.0, 0.0, 0.0, 0.0]})
    targets = {(0, 1): 0.2, (0, 5): 0.9, (4, 1): 0.1, (2, 3): 0.8, (8, 9): 0.6, (10, 11): 0.7}
    targets[(1, 4)] = 0.3
    own = {(0, 5), (1, 4)}
    out, counts = lr.apply_soft_labels(data, targets, own, lambda a, b: a < 10, extra=True)
    # the positive keeps 1; judged negatives take p_real; (2, 7) was not judged
    assert out.label.tolist()[:4] == [1.0, 0.9, 0.3, 0.0]
    # the queue pairs not already rows join, those the train rule accepts
    assert list(zip(out.a[4:], out.b[4:], out.label[4:], strict=True)) == [
        (2, 3, 0.8),
        (4, 1, 0.1),
        (8, 9, 0.6),
    ]
    assert counts == {"soft_negatives": 2, "extra_rows": 3}
    plain, c2 = lr.apply_soft_labels(data, targets, own, lambda a, b: True, extra=False)
    assert len(plain) == 4 and c2["extra_rows"] == 0


def _cfg(tmp_path):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "artifacts": str(tmp_path / "artifacts")}
    return cfg


def _ans(verdict, p):
    return {"verdict": verdict, "p_real": p, "kind": "none", "rationale": "אין"}


def test_a_run_and_its_targets(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    items = pd.DataFrame(
        {
            "set": ["calibration"] * 2 + ["negative"] * 2,
            "custom_id": ["cal-0", "cal-1", "neg-0", "neg-1"],
            "a": [0, 1, 5, 9],
            "b": [10, 11, 6, 2],
            "gold": [True, False, None, None],
        }
    )
    monkeypatch.setattr(lr, "build_items", lambda cfg, log: items)
    monkeypatch.setattr(
        lr, "verse_texts", lambda cfg: {i: {"ref": f"R {i}", "text": "א"} for i in range(15)}
    )
    assert lr.soft_targets(cfg) == ({}, set())
    answers = {"cal-0": _ans("real", 0.9), "cal-1": _ans("not", 0.1),
               "neg-0": _ans("real", 0.85), "neg-1": _ans("not", 0.05)}  # fmt: skip
    client, _ = fake_client(answers)
    meta = lr.run_llm_rerank(cfg, log=lambda s: None, client=client, sleep=lambda s: None)
    assert meta["calibration"]["holds"]
    assert meta["negatives"]["verdicts"] == {"real": 1, "not": 1, "unsure": 0}
    targets, own = lr.soft_targets(cfg)
    assert targets == {(5, 6): 0.85, (2, 9): 0.05} and own == {(5, 6), (2, 9)}
    # a failed calibration: no targets
    path = resolve_path(cfg, "artifacts") / "llm_rerank" / "llm_rerank.meta.json"
    m = json.loads(path.read_text("utf-8"))
    m["calibration"]["holds"] = False
    path.write_text(json.dumps(m), "utf-8")
    assert lr.soft_targets(cfg) == ({}, set())


def test_the_profile_keeps_the_model_in_use():
    cfg = load_config("configs/rerank_llm.yaml")
    base = load_config()["rerank"]
    rc = cfg["rerank"]
    assert rc["soft_labels"] == "llm" and base["soft_labels"] == "none"
    assert rc["output"] != base["output"] and rc["system"] != base["system"]
    assert {k: v for k, v in rc.items() if k not in ("soft_labels", "output", "system")} == {
        k: v for k, v in base.items() if k not in ("soft_labels", "output", "system")
    }
