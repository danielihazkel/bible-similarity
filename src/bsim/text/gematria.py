"""Letter values (gematria) of Hebrew text (DESIGN.md §16.53).

Four systems, summed over the consonants (`normalize.consonantal`: points, te'amim and maqaf
gone):

- `standard` (mispar hechrechi): א 1 … ט 9, י 10 … צ 90, ק 100 … ת 400; a final form counts as
  its letter (ך 20).
- `gadol` (mispar gadol): the same, with the final forms ך ם ן ף ץ at 500 … 900.
- `ordinal` (mispar siduri): a letter's place in the alphabet, 1 … 22 (a final form as its
  letter).
- `katan` (mispar katan): the standard value without its zeros (י 1, ק 1, ר 2), 1 … 9 a letter.
"""

from __future__ import annotations

from bsim.text.normalize import consonantal

LETTERS = "אבגדהוזחטיכלמנסעפצקרשת"
FINALS = "ךםןףץ"
FINAL_OF = dict(zip(FINALS, "כמנפצ", strict=True))
SYSTEMS = ("standard", "gadol", "ordinal", "katan")


def _table(system: str) -> dict[str, int]:
    place = {c: i for i, c in enumerate(LETTERS)}
    if system == "standard":
        base = {c: (i % 9 + 1) * 10 ** (i // 9) for c, i in place.items()}
    elif system == "gadol":
        base = _table("standard")
        return base | {f: 500 + 100 * k for k, f in enumerate(FINALS)}
    elif system == "ordinal":
        base = {c: i + 1 for c, i in place.items()}
    elif system == "katan":
        base = {c: i % 9 + 1 for c, i in place.items()}
    else:
        raise ValueError(f"unknown gematria system {system!r} (one of {SYSTEMS})")
    return base | {f: base[c] for f, c in FINAL_OF.items()}


TABLES = {s: _table(s) for s in SYSTEMS}


def letters(text: str) -> str:
    """The Hebrew letters of `text`, in order, without spaces."""
    return consonantal(text).replace(" ", "")


def value(text: str, system: str = "standard") -> int:
    """The sum of the letter values of `text` in one system (0 without Hebrew letters)."""
    table = TABLES[system]
    return sum(table[c] for c in letters(text))


def values(text: str) -> dict[str, int]:
    """`text`'s value in every system."""
    s = letters(text)
    return {name: sum(t[c] for c in s) for name, t in TABLES.items()}
