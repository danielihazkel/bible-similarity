from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bsim.config import load_config
from bsim.train.common import BestCheckpointCallback
from bsim.train.dev_eval import DevEvaluator
from bsim.train.simcse import simcse_texts

# 8 verses: book 1 = vids 0..3 (chapter 1), book 2 = vids 4..7 (chapter 1)
BOOK = [1, 1, 1, 1, 2, 2, 2, 2]


def _cfg(tmp_path):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(tmp_path), "models": str(tmp_path)}
    cfg["retrieval"] = {**cfg["retrieval"], "device": "cpu", "k": 5, "chunk_size": 3}
    cfg["eval"] = {**cfg["eval"], "ks": [1, 5], "rank_k": 5}
    return cfg


def _write_fixture(tmp_path, dev_pairs):
    pd.DataFrame({"verse_id": range(8), "book_id": BOOK, "chapter": [1] * 8}).to_parquet(
        tmp_path / "verses.parquet"
    )
    rows = [(s, t) for a, b in dev_pairs for s, t in ((a, b), (b, a))]
    pd.DataFrame(
        {
            "src_vid": [s for s, _ in rows],
            "tgt_vid": [t for _, t in rows],
            "level": "verse",
            "split": "dev",
        }
    ).to_parquet(tmp_path / "links.parquet")


def _emb(groups):
    """One-hot-ish unit vectors: verses in the same group share a direction."""
    e = np.zeros((8, 8), np.float32)
    for v, g in enumerate(groups):
        e[v, g] = 1.0
        e[v, 7] = 0.01 * v  # break ties deterministically
    return e / np.linalg.norm(e, axis=1, keepdims=True)


def test_simcse_texts_dedupes_in_order():
    assert simcse_texts(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]


def test_dev_evaluator_perfect_and_shuffled(tmp_path):
    _write_fixture(tmp_path, [(0, 4), (2, 6)])
    ev = DevEvaluator(_cfg(tmp_path))
    good = ev(_emb([0, 1, 2, 3, 0, 4, 2, 5]))  # 0~4, 2~6 nearest
    assert good["queries"] == 4
    assert good["recall@1"] == pytest.approx(1.0)
    bad = ev(_emb([0, 1, 2, 3, 4, 0, 5, 2]))  # 0~5, 2~7: wrong partners
    assert bad["recall@1"] < good["recall@1"]


def test_dev_evaluator_filters_neighbours(tmp_path):
    _write_fixture(tmp_path, [(0, 4)])
    ev = DevEvaluator(_cfg(tmp_path))
    # 0, 1, 4 share a direction. Query 0 ranks 1 (its ±2 neighbour, filtered) then 4 -> MRR 1;
    # query 4 ranks 1 (other book, kept) then 0 -> MRR 1/2. Unfiltered, query 0 would get 1/2.
    m = ev(_emb([0, 0, 1, 2, 0, 3, 4, 5]))
    assert m["mrr@5"] == pytest.approx(0.75)


def test_dev_evaluator_requires_inputs(tmp_path):
    with pytest.raises(RuntimeError, match="build-corpus"):
        DevEvaluator(_cfg(tmp_path))


class FakeModel:
    def __init__(self):
        self.saves = 0

    def encode(self, texts, batch_size, normalize_embeddings, convert_to_numpy, **_):
        return np.eye(len(texts), dtype=np.float32)

    def save(self, path):
        self.saves += 1


class State:
    def __init__(self, epoch, global_step=0):
        self.epoch, self.global_step = epoch, global_step


def _callback(model, scores, eval_steps=None):
    return BestCheckpointCallback(
        model,
        ["a", "b"],
        lambda emb: {"recall@10": next(scores), "queries": 2},
        "recall@10",
        Path("unused"),
        2,
        log=lambda _: None,
        eval_steps=eval_steps,
    )


def test_epoch_select_saves_only_improvements():
    model = FakeModel()
    cb = _callback(model, iter([0.2, 0.5, 0.4, 0.6]))
    cb.score(0, 0.0)
    for epoch in (1, 2, 3):
        cb.on_step_end(None, State(epoch - 0.5, 10 * epoch - 5), None)  # no eval_steps: ignored
        cb.on_epoch_end(None, State(float(epoch), 10 * epoch), None)
    assert [h["step"] for h in cb.history] == [0, 10, 20, 30]
    assert model.saves == 2  # epochs 1 and 3; the step-0 reference is never saved
    assert cb.best_epoch == 3 and cb.best_step == 30 and cb.best == pytest.approx(0.6)


def test_step_select_scores_every_n_steps_once():
    model = FakeModel()
    cb = _callback(model, iter([0.1, 0.3, 0.2, 0.25]), eval_steps=4)
    for step in range(1, 9):
        cb.on_step_end(None, State(step / 8, step), None)
    cb.on_epoch_end(None, State(1.0, 8), None)  # step 8 already scored: skipped
    cb.on_epoch_end(None, State(1.25, 10), None)
    assert [h["step"] for h in cb.history] == [4, 8, 10]
    assert cb.best_step == 8 and model.saves == 2


def test_berel_simcse_registered():
    cfg = load_config()
    spec = cfg["encoders"]["systems"]["berel_simcse"]
    assert spec["pooling"] == "native"
    assert spec["model"].endswith(cfg["train"]["simcse"]["output"])


def test_berel_sup_registered():
    cfg = load_config()
    spec = cfg["encoders"]["systems"]["berel_sup"]
    assert spec["pooling"] == "native"
    assert spec["model"].endswith(cfg["train"]["supervised"]["output"])
