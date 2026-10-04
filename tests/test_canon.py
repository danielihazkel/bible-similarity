import pytest

from bsim.data.canon import BOOKS, BY_OSIS, BY_SEFARIA, TORAH, oshb_to_mam
from bsim.data.refs import parse_range


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


def test_oshb_to_mam_overrides():
    assert oshb_to_mam("Exod", 20, 12) == (20, 12)
    assert oshb_to_mam("Exod", 20, 13) == (20, 13)
    assert oshb_to_mam("Exod", 20, 16) == (20, 13)
    assert oshb_to_mam("Exod", 20, 17) == (20, 14)
    assert oshb_to_mam("Exod", 20, 26) == (20, 23)
    assert oshb_to_mam("Deut", 5, 20) == (5, 17)
    assert oshb_to_mam("Deut", 5, 21) == (5, 18)
    assert oshb_to_mam("Num", 25, 19) == (26, 1)
    assert oshb_to_mam("Num", 26, 1) == (26, 1)
    assert oshb_to_mam("Gen", 1, 1) == (1, 1)


def test_parse_range():
    book, start, end = parse_range("Genesis 1:1-6:8")
    assert (book.sefaria, start, end) == ("Genesis", (1, 1), (6, 8))
    book, start, end = parse_range("I Samuel 3:4-9")
    assert (book.osis, start, end) == ("1Sam", (3, 4), (3, 9))
    assert parse_range("Song of Songs 2:1")[1:] == ((2, 1), (2, 1))
    with pytest.raises(ValueError):
        parse_range("Genesis 1")
