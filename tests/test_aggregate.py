import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp
import torch

from bsim.config import load_config
from bsim.embed.csls import csls_scorer
from bsim.retrieve.topk import Units, dense_scorer
from bsim.retrieve.units import (
    bma_matrix,
    matrix_scorer,
    mean_vectors,
    member_index,
    run_units,
    sparse_cosine_scorer,
)

CPU = torch.device("cpu")


def _emb(n: int = 10, d: int = 4, seed: int = 0) -> np.ndarray:
    e = np.random.default_rng(seed).normal(size=(n, d)).astype(np.float32)
    return e / np.linalg.norm(e, axis=1, keepdims=True)


def _units(ranges: list[tuple[int, int]]) -> Units:
    start, end = (np.array(x, np.int64) for x in zip(*ranges, strict=True))
    return Units(np.array([f"u:{i}" for i in range(len(ranges))], dtype=object), start, end)


def _brute_bma(s: np.ndarray, units: Units) -> np.ndarray:
    n = len(units)
    rng = [range(a, b + 1) for a, b in zip(units.start, units.end, strict=True)]
    d = np.array(
        [
            [np.mean([max(s[a, b] for b in rng[j]) for a in rng[i]]) for j in range(n)]
            for i in range(n)
        ]
    )
    return (d + d.T) / 2


@pytest.mark.parametrize("chunk", [1, 3, 100])
def test_bma_matches_brute_force(chunk):
    e = _emb()
    units = _units([(0, 2), (3, 3), (4, 8), (9, 9)])
    got = bma_matrix(dense_scorer(e, CPU), units, chunk, CPU)
    np.testing.assert_allclose(got, _brute_bma(e @ e.T, units), rtol=1e-5, atol=1e-6)
    np.testing.assert_allclose(got, got.T)


def test_bma_on_a_subset_of_verses_uses_only_member_columns():
    # parasha-like: units cover verses 0..5 of 10; verses 6..9 must not count as best matches
    e = _emb()
    e[6:] = e[0]  # perfect matches for unit 0 outside the units
    units = _units([(0, 1), (2, 3), (4, 5)])
    got = bma_matrix(dense_scorer(e, CPU), units, 4, CPU)
    np.testing.assert_allclose(got, _brute_bma(e @ e.T, units), rtol=1e-5, atol=1e-6)


def test_bma_with_csls_scores():
    e = _emb()
    r = np.linspace(0.1, 0.5, len(e)).astype(np.float32)
    s = 2 * (e @ e.T) - r[:, None] - r[None, :]
    units = _units([(0, 4), (5, 9)])
    got = bma_matrix(csls_scorer(e, r, CPU), units, 3, CPU)
    np.testing.assert_allclose(got, _brute_bma(s, units), rtol=1e-5, atol=1e-6)


def test_member_index_rejects_overlap():
    with pytest.raises(RuntimeError):
        member_index(_units([(0, 3), (3, 5)]))


def test_mean_vectors():
    e = _emb()
    units = _units([(0, 2), (3, 9)])
    got = mean_vectors(e, units)
    want = np.stack([e[0:3].mean(0), e[3:10].mean(0)])
    want /= np.linalg.norm(want, axis=1, keepdims=True)
    np.testing.assert_allclose(got, want, rtol=1e-5, atol=1e-6)


def test_matrix_scorer_does_not_alias_the_matrix():
    m = np.arange(9, dtype=np.float32).reshape(3, 3)
    block = matrix_scorer(m, CPU)(0, 2)
    block[0, 0] = -np.inf
    assert matrix_scorer(m, CPU)(0, 1)[0, 0] == 0


def test_sparse_cosine_scorer():
    x = sp.csr_matrix(np.array([[1, 0], [0.6, 0.8], [0, 1]], dtype=np.float32))
    np.testing.assert_allclose(sparse_cosine_scorer(x)(1, 3), (x @ x.T).toarray()[1:3])


def test_run_units_writes_semantic_and_tfidf(tmp_path):
    cfg = load_config()
    proc, art = tmp_path / "processed", tmp_path / "artifacts"
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art)}
    cfg["units"] = {**cfg["units"], "types": ["verse", "chapter"]}
    cfg["retrieval"] = {**cfg["retrieval"], "device": "cpu", "csls_neighbors": 1}
    proc.mkdir()
    # stored out of canon order: load_units sorts by start verse
    pd.DataFrame(
        {
            "unit_id": ["c:1", "c:0", "c:2"],
            "unit_type": "chapter",
            "start_verse_id": [3, 0, 6],
            "end_verse_id": [5, 2, 9],
        }
    ).to_parquet(proc / "units.parquet")
    (art / "embeddings").mkdir(parents=True)
    np.save(art / "embeddings" / "toy.npy", _emb())
    lex = art / "lexical"
    lex.mkdir()
    x = sp.csr_matrix(np.array([[0, 1], [1, 0], [0.6, 0.8]], dtype=np.float32))  # c:1, c:0, c:2
    sp.save_npz(lex / "tfidf_chapter.npz", x)
    (lex / "tfidf_chapter.ids.json").write_text('["c:1", "c:0", "c:2"]')

    run_units(cfg, "toy", log=lambda _: None)
    run_units(cfg, "toy_csls", log=lambda _: None)
    run_units(cfg, "tfidf", log=lambda _: None)
    out = art / "topk" / "chapter"
    for name in ("toy_bma", "toy_mean", "toy_csls_bma", "toy_csls_mean"):
        df = pd.read_parquet(out / f"{name}.parquet")
        assert len(df) == 6 and (df.src_id != df.tgt_id).all()
        assert set(df.unit_type) == {"chapter"}
        assert (out / f"{name}.meta.json").exists()
    tf = pd.read_parquet(out / "tfidf.parquet")
    # c:0 = [1, 0] and c:1 = [0, 1] share nothing -> dropped; c:2 matches both
    pairs = set(zip(tf.src_id, tf.tgt_id, strict=True))
    assert pairs == {("c:0", "c:2"), ("c:1", "c:2"), ("c:2", "c:1"), ("c:2", "c:0")}
    top = tf[(tf.src_id == "c:2") & (tf["rank"] == 1)].tgt_id.item()
    assert top == "c:1"  # cos 0.8 > 0.6
