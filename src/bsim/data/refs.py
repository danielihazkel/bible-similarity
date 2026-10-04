"""Parse Sefaria citations into verse ranges (DESIGN.md §8.1).

Forms handled: `Book C:V`, `Book C:V-V`, `Book C:V-C:V`, whole chapters `Book C` and chapter
ranges `Book C-C`. Book names are Sefaria titles (`canon.BY_SEFARIA`) and may contain spaces.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from bsim.data.canon import BY_SEFARIA, Book

_REF = re.compile(r"^(?P<book>.+?) (?P<c1>\d+)(?::(?P<v1>\d+))?(?:-(?P<x>\d+)(?::(?P<y>\d+))?)?$")


@dataclass(frozen=True)
class Ref:
    """A citation; `v1`/`v2` are None for whole-chapter forms."""

    book: Book
    c1: int
    v1: int | None
    c2: int
    v2: int | None


def parse_ref(ref: str) -> Ref:
    """`"Genesis 1:1-6:8"` -> Ref(Genesis, 1, 1, 6, 8); `"Judges 4-5"` -> chapters 4 to 5."""
    m = _REF.match(ref.strip())
    if not m or m["book"] not in BY_SEFARIA:
        raise ValueError(f"cannot parse ref {ref!r}")
    book, c1, x, y = BY_SEFARIA[m["book"]], int(m["c1"]), m["x"], m["y"]
    if m["v1"] is None:
        if y is not None:  # "Book C-C:V" is not a Sefaria form
            raise ValueError(f"cannot parse ref {ref!r}")
        c2 = int(x) if x else c1
        if c2 < c1:
            raise ValueError(f"reversed range in ref {ref!r}")
        return Ref(book, c1, None, c2, None)
    v1 = int(m["v1"])
    if x is None:
        c2, v2 = c1, v1
    elif y is None:
        c2, v2 = c1, int(x)
    else:
        c2, v2 = int(x), int(y)
    if (c2, v2) < (c1, v1):
        raise ValueError(f"reversed range in ref {ref!r}")
    return Ref(book, c1, v1, c2, v2)


def parse_range(ref: str) -> tuple[Book, tuple[int, int], tuple[int, int]]:
    """Verse-level forms only: `"Genesis 1:1-6:8"` -> (Genesis, (1, 1), (6, 8))."""
    r = parse_ref(ref)
    if r.v1 is None or r.v2 is None:
        raise ValueError(f"ref {ref!r} is not verse-level")
    return r.book, (r.c1, r.v1), (r.c2, r.v2)


class RefIndex:
    """Resolve refs to inclusive `verse_id` ranges using the verse table."""

    def __init__(self, verses: pd.DataFrame) -> None:
        cols = verses[["verse_id", "book_id", "chapter", "verse"]].itertuples(index=False)
        self._vid: dict[tuple[int, int, int], int] = {}
        self._last: dict[tuple[int, int], int] = {}
        for vid, b, c, v in cols:
            self._vid[(b, c, v)] = vid
            self._last[(b, c)] = max(v, self._last.get((b, c), 0))

    def _get(self, ref: str, b: int, c: int, v: int) -> int:
        try:
            return self._vid[(b, c, v)]
        except KeyError:
            raise ValueError(f"ref {ref!r}: no verse {c}:{v}") from None

    def resolve(self, ref: str | Ref) -> tuple[int, int]:
        """Inclusive (start_vid, end_vid); raises ValueError if either end does not exist."""
        r = parse_ref(ref) if isinstance(ref, str) else ref
        b = r.book.book_id
        v1 = 1 if r.v1 is None else r.v1
        v2 = self._last.get((b, r.c2), 0) if r.v2 is None else r.v2
        return self._get(str(ref), b, r.c1, v1), self._get(str(ref), b, r.c2, v2)
