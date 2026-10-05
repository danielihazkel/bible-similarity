from collections import Counter

import numpy as np
import pytest

from bsim.analysis.structure import (
    chiasm,
    echoes,
    frame_pairs,
    inclusio,
    leitworte,
    lexical_matrix,
    mirror_pairs,
)


def chiastic(n: int, hi: float = 0.9, lo: float = 0.1) -> np.ndarray:
    """Mirror pairs similar, everything else not."""
    s = np.full((n, n), lo)
    for i, j in mirror_pairs(n):
        s[i, j] = s[j, i] = hi
    np.fill_diagonal(s, 1.0)
    return s


def test_mirror_and_frame_pairs():
    assert mirror_pairs(7) == [(0, 6), (1, 5), (2, 4)]
    assert mirror_pairs(6) == [(0, 5), (1, 4)]  # (2, 3) is adjacent
    assert frame_pairs(5) == [(0, 4)]
    assert frame_pairs(8) == [(0, 7), (1, 7), (0, 6)]


def test_chiasm_detects_mirror_structure():
    hit = chiasm(chiastic(9), min_verses=5, samples=2000, seed=1)
    assert hit is not None and hit.pct > 0.99 and hit.z > 3
    flat = chiasm(np.full((9, 9), 0.5), min_verses=5, samples=500, seed=1)
    assert flat.pct == 0.5 and flat.z is None  # no variance: no z
    assert chiasm(chiastic(4), min_verses=5, samples=10, seed=1) is None


def test_inclusio_uses_frame_pairs_and_reports_the_pair():
    s = np.full((8, 8), 0.2)
    s[1, 7] = s[7, 1] = 0.95  # a heading verse 0, then the frame 1 ~ 7
    r = inclusio(s, min_verses=4, samples=1000, seed=0)
    assert r.pair == (1, 7) and r.value == 0.95 and r.pct == 1.0
    assert inclusio(s[:3, :3], min_verses=4, samples=10, seed=0) is None


def test_echoes_skip_adjacent_pairs():
    s = chiastic(6)
    s[0, 1] = s[1, 0] = 0.99  # adjacent: ignored
    assert [(i, j) for i, j, _ in echoes(s, 2)] == [(0, 5), (1, 4)]


def test_lexical_matrix_idf_weighting():
    m = lexical_matrix([["a", "b"], ["a", "c"], []], {"a": 0.0, "b": 1.0, "c": 1.0})
    assert m[0, 1] == pytest.approx(0.0)  # only the zero-idf lemma is shared
    assert m[0, 0] == pytest.approx(1.0) and m[2, 2] == 0.0


def test_leitworte_g2_ranks_overrepresented_lemmas():
    unit = Counter({"x": 7, "y": 3, "z": 3})
    corpus = {"x": 10, "y": 5000, "z": 3}
    keys = leitworte(unit, corpus, corpus_total=10_000, min_count=3, top=5)
    assert [k.lemma for k in keys] == ["x", "z"]  # y: 3 seen, 6.5 expected
    assert keys[0].count == 7 and keys[0].g2 > keys[1].g2 > 0


def test_add_q_per_unit_type():
    import numpy as np
    import pandas as pd

    from bsim.analysis.structure import Q_COLS, SCORE_COLS, add_q

    df = pd.DataFrame(
        {
            "unit_id": ["a", "b", "c"],
            "unit_type": ["chapter", "chapter", "parasha"],
            **{c: [0.999, 0.5, np.nan] for c in SCORE_COLS},
        }
    )
    out = add_q(df, samples=999)
    for c in Q_COLS:
        assert out[c][0] < out[c][1] and np.isnan(out[c][2])


def test_leitwort_numbers_count_matched_baseline():
    from collections import Counter

    from bsim.analysis.structure import leitwort_numbers

    # every chapter: one lemma 7 times (over-represented), filler lemmas 3-6 times
    units = [Counter({"lw": 7, **{f"f{i}": 3 + i % 4 for i in range(20)}}) for _ in range(30)]
    corpus = {"lw": 7 * 30 + 10000, **{f"f{i}": 100000 for i in range(20)}}
    r = leitwort_numbers(units, corpus, 10_000_000, 3, 1, moduli=(7, 10))
    assert r["leitworte"] == 30 and r["7"]["multiples"] == 30
    assert r["7"]["expected"] > 0 and r["10"]["multiples"] == 0
