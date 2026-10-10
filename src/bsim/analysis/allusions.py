"""`bsim allusions`: rare words shared by two passages, spread over a few verses (DESIGN.md §16.32).

An allusion need not quote a phrase: it can borrow a handful of rare words scattered over two
or three verses (Deut 29:16–18 and Jer 9:12–14: לענה, ראש, שררות). Verse retrieval misses such
a pair when no single verse carries enough of them.

- **Rare words:** content lemmas (sense letters dropped, so a lemma is its Strong's number) found
  in 2 to `rare_max` verses, without proper names and gentilics (lists of names would dominate)
  and without Aramaic (rare in the corpus as a whole, common in its own chapters). Weight = idf
  over verses.
- **Windows** of `window` consecutive verses of one chapter. Two windows of different chapters
  sharing at least `min_shared` rare lemmas score the sum of their weights; overlapping window
  pairs keep the strongest (`window` verses on each side).
- **Null:** verse order shuffled within every chapter (`shuffle_within`, as §16.7): each
  chapter keeps its vocabulary, so two chapters on one subject still share their words, and only
  their gathering within a few verses is destroyed. `q` = the share of pairs at least as strong
  expected by chance (null pairs per shuffle ≥ s / observed pairs ≥ s, monotone, as §16.7).
- **Known:** a pair is known when any of its verse pairs is in the final fused top
  `known_rank` or in a parallel sequence (§16.7); the others are the leads this adds.

Writes `artifacts/allusions/pairs.parquet` (`allusion_id, a_start, a_end, b_start, b_end,
a_book, b_book, n_shared, score, q, known, lemmas` JSON `[[lemma, form], …]`) and
`allusions.meta.json`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy.sparse as sp

from bsim.analysis.sequences import q_values
from bsim.analysis.stats import shuffle_within
from bsim.config import config_hash, resolve_path

Log = Callable[[str], None]

PAIR_COLUMNS = [
    "allusion_id",
    "a_start",
    "a_end",
    "b_start",
    "b_end",
    "a_book",
    "b_book",
    "n_shared",
    "score",
    "q",
    "known",
    "lemmas",
]


def rare_lemmas(words: pd.DataFrame, rare_max: int) -> pd.DataFrame:
    """`verse_id, lemma` of the rare content lemmas (2 .. `rare_max` verses; Strong's number
    without sense letter; proper names and Aramaic words left out), one row per verse."""
    w = words[~words.morph.str.contains("N[pg]", na=False) & ~words.morph.str.startswith("A")]
    lem = w[["verse_id", "content_lemmas"]].explode("content_lemmas").dropna()
    lem = lem.assign(lemma=lem.content_lemmas.str.replace(r"[a-z]+$", "", regex=True))
    lem = lem[["verse_id", "lemma"]].drop_duplicates()
    n_verses = lem.groupby("lemma").verse_id.transform("size")
    return lem[(n_verses >= 2) & (n_verses <= rare_max)].reset_index(drop=True)


def window_matrix(x: sp.csr_matrix, order: np.ndarray, chap: np.ndarray, w: int) -> sp.csr_matrix:
    """Row i: the lemmas of verses order[i .. i+w-1] (binary), empty when they cross a chapter."""
    xo = x[order]
    n = xo.shape[0]
    out = xo.copy()
    for k in range(1, w):
        out = out + sp.vstack([xo[k:], sp.csr_matrix((k, xo.shape[1]))])
    out.data[:] = 1
    ch = chap[order]
    valid = np.zeros(n, dtype=bool)
    valid[: n - w + 1] = ch[: n - w + 1] == ch[w - 1 :]
    return sp.csr_matrix(sp.diags(valid.astype(np.float64)) @ out)


def window_pairs(
    x: sp.csr_matrix, idf: np.ndarray, order: np.ndarray, chap: np.ndarray, w: int, min_shared: int
) -> pd.DataFrame:
    """Window pairs (by position in `order`) of different chapters sharing ≥ `min_shared` rare
    lemmas, with the count and the idf sum, strongest first."""
    s = window_matrix(x, order, chap, w)
    shared = (s @ s.T).tocoo()
    weight = (s @ sp.diags(idf) @ s.T).tocsr()
    keep = (shared.row < shared.col) & (shared.data >= min_shared)
    r, c = shared.row[keep], shared.col[keep]
    ch = chap[order]
    other = ch[r] != ch[c]
    r, c = r[other], c[other]
    if len(r) == 0:
        return pd.DataFrame(columns=["i", "j", "n_shared", "score"])
    df = pd.DataFrame(
        {
            "i": r,
            "j": c,
            "n_shared": shared.data[keep][other].astype(int),
            "score": np.asarray(weight[r, c]).ravel(),
        }
    )
    return df.sort_values(["score", "i", "j"], ascending=[False, True, True], ignore_index=True)


def suppress(pairs: pd.DataFrame, w: int) -> pd.DataFrame:
    """Strongest first, drop a pair whose windows both lie within `w` positions of a kept one."""
    kept: list[tuple[int, int]] = []
    rows = []
    for k, (i, j) in enumerate(zip(pairs.i, pairs.j, strict=True)):
        if any(abs(i - a) <= w and abs(j - b) <= w for a, b in kept):
            continue
        kept.append((i, j))
        rows.append(k)
    return pairs.iloc[rows].reset_index(drop=True)


def run_allusions(cfg: dict[str, Any], log: Log = print) -> Path:
    from bsim.store.db import lemma_display_forms

    ac = cfg["allusions"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    t0 = time.perf_counter()
    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter"]
    ).sort_values("verse_id")
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "surface", "lemma", "content_lemmas", "morph"]
    )
    n = len(verses)
    lem = rare_lemmas(words, ac["rare_max"])
    codes, vocab = pd.factorize(lem.lemma)
    x = sp.csr_matrix((np.ones(len(lem)), (lem.verse_id.to_numpy(), codes)), shape=(n, len(vocab)))
    x.data[:] = 1
    df = np.asarray(x.sum(axis=0)).ravel()
    idf = np.log(n / df)
    chap = (verses.book_id * 1000 + verses.chapter).to_numpy()
    w, ms = ac["window"], ac["min_shared"]

    obs = window_pairs(x, idf, np.arange(n), chap, w, ms)
    rng = np.random.default_rng(ac["seed"])
    null = np.concatenate(
        [
            window_pairs(x, idf, shuffle_within(chap, rng), chap, w, ms).score.to_numpy()
            for _ in range(ac["null_reps"])
        ]
    )
    obs["q"] = q_values(obs.score.to_numpy(), null, ac["null_reps"])
    pairs = suppress(obs, w)

    known: set[tuple[int, int]] = set()
    fused = (
        resolve_path(cfg, "artifacts")
        / "topk"
        / "verse"
        / f"{cfg['final_systems']['fused']}.parquet"
    )
    if fused.exists():
        f = pd.read_parquet(fused, columns=["src_id", "tgt_id", "rank"])
        f = f[f["rank"] <= ac["known_rank"]]
        known |= set(zip(f.src_id.str[2:].astype(int), f.tgt_id.str[2:].astype(int), strict=True))
    seq_path = art / "sequences" / "verse.parquet"
    if seq_path.exists():
        for ps in pd.read_parquet(seq_path, columns=["pairs"]).pairs:
            for a, b, *_ in json.loads(ps):
                known |= {(a, b), (b, a)}
    pairs["known"] = [
        int(any((i + di, j + dj) in known for di in range(w) for dj in range(w)))
        for i, j in zip(pairs.i, pairs.j, strict=True)
    ]

    # the shared lemmas, with a display form (sense letters dropped)
    forms_src = words.assign(
        content_lemmas=[
            [c.rstrip("abcdefghijklmnopqrstuvwxyz") for c in cs] for cs in words.content_lemmas
        ]
    )
    forms = dict(zip(*lemma_display_forms(forms_src)[["lemma", "he_lemma"]].T.values, strict=True))
    by_window = window_matrix(x, np.arange(n), chap, w)
    pairs["lemmas"] = [
        json.dumps(
            [[vocab[k], forms.get(vocab[k], vocab[k])] for k in sorted(
                set(by_window[i].indices) & set(by_window[j].indices), key=lambda k: -idf[k])],
            ensure_ascii=False,
        )
        for i, j in zip(pairs.i, pairs.j, strict=True)
    ]  # fmt: skip
    book = verses.book_id.to_numpy()
    out_df = pd.DataFrame(
        {
            "allusion_id": np.arange(1, len(pairs) + 1),
            "a_start": pairs.i.to_numpy(),
            "a_end": pairs.i.to_numpy() + w - 1,
            "b_start": pairs.j.to_numpy(),
            "b_end": pairs.j.to_numpy() + w - 1,
            "a_book": book[pairs.i],
            "b_book": book[pairs.j],
            "n_shared": pairs.n_shared.to_numpy(),
            "score": pairs.score.round(3).to_numpy(),
            "q": pairs.q.round(4).to_numpy(),
            "known": pairs.known.to_numpy(),
            "lemmas": pairs.lemmas.to_numpy(),
        }
    )
    out = art / "allusions"
    out.mkdir(parents=True, exist_ok=True)
    out_df[PAIR_COLUMNS].to_parquet(out / "pairs.parquet")
    max_q = ac["max_q"]
    strong = out_df[out_df.q <= max_q]
    meta = {
        "config_hash": config_hash(cfg, "allusions", "final_systems"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "rare_lemmas": int(len(vocab)),
        "window": w,
        "pairs": int(len(out_df)),
        "known": int(out_df.known.sum()),
        "max_q": max_q,
        "strong": int(len(strong)),
        "strong_known": int(strong.known.sum()),
        "best_new_q": float(out_df.loc[out_df.known == 0, "q"].min())
        if (out_df.known == 0).any()
        else None,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "allusions.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(
        f"done: {meta['pairs']} window pairs ({meta['known']} known);"
        f" q <= {max_q}: {meta['strong']} ({meta['strong_known']} known);"
        f" best new q {meta['best_new_q']} ({meta['seconds']} s)"
        f" -> {out}"
    )
    return out
