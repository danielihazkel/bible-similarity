"""`bsim forms`: graded numerical sayings and lists (DESIGN.md §16.45).

Two small literary forms the other analyses do not see. The *graded numerical saying* names a
number and then the next: על שלשה פשעי דמשק ועל ארבעה (Amos 1:3), שש הנה שנא יהוה ושבע תועבת נפשו
(Prov 6:16). A *list* repeats one verse shape: the genealogy of Genesis 5, the stations of
Numbers 33, the kings of Joshua 12.

- **Numbers.** A word is a number when one of its morphemes has a lemma in `numbers` (the
  cardinals, Hebrew and Aramaic, and רבבה / ריבו; not a name). Number words side by side are one
  compound number (שלשים ושנים, שלש מאות, שלש עשרה) and left out, unless they are just two
  words a step apart (שנים שלשה, אלף ורבבה); the rest are *free*.
- **Graded pairs.** Two free number words of one verse, the second at most `window` words after
  the first, whose values make a step (`steps`: x then x+1, the tens, a thousand then ten
  thousand). A verse holding one is a *saying*.
- **Checks fixed in advance.** (1) `known`: the sayings scholarship names, each found when at
  least half its verses are sayings. (2) Chance: the graded pairs against the values of the
  free number words permuted within each book (`shuffles`). (3) Parallelism: the mean
  probability of parallel halves (§16.9) of the sayings against the other verses holding two
  free numbers within the window, the labels permuted (`shuffles`).
- **Lists.** Each verse becomes the counts of its word-shape n-grams (`lexical.morph`, §16.5,
  1..`max_n`), and is compared (cosine) with the verses up to `lags` before and after it in its
  book; its best match is its *likeness*. A verse is list-like when its likeness is above the
  `quantile` of the likenesses with verse orders shuffled within books (`list_shuffles`); a list
  is a run of at least `min_verses` list-like verses with at most `max_gap` other verses between
  consecutive ones. Its kind (described): the first of `kinds` whose lemmas are in half its
  verses, else `names` when proper nouns are `names_share` of its words. (4) `lists.known`: lists
  named in advance, each found when half its verses are in a list, among more lists than the
  shuffled orders give.

Writes `artifacts/forms/`: `sayings.parquet` (`verse_id, book_id, n_pairs, steps, prob, known`),
`pairs.parquet` (`verse_id, a_tok, b_tok, a_value, b_value`: display tokens), `lists.parquet`
(`list_id, book_id, first_vid, last_vid, n_like, likeness, kind, known`), `books.parquet`
(`book_id, numbers, free, sayings, lists, list_verses`) and `forms.meta.json`.
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

from bsim.analysis.stats import empirical_p, shuffle_within
from bsim.config import config_hash, resolve_path
from bsim.lexical.morph import morph_streams, ngram_tokens

Log = Callable[[str], None]
NUMBER_COLUMNS = ["verse_id", "idx", "display_idx", "value"]


def number_words(words: pd.DataFrame, numbers: dict[str, int]) -> pd.DataFrame:
    """One row per number word: `verse_id, idx, display_idx, value` (its first number morpheme;
    a name is not a number)."""
    rows = []
    for vid, idx, lemma, morph, d in zip(
        words.verse_id, words.idx, words.lemma, words.morph, words.display_idx, strict=True
    ):
        codes = morph[1:].split("/") if isinstance(morph, str) and morph else []
        for k, part in enumerate(str(lemma).split("/")):
            lem = part.replace(" ", "")
            code = codes[k] if k < len(codes) else ""
            if lem in numbers and not code.startswith("Np"):
                rows.append((int(vid), int(idx), d, int(numbers[lem])))
                break
    return pd.DataFrame(rows, columns=NUMBER_COLUMNS)


def free_numbers(nums: pd.DataFrame, steps: set[tuple[int, int]]) -> pd.DataFrame:
    """The number words that are not part of a compound number: alone, or one of just two side
    by side a step apart."""
    if nums.empty:
        return nums.assign(run=pd.Series(dtype=np.int64))
    nums = nums.sort_values(["verse_id", "idx"], kind="stable").reset_index(drop=True)
    vid, idx = nums.verse_id.to_numpy(), nums.idx.to_numpy()
    new = np.ones(len(nums), dtype=bool)
    new[1:] = (vid[1:] != vid[:-1]) | (idx[1:] - idx[:-1] != 1)
    run = np.cumsum(new)
    size = np.bincount(run)[run]
    keep = size == 1
    two = np.flatnonzero(new & (size == 2))
    val = nums.value.to_numpy()
    for i in two:
        if (int(val[i]), int(val[i + 1])) in steps:
            keep[i] = keep[i + 1] = True
    return nums[keep].assign(run=run[keep]).reset_index(drop=True)


def candidate_pairs(free: pd.DataFrame, window: int) -> tuple[np.ndarray, np.ndarray]:
    """Row indices (i, j) of the free numbers of one verse, j after i by at most `window` words."""
    vid, idx = free.verse_id.to_numpy(), free.idx.to_numpy()
    a, b = [], []
    for d in range(1, len(free)):
        i = np.arange(len(free) - d)
        ok = (vid[i] == vid[i + d]) & (idx[i + d] - idx[i] <= window)
        if not ok.any():
            break  # rows sorted, so a larger offset is never closer
        a.append(i[ok])
        b.append(i[ok] + d)
    if not a:
        return np.array([], dtype=np.int64), np.array([], dtype=np.int64)
    return np.concatenate(a), np.concatenate(b)


def step_table(values: np.ndarray, steps: set[tuple[int, int]]) -> tuple[np.ndarray, np.ndarray]:
    """Value codes of each number and a boolean table `ok[code_a, code_b]` of the steps."""
    uniq, codes = np.unique(values, return_inverse=True)
    ok = np.zeros((len(uniq), len(uniq)), dtype=bool)
    for x, y in steps:
        ix, iy = np.searchsorted(uniq, x), np.searchsorted(uniq, y)
        if ix < len(uniq) and iy < len(uniq) and uniq[ix] == x and uniq[iy] == y:
            ok[ix, iy] = True
    return codes, ok


def shape_matrix(words: pd.DataFrame, n_verses: int, max_n: int) -> sp.csr_matrix:
    """Verses × word-shape n-grams (1..`max_n`), counted, rows L2-normalized."""
    streams = [ngram_tokens(t, max_n) for t in morph_streams(words, n_verses)]
    flat = [g for s in streams for g in s]
    codes, vocab = pd.factorize(pd.Series(flat, dtype=object))
    rows = np.repeat(np.arange(n_verses), [len(s) for s in streams])
    x = sp.csr_matrix(
        (np.ones(len(codes)), (rows, codes)), shape=(n_verses, max(len(vocab), 1))
    )
    x.sum_duplicates()
    norm = np.sqrt(np.asarray(x.multiply(x).sum(axis=1)).ravel())
    norm[norm == 0] = 1.0
    return sp.csr_matrix(sp.diags(1 / norm) @ x)


def likeness(x: sp.csr_matrix, order: np.ndarray, book: np.ndarray, lags: int) -> np.ndarray:
    """For the verses in `order` (book by book), each one's best cosine with the verses up to
    `lags` positions before or after it in the same book; returned by position in `order`."""
    xo = x[order]
    bo = book[order]
    best = np.zeros(len(order))
    for lag in range(1, lags + 1):
        s = np.asarray(xo[:-lag].multiply(xo[lag:]).sum(axis=1)).ravel()
        s[bo[:-lag] != bo[lag:]] = 0.0
        best[:-lag] = np.maximum(best[:-lag], s)
        best[lag:] = np.maximum(best[lag:], s)
    return best


def list_runs(
    like: np.ndarray, book: np.ndarray, min_verses: int, max_gap: int
) -> list[tuple[int, int, int]]:
    """Runs of list-like positions (`like` boolean, positions book by book): (first, last,
    list-like count) of each run with at least `min_verses` of them, at most `max_gap` other
    positions between consecutive ones, inside one book."""
    pos = np.flatnonzero(like)
    if len(pos) == 0:
        return []
    new = np.ones(len(pos), dtype=bool)
    new[1:] = (np.diff(pos) > max_gap + 1) | (book[pos[1:]] != book[pos[:-1]])
    starts = np.flatnonzero(new)
    ends = np.append(starts[1:], len(pos))
    return [
        (int(pos[s]), int(pos[e - 1]), int(e - s))
        for s, e in zip(starts, ends, strict=True)
        if e - s >= min_verses
    ]


def run_forms(cfg: dict[str, Any], log: Log = print) -> Path:
    fc = cfg["forms"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "forms"
    t0 = time.perf_counter()
    rng = np.random.default_rng(fc["seed"])
    list_rng = np.random.default_rng([fc["seed"], 1])  # the lists draw on their own stream
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "ref"])
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "idx", "lemma", "morph", "display_idx"]
    ).sort_values(["verse_id", "idx"])
    n_verses = int(verses.verse_id.max()) + 1
    book = np.zeros(n_verses, dtype=np.int64)
    book[verses.verse_id.to_numpy()] = verses.book_id.to_numpy()
    vid_of = dict(zip(verses.ref, verses.verse_id, strict=True))
    steps = {(int(a), int(b)) for a, b in fc["steps"]}
    numbers = {str(k): int(v) for k, v in fc["numbers"].items()}

    # graded pairs
    nums = number_words(words, numbers)
    free = free_numbers(nums, steps)
    ia, ib = candidate_pairs(free, fc["window"])
    codes, ok = step_table(free.value.to_numpy(), steps)
    graded = ok[codes[ia], codes[ib]]
    observed = int(graded.sum())
    fvid = free.verse_id.to_numpy()
    fbook = book[fvid]
    null = np.empty(fc["shuffles"])
    for s in range(fc["shuffles"]):
        c = codes[shuffle_within(fbook, rng)]
        null[s] = ok[c[ia], c[ib]].sum()
    chance = {
        "pairs": int(len(ia)),
        "observed": observed,
        "expected": float(null.mean()),
        "p": empirical_p(observed, null),
    }
    # described: the same test without the steps of `sensitivity_drop` (added after the first run)
    kept = steps - {(int(a), int(b)) for a, b in fc["sensitivity_drop"]}
    _, ok2 = step_table(free.value.to_numpy(), kept)
    obs2 = int(ok2[codes[ia], codes[ib]].sum())
    null2 = np.empty(fc["shuffles"])
    for s in range(fc["shuffles"]):
        c = codes[shuffle_within(fbook, rng)]
        null2[s] = ok2[c[ia], c[ib]].sum()
    chance["without"] = [f"{a} / {b}" for a, b in fc["sensitivity_drop"]]
    chance["without_observed"] = obs2
    chance["without_expected"] = float(null2.mean())
    chance["without_p"] = empirical_p(obs2, null2)

    gi, gj = ia[graded], ib[graded]
    disp = free.display_idx.to_numpy()
    pairs = pd.DataFrame(
        {
            "verse_id": fvid[gi],
            "a_tok": pd.array(disp[gi], dtype="Int64"),
            "b_tok": pd.array(disp[gj], dtype="Int64"),
            "a_value": free.value.to_numpy()[gi],
            "b_value": free.value.to_numpy()[gj],
        }
    )
    say = (
        pairs.groupby("verse_id", sort=True)
        .apply(
            lambda g: pd.Series(
                {
                    "n_pairs": len(g),
                    "steps": "; ".join(
                        dict.fromkeys(
                            f"{a} / {b}" for a, b in zip(g.a_value, g.b_value, strict=True)
                        )
                    ),
                }
            ),
            include_groups=False,
        )
        .reset_index()
        if len(pairs)
        else pd.DataFrame(columns=["verse_id", "n_pairs", "steps"])
    )
    say["book_id"] = book[say.verse_id.to_numpy(dtype=np.int64)]

    # (3) parallel lines: sayings against the other verses holding two free numbers in the window
    par_path = art / "parallelism" / "verses.parquet"
    parallel: dict[str, Any] | None = None
    say["prob"] = pd.array([None] * len(say), dtype="Float64")
    if par_path.exists():
        par = pd.read_parquet(par_path, columns=["verse_id", "prob"])
        par = par[par.prob.notna()]
        prob = dict(zip(par.verse_id, par.prob, strict=True))
        say["prob"] = pd.array([prob.get(int(v)) for v in say.verse_id], dtype="Float64")
        cand = np.unique(fvid[ia])
        cand = cand[[int(v) in prob for v in cand]]
        lab = np.isin(cand, say.verse_id.to_numpy())
        pv = np.array([prob[int(v)] for v in cand])
        if lab.any() and (~lab).any():
            diff = pv[lab].mean() - pv[~lab].mean()
            sims = np.empty(fc["shuffles"])
            for s in range(fc["shuffles"]):
                pl = rng.permutation(lab)
                sims[s] = pv[pl].mean() - pv[~pl].mean()
            parallel = {
                "sayings": int(lab.sum()),
                "others": int((~lab).sum()),
                "saying_prob": float(pv[lab].mean()),
                "other_prob": float(pv[~lab].mean()),
                "saying_parallel": float((pv[lab] >= cfg["parallelism"]["parallel_at"]).mean()),
                "other_parallel": float((pv[~lab] >= cfg["parallelism"]["parallel_at"]).mean()),
                "p": empirical_p(diff, sims),
            }

    # (1) the sayings named in advance
    saying_set = set(say.verse_id.tolist())
    known, known_of = [], {}
    for name, refs in fc["known"]:
        vids = [vid_of[r] for r in refs]
        hit = [v for v in vids if v in saying_set]
        found = 2 * len(hit) >= len(vids)
        known.append({"name": name, "verses": vids, "hits": hit, "found": found})
        for v in vids:
            known_of.setdefault(v, name)
    say["known"] = say.verse_id.map(known_of)

    # lists: runs of verses shaped alike
    lc = fc["lists"]
    x = shape_matrix(words, n_verses, lc["max_n"])
    order = np.argsort(book, kind="stable")  # verse ids are in canon order, so this is the identity
    like = likeness(x, order, book, lc["lags"])
    null_like = []
    for _ in range(fc["list_shuffles"]):
        perm = shuffle_within(book[order], list_rng)
        null_like.append(likeness(x, order[perm], book, lc["lags"]))
    threshold = float(np.quantile(np.concatenate(null_like), lc["quantile"]))
    runs = list_runs(like >= threshold, book[order], lc["min_verses"], lc["max_gap"])
    expected_lists = float(
        np.mean([len(list_runs(n >= threshold, book[order], lc["min_verses"], lc["max_gap"]))
                 for n in null_like])  # fmt: skip
    )
    lemmas_of = (
        words.assign(lem=words.lemma.astype(str).str.split("/"))
        .explode("lem")
        .assign(lem=lambda d: d.lem.str.replace(" ", "", regex=False))
        .groupby("verse_id")
        .lem.agg(set)
    )
    is_name = words.morph.astype(str).str.contains(r"^.(?:[^/]*/)*Np", regex=True)
    name_share = is_name.groupby(words.verse_id).agg(["sum", "size"])
    rows = []
    for first, last, n_like in runs:
        vids = order[first : last + 1]
        kind = "other"
        for name, cues in lc["kinds"].items():
            has = sum(bool(lemmas_of.get(int(v), set()) & set(cues)) for v in vids)
            if 2 * has >= len(vids):
                kind = name
                break
        else:
            ns = name_share.reindex(vids).fillna(0)
            if ns["sum"].sum() >= lc["names_share"] * max(ns["size"].sum(), 1):
                kind = "names"
        rows.append(
            (int(book[vids[0]]), int(vids[0]), int(vids[-1]), n_like,
             float(like[first : last + 1].mean()), kind)
        )  # fmt: skip
    lists = pd.DataFrame(
        rows, columns=["book_id", "first_vid", "last_vid", "n_like", "likeness", "kind"]
    )
    lists = lists.sort_values("first_vid", kind="stable").reset_index(drop=True)
    lists["list_id"] = np.arange(1, len(lists) + 1)
    in_list = np.zeros(n_verses, dtype=bool)
    for a, b in zip(lists.first_vid, lists.last_vid, strict=True):
        in_list[a : b + 1] = True
    known_lists, list_known = [], {}
    for name, first_ref, last_ref in lc["known"]:
        a, b = vid_of[first_ref], vid_of[last_ref]
        covered = int(in_list[a : b + 1].sum())
        found = 2 * covered >= b - a + 1
        ids = lists[(lists.first_vid <= b) & (lists.last_vid >= a)].list_id.tolist()
        known_lists.append(
            {"name": name, "first_vid": a, "last_vid": b, "covered": covered, "found": found,
             "list_ids": [int(i) for i in ids]}
        )  # fmt: skip
        for i in ids:
            list_known.setdefault(int(i), name)
    lists["known"] = lists.list_id.map(list_known)

    # per book
    nb = int(book.max()) + 1
    books = pd.DataFrame(
        {
            "book_id": np.arange(nb),
            "numbers": np.bincount(book[nums.verse_id.to_numpy(dtype=np.int64)], minlength=nb),
            "free": np.bincount(fbook, minlength=nb),
            "sayings": np.bincount(say.book_id.to_numpy(dtype=np.int64), minlength=nb),
            "lists": np.bincount(lists.book_id.to_numpy(dtype=np.int64), minlength=nb),
            "list_verses": np.bincount(book[in_list], minlength=nb),
        }
    )

    out.mkdir(parents=True, exist_ok=True)
    say[["verse_id", "book_id", "n_pairs", "steps", "prob", "known"]].to_parquet(
        out / "sayings.parquet"
    )
    pairs.to_parquet(out / "pairs.parquet")
    lists[["list_id", "book_id", "first_vid", "last_vid", "n_like", "likeness", "kind",
           "known"]].to_parquet(out / "lists.parquet")  # fmt: skip
    books.to_parquet(out / "books.parquet")
    n_found = sum(k["found"] for k in known)
    n_lists_found = sum(k["found"] for k in known_lists)
    meta = {
        "config_hash": config_hash(cfg, "forms"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "window": fc["window"],
        "alpha": fc["alpha"],
        "shuffles": fc["shuffles"],
        "numbers": int(len(nums)),
        "free": int(len(free)),
        "sayings": int(len(say)),
        "graded_pairs": observed,
        "steps": {f"{a} / {b}": int(n) for (a, b), n in
                  pairs.groupby(["a_value", "b_value"]).size().items()},  # fmt: skip
        "chance": chance,
        "parallel": parallel,
        "known": known,
        "known_found": n_found,
        "known_share": fc["known_share"],
        "lists": {
            "threshold": threshold,
            "like_verses": int((like >= threshold).sum()),
            "observed": int(len(lists)),
            "expected": expected_lists,
            "verses": int(in_list.sum()),
            "kinds": {str(k): int(n) for k, n in lists.kind.value_counts().items()},
            "known": known_lists,
            "known_found": n_lists_found,
            "known_share": lc["known_share"],
            "shuffles": fc["list_shuffles"],
            "min_verses": lc["min_verses"],
            "quantile": lc["quantile"],
        },
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "forms.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
    log(
        f"done: {len(say)} sayings ({observed} graded pairs, {chance['expected']:.1f} by chance,"
        f" p {chance['p']:.3f}); known {n_found} / {len(known)}; parallel {parallel}; lists"
        f" {len(lists)} ({expected_lists:.1f} by chance), known {n_lists_found} /"
        f" {len(known_lists)} ({meta['seconds']} s) -> {out}"
    )
    return out
