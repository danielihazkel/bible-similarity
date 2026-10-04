import json

import numpy as np
import pandas as pd
import pytest
import torch

from bsim.config import load_config, resolve_path
from bsim.lexical import bm25
from bsim.retrieve.filters import apply_filters, exclusion_mask, neighbor_mask
from bsim.retrieve.topk import (
    dense_scorer,
    parse_verse_ids,
    read_topk,
    run_topk,
    sparse_scorer,
    topk_chunks,
    topk_frame,
)

CPU = torch.device("cpu")


def _emb(n: int = 9, d: int = 4, seed: int = 0) -> np.ndarray:
    e = np.random.default_rng(seed).normal(size=(n, d)).astype(np.float32)
    return e / np.linalg.norm(e, axis=1, keepdims=True)


def _brute(e: np.ndarray, k: int) -> np.ndarray:
    s = e @ e.T
    np.fill_diagonal(s, -np.inf)
    return np.argsort(-s, axis=1, kind="stable")[:, :k]


@pytest.mark.parametrize("chunk", [2, 4, 100])
def test_dense_topk_matches_brute_force(chunk):
    e = _emb()
    idx, sc = topk_chunks(dense_scorer(e, CPU), len(e), 3, chunk, CPU)
    assert idx.tolist() == _brute(e, 3).tolist()
    assert (idx != np.arange(len(e))[:, None]).all()
    assert (np.diff(sc, axis=1) <= 0).all()


def test_topk_clamps_k_and_breaks_ties_by_id():
    s = np.ones((4, 4), dtype=np.float32)
    idx, sc = topk_chunks(lambda a, b: s[a:b].copy(), 4, 50, 3, CPU)
    assert idx.tolist() == [[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]]
    assert np.isfinite(sc).all()


@pytest.mark.skipif(not torch.cuda.is_available(), reason="no CUDA")
def test_cuda_matches_cpu():
    e = _emb(50, 8)
    cuda = torch.device("cuda")
    a = topk_chunks(dense_scorer(e, CPU), 50, 5, 16, CPU)
    b = topk_chunks(dense_scorer(e, cuda), 50, 5, 16, cuda)
    assert a[0].tolist() == b[0].tolist()
    assert a[1] == pytest.approx(b[1], abs=1e-5)


def _toy_index() -> bm25.Bm25Index:
    docs = [["a", "b"], ["a", "b"], ["a"], ["c"], ["c", "d"]]
    return bm25.build_bm25(docs, [np.ones(len(d)) for d in docs], 1.2, 0.75)


def test_sparse_topk_drops_zero_scores_and_agrees_with_cpu():
    index = _toy_index()
    idx, sc = topk_chunks(sparse_scorer(index), 5, 4, 2, CPU)
    df = topk_frame(idx, sc, drop_nonpositive=True)
    assert (df.score > 0).all()
    hits = df.groupby("src_id").tgt_id.apply(list).to_dict()
    assert hits["v:0"] == ["v:1", "v:2"]
    assert hits["v:3"] == ["v:4"]
    ref, _ = bm25.topk_cpu(index, np.array([0]), 2)
    assert parse_verse_ids(pd.Series(hits["v:0"])).tolist() == ref[0].tolist()
    assert df[df.src_id == "v:0"]["rank"].tolist() == [1, 2]


def test_run_topk_writes_parquet_and_meta(tmp_path):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "artifacts": str(tmp_path)}
    cfg["retrieval"] = {**cfg["retrieval"], "device": "cpu", "chunk_size": 2, "k": 3}
    bm25.save(_toy_index(), tmp_path / "lexical", "toy")
    run_topk(cfg, "toy", log=lambda _: None)
    out = tmp_path / "topk" / "verse"
    df = read_topk(out / "toy.parquet")
    assert list(df.columns[:5]) == ["unit_type", "src_id", "rank", "tgt_id", "score"]
    assert (df.src != df.tgt).all()
    meta = json.loads((out / "toy.meta.json").read_text("utf-8"))
    assert meta["kind"] == "sparse" and meta["k"] == 3


def test_unknown_system_raises(tmp_path):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "artifacts": str(tmp_path)}
    with pytest.raises(RuntimeError, match="unknown system"):
        run_topk(cfg, "nope", log=lambda _: None)


# --- filters ---------------------------------------------------------------------------------

BOOK = np.array([0, 0, 0, 0, 0, 1, 1, 1])
CHAPTER = np.array([1, 1, 1, 2, 2, 1, 1, 2])


def test_neighbor_mask_respects_book_boundary():
    src = np.array([4, 4, 0, 3])
    tgt = np.array([5, 2, 3, 0])
    assert neighbor_mask(src, tgt, BOOK, 2).tolist() == [False, True, False, False]


def test_exclusion_mask_chapter_and_book():
    src = np.array([0, 0, 0, 5])
    tgt = np.array([2, 3, 5, 7])
    assert exclusion_mask(src, tgt, BOOK, CHAPTER, {"chapter"}, 0).tolist() == [
        True,
        False,
        False,
        False,
    ]
    assert exclusion_mask(src, tgt, BOOK, CHAPTER, {"book"}, 0).tolist() == [
        True,
        True,
        False,
        True,
    ]
    with pytest.raises(ValueError):
        exclusion_mask(src, tgt, BOOK, CHAPTER, {"verse"}, 0)


def test_apply_filters_reranks():
    df = pd.DataFrame(
        {"src": [0, 0, 0, 5], "tgt": [1, 6, 4, 2], "rank": [1, 2, 3, 1], "score": [3, 2, 1, 1]}
    )
    out = apply_filters(df, BOOK, CHAPTER, {"neighbors"}, 2)
    assert out[["src", "tgt", "rank"]].values.tolist() == [[0, 6, 1], [0, 4, 2], [5, 2, 1]]


def test_real_topk_acceptance():
    """Ps 53:2 in the bm25_lemma top-5 of Ps 14:1, if `bsim topk` has been run."""
    cfg = load_config()
    path = resolve_path(cfg, "artifacts") / "topk" / "verse" / "bm25_lemma.parquet"
    if not path.exists():
        pytest.skip("bm25_lemma top-k not built")
    proc = resolve_path(cfg, "data_processed")
    refs = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "ref"])
    vid = dict(zip(refs.ref, refs.verse_id, strict=True))
    df = read_topk(path)
    top = df[(df.src == vid["Psalms 14:1"]) & (df["rank"] <= 5)].tgt.tolist()
    assert vid["Psalms 53:2"] in top


def test_topk_frame_with_unit_ids():
    idx = np.array([[1, 2], [0, 2], [1, 0]], np.int32)
    score = np.array([[0.9, 0.0], [0.5, 0.4], [0.3, -0.1]], np.float32)
    ids = np.array(["c:x", "c:y", "c:z"], dtype=object)
    df = topk_frame(idx, score, drop_nonpositive=True, unit_type="chapter", ids=ids)
    assert set(df.unit_type) == {"chapter"}
    assert list(zip(df.src_id, df.tgt_id, df["rank"], strict=True)) == [
        ("c:x", "c:y", 1),
        ("c:y", "c:x", 1),
        ("c:y", "c:z", 2),
        ("c:z", "c:y", 1),
    ]
