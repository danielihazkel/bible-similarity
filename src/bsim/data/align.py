"""OSHB word <-> MAM display token alignment for highlighting (DESIGN.md §3.4).

Both sides are compared as `match_key`s (consonantal, finals folded). `equal` blocks and
equal-length `replace` blocks (plene/defective spelling) map one-to-one; everything else is
left unaligned. Display tokens without letters (e.g. a bare paseq ׀) are skipped but keep their
index.
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
    return out
