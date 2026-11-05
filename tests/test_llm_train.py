"""Training on Claude's verdicts (series L2, §16.84): the queue's next pairs judged, the runs
read only when calibrated, the `llm` source's positives and negatives by the split rule."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from bsim.config import load_config, resolve_path
from bsim.eval import llm_train as lt
from bsim.train.pairs import extra_links, llm_negatives, training_pairs
from bsim.train.supervised import with_overrides
from llm_fakes import fake_client


def _cfg(tmp_path):
    """15 verses in Genesis (0-4), Exodus (5-9), Joshua (10-14); Joshua is a dev book."""
    cfg = load_config()
    proc = tmp_path / "processed"
    proc.mkdir()
    cfg["paths"] = {
        **cfg["paths"],
        "data_processed": str(proc),
        "artifacts": str(tmp_path / "artifacts"),
        "labels": str(tmp_path / "labels.sqlite"),
    }
    pd.DataFrame({"verse_id": range(15), "book_id": np.repeat([0, 1, 5], 5)}).to_parquet(
        proc / "verses.parquet"
    )
    books = {"Genesis": "train", "Exodus": "train", "Joshua": "dev"}
    (proc / "splits.json").write_text(json.dumps({"books": books}), "utf-8")
    return cfg


def _run(cfg, name, meta_file, rows_file, rows, holds=True):
    out = resolve_path(cfg, "artifacts") / name
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"a_id": f"v:{a}", "b_id": f"v:{b}", "status": st, "verdict": v, "p_real": p}
            for a, b, st, v, p in rows
        ]
    ).to_parquet(out / rows_file)
    meta = {"calibration": {"holds": holds, "auc": 0.9 if holds else 0.5}}
    (out / meta_file).write_text(json.dumps(meta), "utf-8")


def triage(cfg, rows, holds=True):
    _run(cfg, "llm", "llm_triage.meta.json", "triage.parquet", rows, holds)


def train_run(cfg, rows, holds=True):
    _run(cfg, "llm_train", "llm_train.meta.json", "judged.parquet", rows, holds)


def test_judged_runs_only_when_calibrated(tmp_path):
    cfg = _cfg(tmp_path)
    assert lt.judged_runs(cfg).empty
    rows = [(0, 6, "ok", "real", 0.9), (1, 7, "ok", "not", 0.1), (2, 8, "errored", None, None)]
    triage(cfg, rows)
    train_run(cfg, [(6, 0, "ok", "not", 0.2), (3, 9, "ok", "real", 0.8)], holds=False)
    df = lt.judged_runs(cfg)
    assert list(zip(df.a, df.b, df.verdict, strict=True)) == [(0, 6, "real"), (1, 7, "not")]
    # once this run holds, its answer replaces the triage's for a pair judged twice
    train_run(cfg, [(6, 0, "ok", "not", 0.2), (3, 9, "ok", "real", 0.8)])
    df = lt.judged_runs(cfg).sort_values(["a", "b"])
    assert list(zip(df.a, df.b, df.verdict, strict=True)) == [
        (0, 6, "not"),
        (1, 7, "not"),
        (3, 9, "real"),
    ]


def test_the_llm_source(tmp_path):
    cfg = _cfg(tmp_path)
    with pytest.raises(RuntimeError, match="run `bsim llm-train` first"):
        extra_links(cfg, "llm")
    triage(
        cfg,
        [
            (0, 6, "ok", "real", 0.9),  # a positive
            (1, 7, "ok", "real", 0.6),  # real, below min_p 0.7: left out
            (2, 11, "ok", "real", 0.95),  # a dev book: kept with its split, never trained
            (3, 8, "ok", "not", 0.1),  # a hard negative
            (4, 9, "ok", "not", 0.5),  # not, above max_p_not 0.3: left out
            (0, 9, "ok", "unsure", 0.5),
        ],
    )
    df = extra_links(cfg, "llm")
    got = {(a, b, s) for a, b, s in zip(df.src_vid, df.tgt_vid, df.split, strict=True)}
    assert got == {(0, 6, "train"), (6, 0, "train"), (2, 11, "dev"), (11, 2, "dev")}
    assert llm_negatives(cfg) == {3: {8}, 8: {3}}
    pd.DataFrame(
        {"src_vid": [5, 10], "tgt_vid": [10, 5], "split": "dev", "level": "verse"}
    ).to_parquet(resolve_path(cfg, "data_processed") / "links.parquet")
    pairs, _ = training_pairs(with_overrides(cfg, extra_pairs=["llm"]))
    assert pairs.source.tolist() == ["llm"] * 2  # the train pair, both ways


def test_build_items_skips_what_the_triage_judged(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    cfg["llm_train"] = {**cfg["llm_train"], "pairs": 3}
    triage(cfg, [(1, 2, "ok", "real", 0.9), (4, 3, "ok", "not", 0.1)])
    asked = []

    def queue(cfg, n):
        asked.append(n)
        return pd.DataFrame({"a": [1, 3, 5, 6, 7, 8], "b": [2, 4, 9, 10, 11, 12]})

    monkeypatch.setattr(lt, "queue_pairs", queue)
    monkeypatch.setattr(
        lt, "calibration_set", lambda cfg, cal, seed: pd.DataFrame(
            {"a": [0, 1], "b": [10, 11], "gold": [True, False]})
    )  # fmt: skip
    items = lt.build_items(cfg, log=lambda s: None)
    assert asked == [5]  # the pairs asked for, and as many again as the triage judged
    tr = items[items.set == "train"]
    assert list(zip(tr.a, tr.b, strict=True)) == [(5, 9), (6, 10), (7, 11)]
    assert tr.custom_id.tolist() == ["trn-0", "trn-1", "trn-2"]
    assert items[items.set == "calibration"].custom_id.tolist() == ["cal-0", "cal-1"]


def _ans(verdict, p):
    return {"verdict": verdict, "p_real": p, "kind": "allusion", "rationale": "שמים"}


def test_a_run(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    items = pd.DataFrame(
        {
            "set": ["calibration"] * 2 + ["train"] * 2,
            "custom_id": ["cal-0", "cal-1", "trn-0", "trn-1"],
            "a": [0, 1, 5, 6],
            "b": [10, 11, 9, 8],
            "gold": [True, False, None, None],
        }
    )
    monkeypatch.setattr(lt, "build_items", lambda cfg, log: items)
    monkeypatch.setattr(
        lt, "verse_texts", lambda cfg: {i: {"ref": f"R {i}", "text": "א"} for i in range(15)}
    )
    client, batches = fake_client({})
    dry = lt.run_llm_train(cfg, log=lambda s: None, dry_run=True, client=client)
    assert dry["requests"] == 4 and batches.created == []
    answers = {"cal-0": _ans("real", 0.9), "cal-1": _ans("not", 0.1),
               "trn-0": _ans("real", 0.8), "trn-1": _ans("not", 0.2)}  # fmt: skip
    client, _ = fake_client(answers)
    meta = lt.run_llm_train(cfg, log=lambda s: None, client=client, sleep=lambda s: None)
    assert meta["calibration"]["holds"] and meta["train"]["verdicts"]["real"] == 1
    df = lt.judged_runs(cfg)
    assert list(zip(df.a, df.b, df.verdict, strict=True)) == [(5, 9, "real"), (6, 8, "not")]
