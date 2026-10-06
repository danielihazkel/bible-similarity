import json

import numpy as np
import pandas as pd
import pytest

from bsim.analysis.dating import (
    FEATURES,
    drivers,
    fit,
    held_out_auc,
    priors,
    rates,
    run_dating,
    sign_test,
    word_flags,
)
from bsim.fixture import fixture_cfg, write_inputs

# וַיִּקָּחֵהוּ (suffix on the verb), אֹתוֹ (את + suffix), מִצְרַיְמָה (directional ה), וָאֶשְׁלְחָה
# (1cs wayyiqtol with ה), אָנֹכִי, דָּוִיד (plene), מַלְכוּת (LBH word), הָלוֹךְ (inf. abs.), an
# Aramaic word left out.
WORDS = pd.DataFrame(
    {
        "verse_id": [0] * 9,
        "surface": [
            "וַ/יִּקָּחֵ/הוּ",
            "אֹת/וֹ",
            "מִצְרַיְמָ/ה",
            "וָ/אֶשְׁלְחָה",
            "אָנֹכִי",
            "דָּוִיד",
            "מַלְכוּת",
            "הָלוֹךְ",
            "מַלְכָּא",
        ],
        "lemma": ["c/3947", "853", "4714", "c/7971", "595", "1732", "4438", "1980", "4430"],
        "morph": [
            "HC/Vqw3ms/Sp3ms",
            "HTo/Sp3ms",
            "HNpl/Sd",
            "HC/Vqw1cs",
            "HPp1bs",
            "HNpm",
            "HNcfsc",
            "HVqaa",
            "ANcmsd",
        ],
    }
)


def test_word_flags():
    f = word_flags(WORDS, {"4438"}).sum()
    assert f.word == 8  # the Aramaic word is not counted
    assert (f.lex, f.anokhi, f.pron_1cs, f.inf_abs) == (1, 1, 1, 1)
    assert (f.et_suffix, f.verb_suffix, f.directional_he) == (1, 1, 1)
    assert (f.way1cs, f.way1cs_h, f.david, f.david_plene) == (1, 1, 1, 1)


def test_rates_shrink_towards_the_prior():
    counts = pd.DataFrame(
        [word_flags(WORDS, {"4438"}).drop(columns="verse_id").sum()] * 2, index=["a", "b"]
    )
    counts.loc["b"] = 0
    counts.loc["b", "word"] = 100
    prior = priors(counts)
    r = rates(counts, prior, shrink=0)
    assert r.loc["a", "et_suffix"] == pytest.approx(0.5)  # 1 of את+suffix / verb+suffix 2
    assert r.loc["a", "david_plene"] == 1.0
    shrunk = rates(counts, prior, shrink=10)
    # no David in b: its plene rate is the prior itself
    assert shrunk.loc["b", "david_plene"] == pytest.approx(prior["david_plene"])
    assert list(r.columns) == list(FEATURES)


def test_held_out_auc_drivers_and_sign_test():
    rng = np.random.default_rng(0)
    x = pd.DataFrame(rng.normal(size=(40, len(FEATURES))), columns=list(FEATURES))
    y = np.array([0] * 20 + [1] * 20)
    x.loc[y == 1, "david_plene"] += 5
    books = np.repeat(np.arange(8), 5)
    out = held_out_auc(x, y, books, 1.0)
    assert out["auc"] > 0.9 and set(out["books"]) == {str(b) for b in range(8)}
    model = fit(x.to_numpy(), y, 1.0)
    d = json.loads(drivers(model, x.iloc[[39]], 3)[0])
    assert d[0] == "david_plene"
    assert sign_test(26, 26) < 1e-7 and sign_test(5, 10) == 1.0


def test_run_dating_needs_both_classes(tmp_path):
    cfg = fixture_cfg(tmp_path)
    write_inputs(cfg, tmp_path)
    cfg["dating"] = {**cfg["dating"], "min_words": 1}
    with pytest.raises(RuntimeError, match="late"):
        run_dating(cfg, log=lambda _: None)  # the fixture has only Genesis and Exodus
