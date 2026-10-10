import numpy as np

from bsim.analysis.stats import shuffle_within
from bsim.analysis.wordplay import (
    find_pairs,
    heard,
    is_proper,
    letters,
    neighbour_index,
    relation,
    skeleton,
    vowel_pattern,
)


def test_skeleton_and_relation():
    assert skeleton("מִשְׁפָּט") == "משפט"
    assert skeleton("שׁוֹפָר") == "שפר"  # vowel letter dropped
    assert skeleton("יָמִים") == "ימ" + "מ"  # first letter kept, final mem folded
    assert relation("משפט", "משפח") == "substitution"
    assert relation("צדקה", "צעקה") == "substitution"
    assert relation("כשב", "כבש") == "metathesis"
    assert relation("אדמ", "אדמה") == "extension"
    assert relation("אדמ", "אדמ") is None
    assert relation("אבג", "דהו") is None
    assert relation("אב", "אבגד") is None


def test_vowels_and_heard_form():
    # mišpāṭ / miśpāḥ: one consonant apart, the same vowels (shin / sin dots ignored)
    a, b = heard("מִשְׁפָּ֔ט", "4941"), heard("מִשְׂפָּ֗ח", "4939")
    assert (a[1], b[1]) == ("משפט", "משפח")
    assert a[2] == b[2] != ""
    # the prefix is not heard as part of the word: וּלְמִשְׁפָּט -> משפט
    c = heard("וּלְמִשְׁפָּט", "c/l/4941")
    assert c[0] == "משפט" and c[2] == a[2]
    # shureq counts as qubbuts
    assert vowel_pattern(letters("שׁוּב")) == vowel_pattern(letters("שֻׁב"))


def test_neighbour_index():
    near = neighbour_index({"משפט", "משפח", "כשב", "כבש", "אב", "צדקה"}, 3)
    assert near["משפט"] == {"משפח": "substitution"}
    assert near["כשב"] == {"כבש": "metathesis"}
    assert "אב" not in near and "צדקה" not in near


def test_find_pairs_window_chapters_and_vowels():
    near = {"משפט": {"משפח": "substitution"}, "משפח": {"משפט": "substitution"}}
    idf = {"x": 6.0, "y": 4.0, "z": 1.0}
    tokens = [("x", "משפט", "ia"), ("z", "zz", ""), ("y", "משפח", "ia"), ("y", "משפח", "oo")]
    chapters = np.array([1, 1, 1, 1])
    found = find_pairs(tokens, chapters, near, idf, 8, 0.5, True)
    assert found == [(0, 2, "substitution", 5.0 - 0.5)]  # other vowels: (0, 3) left out
    assert len(find_pairs(tokens, chapters, near, idf, 8, 0.5, False)) == 2
    assert find_pairs(tokens, chapters, near, idf, 1, 0.5, True) == []  # outside the window
    assert find_pairs(tokens, np.array([1, 1, 2, 2]), near, idf, 8, 0.5, True) == []


def test_shuffle_and_proper():
    chapters = np.array([1, 1, 1, 2, 2])
    perm = shuffle_within(chapters, np.random.default_rng(0))
    assert sorted(perm[:3]) == [0, 1, 2] and sorted(perm[3:]) == [3, 4]
    assert is_proper("HNpm") and is_proper("HTd/Ngmsa") and not is_proper("HNcmsa")
    assert not is_proper(None)
