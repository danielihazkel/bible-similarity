import pandas as pd
import pytest

from bsim.data.canon import BOOKS, hebrew_numeral
from bsim.data.units import build_units, parasha_units, pericope_units


def _verses(spec: list[tuple[int, int, int]]) -> pd.DataFrame:
    """Toy verse table from (book_id, chapter, n_verses) triples, no breaks."""
    rows = []
    for book_id, chapter, n in spec:
        for v in range(1, n + 1):
            rows.append(
                {
                    "verse_id": len(rows),
                    "book_id": book_id,
                    "chapter": chapter,
                    "verse": v,
                    "break_after": None,
                }
            )
    return pd.DataFrame(rows)


def _torah_parashiyot():
    return [(f"P{b.book_id}", "פ", f"{b.sefaria} 1:1-1:2") for b in BOOKS[:5]]


def test_pericopes_cross_chapters_and_break_at_book_end():
    verses = _verses([(0, 1, 3), (0, 2, 2), (1, 1, 2)])
    verses.loc[1, "break_after"] = "pe"
    out = pericope_units(verses)
    spans = [(u["start_verse_id"], u["end_verse_id"], u["marker"]) for u in out]
    assert spans == [(0, 1, "pe"), (2, 4, "book_end"), (5, 6, "book_end")]
    assert [u["unit_id"] for u in out] == ["s:1", "s:2", "s:3"]
    assert out[0]["label_en"] == "Genesis 1:1–2"
    assert out[1]["label_en"] == "Genesis 1:3–2:2"
    assert out[1]["label_he"] == "בראשית א:ג–ב:ב"


def test_parasha_coverage():
    verses = _verses([(b.book_id, 1, 2) for b in BOOKS[:5]])
    good = _torah_parashiyot()
    assert len(parasha_units(verses, good)) == 5
    gap = good[:2] + [("X", "פ", "Leviticus 1:2-1:2")] + good[3:]
    with pytest.raises(RuntimeError, match="tile"):
        parasha_units(verses, gap)


def test_build_units_members():
    verses = _verses([(b.book_id, 1, 2) for b in BOOKS[:5]])
    units, members = build_units(verses, _torah_parashiyot())
    assert units.unit_type.value_counts().to_dict() == {
        "verse": 10,
        "chapter": 5,
        "parasha": 5,
        "pericope": 5,
    }
    assert len(members) == 10 * 4
    assert units.set_index("unit_id").loc["c:0:1", "label_he"] == "בראשית א"


def test_hebrew_numeral():
    assert hebrew_numeral(1) == "א"
    assert hebrew_numeral(15) == "טו"
    assert hebrew_numeral(16) == "טז"
    assert hebrew_numeral(119) == "קיט"
    assert hebrew_numeral(150) == "קנ"
