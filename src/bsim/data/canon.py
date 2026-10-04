"""The 39 books of the Tanakh in Jewish canon order (DESIGN.md §2).

`book_id` is the 0-based position in canon order. Chapter counts follow Hebrew versification
(929 chapters in total) and are used as assertions when parsing the sources.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    book_id: int
    sefaria: str  # Sefaria title, e.g. "I Samuel"
    osis: str  # OSIS / OSHB file name, e.g. "1Sam"
    he: str  # Hebrew name
    section: str  # Torah | Prophets | Writings (Sefaria category names)
    n_chapters: int

    @property
    def sefaria_slug(self) -> str:
        """Sefaria-Export schema file stem: spaces become underscores."""
        return self.sefaria.replace(" ", "_")


_BOOKS: list[tuple[str, str, str, str, int]] = [
    # Torah
    ("Genesis", "Gen", "בראשית", "Torah", 50),
    ("Exodus", "Exod", "שמות", "Torah", 40),
    ("Leviticus", "Lev", "ויקרא", "Torah", 27),
    ("Numbers", "Num", "במדבר", "Torah", 36),
    ("Deuteronomy", "Deut", "דברים", "Torah", 34),
    # Nevi'im
    ("Joshua", "Josh", "יהושע", "Prophets", 24),
    ("Judges", "Judg", "שופטים", "Prophets", 21),
    ("I Samuel", "1Sam", "שמואל א", "Prophets", 31),
    ("II Samuel", "2Sam", "שמואל ב", "Prophets", 24),
    ("I Kings", "1Kgs", "מלכים א", "Prophets", 22),
    ("II Kings", "2Kgs", "מלכים ב", "Prophets", 25),
    ("Isaiah", "Isa", "ישעיהו", "Prophets", 66),
    ("Jeremiah", "Jer", "ירמיהו", "Prophets", 52),
    ("Ezekiel", "Ezek", "יחזקאל", "Prophets", 48),
    ("Hosea", "Hos", "הושע", "Prophets", 14),
    ("Joel", "Joel", "יואל", "Prophets", 4),
    ("Amos", "Amos", "עמוס", "Prophets", 9),
    ("Obadiah", "Obad", "עובדיה", "Prophets", 1),
    ("Jonah", "Jonah", "יונה", "Prophets", 4),
    ("Micah", "Mic", "מיכה", "Prophets", 7),
    ("Nahum", "Nah", "נחום", "Prophets", 3),
    ("Habakkuk", "Hab", "חבקוק", "Prophets", 3),
    ("Zephaniah", "Zeph", "צפניה", "Prophets", 3),
    ("Haggai", "Hag", "חגי", "Prophets", 2),
    ("Zechariah", "Zech", "זכריה", "Prophets", 14),
    ("Malachi", "Mal", "מלאכי", "Prophets", 3),
    # Ketuvim
    ("Psalms", "Ps", "תהילים", "Writings", 150),
    ("Proverbs", "Prov", "משלי", "Writings", 31),
    ("Job", "Job", "איוב", "Writings", 42),
    ("Song of Songs", "Song", "שיר השירים", "Writings", 8),
    ("Ruth", "Ruth", "רות", "Writings", 4),
    ("Lamentations", "Lam", "איכה", "Writings", 5),
    ("Ecclesiastes", "Eccl", "קהלת", "Writings", 12),
    ("Esther", "Esth", "אסתר", "Writings", 10),
    ("Daniel", "Dan", "דניאל", "Writings", 12),
    ("Ezra", "Ezra", "עזרא", "Writings", 10),
    ("Nehemiah", "Neh", "נחמיה", "Writings", 13),
    ("I Chronicles", "1Chr", "דברי הימים א", "Writings", 29),
    ("II Chronicles", "2Chr", "דברי הימים ב", "Writings", 36),
]

BOOKS: tuple[Book, ...] = tuple(
    Book(i, sefaria, osis, he, section, n) for i, (sefaria, osis, he, section, n) in enumerate(_BOOKS)
)
BY_SEFARIA: dict[str, Book] = {b.sefaria: b for b in BOOKS}
BY_OSIS: dict[str, Book] = {b.osis: b for b in BOOKS}
TORAH: tuple[Book, ...] = tuple(b for b in BOOKS if b.section == "Torah")
