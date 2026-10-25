"""Why two verses are alike in meaning (DESIGN.md §16.73): their words aligned through the final
semantic encoder's token vectors.

A semantic match may share no word at all; `/explain` then has nothing to show. Here both verses
are encoded alone (as `bsim maxsim` does, §16.21), each sub-word token's last hidden state
L2-normalized; a word's vector is the mean of its tokens' (renormalized), a word being one OSHB
word of the `words` table, written consonantally as in `text_model`. Words whose content lemmas
are all in `align.stop` (את, אשר, the conjunctions, ...) are encoded with their verse but not
aligned. Two words are linked when each is the other's best match and their cosine is at least
`align.min_cos`; a link between different lemmas is a link of meaning, not of a shared word.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from bsim.text.normalize import consonantal


@dataclass(frozen=True)
class VerseWords:
    """One verse's words as the encoder reads them: their text, char spans and display tokens."""

    text: str
    spans: list[tuple[int, int]]  # [start, end) in `text`, one per kept word
    display: list[int | None]
    lemmas: list[frozenset[str]]


def verse_words(rows: list[dict[str, Any]]) -> VerseWords:
    """From `words` rows (with `surface`) of one verse, in order; empty forms are left out."""
    parts, spans, display, lemmas = [], [], [], []
    pos = 0
    for r in rows:
        form = consonantal(r["surface"] or "")
        if not form:
            continue
        if parts:
            pos += 1
        spans.append((pos, pos + len(form)))
        parts.append(form)
        pos += len(form)
        display.append(r["display_idx"])
        lemmas.append(frozenset((r["content_lemmas"] or "").split()))
    return VerseWords(" ".join(parts), spans, display, lemmas)


def word_vectors(
    vw: VerseWords, tokens: np.ndarray, offsets: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Each word's vector (mean of the tokens starting inside it, renormalized) and whether it
    has any token (a word cut off by truncation has none)."""
    dim = tokens.shape[1] if tokens.ndim == 2 else 0
    out = np.zeros((len(vw.spans), dim), np.float32)
    has = np.zeros(len(vw.spans), bool)
    starts = offsets[:, 0] if len(offsets) else np.empty(0)
    for i, (s, e) in enumerate(vw.spans):
        m = (starts >= s) & (starts < e)
        if m.any():
            v = tokens[m].mean(0)
            out[i] = v / max(float(np.linalg.norm(v)), 1e-12)
            has[i] = True
    return out, has


def mutual_links(
    a: np.ndarray, b: np.ndarray, a_ok: np.ndarray, b_ok: np.ndarray, min_cos: float
) -> list[tuple[int, int, float]]:
    """(i, j, cos) of the word pairs that are each other's best match among the words allowed,
    at least `min_cos`, best first."""
    ia, ib = np.flatnonzero(a_ok), np.flatnonzero(b_ok)
    if len(ia) == 0 or len(ib) == 0:
        return []
    sim = a[ia] @ b[ib].T
    best_b = sim.argmax(1)
    best_a = sim.argmax(0)
    out = [(int(ia[i]), int(ib[j]), float(sim[i, j])) for i, j in enumerate(best_b)
           if best_a[j] == i and sim[i, j] >= min_cos]  # fmt: skip
    return sorted(out, key=lambda x: -x[2])


def align_verses(
    rows_a: list[dict[str, Any]],
    rows_b: list[dict[str, Any]],
    encode_tokens: Any,
    min_cos: float,
    stop: set[str],
) -> list[dict[str, Any]]:
    """The links between two verses' words: `a_word, b_word` (positions among the kept words),
    `a_display, b_display, cos, same_lemma`."""
    wa, wb = verse_words(rows_a), verse_words(rows_b)
    (ta, oa), (tb, ob) = encode_tokens([wa.text, wb.text])
    va, ha = word_vectors(wa, ta, oa)
    vb, hb = word_vectors(wb, tb, ob)

    def allowed(vw: VerseWords, has: np.ndarray) -> np.ndarray:
        return has & np.array([bool(lem - stop) for lem in vw.lemmas], dtype=bool)

    links = mutual_links(va, vb, allowed(wa, ha), allowed(wb, hb), min_cos)
    return [
        {"a_word": i, "b_word": j, "a_display": wa.display[i], "b_display": wb.display[j],
         "cos": round(c, 4), "same_lemma": bool(wa.lemmas[i] & wb.lemmas[j])}  # fmt: skip
        for i, j, c in links
    ]
