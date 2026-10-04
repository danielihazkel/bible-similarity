"""Hebrew text normalization (DESIGN.md §3.2).

`consonantal` keeps Hebrew letters (U+05D0–U+05EA) and whitespace only. That single rule removes
points, te'amim, meteg, paseq, sof pasuq, the combining grapheme joiner and inverted nun (the
MAM `{פ}`/`{ס}` markers are removed earlier, by `data/sefaria.py`). Final letters are kept (BEREL
saw them); `match_key` folds them for surface-form matching only.
"""

from __future__ import annotations

import re

MAQAF = "\u05be"
FINALS = str.maketrans("ךםןףץ", "כמנפצ")

_NON_LETTER = re.compile(r"[^\u05d0-\u05ea\s]")
_SPACES = re.compile(r"\s+")


def consonantal(s: str) -> str:
    """Strip everything but Hebrew letters; maqaf becomes a space, `/` separators vanish."""
    s = s.replace(MAQAF, " ").replace("/", "")
    return _SPACES.sub(" ", _NON_LETTER.sub("", s)).strip()


def fold_finals(s: str) -> str:
    return s.translate(FINALS)


def match_key(word: str) -> str:
    """Key for alignment and surface matching: consonantal, finals folded, no spaces."""
    return fold_finals(consonantal(word)).replace(" ", "")


def display_tokens(text_display: str) -> list[str]:
    """Split display text on whitespace and after each maqaf (the maqaf stays on the left token).

    This defines the `words.display_idx` coordinate system.
    """
    tokens: list[str] = []
    for chunk in text_display.split():
        parts = chunk.split(MAQAF)
        tokens.extend(p + MAQAF for p in parts[:-1])
        if parts[-1]:
            tokens.append(parts[-1])
    return tokens
