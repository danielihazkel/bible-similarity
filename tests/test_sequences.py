import json

import numpy as np
import pandas as pd
import pytest

from bsim.analysis.sequences import (
    all_chains,
    candidate_pairs,
    chain_frame,
    find_chains,
    q_values,
    shuffle_within,
)

BOOK = np.array([0] * 20 + [1] * 20)


def chains(pairs, w=None, book=BOOK, max_step=3, gap=0.25, min_pairs=3, direction="forward"):
    a = np.array([p[0] for p in pairs])
    b = np.array([p[1] for p in pairs])
    w = np.ones(len(pairs)) if w is None else np.array(w, dtype=float)
    return find_chains(a, b, w, book, max_step, gap, min_pairs, direction=direction)


def test_candidate_pairs_unordered_best_rank_no_neighbours():
    topk = pd.DataFrame(
        {
            "src_id": ["v:0", "v:30", "v:0", "v:5"],
            "tgt_id": ["v:30", "v:0", "v:1", "v:25"],
            "rank": [4, 1, 1, 3],
        }
    )
    df = candidate_pairs(topk, BOOK, max_rank=3, window=2)
    # (0, 30): rank 4 is outside the top 3, its reverse (rank 1) counts; (0, 1) are neighbours
    assert df.values.tolist() == [[0, 30, 1.0], [5, 25, 1 / 3]]


def test_find_chains_diagonal_with_a_skip():
    # 2..6 parallel to 22..26 with verse 4 missing on the a side and 24 on the b side
    found = chains([(2, 22), (3, 23), (5, 25), (6, 26)])
    assert len(found) == 1
    c = found[0]
    assert (c.a, c.b) == ([2, 3, 5, 6], [22, 23, 25, 26])
    assert c.score == pytest.approx(4 - 0.25 * 2)


def test_find_chains_stops_at_book_boundaries_and_rejects_out_of_order():
    # 18, 19 are the end of book 0 and 20, 21 the start of book 1: no chain across that line
    assert chains([(18, 30), (19, 31), (20, 32), (21, 33)], min_pairs=3) == []
    # reverse order (b decreasing) never chains
    assert chains([(2, 30), (3, 29), (4, 28), (5, 27)], min_pairs=2) == []


def test_find_chains_rejects_overlapping_spans_and_short_chains():
    # a tandem repeat: 2..6 ~ 5..9 inside one passage
    assert chains([(2, 5), (3, 6), (4, 7), (5, 8), (6, 9)]) == []
    assert chains([(2, 22), (3, 23)]) == []  # below min_pairs


def test_find_chains_each_pair_used_once_strongest_first():
    strong = [(2, 22), (3, 23), (4, 24), (5, 25)]
    weak = [(10, 30), (11, 31), (12, 32)]
    found = chains(strong + weak, w=[1, 1, 1, 1, 0.5, 0.5, 0.5])
    assert [c.a for c in found] == [[2, 3, 4, 5], [10, 11, 12]]
    assert {p for c in found for p in zip(c.a, c.b, strict=True)} == set(strong + weak)


def test_shuffle_within_keeps_groups():
    groups = np.array([0, 0, 0, 1, 1, 2])
    perm = shuffle_within(groups, np.random.default_rng(0))
    assert sorted(perm.tolist()) == list(range(6))
    assert (groups[perm] == groups).all()


def test_q_values():
    obs = np.array([10.0, 5.0, 1.0])
    null = np.array([1.0, 1.0, 6.0, 0.5])  # 2 replicates
    q = q_values(obs, null, reps=2)
    # s=10: 0 null / 1 obs; s=5: (1/2) / 2; s=1: (3/2) / 3
    assert q.tolist() == pytest.approx([0.0, 0.25, 0.5])
    assert q_values(np.array([]), null, 2).tolist() == []
    # monotone: a weaker chain never gets a smaller q
    # raw: s=5 0/1, s=4 1/2, s=3 1/3, s=2 1/4 -> the stronger chains inherit 1/4
    q2 = q_values(np.array([3.0, 5.0, 2.0, 4.0]), np.array([4.5]), reps=1)
    assert q2.tolist() == pytest.approx([0.25, 0.0, 0.25, 0.25])


def test_chain_frame():
    c = chains([(2, 22), (3, 23), (4, 24)])
    chapter = np.array([1] * 40)
    df = chain_frame([("forward", c[0])], np.array([0.01]), BOOK, chapter)
    row = df.iloc[0]
    assert (row.seq_id, row.a_start, row.a_end, row.b_start, row.b_end) == (1, 2, 4, 22, 24)
    assert row.direction == "forward"
    assert (row.a_book, row.b_book, bool(row.same_chapter)) == (0, 1, False)
    assert json.loads(row.pairs) == [[2, 22, 1.0], [3, 23, 1.0], [4, 24, 1.0]]


def test_reverse_chains_mirror_and_spans_are_min_max():
    pairs = [(2, 26), (3, 25), (4, 24), (5, 23)]
    assert chains(pairs) == []  # no same-order chain
    (c,) = chains(pairs, direction="reverse")
    assert c.a == [2, 3, 4, 5] and c.b == [26, 25, 24, 23]
    row = chain_frame([("reverse", c)], np.array([0.5]), BOOK, np.ones(40, int)).iloc[0]
    assert (row.b_start, row.b_end, row.direction) == (23, 26, "reverse")


def test_reverse_chain_nested_in_one_passage_is_kept():
    # A B C ... C' B' A' inside one chapter: a chiasm, not an overlapping tandem repeat
    (c,) = chains([(1, 9), (2, 8), (3, 7)], direction="reverse")
    assert c.a == [1, 2, 3] and c.b == [9, 8, 7]
    assert chains([(1, 3), (2, 2), (3, 1)], direction="reverse") == []  # crossing spans


def test_all_chains_order_dedup_and_monotone_mixed_dropped():
    s = {
        "directions": ["forward", "reverse", "mixed"],
        "max_step": 3,
        "gap": 0.25,
        "min_pairs": 3,
        "max_overlap": 0.5,
    }
    fwd = [(1, 21), (2, 22), (3, 23)]
    mixed = [(10, 32), (11, 30), (12, 33), (13, 31)]  # b goes back and forth
    pairs = fwd + mixed
    a, b = np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs])
    got = all_chains(a, b, np.ones(len(pairs)), BOOK, s)
    kinds = [(d, c.a) for d, c in got]
    assert ("forward", [1, 2, 3]) in kinds
    assert ("mixed", [10, 11, 12, 13]) in kinds
    # the forward chain is not repeated as a monotone "mixed" one
    assert sum(c.a == [1, 2, 3] for _, c in got) == 1
