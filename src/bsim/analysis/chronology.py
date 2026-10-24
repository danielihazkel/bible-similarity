"""`bsim chronology`: the text's own dates, from Adam to the Exile (DESIGN.md §16.70).

The text dates itself. Each father's age at his son's birth runs from Adam to Abram (Gen 5, 11);
stated spans carry on (Gen 15:13, Exod 12:40, 1 Kgs 6:1); Kings gives every reign its length and
dates each king's accession by a year of the king of the other kingdom ("in year twenty of
Jeroboam king of Israel, Asa became king over Judah", 1 Kgs 15:9). The numbers are read from the
words, never typed in.

- **Numbers.** A *number phrase* is a run of number words (`numbers`: the cardinals, the duals
  מאתים / אלפים, the ordinals), side by side or joined by ו, or carried on by ו after שנה (the
  Genesis style: תשע מאות שנה ושלשים שנה, 930). Side by side they add (שלש עשרה), and a hundred
  multiplies the word before it (שלש מאות); a thousand or more multiplies everything before it
  when that is smaller (ששה וארבעים אלף). The dual שנתים is a phrase of two years. A phrase is an
  *age* after בן / בת, a *date* after construct שנת ("in year N of"), else a span; its unit is the
  word after it (or the absolute שנה before it): years, months or days.
- **Dates** (`events`, from Adam as year 0). Each event is the year of another plus (or minus) the
  n-th number phrase of a verse. An event given more than once is computed the first way; the
  others are checks, conflicts when they disagree (Shem's 100 years against "two years after the
  Flood", Gen 11:10; Exod 12:40's 430 years against Gen 15:13's 400). (1) `known`: the Flood,
  Abram's birth and the Exodus at the years Seder Olam gives (1656, 1948, 2448): a check of the
  reading of the numbers.
- **Kings** (`kings`: each king's verses; `syncs`: each synchronism's verse). A reign's length is
  the first span in its verses (days and months: under a year). Each kingdom counts its years
  from the division, under one of two `rules`: *accession* (the year a king comes to the throne is
  his predecessor's; his year 1 is the next) or *non-accession* (that year is his year 1 as
  well). A synchronism ties a year of one kingdom to a year of the other. (2) Taken in the text's
  order, the years between two synchronisms should be the same counted by Judah's reigns and by
  Israel's (within `tolerance`): the share of agreeing intervals, the best of the four pairs of
  rules, against the reign lengths shuffled within each kingdom (`shuffles`, the best pair each
  time). The disagreeing intervals are listed.
- **Digits.** (3) The year numbers of `digits.chapter` (Gen 5: ages at the first son, years after
  and whole lives) end in `digits.ends` (0, 2, 5, 7) more often than the year numbers elsewhere
  (spans and ages of at least `digits.min`, dates left out), the labels permuted (`shuffles`).
  Described: against a uniform last digit, and `digits.compare` (Gen 11).

Writes `artifacts/chronology/`: `events.parquet` (`seq, event, name, from_event, verse_id, value,
sign, year, used, conflict, tok_first, tok_last`), `kings.parquet` (`king, name, kingdom, seq,
verse_id, reign, short, start, am`), `syncs.parquet` (`seq, king, of, verse_id, year, t_judah,
t_israel, agrees`), `numbers.parquet` (Gen 5's year numbers: `verse_id, value, tok_first,
tok_last`) and `chronology.meta.json`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.stats import empirical_p
from bsim.config import config_hash, resolve_path
from bsim.data.refs import RefIndex

Log = Callable[[str], None]
YEAR, AGE_OF = "8141", {"1121", "1323"}  # שנה; בן, בת
UNITS = {"8141": "year", "2320": "month", "3391": "month", "3117": "day"}
DUALS = {"3967", "505"}  # מאתים, אלפים
KINGDOMS = ("judah", "israel")
RULES = ("accession", "non-accession")


@dataclass(frozen=True)
class Word:
    core: str  # the content lemma (Strong's), prefixes stripped
    code: str  # its morphology code
    conj: bool  # carries ו
    tok: int | None  # display index


@dataclass(frozen=True)
class Phrase:
    value: int
    unit: str | None  # year | month | day
    kind: str  # age | date | span
    first: int  # word positions in the verse
    last: int


def words_of(lemma: str, morph: str, tok: int | None) -> Word:
    parts = [(p.split() or [""])[0] for p in str(lemma).split("/")]  # `1121 a`: the homonym dropped
    codes = morph[1:].split("/") if isinstance(morph, str) and morph else []
    k = len(parts) - 1
    return Word(parts[k], codes[k] if k < len(codes) else "", "c" in parts[:k], tok)


def dual(w: Word) -> bool:
    return len(w.code) > 3 and w.code[0] in "NA" and w.code[3] == "d"


def value_of(w: Word, numbers: dict[str, int]) -> int | None:
    if w.core not in numbers or w.code.startswith("Np"):
        return None
    v = numbers[w.core]
    return v * 2 if w.core in DUALS and dual(w) else v


def phrases(ws: list[Word], numbers: dict[str, int]) -> list[Phrase]:
    """The number phrases of one verse, in order."""
    out: list[Phrase] = []
    n, i = len(ws), 0
    val = [value_of(w, numbers) for w in ws]
    while i < n:
        if ws[i].core == YEAR and dual(ws[i]) and ws[i].code.endswith("a"):  # שנתים, not שני חיי
            out.append(Phrase(2, "year", kind_of(ws, i), i, i))
            i += 1
            continue
        if val[i] is None:
            i += 1
            continue
        total, group, last, j = 0, int(val[i]), i, i
        while True:
            k = j + 1
            if k < n and val[k] is not None:
                j = k
            elif k + 1 < n and ws[k].core == YEAR and val[k + 1] is not None and ws[k + 1].conj:
                j = k + 1
            else:
                break
            v = int(val[j])
            if j == last + 1 and not ws[j].conj:  # side by side
                if v == 100:
                    group *= v
                elif v >= 1000:
                    if total + group < v:
                        group, total = (total + group) * v, 0
                    else:
                        group *= v
                else:
                    group += v
            else:
                total, group = total + group, v
            last = j
        unit = None
        if last + 1 < n and ws[last + 1].core in UNITS:
            unit = UNITS[ws[last + 1].core]
        elif i > 0 and ws[i - 1].core == YEAR:
            unit = "year"
        out.append(Phrase(total + group, unit, kind_of(ws, i), i, last))
        i = last + 1
    return out


def kind_of(ws: list[Word], i: int) -> str:
    if i == 0:
        return "span"
    b = ws[i - 1]
    if b.core in AGE_OF:
        return "age"
    if b.core == YEAR and b.code.endswith("c"):
        return "date"
    return "span"


def reign_of(ws: list[Word], ph: list[Phrase]) -> tuple[int, bool] | None:
    """A reign's length in years and whether it was under a year: the first span with a unit."""
    for p in ph:
        if p.kind == "span" and p.unit is not None:
            return (0, True) if p.unit != "year" else (p.value, False)
    if any(w.core == "3391" for w in ws):  # ירח ימים: a month
        return 0, True
    return None


def date_of(ph: list[Phrase]) -> int | None:
    """The year of a synchronism: the first phrase after בשנת."""
    return next((p.value for p in ph if p.kind == "date"), None)


def starts(reign: np.ndarray, short: np.ndarray, rule: str) -> tuple[np.ndarray, np.ndarray]:
    """Each king's year 1 and the year he came to the throne, counted in his kingdom from the
    division (its first accession is year 0)."""
    n = len(reign)
    first = np.zeros(n, dtype=np.int64)
    acc = np.zeros(n, dtype=np.int64)
    post = rule == "accession"
    a = 1 if post else 0
    for i in range(n):
        first[i] = a
        acc[i] = a - 1 if post else a
        a += 0 if short[i] else (int(reign[i]) if post else int(reign[i]) - 1)
    return first, acc


def sync_times(
    reigns: dict[str, tuple[np.ndarray, np.ndarray]],
    rules: dict[str, str],
    syncs: list[tuple[str, int, str, int, int]],
) -> tuple[np.ndarray, np.ndarray]:
    """For each synchronism (kingdom of the new king, his position, the other kingdom, the other
    king's position, year N): its year in Judah's count and in Israel's."""
    st = {k: starts(*reigns[k], rules[k]) for k in KINGDOMS}
    tj = np.empty(len(syncs), dtype=np.int64)
    ti = np.empty(len(syncs), dtype=np.int64)
    for s, (kk, ki, ok, oi, year) in enumerate(syncs):
        mine = st[kk][1][ki]
        other = st[ok][0][oi] + year - 1
        if kk == "judah":
            tj[s], ti[s] = mine, other
        else:
            tj[s], ti[s] = other, mine
    return tj, ti


def agreeing(tj: np.ndarray, ti: np.ndarray, tol: int) -> np.ndarray:
    """Per interval between consecutive synchronisms: do the two counts give the same years?"""
    off = tj - ti
    return np.abs(np.diff(off)) <= tol


def best_rules(
    reigns: dict[str, tuple[np.ndarray, np.ndarray]], syncs: list, tol: int
) -> tuple[dict[str, str], dict[str, int]]:
    """The pair of rules under which most intervals agree (ties: the first), and every pair's
    count."""
    counts: dict[str, int] = {}
    best, best_n = None, -1
    for rj, ri in product(RULES, RULES):
        rules = {"judah": rj, "israel": ri}
        n = int(agreeing(*sync_times(reigns, rules, syncs), tol).sum())
        counts[f"{rj}/{ri}"] = n
        if n > best_n:
            best, best_n = rules, n
    assert best is not None
    return best, counts


def label_share_p(
    hit: np.ndarray, is_a: np.ndarray, reps: int, rng: np.random.Generator
) -> tuple[float, float, float]:
    """Share of hits among `is_a`, among the rest, and the one-sided p of the first with the
    labels permuted."""

    def share(lab: np.ndarray) -> float:
        return float(hit[lab].mean())

    obs = share(is_a)
    null = np.array([share(rng.permutation(is_a)) for _ in range(reps)])
    return obs, float(hit[~is_a].mean()), empirical_p(obs - 1e-12, null)


def run_chronology(cfg: dict[str, Any], log: Log = print) -> Path:
    from scipy.stats import binomtest

    cc = cfg["chronology"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    t0 = time.perf_counter()
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter",
                                                               "verse"])  # fmt: skip
    index = RefIndex(verses)
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "idx", "lemma", "morph", "display_idx"]
    )
    words = words.sort_values(["verse_id", "idx"], kind="stable")
    numbers = {str(k): int(v) for k, v in cc["numbers"].items()}
    by_verse: dict[int, list[Word]] = {}
    for vid, lem, mo, d in zip(words.verse_id, words.lemma, words.morph, words.display_idx,
                               strict=True):  # fmt: skip
        by_verse.setdefault(int(vid), []).append(
            words_of(lem, mo, None if pd.isna(d) else int(d))
        )
    cache: dict[int, list[Phrase]] = {}

    def ph(vid: int) -> list[Phrase]:
        if vid not in cache:
            cache[vid] = phrases(by_verse.get(vid, []), numbers)
        return cache[vid]

    def tokens(vid: int, p: Phrase) -> tuple[int | None, int | None]:
        ws = by_verse[vid]
        return ws[p.first].tok, ws[p.last].tok

    # (1) dates from Adam
    names = {str(k): v for k, v in cc["names"].items()}
    year: dict[str, int] = {}
    rows = []
    for seq, ev in enumerate(cc["events"]):
        eid, frm, ref = ev[0], ev[1], ev[2]
        n, sign = (int(ev[3]) if len(ev) > 3 else 0), (int(ev[4]) if len(ev) > 4 else 1)
        vid = value = tf = tl = None
        if frm is None:
            y = 0
        else:
            vid = index.resolve(ref)[0]
            p = ph(vid)[n - 1]
            value, (tf, tl) = p.value, tokens(vid, p)
            y = year[frm] + sign * value
        used = eid not in year
        if used:
            year[eid] = y
        person = eid.split(".")[0]
        rows.append({
            "seq": seq, "event": eid, "name": names.get(person), "from_event": frm,
            "verse_id": vid, "value": value, "sign": sign, "year": y, "used": used,
            "conflict": (not used) and y != year[eid], "tok_first": tf, "tok_last": tl,
        })  # fmt: skip
    events = pd.DataFrame(rows)
    for c in ("verse_id", "value", "tok_first", "tok_last"):
        events[c] = pd.array(events[c], dtype="Int64")
    known = [{"event": e, "year": year.get(e), "expected": int(y), "holds": year.get(e) == int(y)}
             for e, y in cc["known"].items()]  # fmt: skip
    known_holds = all(k["holds"] for k in known)
    log("dates: " + ", ".join(f"{k['event']} {k['year']} ({k['expected']})" for k in known)
        + f"; {int(events.conflict.sum())} conflicts")  # fmt: skip

    # (2) kings and synchronisms
    krows = []
    pos: dict[str, tuple[str, int]] = {}
    counts = {k: 0 for k in KINGDOMS}
    for king, name, kingdom, ref in cc["kings"]:
        s, e = index.resolve(ref)
        ws = [w for v in range(s, e + 1) for w in by_verse.get(v, [])]
        r = reign_of(ws, [p for v in range(s, e + 1) for p in ph(v)])
        if r is None:
            raise RuntimeError(f"no reign length for {king} in {ref}")
        pos[king] = (kingdom, counts[kingdom])
        counts[kingdom] += 1
        krows.append({"king": king, "name": name, "kingdom": kingdom, "seq": pos[king][1],
                      "verse_id": s, "reign": r[0], "short": r[1]})  # fmt: skip
    kings = pd.DataFrame(krows)
    reigns = {
        k: (kings[kings.kingdom == k].reign.to_numpy(), kings[kings.kingdom == k].short.to_numpy())
        for k in KINGDOMS
    }
    srows = []
    for king, of, ref in cc["syncs"]:
        vid = index.resolve(ref)[0]
        y = date_of(ph(vid))
        if y is None:
            raise RuntimeError(f"no year for the synchronism of {king} in {ref}")
        srows.append((vid, king, of, y))
    srows.sort()
    syncs = [(*pos[k], *pos[o], y) for _, k, o, y in srows]
    tol = int(cc["tolerance"])
    rules, rule_counts = best_rules(reigns, syncs, tol)
    tj, ti = sync_times(reigns, rules, syncs)
    agree = agreeing(tj, ti, tol)
    observed = int(agree.sum())
    rng = np.random.default_rng(cc["seed"])
    reps = int(cc["shuffles"])
    null = np.empty(reps)
    for r in range(reps):
        sh = {}
        for k in KINGDOMS:
            perm = rng.permutation(len(reigns[k][0]))
            sh[k] = (reigns[k][0][perm], reigns[k][1][perm])
        null[r] = max(int(agreeing(*sync_times(sh, {"judah": a, "israel": b}, syncs), tol).sum())
                      for a, b in product(RULES, RULES))  # fmt: skip
    p_sync = empirical_p(observed, null)
    alpha = float(cc["alpha"])
    sync_holds = bool(observed > null.mean() and p_sync <= alpha)
    syncs_df = pd.DataFrame({
        "seq": range(len(srows)), "king": [k for _, k, _, _ in srows],
        "of": [o for _, _, o, _ in srows], "verse_id": [v for v, *_ in srows],
        "year": [y for *_, y in srows], "t_judah": tj, "t_israel": ti,
        "agrees": pd.array([None, *agree.tolist()], dtype="boolean"),
    })  # fmt: skip
    log(f"synchronisms: {observed} of {len(agree)} intervals agree under {rules['judah']} /"
        f" {rules['israel']}, against {null.mean():.1f} shuffled (p {p_sync:.4g})")  # fmt: skip

    # the reigns on the years from Adam
    div = year[cc["division"]]
    kings["start"] = 0
    for k in KINGDOMS:
        first, _ = starts(*reigns[k], rules[k])
        kings.loc[kings.kingdom == k, "start"] = first
    kings["am"] = div + kings.start
    ends = {}
    for k in KINGDOMS:
        last = kings[kings.kingdom == k].iloc[-1]
        ends[k] = int(last.am + (0 if last.short else last.reign - 1))

    # (3) the last digits of Gen 5's year numbers
    dc = cc["digits"]
    s5, e5 = index.resolve(dc["chapter"])
    sc, ec = index.resolve(dc["compare"])
    vals, vid_of, toks = [], [], []
    for vid in sorted(by_verse):
        for p in ph(vid):
            if p.unit == "year" and p.kind != "date" and p.value >= int(dc["min"]):
                vals.append(p.value)
                vid_of.append(vid)
                toks.append(tokens(vid, p))
    vals_a, vid_a = np.array(vals), np.array(vid_of)
    hit = np.isin(vals_a % 10, [int(x) for x in dc["ends"]])
    in5 = (vid_a >= s5) & (vid_a <= e5)
    in11 = (vid_a >= sc) & (vid_a <= ec)
    share5, share_rest, p_dig = label_share_p(hit, in5, reps, rng)
    uniform = len(dc["ends"]) / 10
    dig_holds = bool(share5 > share_rest and p_dig <= alpha)
    digits = {
        "n": int(in5.sum()), "hits": int(hit[in5].sum()), "share": round(share5, 4),
        "rest_n": int((~in5).sum()), "rest_share": round(share_rest, 4), "p": p_dig,
        "uniform": uniform,
        "uniform_p": float(binomtest(int(hit[in5].sum()), int(in5.sum()), uniform,
                                     alternative="greater").pvalue),
        "compare_n": int(in11.sum()), "compare_share": round(float(hit[in11].mean()), 4)
        if in11.any() else None,
        "by_digit": {str(d): int((vals_a[in5] % 10 == d).sum()) for d in range(10)},
        "rest_by_digit": {str(d): int((vals_a[~in5] % 10 == d).sum()) for d in range(10)},
        "holds": dig_holds,
    }  # fmt: skip
    numbers_df = pd.DataFrame({
        "verse_id": vid_a[in5], "value": vals_a[in5],
        "tok_first": pd.array([t[0] for t, m in zip(toks, in5, strict=True) if m], dtype="Int64"),
        "tok_last": pd.array([t[1] for t, m in zip(toks, in5, strict=True) if m], dtype="Int64"),
    })  # fmt: skip
    log(f"digits: {digits['hits']} of {digits['n']} in {dc['chapter']} end in {dc['ends']}"
        f" ({share5:.2f} against {share_rest:.2f}, p {p_dig:.4g})")  # fmt: skip

    out = art / "chronology"
    out.mkdir(parents=True, exist_ok=True)
    events.to_parquet(out / "events.parquet", index=False)
    kings.to_parquet(out / "kings.parquet", index=False)
    syncs_df.to_parquet(out / "syncs.parquet", index=False)
    numbers_df.to_parquet(out / "numbers.parquet", index=False)
    tradition = {k: int(v) for k, v in cc["tradition"].items()}
    meta = {
        "config_hash": config_hash(cfg, "chronology"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "events": len(events), "conflicts": int(events.conflict.sum()),
        "known": known, "known_holds": known_holds,
        "kings": {k: int(c) for k, c in counts.items()}, "syncs": len(srows),
        "intervals": int(len(agree)), "agree": observed, "rules": rules,
        "rule_counts": rule_counts, "tolerance": tol, "shuffles": reps, "alpha": alpha,
        "expected": round(float(null.mean()), 2), "p": p_sync, "holds": sync_holds,
        "absolute": int((np.abs(tj - ti) <= tol).sum()),
        "division": div, "ends": ends, "tradition": tradition,
        "digits": digits, "digits_chapter": dc["chapter"], "digits_compare": dc["compare"],
        "digits_ends": [int(x) for x in dc["ends"]], "digits_min": int(dc["min"]),
        "seconds": round(time.perf_counter() - t0, 1),
    }  # fmt: skip
    (out / "chronology.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                              "utf-8")  # fmt: skip
    log(f"done: known {'holds' if known_holds else 'not borne out'}, synchronisms"
        f" {'hold' if sync_holds else 'not borne out'}, digits"
        f" {'hold' if dig_holds else 'not borne out'} ({meta['seconds']} s) -> {out}")  # fmt: skip
    return out / "events.parquet"
