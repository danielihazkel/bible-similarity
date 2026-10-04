import numpy as np
import pandas as pd
import pytest

from bsim.analysis.corpus_map import book_affinity, book_order, cross_book_pairs, unit_vectors


def test_unit_vectors_mean_then_normalize():
    emb = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]])
    v = unit_vectors(emb, np.array([0, 2]), np.array([1, 2]))
    assert v[0] == pytest.approx([2**-0.5, 2**-0.5]) and v[1] == pytest.approx([1.0, 0.0])


def test_cross_book_pairs_unordered_best_score():
    topk = pd.DataFrame(
        {"src": [0, 3, 0, 1], "tgt": [3, 0, 1, 3], "rank": [1, 2, 1, 20], "score": [0.5, 0.9, 1, 1]}
    )
    book = np.array([0, 0, 1, 1])
    df = cross_book_pairs(topk, book, max_rank=10)
    assert df.values.tolist() == [[0, 3, 0.9]]  # 0-1 same book, 1-3 beyond rank 10


def test_book_affinity_lift_and_order():
    book = np.array([0, 0, 1, 1, 2, 2])
    pairs = pd.DataFrame({"a": [0, 1, 2], "b": [2, 3, 4]})  # 0-1 twice, 1-2 once
    aff, m = book_affinity(pairs, book, 3)
    assert aff[["a_book", "b_book", "n_pairs"]].values.tolist() == [[0, 1, 2], [0, 2, 0], [1, 2, 1]]
    assert aff.expected.sum() == pytest.approx(3) and aff.lift.iloc[0] == pytest.approx(2.0)
    assert m[1, 0] == 2
    order = book_order(aff, 3)
    assert sorted(order) == [0, 1, 2] and abs(order.index(0) - order.index(1)) == 1
