"""Verse halves from the te'amim (DESIGN.md §16.9).

The disjunctive accents mark the Masoretic reading pauses of every verse. The strongest pause
inside a verse divides it into cola (verse members):

- all books: etnahta (U+0591) closes the first half;
- the poetic books (Psalms, Proverbs, Job 3:2–42:6, the "Emet" accent system): oleh-ve-yored
  (ole U+05AB with merkha U+05A5 on the same word or the next) is a stronger pause before the
  etnahta, so such verses have three cola.

Spans are inclusive ranges of display tokens (`text.normalize.display_tokens`, the
`words.display_idx` coordinates). A verse without a pause is one colon.
"""

from __future__ import annotations

ETNAHTA = "֑"
OLE = "֫"
MERKHA = "֥"

POETIC_BOOKS = ("Ps", "Prov", "Job")
# Job's prose frame uses the prose accents: 1:1–3:1 and 42:7–17
JOB_PROSE = ((1, 1, 3, 1), (42, 7, 42, 17))


def poetic(osis: str, chapter: int, verse: int) -> bool:
    """Whether a verse is accented with the poetic (Emet) system."""
    if osis not in POETIC_BOOKS:
        return False
    if osis == "Job":
        for c0, v0, c1, v1 in JOB_PROSE:
            if (c0, v0) <= (chapter, verse) <= (c1, v1):
                return False
    return True


def pauses(tokens: list[str], is_poetic: bool) -> list[tuple[int, str]]:
    """(last token index of a colon, accent name) of each main pause, in order (not the end)."""
    out: list[tuple[int, str]] = []
    last = len(tokens) - 1
    if is_poetic:
        for i, t in enumerate(tokens):
            if OLE in t:
                # the yored (merkha) sits on the ole word or the next one; the pause follows it
                j = i if MERKHA in t or i == last else i + 1
                if j < last:
                    out.append((j, "oleh-ve-yored"))
                break
    for i, t in enumerate(tokens):
        if ETNAHTA in t:
            if i < last and all(i > j for j, _ in out):
                out.append((i, "etnahta"))
            break
    return out


def cola(tokens: list[str], is_poetic: bool) -> list[tuple[int, int]]:
    """Inclusive (first, last) display-token spans of the verse members."""
    if not tokens:
        return []
    spans, start = [], 0
    for end, _ in pauses(tokens, is_poetic):
        spans.append((start, end))
        start = end + 1
    spans.append((start, len(tokens) - 1))
    return spans
