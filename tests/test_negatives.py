import numpy as np
import pandas as pd
import pytest

from bsim.train.negatives import linked_sets, mine_hard_negatives
from bsim.train.supervised import with_overrides

# 15 verses: book 0 = vids 0..4, book 1 = vids 5..9 (train), book 2 = vids 10..14 (dev)
BOOK = np.repeat([0, 1, 2], 5)
TRAIN_BOOK = np.array([True, True, False])
WINDOW = 1


def _candidates(src, tgts):
    """A neighbour-filtered top-k frame for one query: ranks 1.. in the given order."""
    return pd.DataFrame({"src": src, "tgt": tgts, "rank": np.arange(1, len(tgts) + 1)})


def _mine(anchors, positives, cand, linked=None, text_key=None, rank_range=(2, 10), seed=0):
    return mine_hard_negatives(
        np.array(anchors),
        np.array(positives),
        cand,
        BOOK,
        TRAIN_BOOK,
        linked or {},
        np.arange(15) if text_key is None else np.asarray(text_key),
        rank_range,
        WINDOW,
        seed,
    )


def test_only_eligible_candidates_are_drawn():
    # anchor 0, positive 8. Candidate list (rank 1..9):
    #   9 rank 1: below the rank range
    #   10 dev book; 1 neighbour of the anchor; 7 neighbour of the positive;
    #   3 linked to the anchor; 4 linked to the positive; 2 same text as the positive
    #   5 and 6 eligible (ranks 8, 9)
    cand = _candidates(0, [9, 10, 1, 7, 3, 4, 2, 5, 6])
    linked = {0: {8, 3}, 8: {0, 4}}
    text_key = np.arange(15)
    text_key[2] = text_key[8]
    picks = {
        int(_mine([0], [8], cand, linked, text_key, seed=s).negative_vid[0]) for s in range(20)
    }
    assert picks == {5, 6}


def test_rank_and_fallback_columns():
    cand = _candidates(0, [6, 7])
    df = _mine([0, 1], [5, 5], cand)  # anchor 1 has no candidates -> fallback
    assert df.negative_vid[0] == 7 and df.negative_rank[0] == 2  # rank 1 is out of range
    assert not df.fallback[0]
    assert df.fallback[1] and df.negative_rank[1] == 0
    n = int(df.negative_vid[1])
    assert TRAIN_BOOK[BOOK[n]] and n not in (0, 1, 2, 4, 5, 6)  # not anchor/positive ±1


def test_deterministic_for_seed():
    cand = _candidates(0, list(range(5, 10)))
    a = _mine([0] * 10, [3] * 10, cand, seed=7)
    b = _mine([0] * 10, [3] * 10, cand, seed=7)
    pd.testing.assert_frame_equal(a, b)


def test_no_eligible_verse_raises():
    small_train = np.array([True, False, False])
    with pytest.raises(RuntimeError, match="no eligible negative"):
        mine_hard_negatives(
            np.array([0]),
            np.array([4]),
            _candidates(0, []),
            BOOK,
            small_train,
            {0: {2}},
            np.arange(15),
            (1, 10),
            WINDOW,
            0,
        )


def test_linked_sets_uses_verse_rows_of_every_split():
    links = pd.DataFrame(
        {
            "src_vid": [0, 7, 3, 10],
            "tgt_vid": [7, 0, 11, 3],
            "level": ["verse", "verse", "unit", "verse"],
        }
    )
    assert linked_sets(links) == {0: {7}, 7: {0}, 10: {3}}


def test_with_overrides_copies():
    cfg = {"train": {"supervised": {"init_from": "berel-simcse", "hard_negatives": True}}}
    out = with_overrides(cfg, init="base", hard_negatives=False)
    assert out["train"]["supervised"] == {"init_from": "base", "hard_negatives": False}
    assert cfg["train"]["supervised"]["init_from"] == "berel-simcse"
