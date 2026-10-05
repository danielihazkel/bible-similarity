import numpy as np
import pytest

from bsim.analysis.seams import changed_features, pick_peaks, shift_curve


def book(n_a: int, n_b: int):
    """n_a verses using feature 0, then n_b verses using feature 1; 10 words each."""
    counts = np.array([[5.0, 0.0]] * n_a + [[0.0, 5.0]] * n_b)
    return counts, np.full(n_a + n_b, 10.0)


def test_shift_curve_peaks_at_the_change():
    counts, words = book(6, 6)
    curve = shift_curve(counts, words, np.array([0.1, 0.1]), block=30)
    assert np.isnan(curve[:3]).all() and np.isnan(curve[10:]).all()  # sides shorter than 30
    assert np.nanargmax(curve) == 6
    assert curve[6] == pytest.approx(5.0)  # rates 0.5 vs 0 on both features / sd 0.1
    assert curve[4] < curve[5] < curve[6]


def test_pick_peaks_and_features():
    curve = np.array([np.nan, 0.2, 0.9, 0.8, 0.3, 0.7, 0.1])
    words = np.full(7, 10.0)
    assert pick_peaks(curve, words, 0.5, 25) == [2, 5]  # 3 is within 25 words of 2
    assert pick_peaks(curve, words, 0.95, 25) == []
    counts, w = book(6, 6)
    feats = changed_features(counts, w, np.array([0.1, 0.1]), 6, 30, 2)
    assert {i for i, _ in feats} == {0, 1}
    assert dict(feats)[1] == pytest.approx(5.0) and dict(feats)[0] == pytest.approx(-5.0)
