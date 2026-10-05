import json

import numpy as np
import pandas as pd
import pytest

from bsim.analysis.senses import (
    g2_over,
    mutual_info,
    run_senses,
    shift_test,
    token_words,
    top_collocates,
    word_spans,
)
from bsim.data.canon import BOOKS
from bsim.fixture import fixture_cfg, write_inputs


def test_word_spans_match_text_model():
    text, spans = word_spans(["בְּ/רֵאשִׁית", "בָּרָא"])
    assert text == "בראשית ברא"
    assert [text[a:b] for a, b in spans] == ["בראשית", "ברא"]


def test_token_words_maps_subwords_and_skips_specials():
    spans = [(0, 6), (7, 10)]
    offsets = np.array([[0, 0], [0, 2], [2, 6], [7, 10], [0, 0]])
    special = np.array([True, False, False, False, True])
    assert token_words(offsets, special, spans).tolist() == [-1, 0, 0, 1, -1]


def test_mutual_info_and_shift_test():
    g = np.array([0] * 20 + [1] * 20)
    assert mutual_info(g, g, 2, 2) == pytest.approx(1.0)  # one bit: sense = group
    assert mutual_info(g, np.zeros(40, int), 2, 1) == 0.0
    rng = np.random.default_rng(0)
    mi, excess, p = shift_test(np.array(["a"] * 20 + ["b"] * 20), g, 99, rng)
    assert mi == pytest.approx(1.0) and excess > 0.9 and p == 0.01
    mixed = np.array([0, 1] * 20)
    _, excess, p = shift_test(np.array(["a"] * 20 + ["b"] * 20), mixed, 99, rng)
    assert p > 0.5 and abs(excess) < 0.1


def test_g2_and_collocates():
    assert g2_over(10, 10, 0, 10) > 0
    assert g2_over(1, 10, 9, 10) == 0.0  # under-represented here
    labels = np.array([0, 0, 0, 1, 1, 1])
    bags = [{"T", "blood"}] * 3 + [{"T", "field"}] * 3
    assert top_collocates(labels, bags, "T", top=3, min_verses=2) == {0: ["blood"], 1: ["field"]}


def test_run_senses_on_the_fixture(tmp_path):
    cfg = fixture_cfg(tmp_path)
    write_inputs(cfg, tmp_path)
    others = [b.osis for b in BOOKS if b.osis != "Gen"]
    cfg["senses"] = {
        **cfg["senses"],
        "groups": {"genesis": ["Gen"], "rest": others},
        "min_count": 4,
        "min_per_group": 1,
        "min_groups": 2,
        "max_k": 2,
        "min_sense_count": 1,
        "null_reps": 19,
        "collocate_min_verses": 1,
    }
    # ראשית: v0 and v2-v4 in Genesis (book 0), v5 in Exodus; two clear uses
    vec = {
        (0, 0): [1.0, 0.0],
        (2, 0): [1.0, 0.1],
        (3, 0): [0.0, 1.0],
        (4, 0): [0.1, 1.0],
        (5, 0): [0.0, 1.0],
    }
    vectors = {k: np.array(v) / np.linalg.norm(v) for k, v in vec.items()}
    run_senses(cfg, log=lambda _: None, vectors=vectors)
    out = tmp_path / "artifacts" / "senses"
    lemmas = pd.read_parquet(out / "lemmas.parquet")
    (row,) = lemmas.to_dict("records")
    assert row["lemma"] == "7225" and row["n"] == 5 and row["k"] == 2
    assert json.loads(row["groups"]) == {"genesis": 4, "rest": 1}
    assert 0 <= row["use_p"] <= 1 and row["use_q"] == pytest.approx(row["use_p"])
    assert row["n_senses"] == 1 and np.isnan(row["sense_p"])  # one SDBH meaning: not tested
    senses = pd.read_parquet(out / "senses.parquet")
    uses = senses[senses.kind == "use"].sort_values("n")
    assert uses.n.tolist() == [2, 3]
    assert sorted(json.loads(uses.examples.iloc[0])) == [[0, 0], [2, 0]]
    meta = json.loads((out / "senses.meta.json").read_text("utf-8"))
    assert meta["lemmas"] == 1 and meta["occurrences"] == 5
