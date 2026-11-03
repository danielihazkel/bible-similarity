"""`bsim sums`: do the sums add up? (DESIGN.md §16.75).

The text counts and adds. Numbers 1 gives each tribe's men and then all of them (603,550); Ezra 2
lists the families who came back and then "the whole assembly together, 42,360", which the
families do not reach. Where a passage has a parallel, its numbers can differ (David's census:
800,000 in Samuel, 1,100,000 in Chronicles).

- **Counts.** A verse's counts are its number phrases (read as `analysis/chronology.py` reads
  them, with `chronology.numbers` less the `ordinals`) that are not years, months or days and not
  dates, of at least `min_value` (a lone אחד is a word of the list, not a count).
- **Lists** (`lists`). Each list names its items (refs: every count in them) and its total (a ref
  and the place of the total among that verse's counts). (1) Known answers fixed in advance: each
  list adds up, or does not, as `lists` says (the censuses of Num 1, 2, 4 and 26 and Jacob's house
  do; the Levites of Num 3, the temple vessels of Ezra 1 and the returnees of Ezra 2 / Neh 7 do
  not). A check of the reading of the numbers more than a test.
- **Parallels.** Verse pairs from the parallel sequences (§16.7, every sequence), ETCBC's parallel
  passages (§16.34) and Sefaria's verse links, used when the two verses share at least
  `parallels.min_shared` content lemmas besides the number words. Each verse's number phrases (any
  unit, any kind) are aligned in order by unit (count, year, month, day). Two numbers are *one step
  apart* when they differ by a power of ten (40,000 / 4,000) or in one decimal place only
  (18 / 8: a number word added or dropped, as a copyist might). (2) Of the aligned numbers of
  verses in different books that differ (the larger at least `parallels.min_value`), more are one
  step apart than when the second number is drawn from the other verse's book (the same unit,
  `shuffles` times). Pairs inside one book are mostly repeated formulae (Num 7's offerings,
  1 Chr 25's lots), not copies: the first run counted them, and that rule is kept as described
  (`every`). Known
  (`known_parallels`): each pair found with its two numbers, one step apart or not as listed.

Writes `artifacts/sums/`: `lists.parquet` (`key, seq, total_verse, total, total_tok_first,
total_tok_last, sum, n_items, first_verse, last_verse, adds_up, expected, holds`), `items.parquet`
(`key, verse_id, value, tok_first, tok_last`), `parallels.parquet` (`a, b, a_book, b_book, unit,
a_value, b_value, same, one_step, a_tok_first, a_tok_last, b_tok_first, b_tok_last`) and
`sums.meta.json`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.chronology import Phrase, Word, phrases, words_of
from bsim.analysis.stats import empirical_p
from bsim.config import config_hash, resolve_path, write_meta
from bsim.data.refs import RefIndex

Log = Callable[[str], None]


def one_step(x: int, y: int) -> bool:
    """Two different numbers a power of ten apart, or differing in one decimal place only."""
    if x == y or x <= 0 or y <= 0:
        return False
    lo, hi = min(x, y), max(x, y)
    if hi % lo == 0:
        r = hi // lo
        while r % 10 == 0:
            r //= 10
        if r == 1:
            return True
    a, b = str(x), str(y)
    w = max(len(a), len(b))
    return sum(c != d for c, d in zip(a.zfill(w), b.zfill(w), strict=True)) == 1


def is_count(p: Phrase, min_value: int) -> bool:
    return p.unit is None and p.kind != "date" and p.value >= min_value


def label(p: Phrase) -> str:
    return p.unit or "count"


def aligned(pa: list[Phrase], pb: list[Phrase]) -> list[tuple[Phrase, Phrase]]:
    """The number phrases of two verses paired in order by unit (longest matching runs)."""
    sm = SequenceMatcher(a=[label(p) for p in pa], b=[label(p) for p in pb], autojunk=False)
    return [(pa[m.a + k], pb[m.b + k]) for m in sm.get_matching_blocks() for k in range(m.size)]


def parallel_pairs(proc: Path, art: Path, verse_book: dict[int, int]) -> set[tuple[int, int]]:
    """Verse pairs (a < b) from the parallel sequences, ETCBC's parallels and Sefaria's links."""
    out: set[tuple[int, int]] = set()

    def add(a: int, b: int) -> None:
        if a != b and a in verse_book and b in verse_book:
            out.add((min(a, b), max(a, b)))

    seq = art / "sequences" / "verse.parquet"
    if seq.exists():
        for pairs in pd.read_parquet(seq, columns=["pairs"]).pairs:
            for a, b, *_ in json.loads(pairs) if isinstance(pairs, str) else pairs:
                add(int(a), int(b))
    etcbc = proc / "etcbc_links.parquet"
    if etcbc.exists():
        e = pd.read_parquet(etcbc, columns=["src_vid", "tgt_vid"])
        for a, b in zip(e.src_vid, e.tgt_vid, strict=True):
            add(int(a), int(b))
    links = proc / "links.parquet"
    if links.exists():
        lk = pd.read_parquet(links, columns=["src_vid", "tgt_vid", "level"])
        lk = lk[lk.level == "verse"]
        for a, b in zip(lk.src_vid, lk.tgt_vid, strict=True):
            add(int(a), int(b))
    return out


def run_sums(cfg: dict[str, Any], log: Log = print) -> Path:
    sc = cfg["sums"]
    pc = sc["parallels"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    t0 = time.perf_counter()
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter",
                                                               "verse"])  # fmt: skip
    index = RefIndex(verses)
    verse_book = dict(zip(verses.verse_id.astype(int), verses.book_id.astype(int), strict=True))
    words = pd.read_parquet(
        proc / "words.parquet",
        columns=["verse_id", "idx", "lemma", "morph", "display_idx", "surface", "content_lemmas"],
    ).sort_values(["verse_id", "idx"], kind="stable")
    ordinals = {str(x) for x in sc["ordinals"]}
    numbers = {str(k): int(v) for k, v in cfg["chronology"]["numbers"].items()
               if str(k) not in ordinals}  # fmt: skip
    by_verse: dict[int, list[Word]] = {}
    lemmas: dict[int, set[str]] = {}
    for vid, lem, mo, d, sf, cl in zip(words.verse_id, words.lemma, words.morph,
                                       words.display_idx, words.surface, words.content_lemmas,
                                       strict=True):  # fmt: skip
        v = int(vid)
        by_verse.setdefault(v, []).append(words_of(lem, mo, None if pd.isna(d) else int(d), sf))
        lemmas.setdefault(v, set()).update(str(x) for x in cl if str(x) not in numbers)
    cache: dict[int, list[Phrase]] = {}

    def ph(vid: int) -> list[Phrase]:
        if vid not in cache:
            cache[vid] = phrases(by_verse.get(vid, []), numbers)
        return cache[vid]

    def toks(vid: int, p: Phrase) -> tuple[int | None, int | None]:
        ws = by_verse[vid]
        return ws[p.first].tok, ws[p.last].tok

    # (1) lists against their totals
    min_value = int(sc["min_value"])
    lrows, irows = [], []
    for seq, (key, spec) in enumerate(sc["lists"].items()):
        items, total_ref, n, expected = spec
        vids = sorted({v for r in items for s, e in [index.resolve(r)] for v in range(s, e + 1)})
        total_vid = index.resolve(total_ref)[0]
        counts = [p for p in ph(total_vid) if is_count(p, min_value)]
        if len(counts) < int(n):
            raise RuntimeError(f"{key}: {total_ref} has {len(counts)} counts, not {n}")
        tp = counts[int(n) - 1]
        total = 0
        for v in vids:
            for p in ph(v):
                if is_count(p, min_value):
                    tf, tl = toks(v, p)
                    irows.append({"key": key, "verse_id": v, "value": p.value, "tok_first": tf,
                                  "tok_last": tl})  # fmt: skip
                    total += p.value
        adds = total == tp.value
        tf, tl = toks(total_vid, tp)
        lrows.append({
            "key": key, "seq": seq, "total_verse": total_vid, "total": tp.value,
            "total_tok_first": tf, "total_tok_last": tl, "sum": total,
            "n_items": sum(1 for r in irows if r["key"] == key),
            "first_verse": vids[0], "last_verse": vids[-1], "adds_up": adds,
            "expected": bool(expected), "holds": adds == bool(expected),
        })  # fmt: skip
    lists = pd.DataFrame(lrows)
    items = pd.DataFrame(irows)
    for df, cols in ((lists, ("total_tok_first", "total_tok_last")),
                     (items, ("tok_first", "tok_last"))):  # fmt: skip
        for c in cols:
            df[c] = pd.array(df[c], dtype="Int64")
    lists_holds = bool(lists.holds.all())
    log("lists: " + ", ".join(f"{r.key} {r.sum}/{r.total}" for r in lists.itertuples())
        + f"; known {'holds' if lists_holds else 'not borne out'}")  # fmt: skip

    # (2) the numbers of parallel passages
    min_shared, min_big = int(pc["min_shared"]), int(pc["min_value"])
    pairs = parallel_pairs(proc, art, verse_book)
    used = 0
    prows = []
    for a, b in sorted(pairs):
        pa, pb = ph(a), ph(b)
        if not pa or not pb or len(lemmas.get(a, set()) & lemmas.get(b, set())) < min_shared:
            continue
        al = aligned(pa, pb)
        if not al:
            continue
        used += 1
        for x, y in al:
            (af, at), (bf, bt) = toks(a, x), toks(b, y)
            prows.append({
                "a": a, "b": b, "a_book": verse_book[a], "b_book": verse_book[b],
                "unit": label(x), "a_value": x.value, "b_value": y.value,
                "same": x.value == y.value,
                "one_step": None if x.value == y.value else one_step(x.value, y.value),
                "a_tok_first": af, "a_tok_last": at, "b_tok_first": bf, "b_tok_last": bt,
            })  # fmt: skip
    par = pd.DataFrame(prows, columns=["a", "b", "a_book", "b_book", "unit", "a_value", "b_value",
                                       "same", "one_step", "a_tok_first", "a_tok_last",
                                       "b_tok_first", "b_tok_last"])  # fmt: skip
    for c in ("a_tok_first", "a_tok_last", "b_tok_first", "b_tok_last"):
        par[c] = pd.array(par[c], dtype="Int64")
    par["one_step"] = pd.array(par["one_step"], dtype="boolean")

    # the null: each differing pair's second number drawn from its book's numbers of that unit
    values: dict[tuple[int, str], list[int]] = {}
    for v in by_verse:
        for p in ph(v):
            values.setdefault((verse_book[v], label(p)), []).append(p.value)
    pool = {k: np.asarray(v, dtype=np.int64) for k, v in values.items()}
    rng = np.random.default_rng(int(pc["seed"]))
    reps = int(pc["shuffles"])
    step_v = np.vectorize(one_step, otypes=[bool])

    def test(rows: pd.DataFrame) -> dict[str, Any]:
        """The share of differing numbers one step apart, against the second number drawn."""
        diff = rows[(~rows.same) & (np.maximum(rows.a_value, rows.b_value) >= min_big)]
        hits, null_hits, tested = [], np.zeros(reps), 0
        for r in diff.itertuples():
            cand = pool.get((int(r.b_book), str(r.unit)), np.empty(0, dtype=np.int64))
            cand = cand[cand != r.a_value]
            if r.a_value < min_big:
                cand = cand[cand >= min_big]
            if not len(cand):
                continue
            tested += 1
            hits.append(bool(r.one_step))
            null_hits += step_v(int(r.a_value), rng.choice(cand, size=reps))
        if not tested:
            return {"numbers": len(rows), "same": int(rows.same.sum()), "tested": 0,
                    "one_step": 0, "share": None, "expected": None, "p": 1.0}  # fmt: skip
        share, null = float(np.mean(hits)), null_hits / tested
        return {"numbers": len(rows), "same": int(rows.same.sum()), "tested": tested,
                "one_step": int(sum(hits)), "share": round(share, 4),
                "expected": round(float(null.mean()), 4),
                "p": empirical_p(share - 1e-12, null)}  # fmt: skip

    across = test(par[par.a_book != par.b_book])
    every = test(par)  # the first run's rule: pairs inside one book too (described)
    alpha = float(sc["alpha"])
    step_holds = bool(across["tested"] and across["share"] > across["expected"]
                      and across["p"] <= alpha)  # fmt: skip
    log(
        f"parallels: {len(pairs)} pairs, {used} with numbers aligned, {len(par)} numbers,"
        f" {int(par.same.sum())} the same; across books {across}; every pair {every}"
    )

    known = []
    for ra, rb, va, vb, step in sc["known_parallels"]:
        a, b = index.resolve(ra)[0], index.resolve(rb)[0]
        lo, hi, (xa, xb) = min(a, b), max(a, b), ((va, vb) if a < b else (vb, va))
        hit = par[(par.a == lo) & (par.b == hi) & (par.a_value == xa) & (par.b_value == xb)]
        found = len(hit) > 0
        got = bool(hit.one_step.iloc[0]) if found and not bool(hit.same.iloc[0]) else None
        known.append({"a": int(a), "b": int(b), "a_value": int(va), "b_value": int(vb),
                      "found": found, "one_step": got, "expected": bool(step),
                      "holds": found and got == bool(step)})  # fmt: skip
    known_holds = all(k["holds"] for k in known)
    log(f"known parallels: {[(k['a_value'], k['b_value'], k['holds']) for k in known]}")

    out = art / "sums"
    out.mkdir(parents=True, exist_ok=True)
    lists.to_parquet(out / "lists.parquet", index=False)
    items.to_parquet(out / "items.parquet", index=False)
    par.to_parquet(out / "parallels.parquet", index=False)
    meta = {
        "config_hash": config_hash(cfg, "sums", "chronology.numbers"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "lists": len(lists), "lists_adding_up": int(lists.adds_up.sum()),
        "lists_holds": lists_holds, "min_value": min_value,
        "pairs": len(pairs), "pairs_used": used, "numbers": len(par),
        "numbers_same": int(par.same.sum()), "numbers_differ": int((~par.same).sum()),
        "across": across, "every": every, "step_holds": step_holds,
        "known_parallels": known, "known_holds": known_holds,
        "min_shared": min_shared, "min_big": min_big, "shuffles": reps, "alpha": alpha,
        "seconds": round(time.perf_counter() - t0, 1),
    }  # fmt: skip
    write_meta(out / "sums.meta.json", meta)
    log(
        f"done: lists {'hold' if lists_holds else 'not borne out'}, parallels one step"
        f" {'holds' if step_holds else 'not borne out'}, known"
        f" {'holds' if known_holds else 'not borne out'} ({meta['seconds']} s) -> {out}"
    )
    return out
