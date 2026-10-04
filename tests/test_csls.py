import json

import numpy as np
import torch

from bsim.config import load_config
from bsim.embed.csls import csls_scorer, hubness
from bsim.retrieve.topk import dense_scorer, read_topk, run_topk, topk_chunks

CPU = torch.device("cpu")


def _emb(n: int = 12, d: int = 5, seed: int = 1) -> np.ndarray:
    e = np.random.default_rng(seed).normal(size=(n, d)).astype(np.float32)
    return e / np.linalg.norm(e, axis=1, keepdims=True)


def _brute_r(e: np.ndarray, k: int) -> np.ndarray:
    s = e @ e.T
    np.fill_diagonal(s, -np.inf)
    return np.sort(s, axis=1)[:, ::-1][:, :k].mean(axis=1)


def test_hubness_matches_brute_force():
    e = _emb()
    assert np.allclose(hubness(e, 3, 5, CPU), _brute_r(e, 3), atol=1e-6)


def test_csls_topk_matches_brute_force():
    e = _emb()
    r = _brute_r(e, 3)
    s = 2 * (e @ e.T) - r[:, None] - r[None, :]
    np.fill_diagonal(s, -np.inf)
    idx, sc = topk_chunks(csls_scorer(e, r, CPU), len(e), 4, 5, CPU)
    assert idx.tolist() == np.argsort(-s, axis=1, kind="stable")[:, :4].tolist()
    assert np.allclose(sc, np.take_along_axis(s, idx, axis=1), atol=1e-5)


def test_csls_demotes_a_hub():
    e = _emb(40, 8)
    hub = e.mean(axis=0)
    e = np.vstack([e, hub / np.linalg.norm(hub)]).astype(np.float32)
    h = len(e) - 1
    k = 3
    cos_idx, _ = topk_chunks(dense_scorer(e, CPU), len(e), k, 16, CPU)
    csls_idx, _ = topk_chunks(csls_scorer(e, hubness(e, 5, 16, CPU), CPU), len(e), k, 16, CPU)
    assert (csls_idx == h).sum() < (cos_idx == h).sum()


def test_run_topk_resolves_csls_variant(tmp_path):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "artifacts": str(tmp_path)}
    cfg["retrieval"] = {**cfg["retrieval"], "device": "cpu", "chunk_size": 4, "k": 3}
    (tmp_path / "embeddings").mkdir()
    np.save(tmp_path / "embeddings" / "toy.npy", _emb())
    run_topk(cfg, "toy_csls", log=lambda _: None)
    out = tmp_path / "topk" / "verse"
    df = read_topk(out / "toy_csls.parquet")
    assert (df.src != df.tgt).all() and df.groupby("src").size().eq(3).all()
    meta = json.loads((out / "toy_csls.meta.json").read_text("utf-8"))
    assert meta["kind"] == "dense" and meta["source"] == "toy.npy"
