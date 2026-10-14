"""Word- and lemma-level tables of the results DB (DESIGN.md §9): each lemma's display form and
part of speech, the concordance, formula flags and the SDBH domains of the words.

`lemma_gloss.he_lemma`: OSHB lemmas are Strong's numbers and no lexicon is downloaded, so each
lemma is shown as its most common consonantal surface form with the prefix particles stripped.
`words.in_formula`: the word carries a token inside a frequent-formula occurrence, found with the
same `lexical.formulas` code and config as `bsim lexical`. Analysis modules import these helpers
too; this module imports none of them.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

import numpy as np
import pandas as pd

from bsim.lexical.formulas import formula_weights, frequent_ngrams
from bsim.lexical.tokens import lemma_streams
from bsim.store.schema import COLUMNS
from bsim.text.normalize import consonantal

# OSHB prefix morphemes -> their letter; the article's ה is elided after ב / כ / ל (בַּשָּׁמַיִם).
PREFIX_LETTERS = {"b": "ב", "c": "ו", "d": "ה", "k": "כ", "l": "ל", "m": "מ", "s": "ש"}
ARTICLE_ELIDED_AFTER = {"b", "k", "l"}


def strip_prefixes(surface: str, lemma: str) -> str:
    """Consonantal surface without the letters of the lemma's leading prefix morphemes.

    The whole word is kept when it does not start with the expected letters.
    """
    word = consonantal(surface).replace(" ", "")
    parts = lemma.split("/")
    prefix = ""
    for i, p in enumerate(parts):
        if p not in PREFIX_LETTERS:
            break
        if p == "d" and i > 0 and parts[i - 1] in ARTICLE_ELIDED_AFTER:
            continue
        prefix += PREFIX_LETTERS[p]
    if prefix and word.startswith(prefix) and len(word) > len(prefix):
        return word[len(prefix) :]
    return word


def lemma_parts_pos(lemma: str, morph: str | None) -> dict[str, str]:
    """Content lemma -> part-of-speech letter of its morpheme. OSHB lemma parts (`c/6965 b`) line
    up with the morph's morphemes (`HC/Vqq3ms`); suffix morphemes come after and have no lemma."""
    if not morph:
        return {}
    parts, morphemes = lemma.split("/"), morph[1:].split("/")
    out = {}
    for part, m in zip(parts, morphemes, strict=False):
        lem = part.replace(" ", "")
        if lem[:1].isdigit() and m:
            out[lem] = m[0]
    return out


def lemma_display_forms(words: pd.DataFrame) -> pd.DataFrame:
    """`lemma, he_lemma, n_words, n_verses, pos`: each content lemma's most common
    prefix-stripped form (ties: first seen), its number of occurrences and of verses containing
    it, and its most common part of speech (OSHB letter; None without morphology)."""
    forms: dict[str, Counter[str]] = defaultdict(Counter)
    verses: dict[str, set[int]] = defaultdict(set)
    pos: dict[str, Counter[str]] = defaultdict(Counter)
    morphs = words.morph if "morph" in words else [None] * len(words)
    for vid, surface, lemma, content, morph in zip(
        words.verse_id, words.surface, words.lemma, words.content_lemmas, morphs, strict=True
    ):
        if len(content):
            form = strip_prefixes(surface, lemma)
            for lem in content:
                forms[lem][form] += 1
                verses[lem].add(int(vid))
            for lem, p in lemma_parts_pos(lemma, morph).items():
                pos[lem][p] += 1
    rows = [
        (
            lem,
            c.most_common(1)[0][0],
            c.total(),
            len(verses[lem]),
            pos[lem].most_common(1)[0][0] if pos[lem] else None,
        )
        for lem, c in sorted(forms.items())
    ]
    return pd.DataFrame(rows, columns=COLUMNS["lemma_gloss"])


def lemma_verses(words: pd.DataFrame, verses: pd.DataFrame) -> pd.DataFrame:
    """`lemma, verse_id, book_id`: distinct (content lemma, verse) pairs, the concordance."""
    pairs = (
        words[["verse_id", "content_lemmas"]]
        .explode("content_lemmas")
        .dropna()
        .rename(columns={"content_lemmas": "lemma"})
        .drop_duplicates()
    )
    pairs["book_id"] = pairs.verse_id.map(verses.set_index("verse_id").book_id)
    return pairs.sort_values(["lemma", "verse_id"])[COLUMNS["lemma_verses"]]


def formula_flags(words: pd.DataFrame, n_verses: int, formulas: dict[str, Any]) -> np.ndarray:
    """Per `words` row: True if any of its lemma tokens lies inside a formula occurrence."""
    streams = lemma_streams(words, n_verses)
    ngrams = frequent_ngrams(streams, formulas["min_n"], formulas["max_n"], formulas["min_verses"])
    weights = formula_weights(streams, ngrams, formulas["weight"])
    flagged = {
        (vid, idx)
        for vid, (s, w) in enumerate(zip(streams, weights, strict=True))
        for idx, wt in zip(s.word_idx, w, strict=True)
        if wt < 1
    }
    return np.array(
        [(v, i) in flagged for v, i in zip(words.verse_id, words.idx, strict=True)], dtype=bool
    )


def ancestors(code: str) -> list[str]:
    """The code and its broader domains: `002001001` -> [`002001001`, `002001`, `002`]."""
    return [code[:i] for i in range(len(code), 0, -3)]


def domain_tables(
    senses: pd.DataFrame | None, words: pd.DataFrame, domains: pd.DataFrame | None
) -> tuple[list[str | None], pd.DataFrame, pd.DataFrame]:
    """`words.domains` (aligned with `words`), `domain_verses` and `domains` from the word
    senses of `bsim lexicon`; content morphemes only (as `bm25_domain`)."""
    from bsim.data.lexicon import strong_key

    empty_dv = pd.DataFrame(columns=COLUMNS["domain_verses"])
    if senses is None or domains is None:
        return [None] * len(words), empty_dv, pd.DataFrame(columns=COLUMNS["domains"])
    content = {
        (v, i): {strong_key(c) for c in cl}
        for v, i, cl in zip(words.verse_id, words.idx, words.content_lemmas, strict=True)
    }
    keep = [
        s in content.get((v, i), ())
        for v, i, s in zip(senses.verse_id, senses.idx, senses.strong, strict=True)
    ]
    s = senses[keep]
    long = pd.DataFrame(
        [
            (v, i, d, w)
            for v, i, ds, ws in zip(s.verse_id, s.idx, s.domains, s.weights, strict=True)
            for d, w in zip(ds, ws, strict=True)
        ],
        columns=["verse_id", "idx", "code", "weight"],
    )
    per_word = long.groupby(["verse_id", "idx"]).code.agg(lambda c: " ".join(sorted(set(c))))
    word_domains = [
        per_word.get((v, i)) for v, i in zip(words.verse_id, words.idx, strict=True)
    ]
    dv = long.groupby(["code", "verse_id"], as_index=False).weight.sum()
    up = pd.DataFrame(
        [(a, v, w) for c, v, w in zip(dv.code, dv.verse_id, dv.weight, strict=True)
         for a in ancestors(c)],
        columns=["code", "verse_id", "weight"],
    )
    stats = up.groupby("code").agg(n_verses=("verse_id", "nunique"), weight=("weight", "sum"))
    doms = domains.merge(stats, left_on="code", right_index=True, how="left").fillna(
        {"n_verses": 0, "weight": 0.0}
    )
    doms["n_verses"] = doms.n_verses.astype(int)
    doms["weight"] = doms.weight.round(3)
    return word_domains, dv.assign(weight=dv.weight.round(4)), doms[COLUMNS["domains"]]
