"""`bsim mirrors`: chiasm at the small scale — words in a verse, constituents in a clause pair
(DESIGN.md §16.33).

Chiasm (A B … B′ A′) is often said to be a favourite figure of biblical style, but the
whole-unit test of §16.2 finds none beyond chance. Here the question is asked where the figure
is claimed to live, with an order test that needs no similarity model:

- **Words.** In a verse that uses two content lemmas (Strong's number) exactly twice each, the
  four occurrences overlap either in mirrored order (x y … y x, *chiastic*) or in repeated order
  (x y … x y, *parallel*); under a random order both are equally likely. A repeated two-word
  phrase (the pair adjacent both times) is counted apart as a *bigram*: it is formula, not a
  choice of order. Per verse the dominant order is taken (chiastic pairs > parallel pairs or the
  reverse), and the verses are tested with a sign test, for poetry and prose apart (poetic
  books and chapters as §16.24, `dating.poetic`, `poetic_share`); the pair share gets a 95 %
  interval by resampling chapters (`chapter_boot`).
- **Clauses.** Two consecutive BHSA clauses of one verse with the same two constituents
  (phrase functions, `mirrors.functions`: predicate, subject, object, complement, adjunct, …) put
  them in the same order (parallel) or reversed (chiastic). The mirrored share of poetry against
  prose is compared with the genre label permuted over chapters (`shuffles`), and per
  constituent pair.
- **Full mirrors** (leads): verses where ≥ `min_words` lemmas used twice all nest (A B C … C B A,
  no parallel or bigram pair), with p = the share of `verse_shuffles` shuffles of the verse's
  lemma order nesting as many pairs, and BH q.

Writes `artifacts/mirrors/`: `verses.parquet` (full mirrors), `clauses.parquet` (every clause
pair compared) and `mirrors.meta.json` (the tests).
"""

from __future__ import annotations

import itertools
import json
import time
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from bsim.analysis.stats import bh_q, empirical_p
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BY_OSIS

Log = Callable[[str], None]

VERSE_COLUMNS = ["verse_id", "poetic", "n_pairs", "n_words", "p", "q", "lemmas", "idxs"]
CLAUSE_COLUMNS = [
    "verse_id",
    "poetic",
    "pair",
    "first",
    "second",
    "mirrored",
    "a_words",
    "b_words",
]


def order_counts(seq: Sequence[str]) -> tuple[int, int, int, list[str]]:
    """(chiastic, parallel, bigram, the lemmas used exactly twice) over every pair of lemmas used
    exactly twice whose occurrences overlap."""
    cnt = Counter(seq)
    twice = [x for x, n in cnt.items() if n == 2]
    pos = {x: [i for i, y in enumerate(seq) if y == x] for x in twice}
    c = p = b = 0
    for x, y in itertools.combinations(twice, 2):
        (a1, a2), (b1, b2) = sorted([pos[x], pos[y]])
        if b1 > a2:
            continue  # x x … y y: no overlap
        if b2 < a2:
            c += 1
        elif b1 == a1 + 1 and b2 == a2 + 1:
            b += 1
        else:
            p += 1
    return c, p, b, twice


def poetic_verses(cfg: dict[str, Any], verses: pd.DataFrame) -> np.ndarray:
    """Whether each verse is in a poetic book or a chapter of mostly parallel verse halves."""
    from bsim.analysis.dating import poetic_chapters

    books = {BY_OSIS[o].book_id for o in cfg["dating"]["poetic"]}
    chapters = poetic_chapters(cfg, verses)
    return np.array(
        [
            b in books or f"{b}:{c}" in chapters
            for b, c in zip(verses.book_id, verses.chapter, strict=True)
        ]
    )


def sign_test(chiastic: np.ndarray, parallel: np.ndarray) -> dict[str, Any]:
    """Verses where chiastic pairs outnumber parallel ones against the reverse (binomial)."""
    vc, vp = int((chiastic > parallel).sum()), int((parallel > chiastic).sum())
    return {
        "verses_chiastic": vc,
        "verses_parallel": vp,
        "pairs_chiastic": int(chiastic.sum()),
        "pairs_parallel": int(parallel.sum()),
        "share": float(chiastic.sum() / max(1, chiastic.sum() + parallel.sum())),
        "p": float(binomtest(vc, vc + vp).pvalue) if vc + vp else None,
    }


def chapter_interval(
    chiastic: np.ndarray, parallel: np.ndarray, chapter: np.ndarray, reps: int, rng
) -> list[float]:
    """95 % interval of the chiastic pair share, resampling chapters."""
    keys, inv = np.unique(chapter, return_inverse=True)
    c = np.bincount(inv, weights=chiastic, minlength=len(keys))
    p = np.bincount(inv, weights=parallel, minlength=len(keys))
    shares = []
    for _ in range(reps):
        pick = rng.integers(0, len(keys), len(keys))
        tot = c[pick].sum() + p[pick].sum()
        if tot:
            shares.append(c[pick].sum() / tot)
    lo, hi = np.quantile(shares, [0.025, 0.975])
    return [float(lo), float(hi)]


def clause_pairs(phrases: pd.DataFrame, functions: set[str]) -> pd.DataFrame:
    """Consecutive clauses of one verse with the same two constituents (`functions`), in order:
    `verse_id, pair` (sorted), `first, second` (the first clause's order), `mirrored`, and the
    words of the two clauses' constituents (`a_words`, `b_words`: JSON `{function: [idx …]}`)."""
    ph = phrases[phrases.function.isin(functions)].copy()
    ph["start"] = [int(w[0]) for w in ph.words]
    ph = ph.sort_values(["verse_id", "start"])
    clauses = (
        ph.groupby("clause", sort=False)
        .agg(verse_id=("verse_id", "first"), start=("start", "min"), fns=("function", list),
             words=("words", list))
        .reset_index()
        .sort_values(["verse_id", "start"])
    )  # fmt: skip
    rows = []
    for vid, g in clauses.groupby("verse_id", sort=False):
        recs = list(g.itertuples(index=False))
        for a, b in itertools.pairwise(recs):
            if len(a.fns) == 2 == len(b.fns) and len(set(a.fns)) == 2 and set(a.fns) == set(b.fns):
                rows.append(
                    (
                        int(vid),
                        "-".join(sorted(a.fns)),
                        a.fns[0],
                        a.fns[1],
                        int(a.fns != b.fns),
                        _by_function(a.fns, a.words),
                        _by_function(b.fns, b.words),
                    )
                )  # fmt: skip
    return pd.DataFrame(
        rows, columns=["verse_id", "pair", "first", "second", "mirrored", "a_words", "b_words"]
    )


def _by_function(fns: list[str], words: list[Any]) -> str:
    """JSON `{function: [word idx, …]}` of one clause's two constituents."""
    return json.dumps({f: [int(i) for i in w] for f, w in zip(fns, words, strict=True)})


def genre_permutation(
    mirrored: np.ndarray, poetic: np.ndarray, chapter: np.ndarray, reps: int, rng
) -> dict[str, Any]:
    """Mirrored share in poetry minus prose, against the genre label permuted over chapters."""
    keys, inv = np.unique(chapter, return_inverse=True)
    chap_poetic = np.zeros(len(keys), dtype=bool)
    chap_poetic[inv] = poetic

    def diff(lab: np.ndarray) -> float:
        g = lab[inv]
        if g.all() or not g.any():
            return 0.0
        return float(mirrored[g].mean() - mirrored[~g].mean())

    obs = diff(chap_poetic)
    null = np.array([diff(rng.permutation(chap_poetic)) for _ in range(reps)])
    return {
        "poetry": float(mirrored[poetic].mean()) if poetic.any() else None,
        "poetry_n": int(poetic.sum()),
        "prose": float(mirrored[~poetic].mean()) if (~poetic).any() else None,
        "prose_n": int((~poetic).sum()),
        "diff": obs,
        "p": empirical_p(obs, null),
    }


def run_mirrors(cfg: dict[str, Any], log: Log = print) -> Path:
    mc = cfg["mirrors"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "mirrors"
    t0 = time.perf_counter()
    rng = np.random.default_rng(mc["seed"])
    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter"]
    ).sort_values("verse_id")
    poetic = poetic_verses(cfg, verses)
    is_poetic = dict(zip(verses.verse_id, poetic, strict=True))
    chapter_of = dict(zip(verses.verse_id, verses.book_id * 1000 + verses.chapter, strict=True))
    words = pd.read_parquet(proc / "words.parquet", columns=["verse_id", "idx", "content_lemmas"])
    w = words.explode("content_lemmas").dropna()
    w = w.assign(lemma=w.content_lemmas.str.replace(r"[a-z]+$", "", regex=True))

    # word order, and the full mirrors
    rows, mirrors = [], []
    for vid, g in w.groupby("verse_id", sort=True):
        seq = g.lemma.tolist()
        c, p, b, twice = order_counts(seq)
        if len(twice) < 2:
            continue
        rows.append((int(vid), c, p, b))
        if len(twice) >= mc["min_words"] and c >= len(twice) * (len(twice) - 1) // 2 and p + b == 0:
            null = np.array(
                [order_counts(list(rng.permutation(seq)))[0] for _ in range(mc["verse_shuffles"])]
            )
            order = [x for x in seq if x in set(twice)]
            idxs = [int(i) for i, x in zip(g.idx, seq, strict=True) if x in set(twice)]
            mirrors.append((int(vid), bool(is_poetic[vid]), c, len(twice), empirical_p(c, null),
                            json.dumps(order), json.dumps(idxs)))  # fmt: skip
    wv = pd.DataFrame(rows, columns=["verse_id", "c", "p", "b"])
    wv["poetic"] = wv.verse_id.map(is_poetic)
    wv["chapter"] = wv.verse_id.map(chapter_of)
    word_tests = {}
    for name, g in (("all", wv), ("poetry", wv[wv.poetic]), ("prose", wv[~wv.poetic])):
        t = sign_test(g.c.to_numpy(), g.p.to_numpy())
        t["verses"] = int(len(g))
        t["bigrams"] = int(g.b.sum())
        if len(g):
            t["interval"] = chapter_interval(g.c.to_numpy(), g.p.to_numpy(), g.chapter.to_numpy(),
                                             mc["chapter_boot"], rng)  # fmt: skip
        word_tests[name] = t
    mv = pd.DataFrame(
        mirrors, columns=["verse_id", "poetic", "n_pairs", "n_words", "p", "lemmas", "idxs"]
    )
    mv["q"] = bh_q(mv.p.to_numpy()) if len(mv) else []
    mv = mv.sort_values(["p", "n_pairs", "verse_id"], ascending=[True, False, True])

    # clause order
    phrase_path = proc / "syntax_phrases.parquet"
    if phrase_path.exists():
        ph = pd.read_parquet(phrase_path, columns=["clause", "verse_id", "words", "function"])
        cp = clause_pairs(ph, set(mc["functions"]))
    else:
        cp = pd.DataFrame(
            columns=["verse_id", "pair", "first", "second", "mirrored", "a_words", "b_words"]
        )
    cp["poetic"] = cp.verse_id.map(is_poetic).astype(bool)
    clause_tests: dict[str, Any] = {}
    if len(cp):
        mir = cp.mirrored.to_numpy().astype(float)
        chapters = cp.verse_id.map(chapter_of).to_numpy()
        clause_tests = genre_permutation(mir, cp.poetic.to_numpy(), chapters, mc["shuffles"], rng)
        clause_tests["pairs"] = int(len(cp))
        by_pair = []
        for pair, g in cp.groupby("pair"):
            if len(g) < mc["min_pair_n"]:
                continue
            gp, gr = g[g.poetic], g[~g.poetic]
            by_pair.append({
                "pair": pair, "n": int(len(g)),
                "poetry": float(gp.mirrored.mean()) if len(gp) else None, "poetry_n": int(len(gp)),
                "prose": float(gr.mirrored.mean()) if len(gr) else None, "prose_n": int(len(gr)),
            })  # fmt: skip
        clause_tests["by_pair"] = sorted(by_pair, key=lambda r: -r["n"])

    out.mkdir(parents=True, exist_ok=True)
    mv[VERSE_COLUMNS].to_parquet(out / "verses.parquet")
    cp[CLAUSE_COLUMNS].to_parquet(out / "clauses.parquet")
    meta = {
        "config_hash": config_hash(cfg, "mirrors", "dating"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "words": _round(word_tests),
        "clauses": _round(clause_tests),
        "full_mirrors": int(len(mv)),
        "full_mirrors_q": int((mv.q <= mc["max_q"]).sum()) if len(mv) else 0,
        "min_words": mc["min_words"],
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "mirrors.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    a = word_tests["all"]
    log(
        f"done: words chiastic {a['pairs_chiastic']} / parallel {a['pairs_parallel']} pairs"
        f" (verses {a['verses_chiastic']} / {a['verses_parallel']}); clauses mirrored"
        f" {clause_tests.get('poetry')} poetry vs {clause_tests.get('prose')} prose"
        f" (p {clause_tests.get('p')}); {len(mv)} full mirrors ({meta['seconds']} s) -> {out}"
    )
    return out


def _round(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _round(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_round(v) for v in x]
    if isinstance(x, float):
        return float(f"{x:.6g}")
    return x
