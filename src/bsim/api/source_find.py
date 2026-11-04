"""The source finder (`POST /source-find`, DESIGN.md §11.1, D131): the biblical phrases of any
pasted Hebrew text (a prayer, a Mishnah, a letter), each marked with its verses.

- **Words.** A word's key is its consonants (`text.normalize.consonantal`, finals folded), the
  divine name's abbreviations written out (`source_find.aliases`: ה', יי, יקוק; אלקים by
  `elokim`), then its skeleton: the ו / י inside it dropped (liturgy spells fuller or shorter
  than the Masoretic text; `analysis.witnesses.skeleton`). Verses are keyed the same way from
  `verses.text_plain`, whose words are the display tokens with letters, in order.
- **Seeds.** Every two adjacent query keys are looked up in an index of the verses' adjacent
  key pairs; a pair in more than `seed_max` verses (a formula) seeds nothing.
- **Extension.** Each seeded verse is aligned to the stretch of the query round its seeds
  (`pad` words more than the verse either side; seeds further apart than that are aligned
  apart, and a stretch found is blanked and the rest aligned again, so a verse quoted twice is
  found twice) by Smith-Waterman (`analysis.phrases.align`), a
  match scoring the word's `log(N / df)` over the verses, a mismatch and a gap `mismatch` and
  `gap`. A hit needs a score of `min_score` and `min_words` matched words.
- **Choosing.** Hits are taken best first; one that covers `same_span` of a taken hit's query
  words and scores `tie` of it is an alternative to it (the same words in another verse: up to
  `max_alternatives` listed), one that overlaps it otherwise is dropped. Taken hits on
  consecutive verses whose query spans meet (within `merge_gap` words) become one passage
  (Ashrei's Ps 145, verse after verse).

The index is built once per database from its verses (a second or two) and kept.
"""

from __future__ import annotations

import math
import re
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bsim.analysis.phrases import align
from bsim.analysis.witnesses import skeleton
from bsim.text.normalize import consonantal, display_tokens, fold_finals


@dataclass
class SourceIndex:
    keys: list[list[str]]  # per verse_id: its words' keys
    idf: dict[str, float]
    pairs: dict[tuple[str, str], list[tuple[int, int]]]  # adjacent keys -> (verse_id, position)


@dataclass
class Hit:
    q_first: int  # query key positions, inclusive
    q_last: int
    score: float
    matched: int
    verse_id: int
    v_pos: list[int]  # the verse's matched word positions
    q_pos: list[int]  # ... and the query's
    alternatives: list[int] = field(default_factory=list)


class Normaliser:
    """A word's key, as `source_find` reads it (see the module doc)."""

    def __init__(self, sf: dict[str, Any]) -> None:
        self.aliases = {fold_finals(str(k)): fold_finals(str(v)) for k, v in
                        (sf.get("aliases") or {}).items()}  # fmt: skip
        self.elokim = re.compile(str(sf["elokim"])) if sf.get("elokim") else None

    def key(self, word: str) -> str:
        letters = fold_finals(consonantal(word).replace(" ", ""))
        if not letters:
            return ""
        letters = self.aliases.get(letters, letters)
        if self.elokim is not None:
            letters = self.elokim.sub(r"\1אלה", letters)
        return skeleton(letters)


def build_index(texts: list[str], norm: Normaliser) -> SourceIndex:
    keys = [[k for w in t.split() if (k := norm.key(w))] for t in texts]
    df = Counter(k for ks in keys for k in set(ks))
    n = len(keys)
    idf = {k: math.log(n / c) for k, c in df.items()}
    pairs: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    for vid, ks in enumerate(keys):
        for i in range(len(ks) - 1):
            pairs[(ks[i], ks[i + 1])].append((vid, i))
    return SourceIndex(keys, idf, dict(pairs))


_INDEX: dict[str, SourceIndex] = {}
_LOCK = threading.Lock()


def index_for(db: Path | str, texts: Any, norm: Normaliser) -> SourceIndex:
    """The index of a database's verses, built on first use (`texts`: a callable)."""
    key = str(db)
    with _LOCK:
        if key not in _INDEX:
            _INDEX[key] = build_index(texts(), norm)
        return _INDEX[key]


def find_hits(query_keys: list[str], index: SourceIndex, sf: dict[str, Any]) -> list[Hit]:
    """Every verse hit of the query, best first (before choosing)."""
    seed_max, pad = int(sf["seed_max"]), int(sf["pad"])
    seeds: dict[int, list[int]] = defaultdict(list)
    for i in range(len(query_keys) - 1):
        occ = index.pairs.get((query_keys[i], query_keys[i + 1]), [])
        if len(occ) > seed_max:
            continue
        for vid, _ in occ:
            seeds[vid].append(i)
    rare = max(index.idf.values(), default=1.0)
    w_query = [index.idf.get(k, rare) for k in query_keys]
    hits = []
    for vid, qs in seeds.items():
        verse = index.keys[vid]
        w_verse = [index.idf[k] for k in verse]
        # the seeds in clusters along the text: a verse quoted twice is found twice
        clusters: list[list[int]] = []
        for q in sorted(set(qs)):
            if clusters and q - clusters[-1][-1] <= len(verse) + pad:
                clusters[-1].append(q)
            else:
                clusters.append([q])
        for c in clusters:
            lo = max(0, c[0] - len(verse) - pad)
            hi = min(len(query_keys), c[-1] + 2 + len(verse) + pad)
            window = query_keys[lo:hi]
            while True:  # each stretch of the window that quotes the verse, best first
                a = align(window, verse, w_query[lo:hi], w_verse, float(sf["mismatch"]),
                          float(sf["gap"]))  # fmt: skip
                if a.score < float(sf["min_score"]) or len(a.a_pos) < int(sf["min_words"]):
                    break
                q_pos = [lo + p for p in a.a_pos]
                hits.append(Hit(q_pos[0], q_pos[-1], a.score, len(q_pos), vid, a.b_pos, q_pos))
                window = [*window[: a.a_pos[0]], *[""] * (a.a_pos[-1] - a.a_pos[0] + 1),
                          *window[a.a_pos[-1] + 1 :]]  # fmt: skip
    hits.sort(key=lambda h: (-h.score, h.verse_id))
    return hits


def choose(hits: list[Hit], sf: dict[str, Any]) -> list[Hit]:
    """The hits taken (in query order), each with its alternatives (see the module doc)."""
    same, tie, most = float(sf["same_span"]), float(sf["tie"]), int(sf["max_alternatives"])
    taken: list[Hit] = []
    for h in hits:
        span = set(range(h.q_first, h.q_last + 1))
        kept = True
        for t in taken:
            both = len(span & set(range(t.q_first, t.q_last + 1)))
            if not both:
                continue
            kept = False
            if both >= same * len(span) and h.score >= tie * t.score and len(t.alternatives) < most:
                t.alternatives.append(h.verse_id)
            break
        if kept:
            taken.append(h)
    return sorted(taken, key=lambda h: (h.q_first, h.verse_id))


@dataclass
class Passage:
    q_first: int
    q_last: int
    score: float
    matched: int
    hits: list[Hit]  # one per verse, in order


def passages(taken: list[Hit], sf: dict[str, Any]) -> list[Passage]:
    """Taken hits on consecutive verses whose query spans meet, joined."""
    gap = int(sf["merge_gap"])
    out: list[Passage] = []
    for h in taken:
        last = out[-1] if out else None
        if (last is not None and not last.hits[-1].alternatives and not h.alternatives
                and h.verse_id == last.hits[-1].verse_id + 1
                and 0 <= h.q_first - last.q_last - 1 <= gap):  # fmt: skip
            last.q_last, last.score = h.q_last, last.score + h.score
            last.matched += h.matched
            last.hits.append(h)
        else:
            out.append(Passage(h.q_first, h.q_last, h.score, h.matched, [h]))
    return out


def source_find(text: str, index: SourceIndex, norm: Normaliser, sf: dict[str, Any]
                ) -> tuple[list[str], list[int], list[Passage]]:  # fmt: skip
    """(the text's tokens, each query key's token index, the passages found)."""
    tokens = display_tokens(text.replace("-", "־"))  # a hyphen typed for a maqaf
    keys, at = [], []
    for i, t in enumerate(tokens):
        k = norm.key(t)
        if k:
            keys.append(k)
            at.append(i)
    return tokens, at, passages(choose(find_hits(keys, index, sf), sf), sf)
