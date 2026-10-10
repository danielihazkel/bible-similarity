"""`bsim sound`: alliteration and rhyme (DESIGN.md §16.19).

Wordplay (§16.10) pairs two words; sound patterns run through a line.

- Sound of a letter: the consonant as a phoneme — ב / כ / פ are one sound each whether or not
  their dagesh makes them stops (פַּחַד וָפַחַת וָפָח, Isa 24:17, alliterates p / f / f), while
  שׁ and שׂ are told apart (sh / s).
- Alliteration: in every colon (the te'amim cola of §16.9) with at least `min_words` content
  words (function words — particles, prepositions, conjunctions, pronouns, the object marker —
  skipped), the initial sounds of those words after their prefix particles (ו, ה, ב, ל, …) and
  the most frequent one, `count` times. Chance is conditioned on the word's shape (part of
  speech, conjugation, prefixes: `lexical.morph.word_token`), since grammar fixes many initial
  sounds — a chain of wayyiqtol verbs all begin with י. Each word starts with sound s at its
  shape's corpus rate (smoothed towards the overall rate); `p` bounds the chance that any sound
  reaches `count` (Bonferroni over the sounds of exact Poisson-binomial tails), `q` =
  Benjamini–Hochberg over all cola.
- Rhyme: runs of at least `min_run` consecutive cola within a chapter whose last words end alike
  (the last two consonants, finals folded, with the vowel under the first of them) while the
  words themselves differ (a list repeating one word is not a rhyme). Chance: the
  ending's corpus frequency among colon ends, `p = f ** (run − 1)` times the number of positions
  a run could start; `q` = Benjamini–Hochberg over all runs.

Writes `artifacts/sound/{alliteration,rhymes}.parquet` plus `sound.meta.json`.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from bsim.analysis.stats import bh_q
from bsim.config import config_hash, resolve_path
from bsim.text.normalize import consonantal, fold_finals

Log = Callable[[str], None]

SIN_DOT = "ׂ"
VOWELS = {chr(c) for c in range(0x05B0, 0x05BC)} | {"ׇ"}


def clusters(word: str) -> list[tuple[str, str]]:
    """(letter, its points) of a pointed word, finals folded; marks other than points dropped."""
    out: list[tuple[str, str]] = []
    for ch in word:
        if 0x05D0 <= ord(ch) <= 0x05EA:
            out.append((fold_finals(ch), ""))
        elif out and 0x05B0 <= ord(ch) <= 0x05C7:
            out[-1] = (out[-1][0], out[-1][1] + ch)
    return out


def letter_sound(letter: str, points: str) -> str:
    if letter == "ש":
        return "s" if SIN_DOT in points else "sh"
    return letter


def initial_sound(word: str, skip_letters: int = 0) -> str | None:
    """Sound of the first letter after `skip_letters` prefix letters."""
    cs = clusters(word)[skip_letters:]
    return letter_sound(*cs[0]) if cs else None


def prefix_letters(surface: str, lemma: str) -> int:
    """How many letters the lemma's leading prefix morphemes take (as `store.db.strip_prefixes`)."""
    from bsim.store.db import strip_prefixes
    from bsim.text.normalize import consonantal

    whole = consonantal(surface).replace(" ", "")
    return len(whole) - len(strip_prefixes(surface, lemma))


def content_sounds(
    words: pd.DataFrame, skip_pos: set[str]
) -> dict[tuple[int, int], tuple[str, str, str]]:
    """(verse_id, display_idx) -> (initial sound, shape, lemma key) of the token's first content
    word, prefixes skipped; tokens without a content word are left out."""
    from bsim.lexical.morph import word_token
    from bsim.store.db import lemma_parts_pos

    out: dict[tuple[int, int], tuple[str, str, str]] = {}
    w = words.dropna(subset=["display_idx"]).sort_values(["verse_id", "idx"], kind="stable")
    for vid, di, surface, lemma, content, morph in zip(
        w.verse_id, w.display_idx, w.surface, w.lemma, w.content_lemmas, w.morph, strict=True
    ):
        key = (int(vid), int(di))
        if key in out or not len(content):
            continue
        lemma_key = "+".join(content)
        pos = lemma_parts_pos(lemma, morph)
        if all(pos.get(lem) in skip_pos for lem in content):
            continue
        sound = initial_sound(surface, prefix_letters(surface, lemma))
        if sound:
            out[key] = (sound, word_token(morph), lemma_key)
    return out


def ending(word: str) -> str | None:
    """Rhyme key: the vowel under the second-to-last consonant and the last two consonants."""
    cs = clusters(word)
    if len(cs) < 2:
        return None
    (a, pa), (b, _) = cs[-2], cs[-1]
    vowel = "".join(ch for ch in pa if ch in VOWELS)
    return f"{a}{vowel}{b}"


def tail_at_least(probs: list[float], k: int) -> float:
    """P(at least k successes) of independent trials with these probabilities (exact DP)."""
    dist = [1.0]
    for p in probs:
        nxt = [0.0] * (len(dist) + 1)
        for j, d in enumerate(dist):
            nxt[j] += d * (1 - p)
            nxt[j + 1] += d * p
        dist = nxt
    return float(sum(dist[k:]))


def colon_words(tokens: list[str], span: tuple[int, int]) -> list[int]:
    """Display indexes of the colon's words (tokens with Hebrew letters)."""
    s, e = span
    return [i for i in range(s, e + 1) if clusters(tokens[i])]


def run_sound(cfg: dict[str, Any], log: Log = print) -> Path:
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    par_path = art / "parallelism" / "verses.parquet"
    if not par_path.exists():
        raise RuntimeError(f"{par_path} missing; run `bsim parallelism` first")
    t0 = time.perf_counter()
    sc = cfg["sound"]
    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "display_tokens"]
    )
    words = pd.read_parquet(
        proc / "words.parquet",
        columns=["verse_id", "idx", "display_idx", "surface", "lemma", "content_lemmas", "morph"],
    )
    sound_of = content_sounds(words, set(cfg["structure"]["leitwort_skip_pos"]))
    par = pd.read_parquet(par_path, columns=["verse_id", "cola"])
    cola = dict(zip(par.verse_id, (json.loads(c) for c in par.cola), strict=True))
    tokens = {int(v): list(t) for v, t in zip(verses.verse_id, verses.display_tokens, strict=True)}
    chapter = dict(
        zip(verses.verse_id, (verses.book_id * 1000 + verses.chapter).tolist(), strict=True)
    )

    # every colon in canon order: (verse_id, colon index, word display indexes)
    lines = [
        (vid, k, colon_words(tokens[vid], tuple(span)))
        for vid in sorted(tokens)
        for k, span in enumerate(cola.get(vid) or [[0, len(tokens[vid]) - 1]])
    ]
    lines = [x for x in lines if x[2]]

    # corpus frequencies
    heard = [sound_of[(vid, i)] for vid, _, ws in lines for i in ws if (vid, i) in sound_of]
    initial = Counter(s for s, _, _ in heard)
    by_shape: dict[str, Counter[str]] = {}
    for snd, shape, _ in heard:
        by_shape.setdefault(shape, Counter())[snd] += 1
    ends = Counter(e for vid, _, ws in lines if (e := ending(tokens[vid][ws[-1]])))
    f_init = {s: n / initial.total() for s, n in initial.items()}
    smooth = sc["shape_smoothing"]

    def rate(sound: str, shape: str) -> float:
        c = by_shape.get(shape, Counter())
        return (c[sound] + smooth * f_init[sound]) / (c.total() + smooth)

    f_end = {e: n / ends.total() for e, n in ends.items()}

    allit = []
    for vid, k, ws in lines:
        # each lemma once: repeating a word is repetition, not alliteration
        firsts: dict[str, tuple[int, tuple[str, str, str]]] = {}
        for i in ws:
            if (vid, i) in sound_of and sound_of[(vid, i)][2] not in firsts:
                firsts[sound_of[(vid, i)][2]] = (i, sound_of[(vid, i)])
        heard_here = [h for _, h in firsts.values()]
        if len(heard_here) < sc["min_words"]:
            continue
        top, count = Counter(s for s, _, _ in heard_here).most_common(1)[0]
        if count < sc["min_count"]:
            continue
        p = min(
            1.0,
            sum(
                tail_at_least([rate(snd, shape) for _, shape, _ in heard_here], count)
                for snd in f_init
            ),
        )
        sounds = heard_here
        idxs = [i for i, h in firsts.values() if h[0] == top]
        allit.append((vid, k, top, count, len(sounds), json.dumps(idxs), p))
    al = pd.DataFrame(
        allit, columns=["verse_id", "colon", "sound", "count", "n_words", "words", "p"]
    )
    al["q"] = bh_q(al.p.to_numpy())
    al = al.sort_values(["q", "p", "verse_id"], ignore_index=True)

    def last_word(line: tuple[int, int, list[int]]) -> str:
        return tokens[line[0]][line[2][-1]]

    rhymes, k = [], 0
    while k < len(lines):
        vid, _, ws = lines[k]
        e = ending(last_word(lines[k]))
        j = k + 1
        while (
            e is not None
            and j < len(lines)
            and chapter[lines[j][0]] == chapter[vid]
            and ending(last_word(lines[j])) == e
            and consonantal(last_word(lines[j])) != consonantal(last_word(lines[j - 1]))
        ):
            j += 1
        if e is not None and j - k >= sc["min_run"]:
            run = lines[k:j]
            p = min(1.0, len(lines) * f_end[e] ** (j - k - 1))
            members = [[v, w[-1]] for v, _, w in run]
            rhymes.append((run[0][0], run[-1][0], j - k, e, json.dumps(members), p))
        k = j
    rh = pd.DataFrame(rhymes, columns=["start_vid", "end_vid", "n_cola", "ending", "members", "p"])
    rh["q"] = bh_q(rh.p.to_numpy()) if len(rh) else []
    rh = rh.sort_values(
        ["q", "n_cola", "start_vid"], ascending=[True, False, True], ignore_index=True
    )

    out = art / "sound"
    out.mkdir(parents=True, exist_ok=True)
    al.to_parquet(out / "alliteration.parquet")
    rh.to_parquet(out / "rhymes.parquet")
    meta = {
        "config_hash": config_hash(cfg, "sound", "structure.leitwort_skip_pos"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "cola": len(lines),
        "alliterations": int(len(al)),
        "alliterations_q_below_0.05": int((al.q <= 0.05).sum()),
        "rhymes": int(len(rh)),
        "rhymes_q_below_0.05": int((rh.q <= 0.05).sum()) if len(rh) else 0,
        "top_endings": [
            [e, round(f, 4)] for e, f in sorted(f_end.items(), key=lambda x: -x[1])[:10]
        ],
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "sound.meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log(
        f"done: {meta['alliterations_q_below_0.05']} alliterations and"
        f" {meta['rhymes_q_below_0.05']} rhymes with q <= 0.05 in {meta['seconds']} s -> {out}"
    )
    return out
