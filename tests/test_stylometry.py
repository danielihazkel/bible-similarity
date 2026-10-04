import numpy as np
import pandas as pd
import pytest

from bsim.analysis.stylometry import delta_matrix, feature_matrix, pca2, word_features, zscores


def test_word_features():
    assert word_features("HC/Vqw3ms") == ["conj", "pos:C", "pos:V", "verb:w"]
    assert word_features("HR/Td/Ncmsa") == ["article", "pos:N", "pos:R", "pos:T"]
    assert word_features("HNcmsc/Sp3ms") == ["pos:N", "state:c", "suffix"]
    assert word_features("HTo") == ["object", "pos:T"]
    assert "aramaic" in word_features("AVqp3ms")
    assert word_features(None) == word_features(float("nan")) == []


def test_feature_matrix_rates_per_word():
    words = pd.DataFrame(
        {
            "verse_id": [0, 0, 1],
            "content_lemmas": [["559"], ["430"], ["559"]],
            "morph": ["HC/Vqw3ms", "HNcmpa", "HVqp3ms"],
        }
    )
    x, n, names = feature_matrix(words, np.array([0, 1]), 2, ["559"])
    assert n.tolist() == [2, 1]
    col = {f: i for i, f in enumerate(names)}
    assert x[0, col["lemma:559"]] == 0.5 and x[1, col["lemma:559"]] == 1.0
    assert x[0, col["verb:w"]] == 0.5 and x[1, col["verb:p"]] == 1.0


def test_delta_and_pca():
    z = zscores(np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.1]]))
    d = delta_matrix(z)
    assert d[0, 0] == 0 and d[0, 2] < d[0, 1] and d[1, 0] == pytest.approx(d[0, 1])
    scores, load, var = pca2(z)
    assert scores.shape == (3, 2) and var.sum() == pytest.approx(1.0)
    assert load[0, np.argmax(np.abs(load[0]))] > 0
