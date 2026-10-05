import numpy as np
import pandas as pd
import pytest
import torch

from bsim.embed.context import centre_mask, pooled, windows
from bsim.eval.experiments import cross_fit, rrf_many
from bsim.eval.metrics import paired_bootstrap, per_query
from bsim.retrieve.fusion import rrf
from bsim.retrieve.maxsim import TokenStore, maxsim_scores, score_lists


def test_windows_stay_inside_the_group():
    texts = ["aa", "bbb", "c", "dd"]
    group = np.array([1, 1, 1, 2])
    w = windows(texts, group, 1)
    assert w[0] == ("aa bbb", 0, 2)
    assert w[1] == ("aa bbb c", 3, 6)
    assert w[2] == ("bbb c", 4, 5)  # verse 3 is in another chapter
    assert w[3] == ("dd", 0, 2)
    for text, s, e in w:
        assert text[s:e] in texts


def test_centre_mask_and_pooling():
    offsets = np.array([[0, 0], [0, 2], [3, 6], [7, 8], [0, 0]])
    special = np.array([True, False, False, False, True])
    assert centre_mask(offsets, special, 3, 6).tolist() == [False, False, True, False, False]
    hidden = np.array([[[1.0, 0.0], [0.0, 2.0], [3.0, 0.0]]])
    out = pooled(hidden, {"all": np.ones((1, 3), bool), "last": np.array([[False, False, True]])})
    assert out["last"][0] == pytest.approx([1.0, 0.0])
    assert np.linalg.norm(out["all"][0]) == pytest.approx(1.0)
    assert out["all"][0] == pytest.approx(np.array([4.0, 2.0]) / np.hypot(4, 2))


def _brute(a: np.ndarray, b: np.ndarray, symmetric: bool) -> float:
    s = a @ b.T
    fwd = s.max(1).mean()
    return (fwd + s.max(0).mean()) / 2 if symmetric else fwd


def test_maxsim_matches_brute_force():
    rng = np.random.default_rng(0)
    parts = [rng.normal(size=(n, 4)).astype(np.float32) for n in (2, 5, 3, 1)]
    parts = [p / np.linalg.norm(p, axis=1, keepdims=True) for p in parts]
    store = TokenStore.build(parts, torch.device("cpu"))
    cand = pd.DataFrame({"src": [0, 0, 0, 2, 2], "tgt": [1, 2, 3, 0, 3], "rank": [1, 2, 3, 1, 2]})
    for sym in (False, True):
        got = score_lists(store, cand, batch=1, symmetric=sym, device=torch.device("cpu"))
        want = [_brute(parts[s], parts[t], sym) for s, t in zip(cand.src, cand.tgt, strict=True)]
        assert got == pytest.approx(want, abs=1e-5)
    q, qm = store.gather(torch.tensor([3]))
    d, dm = store.gather(torch.tensor([[3]]))
    assert maxsim_scores(q, qm, d, dm, True).item() == pytest.approx(1.0, abs=1e-6)  # itself


def test_rrf_many_equals_two_way_rrf():
    lex = pd.DataFrame({"src": [0, 0, 1], "tgt": [1, 2, 0], "rank": [1, 2, 1], "score": 1.0})
    sem = pd.DataFrame({"src": [0, 0, 1], "tgt": [3, 1, 2], "rank": [1, 2, 1], "score": 1.0})
    a = rrf(lex, sem, 0.5, 1.0, 60, 50)
    b = rrf_many([lex, sem], [0.5, 1.0], 60, 50)
    assert a[["src", "tgt", "rank"]].values.tolist() == b[["src", "tgt", "rank"]].values.tolist()
    assert a.score.to_numpy() == pytest.approx(b.score.to_numpy())
    c = rrf_many([lex, sem, sem], [1.0, 1.0, 1.0], 60, 2)
    assert c.groupby("src").size().max() == 2


def test_per_query_and_bootstrap():
    gold = {1: {5}, 2: {6, 7}, 3: set()}
    pq = per_query({1: [5, 9], 2: [9, 6]}, gold, "recall@1")
    assert pq == {1: 1.0, 2: 0.0}  # query 3 has no gold; queries without lists score 0
    b = paired_bootstrap([0.1, 0.2, -0.1, 0.0], reps=2000, seed=1)
    assert b["mean"] == pytest.approx(0.05)
    assert b["lo"] < b["mean"] < b["hi"]
    assert (b["better"], b["worse"], b["queries"]) == (2, 1, 4)
    assert paired_bootstrap([0.1] * 10, 500, 1)["lo"] == pytest.approx(0.1)


def test_cross_fit_chooses_out_of_fold():
    base = np.zeros(8)
    members = {"good": np.full(8, 0.2), "bad": np.full(8, -0.1)}
    gains, chosen = cross_fit(members, base, folds=2, seed=0)
    assert chosen == ["good", "good"]
    assert gains == pytest.approx(np.full(8, 0.2))
