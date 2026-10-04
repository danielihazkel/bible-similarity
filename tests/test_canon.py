from bsim.data.canon import BOOKS, BY_OSIS, BY_SEFARIA, TORAH


def test_book_table():
    assert len(BOOKS) == 39
    assert sum(b.n_chapters for b in BOOKS) == 929
    assert [b.book_id for b in BOOKS] == list(range(39))
    assert len(BY_SEFARIA) == len(BY_OSIS) == 39
    assert [b.sefaria for b in TORAH] == [
        "Genesis",
        "Exodus",
        "Leviticus",
        "Numbers",
        "Deuteronomy",
    ]


def test_canon_order_and_sections():
    assert BOOKS[0].sefaria == "Genesis"
    assert BOOKS[-1].sefaria == "II Chronicles"
    assert BY_SEFARIA["Malachi"].book_id < BY_SEFARIA["Psalms"].book_id
    assert {b.section for b in BOOKS} == {"Torah", "Prophets", "Writings"}


def test_sefaria_slug():
    assert BY_SEFARIA["Song of Songs"].sefaria_slug == "Song_of_Songs"
    assert BY_OSIS["1Sam"].sefaria_slug == "I_Samuel"
