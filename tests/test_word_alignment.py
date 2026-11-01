"""OSHB words <-> MAM display tokens (DESIGN.md §3.4)."""

from bsim.data.align import align


def test_spelling_variants_map_one_to_one():
    assert align(["דוד", "מלך"], ["דויד", "מלך"]) == [0, 1]
    assert align(["א", "ב"], ["", "א", "ב"]) == [1, 2]  # a token without letters keeps its index


def test_words_divided_otherwise_are_aligned():
    # Ps 57:10: OSHB בל אמים, MAM בלאמים: both OSHB words show the one token
    assert align(["אודך", "בעמים", "בל", "אמים"], ["אודך", "בעמים", "בלאמים"]) == [0, 1, 2, 2]
    # one OSHB word written as two MAM tokens: the first
    assert align(["מבלילו", "ישכן"], ["מבלי", "לו", "ישכן"]) == [0, 2]
    # three into one, and a block that fits neither way stays unaligned
    assert align(["א", "ב", "ג", "ד"], ["אבג", "ד"]) == [0, 0, 0, 1]
    assert align(["x", "y", "z"], ["q", "z"]) == [None, None, 1]
