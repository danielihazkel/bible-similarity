import numpy as np
import pandas as pd

from bsim.analysis.sound import (
    content_sounds,
    ending,
    initial_sound,
    letter_sound,
    prefix_letters,
    tail_at_least,
)


def test_sounds_are_phonemes_with_shin_and_sin_apart():
    # פַּחַד / וָפַחַת: p and f are one phoneme; the conjunction is skipped by prefix count
    assert initial_sound("פַּ֥חַד") == initial_sound("וָפַ֖חַת", skip_letters=1) == "פ"
    assert letter_sound("ש", "ׁ") == "sh" and letter_sound("ש", "ׂ") == "s"
    assert prefix_letters("וָפַ֖חַת", "c/6354") == 1
    assert prefix_letters("הָאָֽרֶץ", "d/776") == 1
    assert prefix_letters("פַּ֥חַד", "6343") == 0


def test_ending_keys_last_two_consonants_with_vowel():
    assert ending("עָשָׂנִי") == "נִי" and ending("וַתְּכוֹנְנֵנִי") == "נִי"
    assert ending("ב") is None


def test_tail_at_least_matches_binomial():
    from scipy.stats import binom

    assert np.isclose(tail_at_least([0.2] * 5, 3), binom.sf(2, 5, 0.2))
    assert tail_at_least([0.5, 0.5], 0) == 1.0


def test_content_sounds_skip_function_words():
    words = pd.DataFrame(
        {
            "verse_id": [0, 0, 0],
            "idx": [0, 1, 2],
            "display_idx": [0, 1, 2],
            "surface": ["פַּ֥חַד", "אֶת־", "וָפָ֑ח"],
            "lemma": ["6343", "853", "c/6341 a"],
            "content_lemmas": [["6343"], ["853"], ["6341a"]],
            "morph": ["HNcmsa", "HTo", "HC/Ncmsa"],
        }
    )
    got = content_sounds(words, skip_pos={"C", "R", "T", "P"})
    assert set(got) == {(0, 0), (0, 2)}  # the object marker is a particle
    assert got[(0, 0)][0] == got[(0, 2)][0] == "פ"
