"""Parse Sefaria citations into verse ranges (DESIGN.md §8.1).

M2 needs only the `Book C:V-C:V` and `Book C:V-V` forms used by schema `wholeRef`s; M3 extends
this module to all citation forms.
"""

from __future__ import annotations

import re

from bsim.data.canon import BY_SEFARIA, Book

_RANGE = re.compile(r"^(?P<book>.+?) (?P<c1>\d+):(?P<v1>\d+)(?:-(?:(?P<c2>\d+):)?(?P<v2>\d+))?$")


def parse_range(ref: str) -> tuple[Book, tuple[int, int], tuple[int, int]]:
    """`"Genesis 1:1-6:8"` -> (Genesis, (1, 1), (6, 8)); a single verse gives start == end."""
    m = _RANGE.match(ref.strip())
    if not m or m["book"] not in BY_SEFARIA:
        raise ValueError(f"cannot parse ref {ref!r}")
    c1, v1 = int(m["c1"]), int(m["v1"])
    c2 = int(m["c2"]) if m["c2"] else c1
    v2 = int(m["v2"]) if m["v2"] else v1
    return BY_SEFARIA[m["book"]], (c1, v1), (c2, v2)
