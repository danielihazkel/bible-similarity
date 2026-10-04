from types import SimpleNamespace

import numpy as np
import pandas as pd

from bsim.train.rerank import combine, training_pairs


def frame(rows):
    return pd.DataFrame(rows, columns=["src", "tgt", "rank", "ce_score"])


def test_combine_ce_alone_and_rrf():
    df = frame([(0, 5, 1, 0.1), (0, 6, 2, 0.9), (0, 7, 3, 0.5), (1, 5, 1, 0.0)])
    alone = combine(df, None, 60)
    assert alone[alone.src == 0].tgt.tolist() == [6, 7, 5]
    assert alone[alone.src == 0].fused_rank.tolist() == [2, 3, 1]
    # equal weights: 6 (ce 1, fused 2) beats 5 (ce 3, fused 1) and 7 (ce 2, fused 3)
    mixed = combine(df, 1.0, 60)
    assert mixed[mixed.src == 0].tgt.tolist() == [6, 5, 7]
    assert mixed["rank"].tolist() == [1, 2, 3, 1]
    # a tiny cross-encoder weight keeps the fused order
    assert combine(df, 0.01, 60)[lambda d: d.src == 0].tgt.tolist() == [5, 6, 7]


def test_training_pairs_rules():
    # verses 0-9: books 0 (train) for 0-5, book 1 (dev) for 6-9; text of 4 = text of 0
    links = pd.DataFrame(
        {
            "src_vid": [0, 3, 0, 8],
            "tgt_vid": [3, 0, 8, 0],
            "level": "verse",
            "split": ["train", "train", "dev", "dev"],
        }
    )
    cand = pd.DataFrame({"src": [0] * 5, "tgt": [1, 4, 5, 7, 8], "rank": [1, 2, 3, 4, 5]})
    corpus = SimpleNamespace(
        links=links,
        candidates=cand,
        book_id=np.array([0] * 6 + [1] * 4),
        text_key=np.array([0, 1, 2, 3, 0, 5, 6, 7, 8, 9]),
        train_book=np.array([True, False]),
        window=2,
    )
    df = training_pairs(corpus, n_neg=5, seed=0)
    a0 = df[df.a == 0]
    assert a0[a0.label == 1].b.tolist() == [3]
    # 1: neighbour (|1-0| <= 2); 4: same text; 7: dev book; 8: linked (dev split) -> only 5
    assert a0[a0.label == 0].b.tolist() == [5]
    assert df[df.a == 3].label.tolist() == [1.0]  # no candidates for 3
