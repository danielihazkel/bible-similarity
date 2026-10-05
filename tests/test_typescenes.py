import pandas as pd

from bsim.analysis.typescenes import candidates, smith_waterman, verb_sequences

IDF = {"go": 1.0, "see": 2.0, "draw": 3.0, "run": 2.5, "tell": 2.0, "x": 0.5}


def test_smith_waterman_local_alignment_in_order():
    a = ["x", "go", "see", "draw", "run", "tell", "x"]
    b = ["see", "draw", "x", "run", "tell"]
    score, path = smith_waterman(a, b, IDF, mismatch=1.0, gap=0.5)
    assert [a[i] for i, _ in path] == ["see", "draw", "run", "tell"]
    assert score == 2 + 3 - 0.5 + 2.5 + 2
    # reversed order aligns at most one rare verb
    _, rev = smith_waterman(a, b[::-1], IDF, 1.0, 0.5)
    assert len(rev) <= 2
    assert smith_waterman([], b, IDF, 1, 1) == (0.0, [])


def test_candidates_keep_pairs_sharing_rare_verbs():
    seqs = {"u1": ["draw", "run", "tell"], "u2": ["draw", "run"], "u3": ["x"]}
    assert candidates(seqs, IDF, min_shared=5.0, max_partners=5) == [("u1", "u2")]
    assert candidates(seqs, IDF, min_shared=6.0, max_partners=5) == []


def test_verb_sequences_take_verb_morphemes_in_order():
    words = pd.DataFrame(
        {
            "verse_id": [0, 0, 1],
            "idx": [0, 1, 0],
            "lemma": ["c/1980", "776", "7200"],
            "morph": ["HC/Vqw3ms", "HNcbsa", "HVqp3ms"],
        }
    )
    units = pd.DataFrame(
        {"unit_id": ["s:1"], "start_verse_id": [0], "end_verse_id": [1], "n_verses": [2]}
    )
    assert verb_sequences(words, units, max_verses=10) == {"s:1": [(0, "1980"), (1, "7200")]}
