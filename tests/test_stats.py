import numpy as np

from bsim.analysis.stats import bh_q, empirical_p, pct_to_p


def test_empirical_p_never_zero():
    assert empirical_p(5.0, np.array([1.0, 2.0, 3.0])) == 0.25
    assert empirical_p(2.0, np.array([1.0, 2.0, 3.0])) == 0.75


def test_bh_q_matches_hand_computation_and_keeps_order():
    p = np.array([0.04, 0.01, 0.03, 0.5, np.nan])
    q = bh_q(p)
    # sorted p 0.01, 0.03, 0.04, 0.5 (m = 4): 0.04, 0.06, 0.0533, 0.5 -> monotone 0.04, 0.0533, ...
    assert np.allclose(q[:4], [0.04 * 4 / 3, 0.04, 0.04 * 4 / 3, 0.5])
    assert np.isnan(q[4])
    assert bh_q(np.array([])).shape == (0,)


def test_pct_to_p():
    assert np.allclose(pct_to_p(np.array([1.0, 0.0]), 99), [0.01, 1.0])
