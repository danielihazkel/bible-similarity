"""Units: verse, chapter, parasha, pericope (DESIGN.md §4).

All units are contiguous verse ranges. Pericopes end after any verse carrying a MAM pe/samekh
marker (mid-verse markers are snapped to the end of their verse; several markers in one verse
collapse into one break, typed by the last) and always at the end of a book.
"""

from __future__ import annotations

import pandas as pd

from bsim.data.canon import BOOKS, hebrew_numeral
from bsim.data.refs import parse_range

UNIT_COLUMNS = [
    "unit_id",
    "unit_type",
    "label_en",
    "label_he",
    "book_id",
    "start_verse_id",
    "end_verse_id",
    "n_verses",
    "marker",
]


def _ref_en(row) -> str:
    return f"{row.chapter}:{row.verse}"


def _ref_he(row) -> str:
    return f"{hebrew_numeral(row.chapter)}:{hebrew_numeral(row.verse)}"


def _range_labels(book_id: int, first, last) -> tuple[str, str]:
    """English and Hebrew labels for a verse range; `first`/`last` are verse rows."""
    book = BOOKS[book_id]
    if (first.chapter, first.verse) == (last.chapter, last.verse):
        return f"{book.sefaria} {_ref_en(first)}", f"{book.he} {_ref_he(first)}"
    if first.chapter == last.chapter:
        en = f"{book.sefaria} {_ref_en(first)}–{last.verse}"
        he = f"{book.he} {_ref_he(first)}–{hebrew_numeral(last.verse)}"
    else:
        en = f"{book.sefaria} {_ref_en(first)}–{_ref_en(last)}"
        he = f"{book.he} {_ref_he(first)}–{_ref_he(last)}"
    return en, he


def _unit(unit_id, unit_type, en, he, book_id, start, end, marker=None) -> dict:
    return {
        "unit_id": unit_id,
        "unit_type": unit_type,
        "label_en": en,
        "label_he": he,
        "book_id": int(book_id),
        "start_verse_id": int(start),
        "end_verse_id": int(end),
        "n_verses": int(end - start + 1),
        "marker": marker,
    }


def verse_units(verses: pd.DataFrame) -> list[dict]:
    out = []
    for row in verses.itertuples(index=False):
        en, he = _range_labels(row.book_id, row, row)
        out.append(
            _unit(f"v:{row.verse_id}", "verse", en, he, row.book_id, row.verse_id, row.verse_id)
        )
    return out


def chapter_units(verses: pd.DataFrame) -> list[dict]:
    out = []
    for (book_id, chapter), g in verses.groupby(["book_id", "chapter"], sort=True):
        book = BOOKS[book_id]
        out.append(
            _unit(
                f"c:{book_id}:{chapter}",
                "chapter",
                f"{book.sefaria} {chapter}",
                f"{book.he} {hebrew_numeral(chapter)}",
                book_id,
                g.verse_id.min(),
                g.verse_id.max(),
            )
        )
    return out


def parasha_units(verses: pd.DataFrame, parashiyot: list[tuple[str, str, str]]) -> list[dict]:
    """Parashiyot from schema `wholeRef`s; asserts they tile the Torah exactly."""
    index = {(r.book_id, r.chapter, r.verse): r.verse_id for r in verses.itertuples(index=False)}
    out = []
    for title, he_title, whole_ref in parashiyot:
        book, (c1, v1), (c2, v2) = parse_range(whole_ref)
        try:
            start, end = index[(book.book_id, c1, v1)], index[(book.book_id, c2, v2)]
        except KeyError as e:
            raise RuntimeError(f"parasha {title}: ref {whole_ref} not in the verse table") from e
        out.append(_unit(f"p:{title}", "parasha", title, he_title, book.book_id, start, end))
    out.sort(key=lambda u: u["start_verse_id"])
    torah = verses[verses.book_id.isin([b.book_id for b in BOOKS if b.section == "Torah"])]
    expected = int(torah.verse_id.min())
    for u in out:
        if u["start_verse_id"] != expected:
            raise RuntimeError(f"parashiyot do not tile the Torah: gap/overlap at {u['unit_id']}")
        expected = u["end_verse_id"] + 1
    if expected != int(torah.verse_id.max()) + 1:
        raise RuntimeError("parashiyot do not reach the end of the Torah")
    return out


def pericope_units(verses: pd.DataFrame) -> list[dict]:
    out = []
    start = None
    rows = list(verses.itertuples(index=False))
    for i, row in enumerate(rows):
        if start is None:
            start = row
        book_end = i + 1 == len(rows) or rows[i + 1].book_id != row.book_id
        brk = row.break_after if isinstance(row.break_after, str) else None  # None/NaN -> None
        if brk or book_end:
            en, he = _range_labels(row.book_id, start, row)
            marker = brk or "book_end"
            n = len(out) + 1
            out.append(
                _unit(
                    f"s:{n}", "pericope", en, he, row.book_id, start.verse_id, row.verse_id, marker
                )
            )
            start = None
    return out


def build_units(
    verses: pd.DataFrame, parashiyot: list[tuple[str, str, str]]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`units` and `unit_members` tables. `verses` must be sorted by verse_id."""
    units = (
        verse_units(verses)
        + chapter_units(verses)
        + parasha_units(verses, parashiyot)
        + pericope_units(verses)
    )
    units_df = pd.DataFrame(units, columns=UNIT_COLUMNS)
    members_df = pd.DataFrame(
        [
            (u["unit_id"], vid)
            for u in units
            for vid in range(u["start_verse_id"], u["end_verse_id"] + 1)
        ],
        columns=["unit_id", "verse_id"],
    )
    return units_df, members_df
