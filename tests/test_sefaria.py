from bsim.data.sefaria import Break, clean_mam_verse


def test_footnote_dropped():
    v = clean_mam_verse(
        'עֲוֺנִ֖י מִנְּשֹֽׂא<sup class="footnote-marker">*</sup>'
        '<i class="footnote">(בספרי ספרד ואשכנז מִנְּשֽׂוֹא)</i>׃'
    )
    assert v.text_display == "עֲוֺנִ֖י מִנְּשֹֽׂא׃"
    assert v.ketiv_note is None
    assert v.breaks == []


def test_ketiv_qere():
    v = clean_mam_verse(
        'אִמָּ֑הּ <span class="mam-kq"><span class="mam-kq-k">(יעשה)</span> '
        '<span class="mam-kq-q">[יַ֣עַשׂ]</span></span> יְהֹוָ֤ה'
    )
    assert v.text_display == "אִמָּ֑הּ יַ֣עַשׂ יְהֹוָ֤ה"
    assert v.ketiv_note == "יעשה"


def test_qere_only_ketiv_only_trivial():
    v = clean_mam_verse('יְהֹוָ֥ה <span class="mam-kq-q">[צְבָא֖וֹת]</span> תַּעֲשֶׂה')
    assert v.text_display == "יְהֹוָ֥ה צְבָא֖וֹת תַּעֲשֶׂה"
    v = clean_mam_verse('חֲמֵ֥שׁ <span class="mam-kq-k">(חמש)</span> מֵא֖וֹת')
    assert (v.text_display, v.ketiv_note) == ("חֲמֵ֥שׁ מֵא֖וֹת", "חמש")
    v = clean_mam_verse('בַשָּׁמַ֙יִם֙ <span class="mam-kq-trivial">מַעֲלוֹתָ֔ו</span> וַאֲגֻדָּת֖וֹ')
    assert v.text_display == "בַשָּׁמַ֙יִם֙ מַעֲלוֹתָ֔ו וַאֲגֻדָּת֖וֹ"


def test_paseq_big_invnun_implicit_maqaf():
    v = clean_mam_verse(
        '<span class="mam-spi-invnun">׆</span>&nbsp;<big>בְּ</big>רֵאשִׁ֖ית&thinsp;<b>׀</b> '
        'יְֽהִ֫י<span class="mam-implicit-maqaf">־</span>חֹ֥שֶׁךְ'
    )
    assert v.text_display == "בְּרֵאשִׁ֖ית ׀ יְֽהִ֫י־חֹ֥שֶׁךְ"


def test_break_at_verse_end():
    v = clean_mam_verse('אֶחָֽד׃&nbsp;<span class="mam-spi-pe">{פ}</span><br>')
    assert v.text_display == "אֶחָֽד׃"
    assert v.breaks == [Break("pe", False)]


def test_several_breaks_mid_verse():
    v = clean_mam_verse(
        'לֹ֥א תִּרְצָ֖ח׃ <span class="mam-spi-samekh">{ס}</span> לֹ֣א תִּנְאָ֑ף׃ '
        '<span class="mam-spi-samekh">{ס}</span>&nbsp;&nbsp;'
    )
    assert v.breaks == [Break("samekh", True), Break("samekh", False)]
    assert v.text_display == "לֹ֥א תִּרְצָ֖ח׃ לֹ֣א תִּנְאָ֑ף׃"
