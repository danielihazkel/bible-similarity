import pytest

from bsim.api.resolve import parse_number, resolve
from bsim.text.morph import decode


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Genesis 1:1", ("Genesis", 1, 1)),
        ("gen 1 1", ("Genesis", 1, 1)),
        ("1Sam 3:4", ("I Samuel", 3, 4)),
        ("I Kings 17", ("I Kings", 17, None)),
        ("Ps 23", ("Psalms", 23, None)),
        ("Song of Songs 2:1", ("Song of Songs", 2, 1)),
        ("Isa 40:1-3", ("Isaiah", 40, 1)),
        ("בראשית א א", ("Genesis", 1, 1)),
        ("בְּרֵאשִׁית א:א", ("Genesis", 1, 1)),
        ("בר' א, ב", ("Genesis", 1, 2)),
        ("שמואל א ג ד", ("I Samuel", 3, 4)),
        ('תהלים קי"ט קה', ("Psalms", 119, 105)),
        ('דה"א ה', ("I Chronicles", 5, None)),
    ],
)
def test_resolve(query, expected):
    r = resolve(query)
    assert r is not None
    assert (r.book.sefaria, r.chapter, r.verse) == expected


@pytest.mark.parametrize(
    "query", ["jo 3", "בראשית", "בראשית ברא אלהים", "Gen 51", "ויאמר", "שמואל ג ד", ""]
)
def test_not_a_reference(query):
    assert resolve(query) is None


def test_parse_number():
    assert [parse_number(t) for t in ("12", "א", "טו", "טז", "קיט", "תתק")] == [
        12,
        1,
        15,
        16,
        119,
        900,
    ]
    assert parse_number("יה") is None  # 15 is written טו
    assert parse_number("ברא") is None


def test_decode_morph():
    assert decode("HC/Vqw3ms") == [
        "מילת חיבור",
        "פועל · קל · עתיד מהופך (ויקטל) · גוף שלישי · זכר · יחיד",
    ]
    assert decode("HC/Ncfdc/Sp3mp")[1:] == [
        "שם עצם · נקבה · זוגי · נסמך",
        "סיומת · כינוי חבור · גוף שלישי · זכר · רבים",
    ]
    assert decode("HTd/Aafsa") == ["מילית · ה הידיעה", "שם תואר · נקבה · יחיד · נפרד"]
    assert decode("HVqrmsa") == ["פועל · קל · בינוני פועל · זכר · יחיד · נפרד"]
    assert decode("HPdxms") == ["כינוי · רומז · זכר · יחיד"]
    assert decode("AVhp3ms") == ["ארמית · פועל · הפעל · עבר · גוף שלישי · זכר · יחיד"]
    assert decode("H") == decode(None) == decode("") == []
