from collections import Counter

import numpy as np
import pandas as pd
import pytest

from bsim.analysis.parallelism import (
    FEATURES,
    fit_model,
    held_out_auc,
    known_poem_ranks,
    pair_features,
    verse_features,
)
from bsim.text.accents import ETNAHTA, MERKHA, OLE, cola, pauses, poetic

GEN_1_1 = ["בְּרֵאשִׁ֖ית", "בָּרָ֣א", "אֱלֹהִ֑ים", "אֵ֥ת", "הַשָּׁמַ֖יִם", "וְאֵ֥ת", "הָאָֽרֶץ׃"]
PS_1_1 = [
    "אַ֥שְֽׁרֵי־",
    "הָאִ֗ישׁ",
    "אֲשֶׁ֤ר",
    "׀",
    "לֹ֥א",
    "הָלַךְ֮",
    "בַּעֲצַ֢ת",
    "רְשָׁ֫עִ֥ים",
    "וּבְדֶ֣רֶךְ",
    "חַ֭טָּאִים",
    "לֹ֥א",
    "עָמָ֑ד",
    "וּבְמוֹשַׁ֥ב",
    "לֵ֝צִ֗ים",
    "לֹ֣א",
    "יָשָֽׁב׃",
]


def test_poetic_books_and_job_frame():
    assert poetic("Ps", 1, 1) and poetic("Job", 3, 2) and poetic("Prov", 31, 31)
    assert not poetic("Job", 1, 5) and not poetic("Job", 3, 1) and not poetic("Job", 42, 10)
    assert not poetic("Gen", 1, 1)


def test_prose_split_at_etnahta():
    assert ETNAHTA in GEN_1_1[2]
    assert pauses(GEN_1_1, False) == [(2, "etnahta")]
    assert cola(GEN_1_1, False) == [(0, 2), (3, 6)]


def test_poetic_split_at_oleh_ve_yored_and_etnahta():
    i = next(k for k, t in enumerate(PS_1_1) if OLE in t)
    assert MERKHA in PS_1_1[i]  # ole and yored on one word (רשעים)
    assert cola(PS_1_1, True) == [(0, i), (i + 1, 11), (12, 15)]
    assert [n for _, n in pauses(PS_1_1, True)] == ["oleh-ve-yored", "etnahta"]
    # read with prose rules, only the etnahta divides
    assert cola(PS_1_1, False) == [(0, 11), (12, 15)]


def test_no_pause_and_edges():
    assert cola(["אחד", "שנים"], False) == [(0, 1)]
    assert cola([], False) == []
    # an etnahta on the last word is not a pause inside the verse
    assert cola(["א", "ב" + ETNAHTA], False) == [(0, 1)]
    # yored on the next word: the pause follows that word
    assert cola(["א" + OLE, "ב" + MERKHA, "ג", "ד" + ETNAHTA, "ה"], True) == [
        (0, 1),
        (2, 3),
        (4, 4),
    ]


def test_pair_and_verse_features():
    f = pair_features({"1", "2"}, {"2", "3"}, Counter({"Nc": 2}), Counter({"Nc": 1, "V": 3}), 0.7)
    assert f == {"cos": 0.7, "shared": 1.0, "shape": 0.25, "balance": 0.5}
    lemmas = {(0, 0): ["1"], (0, 1): ["2"], (0, 2): ["1"], (0, 3): ["9"]}
    shapes = {(0, t): ["Nc"] for t in range(4)}
    emb = np.array([[1.0, 0.0], [0.6, 0.8]], dtype=np.float32)
    v = verse_features(0, [(0, 1), (2, 3)], emb, lemmas, shapes)
    assert v == pytest.approx({"cos": 0.6, "shared": 1.0, "shape": 1.0, "balance": 1.0})


def test_model_checks():
    rng = np.random.default_rng(0)
    books = ["Ps", "Prov", "Gen", "Exod", "Lev", "Num"]
    rows = []
    for b in books:
        pos = b in ("Ps", "Prov")
        for c in range(1, 4):
            for _ in range(20):
                x = rng.normal(1.0 if pos else 0.0, 0.5, 4)
                rows.append((b, c, *x, int(pos)))
    df = pd.DataFrame(rows, columns=["osis", "chapter", *FEATURES, "y"])
    model = fit_model(df[list(FEATURES)].to_numpy(), df.y.to_numpy(), 1.0)
    df["prob"] = model.predict_proba(df[list(FEATURES)].to_numpy())[:, 1]
    aucs = held_out_auc(df, ["Ps", "Prov"], 1.0)
    assert set(aucs) == {"Ps", "Prov"} and min(aucs.values()) > 0.9
    ranks = known_poem_ranks(df, ["Gen", "Exod", "Lev", "Num"], ["Gen 2", "Ruth 1"], 5)
    assert ranks["chapters"] == 12 and set(ranks["ranks"]) == {"Gen 2"}
    assert 1 <= ranks["ranks"]["Gen 2"] <= 12
