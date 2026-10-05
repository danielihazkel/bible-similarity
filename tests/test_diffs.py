import json

import pandas as pd

from bsim.analysis.diffs import (
    Word,
    align_words,
    find_changes,
    key_letters,
    make_word,
    shared_ratio,
    word_key,
)


def w(key, form, idx=0):
    return Word(idx, key, form)


def ops(a, b):
    return [(o.op, o.a, o.b) for o in align_words(a, b, match=2, mismatch=1, gap=1)]


def test_word_key():
    assert word_key(["1121a"], "1121 a") == "1121a"
    assert word_key("430 559", "x") == "430+559"
    assert word_key([], "c/l") == "~c/l"
    assert key_letters("~c/l") == "ול"
    assert key_letters("430") is None


def test_labels():
    a = [w("1732", "דוד"), w("559", "ויאמר"), w("3068", "יהוה"), w("5921a", "על")]
    b = [w("1732", "דויד"), w("559", "אמר"), w("430", "אלהימ"), w("5921a", "על")]
    assert ops(a, b) == [
        ("spelling", 0, 0),  # דוד / דויד: only a yod differs
        ("form", 1, 1),  # ויאמר / אמר
        ("substitution", 2, 2),
        ("same", 3, 3),
    ]


def test_added_omitted_and_moved():
    a = [w("1", "א"), w("2", "ב"), w("3", "ג")]
    b = [w("1", "א"), w("3", "ג"), w("4", "ד")]
    assert ops(a, b) == [("same", 0, 0), ("omitted", 1, None), ("same", 2, 1), ("added", None, 2)]
    # 2 and 3 swap: one of them (equal scores either way) is moved, on both sides
    b2 = [w("1", "א"), w("3", "ג"), w("2", "ב")]
    got = ops(a, b2)
    moved = [(o, i, j) for o, i, j in got if o == "moved"]
    assert [o for o, *_ in got].count("same") == 2 and len(moved) == 2
    (_, ia, _), (_, _, jb) = sorted(moved, key=lambda m: m[1] is None)
    assert a[ia].key == b2[jb].key
    assert ops([], b) == [("added", None, 0), ("added", None, 1), ("added", None, 2)]


def test_find_changes_filters_and_rows():
    words = {
        0: [w("1", "א", 0), w("2", "ב", 1)],
        5: [w("1", "א", 0), w("9", "ט", 1)],
        1: [w("1", "א", 0)],
        6: [w("1", "א", 0)],
    }
    seqs = pd.DataFrame(
        {
            "seq_id": [1, 2, 3],
            "a_book": [0, 0, 0],
            "b_book": [1, 1, 0],
            "same_chapter": [False, False, True],
            "q": [0.01, 0.5, 0.0],
            "pairs": [json.dumps([[0, 5, 1.0, 0]]), json.dumps([[1, 6, 1.0, 0]]), json.dumps([])],
        }
    )
    d = {"max_q": 0.05, "same_chapter": False, "match": 2, "mismatch": 1, "gap": 1}
    df, totals, n, loose = find_changes(seqs, words, {"diffs": {**d, "min_shared": 0.3}})
    assert (n, loose) == (1, 0)  # seq 2 is too weak, seq 3 is a same-chapter repeat
    assert totals == {"same": 1, "substitution": 1}
    row = df.iloc[0]
    assert (row.seq_id, row.a, row.b, row.op) == (1, 0, 5, "substitution")
    assert (row.a_idx, row.b_idx) == (1, 1)
    assert (row.a_key, row.b_key) == ("2", "9")
    # 1 of 2 words kept: below a 0.6 threshold the pair is left out as too loose
    _, _, n, loose = find_changes(seqs, words, {"diffs": {**d, "min_shared": 0.6}})
    assert (n, loose) == (0, 1)


def test_shared_ratio_and_make_word():
    a = [w("1", "א"), w("2", "ב")]
    b = [w("1", "א"), w("3", "ג"), w("4", "ד")]
    assert shared_ratio(align_words(a, b, 2, 1, 1), 2, 3) == 0.5
    assert shared_ratio([], 0, 3) == 0.0
    word = make_word(4, ["1732"], "1732", "דָּוִ֑יד")
    assert (word.idx, word.key, word.form, word.text) == (4, "1732", "דויד", "דויד")
