"""`bsim vocabulary`: the vocabulary over the canon, book by book (DESIGN.md §16.76).

Read in canon order, each book brings in words not found before it. Genesis brings in most of the
vocabulary; a late book is said to bring in words of its own age (Late Biblical Hebrew, §16.24).
Does it, once its length and its place in the canon are allowed for?

- **Words.** A word counts by its content lemmas (OSHB, homonyms apart), Hebrew only (Aramaic
  words left out) and not proper names (morphology Np). A book's *new* lemmas are those found in
  no book before it; a *hapax* is a lemma found once in the canon; a lemma of *one corpus* is
  found in one of Torah, Prophets and Writings only.
- **Heaps' law.** The vocabulary V after N words, V = K N^b, fitted by least squares on the logs
  at each book's end. A book's expected new lemmas are K (N_end^b − N_start^b); its *excess* is
  log((new + 1) / (expected + 1)). Its *novelty* is its mean excess over `orders` random orders of
  the books (each with its own fit), so that its place in the canon does not decide it: a book read
  last brings in few new words wherever it stands in the history of the language.
- **Claims fixed in advance.** (1) The late books (`dating.late`) have a higher mean novelty than
  the early books (`dating.early`): the difference of the two means against every split of those
  books into two sets of their sizes (exact). (2) Known: each book of `known` at or above its rank
  by hapax per 1,000 words (Job, the Song).

Writes `artifacts/vocabulary/`: `books.parquet` (`book_id, words, lemmas, new, new_per_k,
expected, excess, novelty, hapax, hapax_per_k, one_corpus, end_words, end_lemmas, period`),
`lemmas.parquet` (`lemma, first_verse, first_tok, n_words, n_books, section, counted, hapax`: every
content lemma, names and Aramaic too; `counted` = in the vocabulary above; `section` when it is
found in one corpus only) and `vocabulary.meta.json`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path, write_meta
from bsim.data.canon import BOOKS, BY_OSIS

Log = Callable[[str], None]


def counted_word(morph: str) -> bool:
    """Hebrew, not a proper name."""
    if not isinstance(morph, str) or not morph.startswith("H"):
        return False
    return not any(seg.startswith("Np") for seg in morph[1:].split("/"))


def heaps(ends_n: np.ndarray, ends_v: np.ndarray) -> tuple[float, float]:
    """K and b of V = K N^b, least squares on the logs."""
    b, log_k = np.polyfit(np.log(ends_n), np.log(ends_v), 1)
    return float(np.exp(log_k)), float(b)


def walk(order: list[int], sets: dict[int, np.ndarray], sizes: dict[int, int], n_lemmas: int
         ) -> tuple[dict[int, int], np.ndarray, np.ndarray]:  # fmt: skip
    """Read the books in `order`: each book's new lemmas; the words and vocabulary at each end."""
    seen = np.zeros(n_lemmas, dtype=bool)
    new: dict[int, int] = {}
    ends_n, ends_v, n, v = [], [], 0, 0
    for b in order:
        s = sets[b]
        k = int((~seen[s]).sum())
        seen[s] = True
        new[b] = k
        n += sizes[b]
        v += k
        ends_n.append(n)
        ends_v.append(v)
    return new, np.asarray(ends_n, dtype=float), np.asarray(ends_v, dtype=float)


def excess(order: list[int], new: dict[int, int], sizes: dict[int, int], ends_n: np.ndarray,
           ends_v: np.ndarray) -> dict[int, tuple[float, float]]:  # fmt: skip
    """Each book's expected new lemmas under the fitted Heaps curve and its excess."""
    k, b = heaps(ends_n, ends_v)
    out, start = {}, 0.0
    for bk, end in zip(order, ends_n, strict=True):
        exp = k * (end**b - start**b)
        out[bk] = (exp, float(np.log((new[bk] + 1) / (exp + 1))))
        start = end
    return out


def run_vocabulary(cfg: dict[str, Any], log: Log = print) -> Path:
    vc, dc = cfg["vocabulary"], cfg["dating"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    t0 = time.perf_counter()
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id"])
    book_of = dict(zip(verses.verse_id.astype(int), verses.book_id.astype(int), strict=True))
    words = pd.read_parquet(
        proc / "words.parquet",
        columns=["verse_id", "idx", "morph", "content_lemmas", "display_idx"],
    ).sort_values(["verse_id", "idx"], kind="stable")
    words["book_id"] = words.verse_id.map(book_of)
    words["counted"] = [counted_word(m) for m in words.morph]
    words = words.explode("content_lemmas").dropna(subset=["content_lemmas"])
    words["lemma"] = words.content_lemmas.astype(str)
    section = {b.book_id: b.section for b in BOOKS}

    # every lemma: its first occurrence, how often and where
    first = words.drop_duplicates("lemma", keep="first")
    lem = pd.DataFrame({"lemma": first.lemma.to_numpy(), "first_verse": first.verse_id.to_numpy(),
                        "first_tok": pd.array(first.display_idx, dtype="Int64")})  # fmt: skip
    grp = words.groupby("lemma", sort=False)
    lem["n_words"] = lem.lemma.map(grp.size()).astype(int)
    lem["n_books"] = lem.lemma.map(grp.book_id.nunique()).astype(int)
    secs = words.assign(section=words.book_id.map(section)).groupby("lemma").section.unique()
    lem["section"] = lem.lemma.map(lambda x: secs[x][0] if len(secs[x]) == 1 else None)
    cw = words[words.counted]
    cnt = cw.groupby("lemma").size()
    lem["counted"] = lem.lemma.isin(cnt.index)
    lem["hapax"] = lem.lemma.map(cnt).fillna(0).astype(int).eq(1)

    # the books in canon order, counted words only
    ids = {x: i for i, x in enumerate(cnt.index)}
    book_ids = sorted(int(b) for b in cw.book_id.unique())
    sets = {b: np.unique([ids[x] for x in g.lemma]) for b, g in cw.groupby("book_id")}
    sizes = {int(b): int(n) for b, n in cw.groupby("book_id").size().items()}
    hapax_lemmas = set(cnt.index[cnt == 1])
    new, ends_n, ends_v = walk(book_ids, sets, sizes, len(ids))
    canon = excess(book_ids, new, sizes, ends_n, ends_v)
    k_canon, b_canon = heaps(ends_n, ends_v)

    rng = np.random.default_rng(int(vc["seed"]))
    reps = int(vc["orders"])
    nov = {b: 0.0 for b in book_ids}
    for _ in range(reps):
        order = [book_ids[i] for i in rng.permutation(len(book_ids))]
        n2, en, ev = walk(order, sets, sizes, len(ids))
        for b, (_, e) in excess(order, n2, sizes, en, ev).items():
            nov[b] += e / reps

    early = {BY_OSIS[o].book_id for o in dc["early"]}
    late = {BY_OSIS[o].book_id for o in dc["late"]}
    lemma_section = lem.set_index("lemma").section
    rows = []
    for i, b in enumerate(book_ids):
        g = cw[cw.book_id == b]
        lemmas_b = set(g.lemma)
        rows.append({
            "book_id": b, "words": sizes[b], "lemmas": len(lemmas_b), "new": new[b],
            "new_per_k": round(1000 * new[b] / sizes[b], 3),
            "expected": round(canon[b][0], 2), "excess": round(canon[b][1], 4),
            "novelty": round(nov[b], 4),
            "hapax": int(g.lemma.isin(hapax_lemmas).sum()),
            "hapax_per_k": round(1000 * int(g.lemma.isin(hapax_lemmas).sum()) / sizes[b], 3),
            "one_corpus": int(sum(1 for x in lemmas_b if pd.notna(lemma_section.get(x)))),
            "end_words": int(ends_n[i]), "end_lemmas": int(ends_v[i]),
            "period": "late" if b in late else "early" if b in early else None,
        })  # fmt: skip
    books = pd.DataFrame(rows)

    # (1) the late books' novelty against every split of the early and late books
    pool = books[books.period.notna()]
    vals = pool.novelty.to_numpy()
    is_late = (pool.period == "late").to_numpy()
    n_late = int(is_late.sum())
    observed = float(vals[is_late].mean() - vals[~is_late].mean())
    total = vals.sum()
    diffs = []
    for c in combinations(range(len(vals)), n_late):
        s = vals[list(c)].sum()
        diffs.append(s / n_late - (total - s) / (len(vals) - n_late))
    diffs_a = np.asarray(diffs)
    p_late = float((diffs_a >= observed - 1e-12).mean())
    alpha = float(vc["alpha"])
    late_holds = bool(observed > 0 and p_late <= alpha)
    log(f"novelty: late {vals[is_late].mean():.3f}, early {vals[~is_late].mean():.3f},"
        f" difference {observed:.3f} (exact p {p_late:.4g}, {len(diffs)} splits)")  # fmt: skip

    # (2) known: rare words
    ranked = books.sort_values("hapax_per_k", ascending=False).book_id.tolist()
    known = []
    for osis, at_most in vc["known"]:
        b = BY_OSIS[osis].book_id
        rank = ranked.index(b) + 1 if b in ranked else None
        known.append({"book": osis, "book_id": b, "rank": rank, "at_most": int(at_most),
                      "holds": rank is not None and rank <= int(at_most)})  # fmt: skip
    known_holds = all(k["holds"] for k in known)
    log(f"known: {[(k['book'], k['rank']) for k in known]}")

    out = art / "vocabulary"
    out.mkdir(parents=True, exist_ok=True)
    books.to_parquet(out / "books.parquet", index=False)
    lem.to_parquet(out / "lemmas.parquet", index=False)
    one = lem[lem.counted & lem.section.notna()].section.value_counts()
    meta = {
        "config_hash": config_hash(cfg, "vocabulary", "dating.early", "dating.late"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "words": int(sum(sizes.values())), "lemmas": len(ids),
        "hapax": len(hapax_lemmas), "one_corpus": {str(k): int(v) for k, v in one.items()},
        "heaps_k": round(k_canon, 4), "heaps_b": round(b_canon, 4),
        "late_novelty": round(float(vals[is_late].mean()), 4),
        "early_novelty": round(float(vals[~is_late].mean()), 4),
        "difference": round(observed, 4), "late_p": p_late, "splits": len(diffs),
        "late_holds": late_holds, "known": known, "known_holds": known_holds,
        "orders": reps, "alpha": alpha, "seconds": round(time.perf_counter() - t0, 1),
    }  # fmt: skip
    write_meta(out / "vocabulary.meta.json", meta)
    log(
        f"done: late novelty {'holds' if late_holds else 'not borne out'}, known"
        f" {'holds' if known_holds else 'not borne out'} ({meta['seconds']} s) -> {out}"
    )
    return out
