import pandas as pd
import pytest

from bsim.analysis.entities import classify, g2, is_name, links, name_cues, top_partners


def test_is_name_and_classify():
    assert is_name("HNp") and is_name("HR/Np") and not is_name("HNcmsa") and not is_name(None)
    assert classify(0.0, 0.3, 1.5, 0.05) == "person"
    assert classify(1.2, 0.1, 1.5, 0.05) == "place"
    assert classify(0.3, 0.25, 1.5, 0.05) == "mixed"
    assert classify(0.01, 0.02, 1.5, 0.05) == "unclear"


def test_name_cues():
    # וַיֹּאמֶר משֶׁה ... מִצְרַיְמָה ... בֶּן נוּן
    words = pd.DataFrame(
        {
            "verse_id": [0, 0, 0, 0, 1, 1],
            "idx": [0, 1, 2, 3, 0, 1],
            "lemma": ["c/559", "4872", "4714", "1121 a", "5126", "b/3389"],
            "content_lemmas": [["559"], ["4872"], ["4714"], ["1121a"], ["5126"], ["3389"]],
            "morph": ["HC/Vqw3ms", "HNp", "HNp/Sd", "HNcmsc", "HNp", "HR/Np"],
        }
    )
    c = name_cues(words).set_index("lemma")
    assert list(c.index) == ["4872", "4714", "5126", "3389"]
    assert c.loc["4872", "speech"] and not c.loc["4872", "directional"]
    assert c.loc["4714", "directional"] and c.loc["4714", "son"]  # next word is בן
    assert not c.loc["5126", "son"]  # בן is in the previous verse
    assert c.loc["3389", "in_from"]


def test_g2_and_links():
    assert g2(5, 5, 5, 100) > g2(1, 5, 5, 100) > 0
    verse_names = {0: {"a", "b"}, 1: {"a", "b"}, 2: {"a", "c"}, 3: {"c"}}
    df = links(verse_names, {"a": 3, "b": 2, "c": 2}, 100, 2)
    assert df[["a", "b", "n_verses"]].values.tolist() == [["a", "b", 2]]
    assert df.expected.iloc[0] == pytest.approx(0.06)
    both = top_partners(pd.concat([df, df.assign(b="c", g2=0.1)]), 1)
    assert sorted(map(tuple, both[["a", "b"]].values.tolist())) == [
        ("a", "b"),
        ("b", "a"),
        ("c", "a"),
    ]


def test_lexicon_kinds_and_agreement(tmp_path):
    from bsim.analysis.entities import agreement, lexicon_kinds

    assert lexicon_kinds(tmp_path) is None
    pd.DataFrame(
        {
            "strong": ["4872", "4714", "1568", "1"],
            "pos": ["", "", "", ""],
            "name_kind": ["person", "place", "both", None],
        }
    ).to_parquet(tmp_path / "lexicon_lemmas.parquet")
    assert lexicon_kinds(tmp_path) == {"4872": "person", "4714": "place", "1568": "both"}
    out = agreement(
        ["person", "place", "both", None, "place"],
        ["person", "person", "place", "place", "unclear"],
    )
    assert out["decided_by_both"] == 2 and out["agree"] == 0.5
    assert out["lexicon/cues"] == {"person/person": 1, "place/person": 1}
