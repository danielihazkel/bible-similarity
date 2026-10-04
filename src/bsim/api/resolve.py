"""Free-form references -> (book, chapter, verse) for `/api/resolve` (DESIGN.md §10).

Accepted: English titles, OSIS ids and Hebrew names, any unambiguous prefix of them (`Gen`, `1 Sam`,
`בר'`), followed by a chapter and an optional verse in Arabic digits or Hebrew numerals
(`Genesis 1:1`, `1Kgs 17`, `בראשית א א`, `שמואל א ג:ד`, `תהלים קיט קה`). Anything else -> None, so
the search box can try a reference and a text search with the same input.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bsim.data.canon import BOOKS, Book, hebrew_numeral
from bsim.text.normalize import MAQAF

_ROMAN = {"i": "1", "ii": "2"}
# Common spellings that differ from the canon table's Hebrew names.
_HE_VARIANTS = {
    "תהילים": ["תהלים"],
    "ישעיהו": ["ישעיה"],
    "ירמיהו": ["ירמיה"],
    "עובדיה": ["עבדיה"],
    "צפניה": ["צפניהו"],
    "שיר השירים": ['שה"ש'],
    "דברי הימים א": ["דהי א", 'דה"א'],
    "דברי הימים ב": ["דהי ב", 'דה"ב'],
}
_SPLIT = re.compile(r"[\s:.,;\-–]+")
_PUNCT = re.compile(r"[\"'׳״]")
# points and te'amim (U+0591-U+05BD, U+05BF-U+05C7) and CGJ; maqaf (U+05BE) becomes a space
_MARKS = re.compile(f"[{chr(0x591)}-{chr(0x5BD)}{chr(0x5BF)}-{chr(0x5C7)}{chr(0x34F)}]")
_LETTERS = {ch: v for v, ch in enumerate("אבגדהוזחט", 1)}
_LETTERS |= {ch: 10 * v for v, ch in enumerate("יכלמנסעפצ", 1)}
_LETTERS |= {ch: 100 * v for v, ch in enumerate("קרשת", 1)}


@dataclass(frozen=True)
class Resolved:
    book: Book
    chapter: int
    verse: int | None


def _tokens(s: str) -> list[str]:
    s = _PUNCT.sub("", _MARKS.sub("", s).replace(MAQAF, " ").lower())
    s = re.sub(r"^([12])(?=[a-z])", r"\1 ", s.strip())  # 1Sam -> 1 sam
    return [t for t in _SPLIT.split(s) if t]


def _aliases(book: Book) -> list[list[str]]:
    en = book.sefaria.lower().split()
    names = [en, [_ROMAN.get(t, t) for t in en], _tokens(book.osis), _tokens(book.he)]
    names += [_tokens(v) for v in _HE_VARIANTS.get(book.he, [])]
    return names


ALIASES: list[tuple[Book, list[str]]] = [(b, a) for b in BOOKS for a in _aliases(b)]


def parse_number(token: str) -> int | None:
    """Arabic digits, or a Hebrew numeral written canonically (`קיט`, `טו`); else None."""
    if token.isdigit():
        return int(token)
    if not token or any(ch not in _LETTERS for ch in token):
        return None
    n = sum(_LETTERS[ch] for ch in token)
    return n if 0 < n < 1000 and hebrew_numeral(n) == token else None


def _match_book(tokens: list[str], n: int) -> Book | None:
    """The one book an alias of which is `tokens[:n]` exactly, else the one it prefixes."""
    head = tokens[:n]
    exact = {b.book_id: b for b, a in ALIASES if a == head}
    if len(exact) == 1:
        return next(iter(exact.values()))
    prefix = {
        b.book_id: b
        for b, a in ALIASES
        if len(a) == n and a[:-1] == head[:-1] and a[-1].startswith(head[-1])
    }
    return next(iter(prefix.values())) if len(prefix) == 1 else None


def resolve(query: str) -> Resolved | None:
    tokens = _tokens(query)
    for n in (3, 2, 1):
        # chapter [verse [range end, ignored]]
        if len(tokens) <= n or len(tokens) > n + 3:
            continue
        book = _match_book(tokens, n)
        nums = [parse_number(t) for t in tokens[n : n + 2]]
        if book is None or None in nums:
            continue
        chapter, verse = nums[0], nums[1] if len(nums) > 1 else None
        if 1 <= chapter <= book.n_chapters:
            return Resolved(book, chapter, verse)
    return None
