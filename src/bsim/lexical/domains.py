"""Semantic-domain tokens for the `bm25_domain` / `tfidf_domain` systems (DESIGN.md §16.22).

Every content morpheme tagged by `bsim lexicon` (`word_senses.parquet`) becomes its SDBH domain
codes, weighted by its share of each (a morpheme with two candidate meanings gives each half),
plus every ancestor code at `lexical.domain.ancestor_weight` times that weight. Two verses then
match when their words share meanings in the same domain ("Move", "Weak", "Waterbodies") or, more
weakly, the same broader domain, whether or not they share a lemma. Function words (prepositions,
the article, conjunctions: not in a word's `content_lemmas`) are left out with
`lexical.domain.content_only`.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from bsim.data.lexicon import strong_key


def ancestors(code: str) -> list[str]:
    """`002001001069` -> [`002001001`, `002001`, `002`] (3 digits per level)."""
    return [code[:i] for i in range(len(code) - 3, 0, -3)]


def domain_streams(
    senses: pd.DataFrame, words: pd.DataFrame, n: int, ancestor_weight: float, content_only: bool
) -> tuple[list[list[str]], list[np.ndarray]]:
    """Per verse the domain tokens and their weights, in word order."""
    content = {
        (v, i): {strong_key(c) for c in cl}
        for v, i, cl in zip(words.verse_id, words.idx, words.content_lemmas, strict=True)
    }
    tokens: list[list[str]] = [[] for _ in range(n)]
    weights: dict[int, list[float]] = defaultdict(list)
    for v, i, strong, doms, ws in zip(
        senses.verse_id, senses.idx, senses.strong, senses.domains, senses.weights, strict=True
    ):
        if content_only and strong not in content.get((v, i), ()):
            continue
        for d, w in zip(doms, ws, strict=True):
            tokens[v].append(d)
            weights[v].append(w)
            if ancestor_weight > 0:
                for a in ancestors(d):
                    tokens[v].append(a)
                    weights[v].append(w * ancestor_weight)
    return tokens, [np.asarray(weights[v], dtype=np.float64) for v in range(n)]
