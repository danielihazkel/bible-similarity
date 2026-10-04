import json

import numpy as np
import pandas as pd

from bsim.analysis.phrases import align, candidate_pairs, find_phrases
from bsim.lexical.tokens import Stream


def test_align_contiguous_phrase():
    a = ["x", "p", "q", "r", "y"]
    b = ["p", "q", "z", "r"]
    al = align(a, b, [1.0] * 5, [1.0] * 4, mismatch=1.5, gap=1.5)
    assert (al.a_pos, al.b_pos) == ([1, 2], [0, 1])  # the gap before r costs more than r gains
    al = align(a, b, [1.0, 5.0, 5.0, 5.0, 1.0], [5.0, 5.0, 1.0, 5.0], mismatch=1.5, gap=1.5)
    assert (al.a_pos, al.b_pos) == ([1, 2, 3], [0, 1, 3])  # a rare r bridges the mismatch
    assert al.score == 5 + 5 - 1.5 + 5  # p, q, a gap over b's z, r


def test_align_order_matters():
    al = align(["p", "q", "r"], ["r", "q", "p"], [3.0] * 3, [3.0] * 3, 1.5, 1.5)
    assert len(al.a_pos) == 1  # same words, reversed: no phrase


def test_align_empty():
    assert align([], ["p"], [], [1.0], 1, 1).score == 0


def test_candidate_pairs_dedupe_and_neighbours():
    topk = pd.DataFrame(
        {
            "src_id": ["v:0", "v:5", "v:0", "v:1"],
            "tgt_id": ["v:5", "v:0", "v:1", "v:9"],
            "rank": [1, 1, 2, 60],
        }
    )
    book = np.zeros(10, dtype=int)
    assert candidate_pairs(topk, book, 50, 2).tolist() == [[0, 5]]


def test_find_phrases_maps_word_indices():
    s0 = Stream(["p", "q", "r"], [0, 1, 1])  # one word may carry two lemma tokens
    s1 = Stream(["z", "p", "q", "r"], [0, 1, 2, 3])
    w = [np.full(3, 5.0), np.full(4, 5.0)]
    cfg = {"phrases": {"mismatch": 1.5, "gap": 1.5, "min_tokens": 3, "min_score": 14}}
    df = find_phrases([s0, s1], w, np.array([[0, 1]]), cfg)
    assert df[["a", "b", "score", "n_tokens"]].values.tolist() == [[0, 1, 15.0, 3]]
    assert json.loads(df.a_words[0]) == [0, 1] and json.loads(df.b_words[0]) == [1, 2, 3]
    assert df.spread[0] == 2
    cfg["phrases"]["min_score"] = 16
    assert find_phrases([s0, s1], w, np.array([[0, 1]]), cfg).empty


def test_spread_counts_verses_sharing_a_phrase():
    s = [Stream(["p", "q", "r"], [0, 1, 2]) for _ in range(3)]
    s += [Stream(["x", "y", "z"], [0, 1, 2]) for _ in range(2)]
    w = [np.full(3, 5.0)] * 5
    cfg = {"phrases": {"mismatch": 1.5, "gap": 1.5, "min_tokens": 3, "min_score": 14}}
    df = find_phrases(s, w, np.array([[0, 1], [0, 2], [1, 2], [3, 4]]), cfg)
    spread = {(a, b): n for a, b, n in df[["a", "b", "spread"]].itertuples(index=False)}
    assert spread == {(0, 1): 3, (0, 2): 3, (1, 2): 3, (3, 4): 2}
