"""`bsim ciphers`: names hidden by atbash and albam, against random letter swaps (DESIGN.md §16.54).

Jeremiah writes Babel as ששך (25:26, 51:41) and the Chaldeans as לב קמי (51:1): atbash, the
alphabet folded on itself (`text/ciphers.py`). Does the cipher stand out where it is known to be,
and does it hide names anywhere else?

- **Spans** (the MAM display tokens, the qere read; letters only, final forms folded): one word
  whose written form occurs at most `rare_form` times (a cipher makes an odd word), or two
  adjacent words read as one (לב קמי). At least `min_letters` letters.
- **A hit**: a span that a swap turns into a name of the text: the name part of an OSHB word
  tagged `Np` (the divine names of `entities.skip_lemmas` left out), at least `min_letters`
  letters.
- **The null**: `shuffles` random pairings of the 22 letters (eleven swaps, as atbash and albam
  are), each scored the same way. Every check is the swap's hits against theirs, one-sided:
  `known` (the three named cases are found), `jeremiah` (atbash in the chapters named), `elsewhere`
  (atbash in the rest of the Bible) and `albam` (anywhere). Per chapter, each swap's hits get the
  share of random pairings that do as well (`p`) and BH q over the chapters.

Writes `artifacts/ciphers/`: `hits.parquet` (`cipher, verse_id, book_id, first_tok, last_tok,
span, letters, reads, name_lemma, known`), `chapters.parquet` (per swap the chapters with a hit:
`cipher, unit_id, book_id, hits, expected, p, q`) and `ciphers.meta.json`.
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.stats import bh_q, empirical_p
from bsim.config import config_hash, resolve_path
from bsim.data.lexicon import strong_key
from bsim.data.refs import RefIndex
from bsim.text.ciphers import CIPHERS, TABLES, key, random_swap, table
from bsim.text.normalize import consonantal

Log = Callable[[str], None]


def name_forms(words: pd.DataFrame, skip: set[str], min_letters: int) -> dict[str, tuple[str, str]]:
    """Each name of the text (letters, finals folded) -> (its commonest written form, its
    commonest lemma): the name part of every OSHB word tagged `Np`."""
    forms: dict[str, Counter[tuple[str, str]]] = defaultdict(Counter)
    for surface, lemma, morph in zip(words.surface, words.lemma, words.morph, strict=True):
        if not isinstance(morph, str) or "Np" not in morph:
            continue
        parts, lemmas, codes = surface.split("/"), str(lemma).split("/"), morph[1:].split("/")
        for i, code in enumerate(codes):
            if not code.startswith("Np") or i >= len(parts) or i >= len(lemmas):
                continue
            lem = lemmas[i].replace(" ", "")
            if strong_key(lem) in skip:
                continue
            written = consonantal(parts[i]).replace(" ", "")
            if len(written) >= min_letters:
                forms[key(written)][(written, lem)] += 1
    return {k: c.most_common(1)[0][0] for k, c in forms.items()}


def spans(verses: pd.DataFrame, rare_form: int, min_letters: int, max_letters: int) -> pd.DataFrame:
    """Every span a cipher may hide in: a rare written form, or two adjacent words as one."""
    toks = [
        (int(v), i, t, key(t))
        for v, ts in zip(verses.verse_id, verses.display_tokens, strict=True)
        for i, t in enumerate(ts)
    ]
    toks = [t for t in toks if t[3]]
    n_form = Counter(t[3] for t in toks)
    rows = []
    for j, (v, i, t, k) in enumerate(toks):
        if n_form[k] <= rare_form and min_letters <= len(k) <= max_letters:
            rows.append((v, i, i, consonantal(t), k))
        if j + 1 < len(toks) and toks[j + 1][0] == v:
            _, i2, t2, k2 = toks[j + 1]
            if min_letters <= len(k) + len(k2) <= max_letters:
                rows.append((v, i, i2, f"{consonantal(t)} {consonantal(t2)}", k + k2))
    return pd.DataFrame(rows, columns=["verse_id", "first_tok", "last_tok", "span", "letters"])


def hits_of(unique: list[str], tab: dict[int, str], names: dict[str, Any]) -> np.ndarray:
    """Which of the unique span strings a swap turns into a name."""
    return np.fromiter((s.translate(tab) in names for s in unique), bool, len(unique))


def run_ciphers(cfg: dict[str, Any], log: Log = print) -> Path:
    cc = cfg["ciphers"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "ciphers"
    t0 = time.perf_counter()
    rng = np.random.default_rng(cc["seed"])
    alpha, reps, min_letters = cc["alpha"], int(cc["shuffles"]), int(cc["min_letters"])

    verses = pd.read_parquet(
        proc / "verses.parquet",
        columns=["verse_id", "book_id", "chapter", "verse", "display_tokens"],
    ).sort_values("verse_id")
    words = pd.read_parquet(proc / "words.parquet", columns=["surface", "lemma", "morph"])
    skip = {strong_key(s) for s in cfg["entities"]["skip_lemmas"]}
    names = name_forms(words, skip, min_letters)
    max_letters = max((len(k) for k in names), default=0)
    sp = spans(verses, int(cc["rare_form"]), min_letters, max_letters)
    unique, inverse = np.unique(sp.letters.to_numpy(dtype=object), return_inverse=True)
    unique = [str(u) for u in unique]
    chap_of = dict(
        zip(verses.verse_id, zip(verses.book_id, verses.chapter, strict=True), strict=True)
    )
    chapters = sorted(set(chap_of.values()))
    chap_index = {c: i for i, c in enumerate(chapters)}
    occ_chap = np.array([chap_index[chap_of[v]] for v in sp.verse_id], dtype=np.int64)
    log(
        f"{len(names):,} names; {len(sp):,} spans ({len(unique):,} distinct) in"
        f" {len(chapters):,} chapters"
    )

    def per_chapter(tab: dict[int, str]) -> tuple[np.ndarray, np.ndarray]:
        hit = hits_of(unique, tab, names)[inverse]
        return hit, np.bincount(occ_chap[hit], minlength=len(chapters))

    # the chapters and verses named, resolved first
    index = RefIndex(verses)
    named = [chap_index[chap_of[index.resolve(ref)[0]]] for ref in cc["chapters"]]
    known_vid = {k["ref"]: index.resolve(k["ref"])[0] for k in cc["known"]}
    in_named = np.zeros(len(chapters), dtype=bool)
    in_named[named] = True

    observed = {c: per_chapter(TABLES[c]) for c in CIPHERS}
    null = np.zeros((reps, len(chapters)), dtype=np.int32)
    for r in range(reps):
        null[r] = per_chapter(table(random_swap(rng)))[1]
    log(f"  {reps} random pairings scored ({time.perf_counter() - t0:.0f} s)")

    def test(counts: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
        obs = int(counts[mask].sum())
        sims = null[:, mask].sum(axis=1)
        return {"observed": obs, "expected": float(sims.mean()), "p": empirical_p(obs, sims)}

    atbash = observed["atbash"][1]
    tests = {
        "jeremiah": test(atbash, in_named),
        "elsewhere": test(atbash, ~in_named),
        "albam": test(observed["albam"][1], np.ones(len(chapters), dtype=bool)),
    }
    tests["albam_elsewhere"] = test(observed["albam"][1], ~in_named)

    # the hits, with the cases named in advance marked
    hit_rows = []
    for c in CIPHERS:
        hit = observed[c][0]
        for r in sp[hit].itertuples(index=False):
            k = r.letters.translate(TABLES[c])
            written, lemma = names[k]
            hit_rows.append((c, r.verse_id, r.first_tok, r.last_tok, r.span, r.letters,
                             written, lemma))  # fmt: skip
    hits = pd.DataFrame(
        hit_rows,
        columns=["cipher", "verse_id", "first_tok", "last_tok", "span", "letters", "reads",
                 "name_lemma"],  # fmt: skip
    )
    hits["book_id"] = hits.verse_id.map(lambda v: chap_of[v][0]).astype(int)
    hits["known"] = None
    known = []
    for k in cc["known"]:
        vid = known_vid[k["ref"]]
        m = (
            (hits.cipher == k["cipher"])
            & (hits.verse_id == vid)
            & (hits.letters == key(k["text"]))
            & (hits.reads.map(key) == key(k["name"]))
        )
        hits.loc[m, "known"] = k["ref"]
        known.append({"ref": k["ref"], "verse_id": int(vid), "cipher": k["cipher"],
                      "text": k["text"], "name": k["name"], "found": bool(m.any())})  # fmt: skip
    hits = hits[
        ["cipher", "verse_id", "book_id", "first_tok", "last_tok", "span", "letters", "reads",
         "name_lemma", "known"]  # fmt: skip
    ].sort_values(["cipher", "verse_id", "first_tok", "last_tok"], kind="stable")

    # per chapter: each swap's hits against the random pairings
    chap_rows = []
    for c in CIPHERS:
        counts = observed[c][1]
        p = (1 + (null >= counts).sum(axis=0)) / (1 + reps)
        q = bh_q(p)
        for i in np.flatnonzero(counts):
            b, ch = chapters[i]
            chap_rows.append((c, f"c:{b}:{ch}", b, int(counts[i]), float(null[:, i].mean()),
                              float(p[i]), float(q[i])))  # fmt: skip
    chap = pd.DataFrame(
        chap_rows, columns=["cipher", "unit_id", "book_id", "hits", "expected", "p", "q"]
    ).sort_values(["cipher", "p", "book_id", "unit_id"], kind="stable")

    out.mkdir(parents=True, exist_ok=True)
    hits.to_parquet(out / "hits.parquet")
    chap.to_parquet(out / "chapters.parquet")
    found = sum(k["found"] for k in known)
    meta = {
        "config_hash": config_hash(cfg, "ciphers", "entities"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "min_letters": min_letters,
        "rare_form": int(cc["rare_form"]),
        "shuffles": reps,
        "alpha": alpha,
        "names": len(names),
        "spans": len(sp),
        "single_spans": int((sp.first_tok == sp.last_tok).sum()),
        "distinct_spans": len(unique),
        "chapters": [str(c) for c in cc["chapters"]],
        "n_chapters": len(chapters),
        "hits": {c: int(observed[c][0].sum()) for c in CIPHERS},
        "random_hits": float(null.sum(axis=1).mean()),
        "known": known,
        "known_found": found,
        "tests": tests,
        "chapters_q": {c: int((chap[chap.cipher == c].q <= alpha).sum()) for c in CIPHERS},
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "ciphers.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
    t = tests
    log(
        f"done: atbash {meta['hits']['atbash']} hits, albam {meta['hits']['albam']}, a random"
        f" pairing {meta['random_hits']:.1f}; known {found}/{len(known)}; Jeremiah"
        f" {t['jeremiah']['observed']} vs {t['jeremiah']['expected']:.2f} (p"
        f" {t['jeremiah']['p']:.3f}); elsewhere {t['elsewhere']['observed']} vs"
        f" {t['elsewhere']['expected']:.1f} (p {t['elsewhere']['p']:.3f}); albam"
        f" {t['albam']['observed']} vs {t['albam']['expected']:.1f} (p {t['albam']['p']:.3f})"
        f" ({meta['seconds']} s) -> {out}"
    )
    return out

