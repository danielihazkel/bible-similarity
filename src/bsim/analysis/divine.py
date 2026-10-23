"""`bsim divine`: the divine names across the canon (DESIGN.md §16.65).

Which name of God a passage uses — יהוה, אלהים, אדני, אל, אלוה, שדי, יה, עליון, (יהוה) צבאות —
is counted per chapter from the OSHB lemmas (`divine.names`). A chapter's *mix* is the share of
the first name of `divine.measure` among the two (יהוה among יהוה and אלהים).

- **Splits.** Each book with enough names and chapters is cut in three parts of consecutive
  chapters (each at least `min_segment` long) where the mix changes most: the cut that maximizes
  the binomial log-likelihood of the three parts' rates over the whole book's one rate. Its gain
  is set against the same search on the book's chapters shuffled (`shuffles`), giving p, and BH q
  over the books.
- **Check 1, the Elohistic Psalter.** Psalms' best three-part split is found without its bounds:
  the middle part starts and ends within `tolerance` psalms of Psalms 42 and 83, and its gain
  beats the shuffles at `alpha`.
- **Check 2, the doubled psalms.** For each pair of `doubled` passages (the side inside Psalms
  42–83 first) the words are aligned (Needleman–Wunsch of `bsim diffs`), and every aligned place
  where one side has יהוה and the other אלהים is counted by direction. Across the pairs the
  Elohistic side has אלהים for the other's יהוה more often than the reverse (one-sided sign
  test at `alpha`).

Writes `artifacts/divine/`: `chapters.parquet` (`unit_id, book_id, chapter, words`, a count per
name, `share`, `part`), `books.parquet` (`book_id, chapters, words`, a count per name, `share`,
`split`, `cut1, cut2` (first chapter of the second and third parts), `share1..3, gain, p, q`),
`pairs.parquet` (each aligned place with a name on either side: `pair, e_vid, e_idx, e_word,
e_name, y_vid, y_idx, y_word, y_name, kind`), `words.parquet` (every word that is a name: `verse_id,
idx, book_id, name`) and `divine.meta.json`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from math import comb
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.diffs import Word, align_words, verse_words
from bsim.analysis.stats import bh_q, empirical_p
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS
from bsim.data.refs import RefIndex

Log = Callable[[str], None]


def name_of_lemma(names: dict[str, list[str]]) -> dict[str, str]:
    """Each Strong's key -> the name it counts for."""
    return {str(k).replace(" ", ""): n for n, ks in names.items() for k in ks}


def word_name(lemma: str, lookup: dict[str, str]) -> str | None:
    """The name a word counts for: the first of its lemma's parts that is one."""
    for part in str(lemma).split("/"):
        n = lookup.get(part.replace(" ", ""))
        if n is not None:
            return n
    return None


def _ll(k: np.ndarray, n: np.ndarray) -> np.ndarray:
    """Binomial log-likelihood of k successes in n at their own rate (0 for n = 0)."""
    k, n = np.asarray(k, dtype=float), np.asarray(n, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = np.where(n > 0, k / n, 0.0)
        a = np.where(k > 0, k * np.log(np.where(p > 0, p, 1)), 0.0)
        b = np.where(n - k > 0, (n - k) * np.log(np.where(p < 1, 1 - p, 1)), 0.0)
    return a + b


def best_split(k: np.ndarray, n: np.ndarray, min_seg: int) -> tuple[int, int, float]:
    """The cut of a sequence in three parts of at least `min_seg` items where the rate changes
    most: (start of the second part, start of the third, the log-likelihood gain over one rate).
    Every pair of cuts is scored at once from cumulative sums."""
    m = len(k)
    ck = np.concatenate([[0.0], np.cumsum(k, dtype=float)])
    cn = np.concatenate([[0.0], np.cumsum(n, dtype=float)])
    i = np.arange(min_seg, m - 2 * min_seg + 1)[:, None]
    j = np.arange(2 * min_seg, m - min_seg + 1)[None, :]
    ok = j - i >= min_seg
    total = (
        _ll(ck[i], cn[i]) + _ll(ck[j] - ck[i], cn[j] - cn[i]) + _ll(ck[m] - ck[j], cn[m] - cn[j])
    )
    total = np.where(ok, total, -np.inf)
    a, b = np.unravel_index(int(np.argmax(total)), total.shape)
    gain = float(total[a, b] - _ll(ck[m], cn[m]))
    return int(i[a, 0]), int(j[0, b]), max(0.0, gain)


def split_p(
    k: np.ndarray, n: np.ndarray, min_seg: int, gain: float, reps: int, rng: np.random.Generator
) -> float:
    """The split's gain against the best split of the same chapters in shuffled orders."""
    null = np.empty(reps)
    for r in range(reps):
        perm = rng.permutation(len(k))
        null[r] = best_split(k[perm], n[perm], min_seg)[2]
    return empirical_p(gain - 1e-9, null)


def sign_test(wins: int, n: int) -> float:
    """One-sided binomial p of at least `wins` of `n` at even odds."""
    if n == 0:
        return 1.0
    return float(sum(comb(n, x) for x in range(wins, n + 1)) / 2**n)


def aligned_names(
    e: list[Word], y: list[Word], e_names: list[str | None], y_names: list[str | None],
    score: dict[str, float],
) -> list[tuple[int | None, int | None]]:  # fmt: skip
    """Positions (in each side's word list) aligned with a name on either side."""
    ops = align_words(e, y, score["match"], score["mismatch"], score["gap"])
    return [
        (o.a, o.b)
        for o in ops
        if (o.a is not None and e_names[o.a]) or (o.b is not None and y_names[o.b])
    ]


def elohistic_check(books: pd.DataFrame, el: dict[str, Any], alpha: float) -> dict[str, Any]:
    """Check 1: the named book's best three-part split puts its middle part at the named
    chapters (each end within `tolerance`) and beats its shuffles."""
    ps = next(b.book_id for b in BOOKS if b.sefaria == el["book"])
    out: dict[str, Any] = {"book_id": int(ps), "named": [el["first"], el["last"]],
                           "tolerance": el["tolerance"], "first": None, "last": None,
                           "shares": None, "gain": None, "p": None, "found": None,
                           "holds": False}  # fmt: skip
    rows = books[(books.book_id == ps) & books.split]
    if rows.empty:  # the book is not in the corpus, or too small to split
        return out
    r = rows.iloc[0]
    first, last = int(r.cut1), int(r.cut2) - 1
    found = (
        abs(first - el["first"]) <= el["tolerance"] and abs(last - el["last"]) <= el["tolerance"]
    )
    out.update(first=first, last=last, shares=[float(r.share1), float(r.share2), float(r.share3)],
               gain=float(r.gain), p=float(r.p), found=bool(found),
               holds=bool(found and float(r.p) <= alpha))  # fmt: skip
    return out


def doubled_check(
    verses: pd.DataFrame,
    words: pd.DataFrame,
    doubled: list[dict[str, str]],
    measure: tuple[str, str],
    score: dict[str, float],
    alpha: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Check 2: each pair of passages aligned word by word; every aligned place with a name on
    either side, by direction. `e_ward`: the first side (inside the named part) has the second
    name where the other has the first. A passage the corpus lacks is listed as missing."""
    num, den = measure
    index = RefIndex(verses)
    by_verse = verse_words(words)
    # a word that is no name holds NaN in the frame: keep only the names (NaN is truthy)
    name_at = {
        (int(v), int(i)): n
        for v, i, n in zip(words.verse_id, words.idx, words.name, strict=True)
        if isinstance(n, str)
    }
    rows, meta, missing = [], [], []
    for p_i, pair in enumerate(doubled):
        sides = []
        for ref in (pair["e"], pair["y"]):
            try:
                s, e = index.resolve(ref)
            except (ValueError, KeyError):
                missing.append(ref)
                break
            sides.append([(v, w) for v in range(s, e + 1) for w in by_verse.get(v, [])])
        if len(sides) < 2:
            continue
        ew, yw = sides
        e_names = [name_at.get((v, w.idx)) for v, w in ew]
        y_names = [name_at.get((v, w.idx)) for v, w in yw]
        counts = {"e_ward": 0, "y_ward": 0, "same": 0, "other": 0}
        for a, b in aligned_names([w for _, w in ew], [w for _, w in yw], e_names, y_names, score):
            en = e_names[a] if a is not None else None
            yn = y_names[b] if b is not None else None
            if en == den and yn == num:
                kind = "e_ward"
            elif en == num and yn == den:
                kind = "y_ward"
            elif en is not None and en == yn:
                kind = "same"
            else:
                kind = "other"
            counts[kind] += 1
            ea = ew[a] if a is not None else None
            yb = yw[b] if b is not None else None
            rows.append((
                p_i, ea[0] if ea else None, ea[1].idx if ea else None, ea[1].text if ea else None,
                en, yb[0] if yb else None, yb[1].idx if yb else None, yb[1].text if yb else None,
                yn, kind,
            ))  # fmt: skip
        meta.append({"pair": p_i, "e": pair["e"], "y": pair["y"], **counts})
    pairs = pd.DataFrame(
        rows,
        columns=[
            "pair",
            "e_vid",
            "e_idx",
            "e_word",
            "e_name",
            "y_vid",
            "y_idx",
            "y_word",
            "y_name",
            "kind",
        ],  # fmt: skip
    ).astype({"e_vid": "Int64", "e_idx": "Int64", "y_vid": "Int64", "y_idx": "Int64"})
    e_ward = sum(m["e_ward"] for m in meta)
    y_ward = sum(m["y_ward"] for m in meta)
    p = sign_test(e_ward, e_ward + y_ward)
    check = {"pairs": meta, "missing": missing, "e_ward": e_ward, "y_ward": y_ward, "p": p,
             "holds": bool(meta) and e_ward > y_ward and p <= alpha}  # fmt: skip
    return pairs, check


def run_divine(cfg: dict[str, Any], log: Log = print) -> Path:
    dc = cfg["divine"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "divine"
    t0 = time.perf_counter()
    rng = np.random.default_rng(dc["seed"])
    names = list(dc["names"])
    num, den = dc["measure"]
    lookup = name_of_lemma(dc["names"])
    min_seg, reps, alpha = int(dc["min_segment"]), int(dc["shuffles"]), float(dc["alpha"])

    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "verse"]
    ).sort_values("verse_id")
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "idx", "surface", "lemma", "content_lemmas"]
    )
    words["name"] = [word_name(lem, lookup) for lem in words.lemma]
    words = words.merge(verses[["verse_id", "book_id", "chapter"]], on="verse_id")

    # per chapter
    chap = (
        words.groupby(["book_id", "chapter"]).size().rename("words").reset_index()
        .merge(
            words[words.name.notna()].pivot_table(
                index=["book_id", "chapter"], columns="name", values="idx", aggfunc="count"
            ).reset_index(),
            on=["book_id", "chapter"], how="left",
        )
    )  # fmt: skip
    for n in names:
        chap[n] = chap[n].fillna(0).astype(int) if n in chap else 0
    chap["unit_id"] = [f"c:{b}:{c}" for b, c in zip(chap.book_id, chap.chapter, strict=True)]
    both = chap[num] + chap[den]
    chap["share"] = np.where(both > 0, chap[num] / both.where(both > 0, 1), np.nan)
    chap = chap.sort_values(["book_id", "chapter"]).reset_index(drop=True)
    chap["part"] = pd.array([pd.NA] * len(chap), dtype="Int64")

    # per book: the best three-part split, against shuffled chapter orders
    book_rows = []
    for b, g in chap.groupby("book_id", sort=True):
        k, n = g[num].to_numpy(), (g[num] + g[den]).to_numpy()
        row: dict[str, Any] = {"book_id": int(b), "chapters": len(g), "words": int(g.words.sum()),
                               **{x: int(g[x].sum()) for x in names}}  # fmt: skip
        row["share"] = float(k.sum() / n.sum()) if n.sum() else np.nan
        row.update(split=False, cut1=None, cut2=None, share1=np.nan, share2=np.nan,
                   share3=np.nan, gain=np.nan, p=np.nan)  # fmt: skip
        if n.sum() >= dc["min_names"] and len(g) >= max(dc["min_chapters"], 3 * min_seg):
            i, j, gain = best_split(k, n, min_seg)
            chapters = g.chapter.to_numpy()
            parts = [(0, i), (i, j), (j, len(g))]
            shares = [k[s:e].sum() / n[s:e].sum() if n[s:e].sum() else np.nan for s, e in parts]
            row.update(split=True, cut1=int(chapters[i]), cut2=int(chapters[j]), gain=gain,
                       share1=shares[0], share2=shares[1], share3=shares[2],
                       p=split_p(k, n, min_seg, gain, reps, rng))  # fmt: skip
            chap.loc[g.index, "part"] = np.repeat([1, 2, 3], [i, j - i, len(g) - j])
        book_rows.append(row)
    books = pd.DataFrame(book_rows)
    books["q"] = bh_q(books.p.to_numpy(dtype=float))
    books = books.astype({"cut1": "Int64", "cut2": "Int64"})
    log(f"{int(books.split.sum())} books split; {(books.q <= alpha).sum()} at q ≤ {alpha}")

    check1 = elohistic_check(books, dc["elohistic"], alpha)
    if check1["found"] is not None:
        log(
            f"Psalms: middle part {check1['first']}–{check1['last']} (named"
            f" {check1['named'][0]}–{check1['named'][1]}), shares"
            f" {', '.join(f'{s:.2f}' for s in check1['shares'])}, p {check1['p']:.3f}"
        )
    score = {k: float(cfg["diffs"][k]) for k in ("match", "mismatch", "gap")}
    pairs, check2 = doubled_check(verses, words, dc["doubled"], (num, den), score, alpha)
    log(
        f"doubled psalms: {den} for {num} {check2['e_ward']}, the reverse {check2['y_ward']}"
        f" (p {check2['p']:.3g}); {len(check2['missing'])} passages missing"
    )

    out.mkdir(parents=True, exist_ok=True)
    cols = ["unit_id", "book_id", "chapter", "words", *names, "share", "part"]
    chap[cols].to_parquet(out / "chapters.parquet")
    books[["book_id", "chapters", "words", *names, "share", "split", "cut1", "cut2", "share1",
           "share2", "share3", "gain", "p", "q"]].to_parquet(out / "books.parquet")  # fmt: skip
    pairs.to_parquet(out / "pairs.parquet")
    named = words[words.name.notna()]
    named[["verse_id", "idx", "book_id", "name"]].sort_values(["verse_id", "idx"]).to_parquet(
        out / "words.parquet", index=False
    )
    totals = {n: int(chap[n].sum()) for n in names}
    meta = {
        "config_hash": config_hash(cfg, "divine", "diffs"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "names": names,
        "measure": [num, den],
        "min_segment": min_seg,
        "shuffles": reps,
        "alpha": alpha,
        "totals": totals,
        "books_split": int(books.split.sum()),
        "books_q": int((books.q <= alpha).sum()),
        "elohistic": check1,
        "doubled": check2,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "divine.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
    log(
        f"done: {', '.join(f'{n} {c:,}' for n, c in totals.items())}; Elohistic Psalter"
        f" {'holds' if check1['holds'] else 'not borne out'}, doubled psalms"
        f" {'holds' if check2['holds'] else 'not borne out'} ({meta['seconds']} s) -> {out}"
    )
    return out
