import numpy as np
import pytest
from scipy.stats import chi2_contingency

from bsim.analysis.stats import bh_q, empirical_p, g2_table, pct_to_p, shuffle_within


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


def test_g2_table_is_the_log_likelihood_ratio():
    table = np.array([[12, 30], [8, 150]])
    want = chi2_contingency(table, correction=False, lambda_="log-likelihood")[0]
    assert g2_table(12, 42, 20, 200) == pytest.approx(want)
    assert g2_table(0, 5, 0, 100) == 0.0  # empty cells add nothing
    assert g2_table(5, 5, 5, 100) > g2_table(1, 5, 5, 100) > 0


def test_shuffle_within_keeps_groups_even_when_split():
    groups = np.array([2, 2, 1, 1, 2, 1])
    perm = shuffle_within(groups, np.random.default_rng(3))
    assert sorted(perm) == list(range(6))
    assert (groups[perm] == groups).all()
