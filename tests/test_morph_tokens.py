import pandas as pd

from bsim.lexical.morph import morph_streams, ngram_tokens, word_token


def test_word_token_keeps_shape_drops_agreement():
    assert word_token("HC/Vqw3ms") == "C+Vw"  # וַיֹּאמֶר
    assert word_token("HR/Td/Ncmsa") == "R+Td+Na"
    assert word_token("HNcmsc/Sp3ms") == "Nc+Sp"
    assert word_token("HNp") == "Np"
    assert word_token("HVhp3ms") == word_token("HVqp1cp") == "Vp"  # stem / person ignored
    assert word_token("HAafsa") == "A"
    assert word_token("HTo/Sp3mp") == "To+Sp"
    assert word_token("AVqp3ms") == "Vp"  # Aramaic: same shape alphabet
    assert word_token(None) == word_token("H") == "?"


def test_streams_and_ngrams():
    words = pd.DataFrame(
        {"verse_id": [0, 0, 1], "idx": [1, 0, 0], "morph": ["HNcmsa", "HC/Vqw3ms", None]}
    )
    assert morph_streams(words, 2) == [["C+Vw", "Na"], ["?"]]
    assert ngram_tokens(["a", "b", "c"], 2) == ["a", "b", "c", "a b", "b c"]
