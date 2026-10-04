"""Per-verse token streams for the lexical systems (DESIGN.md §3.3, §5.1).

A stream is the ordered token list of one verse plus, for each token, the `words.idx` it came
from (used to show formulas in Hebrew). Lemma tokens are OSHB content lemmas (prefix particles
dropped, sense letter kept: `1121a`); surface tokens are `match_key` forms (finals folded,
prefixes not stripped).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from bsim.text.normalize import match_key


@dataclass
class Stream:
    tokens: list[str] = field(default_factory=list)
    word_idx: list[int] = field(default_factory=list)


def _streams(words: pd.DataFrame, n_verses: int, tokens_of) -> list[Stream]:
    out = [Stream() for _ in range(n_verses)]
    ordered = words.sort_values(["verse_id", "idx"], kind="stable")
    for w in ordered.itertuples(index=False):
        s = out[w.verse_id]
        for tok in tokens_of(w):
            s.tokens.append(tok)
            s.word_idx.append(w.idx)
    return out


def lemma_streams(words: pd.DataFrame, n_verses: int) -> list[Stream]:
    """Content lemmas of each verse, flattened in word order."""
    return _streams(words, n_verses, lambda w: list(w.content_lemmas))


def surface_streams(words: pd.DataFrame, n_verses: int) -> list[Stream]:
    """One `match_key` token per OSHB word (empty keys dropped)."""
    return _streams(words, n_verses, lambda w: [k] if (k := match_key(w.surface)) else [])


def with_bigrams(tokens: list[str], weights: np.ndarray) -> tuple[list[str], np.ndarray]:
    """Append adjacent-token bigrams `a_b`; a bigram's weight is the min of its two tokens'."""
    if len(tokens) < 2:
        return list(tokens), np.asarray(weights, dtype=np.float64)
    bigrams = [f"{a}_{b}" for a, b in zip(tokens, tokens[1:], strict=False)]
    bw = np.minimum(weights[:-1], weights[1:])
    return list(tokens) + bigrams, np.concatenate([weights, bw]).astype(np.float64)
