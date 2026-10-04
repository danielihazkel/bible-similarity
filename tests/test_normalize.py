from bsim.text.normalize import consonantal, display_tokens, fold_finals, match_key


def test_points_and_teamim_stripped():
    assert consonantal("בְּ/רֵאשִׁ֖ית") == "בראשית"
    assert consonantal("הָאָֽרֶץ׃") == "הארץ"


def test_maqaf_paseq_cgj_removed():
    assert consonantal("וַֽיְהִי־עֶ֥רֶב") == "ויהי ערב"
    assert consonantal("אֱלֹהִ֤ים ׀ לָאוֹר֙") == "אלהים לאור"
    assert consonantal("מִירוּשָׁלַ֙" + "\u034f" + "ִם֙") == "מירושלם"
    assert consonantal("׆ וַיְהִ֛י׃") == "ויהי"


def test_finals_folded_only_in_key():
    assert consonantal("הָאָֽרֶץ") == "הארץ"
    assert match_key("הָאָֽרֶץ") == "הארצ"
    assert fold_finals("ךםןףץ") == "כמנפצ"


def test_display_tokens_split_after_maqaf():
    assert display_tokens("וַֽיְהִי־עֶ֥רֶב יוֹם") == ["וַֽיְהִי־", "עֶ֥רֶב", "יוֹם"]
    assert display_tokens("בִּימֵ֣י ׀ עֻזִּיָּ֣ה") == ["בִּימֵ֣י", "׀", "עֻזִּיָּ֣ה"]


def test_strip_prefix():
    from bsim.text.normalize import strip_prefix

    assert strip_prefix("ובראשית") == "ראשית"
    assert strip_prefix("והארצ") == "ארצ"
    assert strip_prefix("משה") == "שה"  # greedy; only the min-root guard stops it
    assert strip_prefix("לב") == "לב"  # would leave one letter
    assert strip_prefix("ושמ", min_root=1) == "מ"
    assert strip_prefix("ארצ") == "ארצ"
    assert strip_prefix("") == ""
