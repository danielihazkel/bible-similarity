"""Letter-swap ciphers: atbash and albam (DESIGN.md §16.54).

Both pair the 22 letters and write each letter as its partner, so a word reads back by the same
swap:

- `atbash`: the alphabet folded on itself, א↔ת ב↔ש ג↔ר … כ↔ל. Jeremiah writes Babel as ששך
  (25:26, 51:41) and the Chaldeans (כשדים) as לב קמי (51:1).
- `albam`: the alphabet cut in two halves laid side by side, א↔ל ב↔מ ג↔נ … כ↔ת.

A final form is read as its letter, and the last letter of each word is written in its final form.
`random_swap` draws another such pairing (eleven pairs of the 22 letters): the null of
`bsim ciphers`.
"""

from __future__ import annotations

import numpy as np

from bsim.text.normalize import consonantal, fold_finals

LETTERS = "אבגדהוזחטיכלמנסעפצקרשת"
TO_FINAL = str.maketrans("כמנפצ", "ךםןףץ")
CIPHERS = ("atbash", "albam")


def pairing(pairs: list[tuple[str, str]]) -> dict[str, str]:
    """Each letter -> its partner, both ways."""
    out = {a: b for a, b in pairs} | {b: a for a, b in pairs}
    if sorted(out) != sorted(LETTERS):
        raise ValueError("a swap must pair all 22 letters")
    return out


SWAPS = {
    "atbash": pairing([(LETTERS[i], LETTERS[21 - i]) for i in range(11)]),
    "albam": pairing([(LETTERS[i], LETTERS[i + 11]) for i in range(11)]),
}


def table(swap: dict[str, str]) -> dict[int, str]:
    """A `str.translate` table of a swap."""
    return str.maketrans(swap)


TABLES = {name: table(s) for name, s in SWAPS.items()}


def random_swap(rng: np.random.Generator) -> dict[str, str]:
    """A random pairing of the 22 letters (a shuffled alphabet, taken two by two)."""
    order = [LETTERS[i] for i in rng.permutation(len(LETTERS))]
    return pairing([(order[i], order[i + 1]) for i in range(0, len(order), 2)])


def key(text: str) -> str:
    """The letters of `text` as one string, final forms folded: what a swap is applied to."""
    return fold_finals(consonantal(text).replace(" ", ""))


def finalize(word: str) -> str:
    """`word` with its last letter in final form."""
    return word[:-1] + word[-1:].translate(TO_FINAL)


def apply(text: str, name: str) -> str:
    """`text` written in a cipher, word by word (spaces kept, the last letter of each word
    final)."""
    t = TABLES[name]
    return " ".join(finalize(key(w).translate(t)) for w in consonantal(text).split())
