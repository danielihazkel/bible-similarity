import numpy as np
import pandas as pd
import pytest

from bsim.eval.unit_experiments import adoption, report, score_lists, unit_gold_of
from bsim.retrieve.topk import Units
from bsim.retrieve.unit_pairs import ranked, unit_of_verse, unit_scores

# three units over verses 0-1, 2-4, 5; verse 6 outside every unit
IDS = np.array(["u:0", "u:1", "u:2"], dtype=object)
UNITS = Units(IDS, np.array([0, 2, 5]), np.array([1, 4, 5]))


def _g(mean, lo, hi):
    return {"mean": mean, "lo": lo, "hi": hi, "better": 1, "worse": 1, "queries": 2}


def test_unit_scores_sum_both_ways_and_drop_inside_pairs():
    unit_of = unit_of_verse(UNITS, 7)
    assert unit_of.tolist() == [0, 0, 1, 1, 1, 2, -1]
    pairs = pd.DataFrame(
        {
            "a": [0, 1, 3, 2, 0, 1],
            "b": [2, 4, 0, 3, 6, 5],
            "w": [1.0, 2.0, 0.5, 9.0, 9.0, 0.25],
        }
    )  # (2, 3) inside u:1 and (0, 6) outside the units are dropped
    s = unit_scores(pairs, unit_of).set_index(["src", "tgt"]).score
    assert s[(0, 1)] == s[(1, 0)] == pytest.approx(3.5)
    assert s[(0, 2)] == s[(2, 0)] == pytest.approx(0.25)
    assert len(s) == 4
    r = ranked(s.reset_index(), k=1)
    assert r[["src", "tgt", "rank"]].values.tolist() == [[0, 1, 1], [1, 0, 1], [2, 0, 1]]


def test_ranked_ties_by_target_and_drops_zero():
    scores = pd.DataFrame({"src": [0, 0, 0], "tgt": [3, 1, 2], "score": [1.0, 1.0, 0.0]})
    assert ranked(scores, k=5).tgt.tolist() == [1, 3]


def test_unit_gold_needs_m_distinct_verse_pairs():
    unit_of = unit_of_verse(UNITS, 7)
    verse_gold = {0: {2, 3}, 1: {5}, 2: {3}, 4: {0}, 6: {0}}
    assert unit_gold_of(verse_gold, unit_of, 2) == {0: {1}}
    assert unit_gold_of(verse_gold, unit_of, 1) == {0: {1, 2}, 1: {0}}


def test_score_lists_every_gold_query_and_missing_lists_score_zero():
    df = pd.DataFrame({"src": [0, 0], "tgt": [2, 1], "rank": [1, 2]})
    out = score_lists(df, {"g": {0: {1}, 1: {0}}}, "recall@1")
    assert out["g"].tolist() == [0.0, 0.0]
    out = score_lists(df, {"g": {0: {2}, 1: {0}}}, "recall@1")
    assert out["g"].tolist() == [1.0, 0.0]


def test_adoption_rule():
    def entry(cf, ob=(0.0, -0.01, 0.01), et=(0.0, -0.01, 0.01)):
        return {"cross_fitted_gain": _g(*cf), "gains": {"openbible": _g(*ob), "etcbc": _g(*et)}}

    entries = {
        "small": entry((0.004, 0.001, 0.007)),
        "best": entry((0.02, 0.01, 0.03)),
        "unsure": entry((0.05, -0.001, 0.1)),  # cross-fitted CI reaches 0
        "loses": entry((0.03, 0.01, 0.05), et=(-0.02, -0.04, -0.001)),
    }
    ok, chosen = adoption(entries, ["openbible", "etcbc"])
    assert ok == {"small": True, "best": True, "unsure": False, "loses": False}
    assert chosen == "best"
    assert adoption({"unsure": entries["unsure"]}, ["openbible"]) == ({"unsure": False}, None)


def test_report_lists_families_and_alone():
    fam = {
        "alone": {"phrases": {"scores": {"sefaria": 0.2}, "units_with_list": 12}},
        "members": {"phrases, w=1": {"sefaria": 0.19}},
        "selected": "phrases, w=1",
        "gains": {"sefaria": _g(0.02, 0.01, 0.03)},
        "cross_fitted_choices": ["phrases, w=1"] * 2,
        "cross_fitted_gain": _g(0.02, 0.01, 0.03),
        "adopt": True,
    }
    out = {
        "metric": "ndcg@10",
        "baseline": "fused",
        "unit_types": {
            "chapter": {
                "baseline_scores": {"sefaria": 0.17},
                "queries": {"sefaria": 154},
                "families": {"phrases": fam},
                "chosen": "phrases",
            }
        },
    }
    md = report(out)
    assert "| phrases | phrases, w=1 | +0.0200 [+0.0100, +0.0300] |" in md
    assert "| phrases | phrases | 12 | 0.2000 |" in md and "Chosen: phrases." in md
