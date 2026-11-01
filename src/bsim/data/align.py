"""OSHB word <-> MAM display token alignment for highlighting (DESIGN.md §3.4).

Both sides are compared as `match_key`s (consonantal, finals folded). `equal` blocks and
equal-length `replace` blocks (plene/defective spelling) map one-to-one. Inside an unequal
`replace` block, words divided differently are matched by their letters joined: two or three
OSHB words written as one MAM token (בל אמים / בלאמים) all map to it, one OSHB word written as two
or three MAM tokens maps to the first; the walk stops at the first word that fits neither.
Everything else is left unaligned. Display tokens without letters (e.g. a bare paseq ׀) are
skipped but keep their index.
"""

from __future__ import annotations

from difflib import SequenceMatcher


def align(oshb_keys: list[str], mam_keys: list[str]) -> list[int | None]:
    """For each OSHB word, the index of its MAM display token (or None)."""
    mam_pos = [i for i, k in enumerate(mam_keys) if k]
    mam = [mam_keys[i] for i in mam_pos]
    out: list[int | None] = [None] * len(oshb_keys)
    sm = SequenceMatcher(a=oshb_keys, b=mam, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
            for i, j in zip(range(i1, i2), range(j1, j2), strict=True):
                out[i] = mam_pos[j]
        elif tag == "replace":
            for i, j in _divided(oshb_keys, mam, i1, i2, j1, j2):
                out[i] = mam_pos[j]
    return out


def _divided(a: list[str], b: list[str], i1: int, i2: int, j1: int, j2: int):
    """(OSHB index, MAM index) pairs of a block whose words are divided differently."""
    i, j = i1, j1
    while i < i2 and j < j2:
        if a[i] == b[j]:
            yield i, j
            i, j = i + 1, j + 1
            continue
        for k in (2, 3):
            if i + k <= i2 and "".join(a[i : i + k]) == b[j]:  # k OSHB words, one MAM token
                yield from ((x, j) for x in range(i, i + k))
                i, j = i + k, j + 1
                break
            if j + k <= j2 and a[i] == "".join(b[j : j + k]):  # one OSHB word, k MAM tokens
                yield i, j
                i, j = i + 1, j + k
                break
        else:
            return
