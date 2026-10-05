"""`bsim wordplay`: sound-alike words close together (paronomasia; DESIGN.md §16.10).

Isaiah 5:7 plays מִשְׁפָּט ("justice") against מִשְׂפָּח ("bloodshed") and צְדָקָה ("righteousness")
against צְעָקָה ("outcry"): different words, one consonant apart, same vowels, a few words apart.

- Words: OSHB words with exactly one content lemma whose part of speech is not a particle,
  preposition, conjunction or pronoun (proper nouns and gentilics too with `skip_proper`:
  genealogies and town lists are full of names built alike). A word is what is heard: its
  pointed surface without the prefix morphemes (`store.db.strip_prefixes`), reduced to a
  consonant skeleton (finals folded, ו / י after the first letter dropped) and a vowel pattern
  (the niqqud vowels in order; shureq counts as qubbuts, dagesh / meteg / shin dots ignored).
- Pairs: two words with different lemmas within `window` words of each other (verse boundaries
  are crossed, chapter boundaries are not) whose skeletons (each ≥ `min_letters`) are related —
  `substitution` (same length, one letter differs), `metathesis` (two adjacent letters swapped)
  or `extension` (one letter more or less) — and, with `same_vowels`, whose vowel patterns are
  identical. Hebrew roots are three letters, so nearly every word has one-letter neighbours; the
  shared vowel pattern is what makes the echo audible.
- Score: the mean idf of the two lemmas (rare words make a pun audible) minus `distance` per
  word between them.
- Significance: word order is shuffled within every chapter `null_reps` times (vocabulary and
  counts kept, closeness destroyed), the pairs recounted, and `q` = (null pairs per replicate
  scoring ≥ s) / (observed pairs scoring ≥ s), monotone — as for parallel sequences (§16.7).

Writes `artifacts/wordplay/pairs.parquet`: `a_vid, a_idx, b_vid, b_idx` (verse id, `words.idx`;
a first), `a_lemma, b_lemma`, `a_form, b_form` (heard forms, consonantal), `kind`, `gap` (words
apart), `score`, `q`; plus `wordplay.meta.json`.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.sequences import q_values
from bsim.config import config_hash, resolve_path
from bsim.text.normalize import consonantal, fold_finals

Log = Callable[[str], None]

MATRES = str.maketrans("", "", "וי")
VOWELS = {chr(c) for c in range(0x05B0, 0x05BC)} | {"ׇ"}  # sheva .. qubbuts, qamats qatan
QAMATS, QAMATS_QATAN, QUBBUTS, DAGESH = "ָ", "ׇ", "ֻ", "ּ"

Token = tuple[str, str, str]  # (lemma, skeleton, vowel pattern)


def skeleton(form: str) -> str:
    """Consonants of a form, finals folded, vowel letters (ו / י after the first letter) dropped."""
    s = fold_finals(consonantal(form).replace(" ", ""))
    return s[:1] + s[1:].translate(MATRES)


def letters(surface: str) -> list[tuple[str, str]]:
    """(letter, its marks) of a pointed word, in order (maqaf / punctuation dropped)."""
    out: list[tuple[str, str]] = []
    for ch in surface:
        if 0x05D0 <= ord(ch) <= 0x05EA:
            out.append((ch, ""))
        elif out and 0x0591 <= ord(ch) <= 0x05C7:
            out[-1] = (out[-1][0], out[-1][1] + ch)
    return out


def vowel_pattern(clusters: list[tuple[str, str]]) -> str:
    """The vowels of a word in order; shureq (וּ without a vowel) counts as qubbuts."""
    out = []
    for i, (ch, marks) in enumerate(clusters):
        v = [m for m in marks if m in VOWELS]
        if v:
            out.append(QAMATS if v[0] == QAMATS_QATAN else v[0])
        elif ch == "ו" and DAGESH in marks and i > 0:
            out.append(QUBBUTS)
    return "".join(out)


def heard(surface: str, lemma: str) -> tuple[str, str, str]:
    """(consonantal form, skeleton, vowel pattern) of a word without its prefix morphemes."""
    from bsim.store.db import strip_prefixes

    clusters = letters(surface)
    form = strip_prefixes(surface, lemma)
    rest = clusters[len(clusters) - len(form) :] if len(form) <= len(clusters) else clusters
    return form, skeleton(form), vowel_pattern(rest)


def relation(a: str, b: str) -> str | None:
    """How two skeletons sound alike: substitution / metathesis / extension, or None."""
    if a == b:
        return None
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        if len(diff) == 1:
            return "substitution"
        if len(diff) == 2 and diff[1] == diff[0] + 1:
            i = diff[0]
            if a[i] == b[i + 1] and a[i + 1] == b[i]:
                return "metathesis"
        return None
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    if len(long_) - len(short) != 1:
        return None
    if any(long_[:i] + long_[i + 1 :] == short for i in range(len(long_))):
        return "extension"
    return None


def neighbour_index(skeletons: set[str], min_letters: int) -> dict[str, dict[str, str]]:
    """skeleton -> {sound-alike skeleton: kind}, both ≥ `min_letters` letters."""
    keep = [s for s in skeletons if len(s) >= min_letters]
    # bucket keys shared by any two related skeletons: one letter masked (substitution), one
    # letter dropped (extension: the longer one dropped equals the shorter), a sorted adjacent
    # pair (metathesis)
    keys: dict[str, set[str]] = defaultdict(set)
    for s in keep:
        keys["x" + s].add(s)
        for i in range(len(s)):
            keys["d" + s[:i] + "*" + s[i + 1 :]].add(s)
            keys["x" + s[:i] + s[i + 1 :]].add(s)
        for i in range(len(s) - 1):
            keys[f"m{i}" + s[:i] + "".join(sorted(s[i : i + 2])) + s[i + 2 :]].add(s)
    out: dict[str, dict[str, str]] = defaultdict(dict)
    for group in keys.values():
        if len(group) < 2:
            continue
        ordered = sorted(group)
        for k, s1 in enumerate(ordered):
            for s2 in ordered[k + 1 :]:
                if s2 in out[s1]:
                    continue
                kind = relation(s1, s2)
                if kind is not None:
                    out[s1][s2] = kind
                    out[s2][s1] = kind
    return dict(out)


def find_pairs(
    tokens: list[Token],
    chapters: np.ndarray,
    near: dict[str, dict[str, str]],
    idf: dict[str, float],
    window: int,
    distance: float,
    same_vowels: bool,
) -> list[tuple[int, int, str, float]]:
    """(position a, position b, kind, score) of sound-alike words within `window` positions in one
    chapter; positions index the word sequence."""
    out = []
    n = len(tokens)
    for i in range(n):
        li, si, vi = tokens[i]
        alike = near.get(si)
        if not alike:
            continue
        for j in range(i + 1, min(n, i + window + 1)):
            if chapters[j] != chapters[i]:
                break
            lj, sj, vj = tokens[j]
            kind = alike.get(sj)
            if kind is None or lj == li or (same_vowels and vi != vj):
                continue
            out.append((i, j, kind, (idf[li] + idf[lj]) / 2 - distance * (j - i - 1)))
    return out


def shuffle_within(chapters: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """A permutation of positions that keeps every position inside its (contiguous) chapter."""
    perm = np.arange(len(chapters))
    bounds = np.flatnonzero(np.diff(chapters)) + 1
    for ids in np.split(perm.copy(), bounds):
        perm[ids] = rng.permutation(ids)
    return perm


def is_proper(morph: str | None) -> bool:
    """A proper noun or a gentilic (Ng: Shuphamite, Israelite) in any morpheme."""
    return isinstance(morph, str) and any(p.startswith(("Np", "Ng")) for p in morph[1:].split("/"))


def run_wordplay(cfg: dict[str, Any], log: Log = print) -> Path:
    from bsim.store.db import lemma_display_forms

    proc = resolve_path(cfg, "data_processed")
    wc = cfg["wordplay"]
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter"])
    words = pd.read_parquet(
        proc / "words.parquet",
        columns=["verse_id", "idx", "surface", "lemma", "content_lemmas", "morph"],
    )
    t0 = time.perf_counter()
    gloss = lemma_display_forms(words)
    skip = set(wc["skip_pos"])
    content = {lem for lem, pos in zip(gloss.lemma, gloss.pos, strict=True) if pos not in skip}
    idf = {
        lem: math.log(len(verses) / nv) for lem, nv in zip(gloss.lemma, gloss.n_verses, strict=True)
    }

    w = words.sort_values(["verse_id", "idx"], kind="stable")
    w = w[w.content_lemmas.map(len) == 1]
    w = w.assign(lem=w.content_lemmas.map(lambda c: c[0]))
    w = w[w.lem.isin(content)]
    if wc["skip_proper"]:
        w = w[~w.morph.map(is_proper)]
    w = w.reset_index(drop=True)
    heard_ = [heard(s, lem) for s, lem in zip(w.surface, w.lemma, strict=True)]
    tokens: list[Token] = [(lem, h[1], h[2]) for lem, h in zip(w.lem, heard_, strict=True)]
    chapter_key = verses.book_id.to_numpy() * 1000 + verses.chapter.to_numpy()
    chapters = chapter_key[w.verse_id.to_numpy()]

    near = neighbour_index({t[1] for t in tokens}, wc["min_letters"])
    n_alike = sum(len(v) for v in near.values()) // 2
    log(f"{len(w)} content words, {n_alike} sound-alike skeleton pairs")
    args = (near, idf, wc["window"], wc["distance"], wc["same_vowels"])
    found = find_pairs(tokens, chapters, *args)

    rng = np.random.default_rng(wc["seed"])
    null: list[float] = []
    for r in range(wc["null_reps"]):
        perm = shuffle_within(chapters, rng)
        null += [s for *_, s in find_pairs([tokens[k] for k in perm], chapters, *args)]
        log(f"  null {r + 1}/{wc['null_reps']}: {len(null)} chance pairs so far")
    scores = np.array([s for *_, s in found], dtype=np.float64)
    q = q_values(scores, np.array(null), wc["null_reps"])

    vid, idx = w.verse_id.to_numpy(), w.idx.to_numpy()
    df = pd.DataFrame(
        {
            "a_vid": [int(vid[i]) for i, *_ in found],
            "a_idx": [int(idx[i]) for i, *_ in found],
            "b_vid": [int(vid[j]) for _, j, *_ in found],
            "b_idx": [int(idx[j]) for _, j, *_ in found],
            "a_lemma": [tokens[i][0] for i, *_ in found],
            "b_lemma": [tokens[j][0] for _, j, *_ in found],
            "a_form": [heard_[i][0] for i, *_ in found],
            "b_form": [heard_[j][0] for _, j, *_ in found],
            "kind": [k for *_, k, _ in found],
            "gap": [j - i for i, j, *_ in found],
            "score": scores.round(4),
            "q": q,
        }
    ).sort_values(["score", "a_vid", "a_idx"], ascending=[False, True, True], ignore_index=True)

    out = resolve_path(cfg, "artifacts") / "wordplay"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "pairs.parquet")
    meta = {
        "config_hash": config_hash(cfg, "wordplay"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "words": int(len(w)),
        "pairs": int(len(df)),
        "null_pairs_per_rep": round(len(null) / max(1, wc["null_reps"]), 1),
        "q_below_0.05": int((df.q < 0.05).sum()),
        "kinds": dict(Counter(df.kind)),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "wordplay.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(
        f"done: {len(df)} pairs ({meta['q_below_0.05']} with q < 0.05; {meta['kinds']};"
        f" {meta['null_pairs_per_rep']} per shuffle) in {meta['seconds']} s"
    )
    return out / "pairs.parquet"
