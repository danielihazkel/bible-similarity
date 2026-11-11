import numpy as np

from bsim.analysis.acrostic import (
    ALPHABET,
    ORDERS,
    best_chain,
    chain_scores,
    chapter_lines,
    chapter_options,
    first_letter,
    known_unit_ids,
    positions,
    score_chapter,
    span,
)
from bsim.config import load_config

CFG = {
    "acrostics": {
        "granularities": ["verse", "colon"],
        "max_line_gap": 3,
        "missing_penalty": 1.0,
        "span_trim": True,
        "null_reps": 199,
        "null_screen": 19,
        "screen_hits": 10,
        "second_word": False,
    }
}
CFG2 = {"acrostics": {**CFG["acrostics"], "second_word": True}}


def lines_of(letters: str):
    return [(i, 0, ch) for i, ch in enumerate(letters)]


def options_of(letters: str):
    """Each line its one letter (`score_chapter` takes each line's options)."""
    return [[line] for line in lines_of(letters)]


def test_first_letter_skips_marks_and_folds_finals():
    assert first_letter(["׀", "אַשְׁרֵי"]) == (1, "א")
    assert first_letter(["ךְ"]) == (0, "כ")
    assert first_letter([]) is None


def test_best_chain_with_blocks_gaps_and_missing_letters():
    order = ORDERS["standard"]
    # Lam 3 style: three lines per letter
    c = best_chain(positions(lines_of("אאאבבבגגג"), order), 3, 1.0)
    assert c.score == 3 and len(c.lines) == 3
    # a letter missing costs the penalty: א ב ד = 3 - 1
    assert best_chain(positions(lines_of("אבד"), order), 3, 1.0).score == 2
    # too far apart: no chain across a gap longer than max_gap
    assert best_chain(positions(lines_of("אוווווב"), order), 3, 1.0).score == 1


def test_vectorized_scores_match_the_traceback():
    rng = np.random.default_rng(0)
    pos = rng.integers(0, 22, size=(50, 30))
    fast = chain_scores(pos, 4, 1.0)
    slow = [best_chain(row, 4, 1.0).score for row in pos]
    assert np.allclose(fast, slow)


def test_whole_acrostic_is_significant_and_pe_ayin_order_found():
    lam = ORDERS["pe-ayin"]
    lines = {"verse": options_of(lam), "colon": options_of(lam)}
    r = score_chapter(lines, CFG, np.random.default_rng(1))
    assert r["n_letters"] == 22 and r["order_name"] == "pe-ayin" and r["missing"] == 0
    assert r["p"] <= 1 / 200 + 1e-12  # no shuffle comes close
    assert r["first_letter"] == "א" and r["last_letter"] == "ת"


def test_ordinary_text_is_not_significant():
    text = "ויאמרויהיוידברהנהאשרכיולאועתה"  # verse starts of narrative
    lines = {"verse": options_of(text), "colon": options_of(text)}
    r = score_chapter(lines, CFG, np.random.default_rng(2))
    assert r["p"] > 0.05


def test_chapter_lines_use_cola():
    tokens = {0: ["אַשְׁרֵי", "הָאִישׁ", "בְּטוּב"], 1: ["גַּם"]}
    lines = chapter_lines([0, 1], tokens, {0: [[0, 1], [2, 2]]})
    assert [ch for *_, ch in lines["verse"]] == ["א", "ג"]
    assert lines["colon"] == [(0, 0, "א"), (0, 2, "ב"), (1, 0, "ג")]


def test_known_ids_and_config():
    assert known_unit_ids(["Ps 119", "Lam 3"]) == ["c:26:119", "c:31:3"]
    assert len(ALPHABET) == 22
    assert known_unit_ids(load_config()["acrostics"]["known"])


def test_a_letter_on_the_second_word():
    """Nahum 1: a leading word (יהוה, לפני) before the letter; read with the second word, the
    chain runs on, and shuffles read lines the same way."""
    first = "איגהולחטי"  # the first words' letters: ב and ז sit on the second words
    lines = [
        [(i, 0, a)] + ([(i, 1, b)] if b != "_" else [])
        for i, (a, b) in enumerate(zip(first, "_ב___ז___", strict=True))
    ]
    firsts = [ls[:1] for ls in lines]
    old = score_chapter({"verse": firsts, "colon": []}, CFG, np.random.default_rng(3))
    new = score_chapter({"verse": lines, "colon": []}, CFG2, np.random.default_rng(3))
    assert new["score"] > old["score"] and new["second_words"] == 2
    assert new["n_letters"] == 9 and new["missing"] == 1  # א ב ג (ד) ה ו ז ח ט י


def test_chapter_options_offer_the_next_word():
    tokens = {0: ["יְהוָה", "בְּסוּפָה"], 1: ["גֹּעֵר"]}
    opts = chapter_options([0, 1], tokens, {})
    assert [[x[2] for x in o] for o in opts["verse"]] == [["י", "ב"], ["ג"]]
    assert chapter_lines([0, 1], tokens, {})["verse"] == [(0, 0, "י"), (1, 0, "ג")]


def test_the_span_starts_where_the_alphabet_does():
    """M159: Prov 31's chain takes the א of 31:3; the span starts at the last א line before the
    chain's ב (31:10), runs back over lines opening alike and on after its last letter."""
    line = lambda v, letter: [(v, 0, letter)]  # noqa: E731
    ls = [line(0, "א"), line(1, "ל"), line(2, "א"), line(3, "ב"), line(4, "ג"), line(5, "ג")]
    assert span(ls, [0, 3, 4], "א", "ג") == (2, 5)
    stanza = [line(0, "א"), line(1, "א"), line(2, "א"), line(3, "ב"), line(4, "ב")]
    assert span(stanza, [0, 3], "א", "ב") == (0, 4)  # Ps 119's eight verses a letter
