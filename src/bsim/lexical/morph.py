"""Grammatical-shape tokens for the `structural` mode (DESIGN.md §16.5).

Each OSHB word becomes one coarse morphology token that keeps its shape and drops its lexeme and
agreement: per morpheme the part of speech plus the feature that matters most for syntax (verb
form, noun state, particle / pronoun / suffix type), joined with `+`. `HC/Vqw3ms` (וַיֹּאמֶר) ->
`C+Vw`, `HR/Td/Ncmsa` (בַּשָּׁמַיִם) -> `R+Td+Na`, `HNcmsc/Sp3ms` -> `Nc+Sp`. A verse is indexed as
the n-grams (1..`lexical.morph.max_n`) of its word tokens, so two verses match when they share
grammatical patterns (wayyiqtol chains, construct chains, parallel poetic clauses) whatever
their words.
"""

from __future__ import annotations

import pandas as pd

KEEP_SUBTYPE = {"P", "S", "T"}  # pronoun / suffix / particle: the type letter is the function
VERB_FORMS = set("pqiwhjvrsac")
STATES = set("acd")


def morpheme_token(m: str) -> str:
    if not m:
        return ""
    pos, rest = m[0], m[1:]
    if pos == "V":
        form = rest[1:2]
        return "V" + (form if form in VERB_FORMS else "")
    if pos == "N":
        if rest[:1] == "p":
            return "Np"
        state = rest[-1:] if rest[-1:] in STATES and len(rest) >= 4 else ""
        return "N" + state
    if pos in KEEP_SUBTYPE:
        return pos + rest[:1]
    return pos  # A C D R (adjectives keep only their part of speech)


def word_token(morph: str | None) -> str:
    """Coarse shape of one word, or `?` without morphology."""
    if not isinstance(morph, str) or len(morph) < 2:  # None / NaN: no morphology
        return "?"
    return "+".join(t for t in (morpheme_token(m) for m in morph[1:].split("/")) if t) or "?"


def morph_streams(words: pd.DataFrame, n_verses: int) -> list[list[str]]:
    """Word shape tokens of each verse, in word order."""
    out: list[list[str]] = [[] for _ in range(n_verses)]
    for vid, morph in words.sort_values(["verse_id", "idx"])[["verse_id", "morph"]].itertuples(
        index=False
    ):
        out[vid].append(word_token(morph))
    return out


def ngram_tokens(tokens: list[str], max_n: int) -> list[str]:
    """Space-joined n-grams for n = 1..max_n."""
    return [
        " ".join(tokens[i : i + n]) for n in range(1, max_n + 1) for i in range(len(tokens) - n + 1)
    ]
