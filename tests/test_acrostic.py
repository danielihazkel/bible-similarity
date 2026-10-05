import numpy as np

from bsim.analysis.acrostic import (
    ALPHABET,
    ORDERS,
    best_chain,
    chain_scores,
    chapter_lines,
    first_letter,
    known_unit_ids,
    positions,
    score_chapter,
)
from bsim.config import load_config

CFG = {
    "acrostics": {
        "granularities": ["verse", "colon"],
        "max_line_gap": 3,
        "missing_penalty": 1.0,
        "null_reps": 199,
        "null_screen": 19,
        "screen_hits": 10,
    }
}


def lines_of(letters: str):
    return [(i, 0, ch) for i, ch in enumerate(letters)]


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
    lines = {"verse": lines_of(lam), "colon": lines_of(lam)}
    r = score_chapter(lines, CFG, np.random.default_rng(1))
    assert r["n_letters"] == 22 and r["order_name"] == "pe-ayin" and r["missing"] == 0
    assert r["p"] <= 1 / 200 + 1e-12  # no shuffle comes close
    assert r["first_letter"] == "א" and r["last_letter"] == "ת"


def test_ordinary_text_is_not_significant():
    text = "ויאמרויהיוידברהנהאשרכיולאועתה"  # verse starts of narrative
    lines = {"verse": lines_of(text), "colon": lines_of(text)}
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
