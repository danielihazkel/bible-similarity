"""English (KJV) verse numbers -> our verses (MAM, Hebrew numbering; DESIGN.md §16.63).

TIPNR, like most English tools, numbers verses as the KJV does. Where a chapter break falls
elsewhere in the Hebrew (Exod 8:1 is 7:26, 1 Chr 6:1–15 is 5:27–41, Joel 3 is chapter 4) every
reference of that chapter lands some verses off, which a fixed tolerance cannot absorb (1 Chr 6,
the Levites' genealogy, is 15 verses off). Each rule below says where an English chapter's run of
verses starts in the Hebrew; the verses after it follow one by one in canon order (`verse_id`),
across a chapter end if need be. An English verse past the end of a Hebrew chapter without a rule
(Gen 31:55, Num 16:36) runs on into the next chapter the same way, which is where it is.

Checked on TIPNR's 29,782 Hebrew Bible references: 98.3% name their verse's Strong's number
exactly (about 80% without the rules). Not covered: the Psalm titles (counted as verse 1 in the
Hebrew, so a psalm's verses run one or two on) and the Decalogue's merged verses (Exod 20,
Deut 5); a caller snaps what is left to the nearest verse naming the person.
"""

from __future__ import annotations

from bisect import bisect_right

# (osis, English chapter, from English verse) -> (Hebrew chapter, verse)
RULES: tuple[tuple[str, int, int, int, int], ...] = (
    ("Gen", 32, 1, 32, 2),
    ("Exod", 8, 1, 7, 26),
    ("Exod", 22, 1, 21, 37),
    ("Lev", 6, 1, 5, 20),
    ("Num", 17, 1, 17, 16),
    ("Num", 30, 1, 30, 2),
    ("Deut", 13, 1, 13, 2),
    ("Deut", 23, 1, 23, 2),
    ("Deut", 29, 1, 28, 69),
    ("1Sam", 21, 1, 21, 2),
    ("1Sam", 24, 1, 24, 2),
    ("2Sam", 19, 1, 19, 2),
    ("1Kgs", 5, 1, 5, 15),
    ("1Kgs", 22, 44, 22, 45),
    ("2Kgs", 12, 1, 12, 2),
    ("1Chr", 6, 1, 5, 27),
    ("1Chr", 12, 5, 12, 6),
    ("2Chr", 2, 1, 1, 18),
    ("2Chr", 14, 1, 13, 23),
    ("Neh", 4, 1, 3, 33),
    ("Neh", 10, 1, 10, 2),
    ("Job", 41, 1, 40, 25),
    ("Eccl", 5, 1, 4, 17),
    ("Song", 7, 1, 7, 2),
    ("Isa", 9, 1, 8, 23),
    ("Isa", 64, 1, 63, 19),
    ("Jer", 9, 1, 8, 23),
    ("Ezek", 21, 1, 21, 6),
    ("Dan", 4, 1, 3, 31),
    ("Dan", 6, 1, 6, 2),
    ("Hos", 2, 1, 2, 3),
    ("Hos", 12, 1, 12, 2),
    ("Hos", 14, 1, 14, 2),
    ("Joel", 3, 1, 4, 1),
    ("Jonah", 2, 1, 2, 2),
    ("Mic", 5, 1, 4, 14),
    ("Nah", 2, 1, 2, 2),
    ("Zech", 2, 1, 2, 5),
    ("Mal", 4, 1, 3, 19),
)  # fmt: skip


class English:
    """English (book_id, chapter, verse) -> verse_id, over the verses of the corpus."""

    def __init__(self, vid_of: dict[tuple[int, int, int], int], osis_of: dict[int, str]):
        self.vid_of = vid_of
        self.book_at = {vid: b for (b, _, _), vid in vid_of.items()}
        book_of = {o: b for b, o in osis_of.items()}
        self.rules: dict[tuple[int, int], tuple[list[int], list[tuple[int, int]]]] = {}
        for osis, ch, v, hc, hv in sorted(RULES):
            if osis in book_of:
                starts, to = self.rules.setdefault((book_of[osis], ch), ([], []))
                starts.append(v)
                to.append((hc, hv))

    def __call__(self, book: int, chapter: int, verse: int) -> int | None:
        verse = max(verse, 1)  # a psalm title (verse 0) is the Hebrew's verse 1
        anchor, offset = self.vid_of.get((book, chapter, 1)), verse - 1
        rule = self.rules.get((book, chapter))
        if rule:
            starts, to = rule
            i = bisect_right(starts, verse) - 1
            if i >= 0:
                anchor, offset = self.vid_of.get((book, *to[i])), verse - starts[i]
        if anchor is None:
            return None
        vid = anchor + offset  # on into the next chapter past the end of this one
        return vid if self.book_at.get(vid) == book else None
