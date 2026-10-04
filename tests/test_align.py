from bsim.data.align import align


def test_identical():
    assert align(["א", "ב", "ג"], ["א", "ב", "ג"]) == [0, 1, 2]


def test_plene_defective_replacement_maps():
    assert align(["תוכחת", "ב"], ["תוכחות", "ב"]) == [0, 1]


def test_split_word_left_unaligned():
    # WLC בל־אמים vs MAM בלאמים (Ps 149:7): a 2:1 replacement is not mapped.
    assert align(["לעשות", "בל", "אמימ"], ["לעשות", "בלאמימ"]) == [0, None, None]


def test_letterless_display_tokens_skipped():
    assert align(["אלהימ", "לאור"], ["אלהימ", "", "לאור"]) == [0, 2]
