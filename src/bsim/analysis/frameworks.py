"""`bsim frameworks`: the narrative frameworks of Judges and Kings (DESIGN.md §16.71).

Judges tells its deliverances in one frame: Israel did evil in the eyes of the LORD, he sold them
into the hand of an enemy for so many years, they cried out, he raised them a deliverer, and the
land was quiet so many years (Judg 3:7-11, Othniel). Kings frames every reign alike: the
accession, the age and the mother (in Judah), the verdict (he did evil, or right, in the eyes of
the LORD), the high places, the sins of Jeroboam, the burial.

- **Judges.** Each episode (`episodes`, the major judges in book order) is searched for the
  cycle's `slots`: a slot is present when one verse of its window (the first `open` verses, or
  the whole episode) holds every lemma of one of its alternatives, and for `years` a span of
  years (read as `bsim chronology` reads numbers). (1) Claim fixed in advance: an episode's share
  of the slots falls through the book, Spearman's rho with its order below 0, against every order
  of the episodes (exact). Known: `known_complete` holds every slot, `known_missing` lacks those.
- **Kings.** The kings and their regnal formulas are `chronology.kings`; a king's section runs to
  the next formula. His verdict is the first verse within `verdict_within` of the formula (and in
  his section) holding עשה, עין and רע (bad) or ישר (good; with לא, bad). (2) Claim fixed in
  advance: the verdicts' wording (the lemmas of the verdict and the next verses, `verdict_span`,
  less `stop`; binary, cosine) is closer within a kingdom than across, against the kingdoms'
  labels permuted (`shuffles`). Known: `known_verdicts`. Described: the `regnal` slots each
  account holds (age, mother, high places, the sins of Jeroboam, burial), by kingdom.

Writes `artifacts/frameworks/`: `episodes.parquet` (`episode, judge, seq, first_vid, last_vid,
n_slots, share`), `slots.parquet` (`episode, slot, verse_id`), `kings.parquet` (`king, name,
kingdom, seq, first_vid, last_vid, verdict, verdict_vid` and a verse id per `regnal` slot) and
`frameworks.meta.json`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from itertools import permutations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from bsim.analysis.chronology import Phrase, Word, phrases, words_of
from bsim.analysis.stats import empirical_p
from bsim.config import config_hash, resolve_path
from bsim.data.refs import RefIndex

Log = Callable[[str], None]


def find_slot(
    vids: range | list[int],
    lemmas: dict[int, set[str]],
    alternatives: list[list[str]],
    years: Callable[[int], bool] | None = None,
) -> int | None:
    """The first verse holding every lemma of one alternative (and a span of years, with
    `years`)."""
    for v in vids:
        have = lemmas.get(v, set())
        if any(set(alt) <= have for alt in alternatives) and (years is None or years(v)):
            return v
    return None


def ordered_rho(shares: list[float]) -> tuple[float, float]:
    """Spearman's rho of the shares with their order, and the share of all orders whose rho is
    as low or lower (exact; 1 when every share is equal)."""
    if len(set(shares)) < 2:
        return 0.0, 1.0
    pos = np.arange(len(shares))
    obs = float(spearmanr(pos, shares).statistic)
    null = np.array([spearmanr(pos, p).statistic for p in permutations(shares)])
    return obs, float((null <= obs + 1e-12).mean())


def cosine_sets(sets: list[set[str]]) -> np.ndarray:
    """Pairwise cosine of binary lemma sets."""
    vocab = {w: i for i, w in enumerate(sorted(set().union(*sets)))} if sets else {}
    x = np.zeros((len(sets), len(vocab)))
    for i, s in enumerate(sets):
        x[i, [vocab[w] for w in s]] = 1
    norm = np.linalg.norm(x, axis=1)
    norm[norm == 0] = 1
    x /= norm[:, None]
    return x @ x.T


def within_between(sim: np.ndarray, labels: np.ndarray) -> float:
    """Mean similarity of pairs within a label minus pairs across."""
    iu = np.triu_indices(len(labels), 1)
    same = labels[iu[0]] == labels[iu[1]]
    vals = sim[iu]
    if not same.any() or same.all():
        return 0.0
    return float(vals[same].mean() - vals[~same].mean())


def verdict_of(ws: list[Word], vc: dict[str, str]) -> str | None:
    """bad (הרע), good (הישר) or, with לא right before עשה, bad (ולא עשה הישר, 2 Kgs 16:2); a
    לא elsewhere in the verse (לא סר ממנו) is not a negation of the verdict."""
    cores = [w.core for w in ws]
    if vc["verb"] not in cores or vc["eyes"] not in cores:
        return None
    if vc["bad"] in cores:
        return "bad"
    if vc["good"] in cores:
        negated = any(c == vc["verb"] and i > 0 and cores[i - 1] == vc["negation"]
                      for i, c in enumerate(cores))  # fmt: skip
        return "bad" if negated else "good"
    return None


def run_frameworks(cfg: dict[str, Any], log: Log = print) -> Path:
    fc = cfg["frameworks"]
    numbers = {str(k): int(v) for k, v in cfg["chronology"]["numbers"].items()}
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    t0 = time.perf_counter()
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter",
                                                               "verse"])  # fmt: skip
    index = RefIndex(verses)
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "idx", "lemma", "morph", "display_idx"]
    ).sort_values(["verse_id", "idx"], kind="stable")
    by_verse: dict[int, list[Word]] = {}
    for vid, lem, mo in zip(words.verse_id, words.lemma, words.morph, strict=True):
        by_verse.setdefault(int(vid), []).append(words_of(lem, mo, None))
    lemmas = {v: {w.core for w in ws} for v, ws in by_verse.items()}
    cache: dict[int, list[Phrase]] = {}

    def ph(v: int) -> list[Phrase]:
        if v not in cache:
            cache[v] = phrases(by_verse.get(v, []), numbers)
        return cache[v]

    def has_years(v: int) -> bool:
        return any(p.unit == "year" and p.kind == "span" for p in ph(v))

    # (1) the judges' cycle
    erows, srows = [], []
    for seq, (ep, judge, ref) in enumerate(fc["episodes"]):
        s, e = index.resolve(ref)
        n = 0
        for slot, window, alts, years in fc["slots"]:
            last = min(e, s + int(fc["open"]) - 1) if window == "open" else e
            vids = range(s, last + 1)
            alts = [[str(x) for x in a] for a in alts]
            hit = find_slot(vids, lemmas, alts, has_years if years else None)
            srows.append((ep, slot, hit))
            n += hit is not None
        erows.append((ep, judge, seq, s, e, n, round(n / len(fc["slots"]), 4)))
    episodes = pd.DataFrame(erows, columns=["episode", "judge", "seq", "first_vid", "last_vid",
                                            "n_slots", "share"])  # fmt: skip
    slots = pd.DataFrame(srows, columns=["episode", "slot", "verse_id"])
    slots["verse_id"] = pd.array(slots.verse_id, dtype="Int64")
    rho, p_cycle = ordered_rho(episodes.share.tolist())
    alpha = float(fc["alpha"])
    cycle_holds = bool(rho < 0 and p_cycle <= alpha)
    present = {(r.episode, r.slot) for r in slots.itertuples() if not pd.isna(r.verse_id)}
    names = [s[0] for s in fc["slots"]]
    known_cycle = [{"episode": ep, "expect": "complete",
                    "missing": [s for s in names if (ep, s) not in present],
                    "holds": all((ep, s) in present for s in names)}
                   for ep in fc["known_complete"]]  # fmt: skip
    for ep, miss in fc["known_missing"].items():
        known_cycle.append({"episode": ep, "expect": "missing " + ", ".join(miss),
                            "missing": [s for s in names if (ep, s) not in present],
                            "holds": all((ep, s) not in present for s in miss)})  # fmt: skip
    known_cycle_holds = all(k["holds"] for k in known_cycle)
    log("cycle: " + ", ".join(f"{r.episode} {r.n_slots}" for r in episodes.itertuples())
        + f"; rho {rho:.3f} (p {p_cycle:.4g})")  # fmt: skip

    # (2) the kings' verdicts
    kc = cfg["chronology"]["kings"]
    starts = []
    for king, name, kingdom, ref in kc:
        s, e = index.resolve(ref)
        starts.append((s, e, king, name, kingdom))
    starts.sort()
    book = dict(zip(verses.verse_id, verses.book_id, strict=True))
    last_of_book = verses.groupby("book_id").verse_id.max().to_dict()
    vc = {k: str(v) for k, v in fc["verdict"].items()}
    stop = {str(x) for x in fc["stop"]}
    krows, wording = [], []
    for i, (s, e, king, name, kingdom) in enumerate(starts):
        end = starts[i + 1][0] - 1 if i + 1 < len(starts) else last_of_book[book[s]]
        verdict = vid = None
        for v in range(s, min(end, s + int(fc["verdict_within"]) - 1) + 1):
            verdict = verdict_of(by_verse.get(v, []), vc)
            if verdict:
                vid = v
                break
        span = range(0)
        if vid is not None:
            span = range(vid, min(end, vid + int(fc["verdict_span"]) - 1) + 1)
        row: dict[str, Any] = {"king": king, "name": name, "kingdom": kingdom, "seq": i,
                               "first_vid": s, "last_vid": end, "verdict": verdict,
                               "verdict_vid": vid}  # fmt: skip
        windows = {"formula": range(s, min(end, e + 1) + 1), "verdict": span,
                   "section": range(s, end + 1)}  # fmt: skip
        for slot, where, lems in fc["regnal"]:
            w = windows[where]
            if slot == "age":
                row[slot] = next((v for v in w if any(p.kind == "age" for p in ph(v))), None)
            else:
                row[slot] = find_slot(w, lemmas, [[str(x) for x in lems]])
        krows.append(row)
        if vid is not None:
            wording.append((i, kingdom, set().union(*(lemmas.get(v, set()) for v in span)) - stop))
    kings = pd.DataFrame(krows)
    for c in ["verdict_vid", *(r[0] for r in fc["regnal"])]:
        kings[c] = pd.array(kings[c], dtype="Int64")
    labels = np.array([k for _, k, _ in wording])
    sim = cosine_sets([w for _, _, w in wording])
    diff = within_between(sim, labels)
    rng = np.random.default_rng(fc["seed"])
    reps = int(fc["shuffles"])
    null = np.array([within_between(sim, rng.permutation(labels)) for _ in range(reps)])
    p_verdict = empirical_p(diff - 1e-12, null)
    verdict_holds = bool(diff > 0 and p_verdict <= alpha)
    iu = np.triu_indices(len(labels), 1)
    same = labels[iu[0]] == labels[iu[1]]
    within = {k: float(sim[iu][m].mean()) for k in sorted(set(labels))
              if (m := same & (labels[iu[0]] == k)).any()}  # fmt: skip
    by_king = dict(zip(kings.king, kings.verdict, strict=True))
    known_v = [{"king": k, "expected": v, "found": by_king.get(k), "holds": by_king.get(k) == v}
               for k, v in fc["known_verdicts"].items()]  # fmt: skip
    known_v_holds = all(k["holds"] for k in known_v)
    shares = {
        k: {slot: round(float(kings[kings.kingdom == k][slot].notna().mean()), 4)
            for slot in ["verdict_vid", *(r[0] for r in fc["regnal"])]}
        for k in ("judah", "israel")
    }  # fmt: skip
    log(f"verdicts: {len(wording)} of {len(kings)} kings; within - between {diff:.3f} (p"
        f" {p_verdict:.4g}); known {[k['found'] for k in known_v]}")  # fmt: skip

    out = art / "frameworks"
    out.mkdir(parents=True, exist_ok=True)
    episodes.to_parquet(out / "episodes.parquet", index=False)
    slots.to_parquet(out / "slots.parquet", index=False)
    kings.to_parquet(out / "kings.parquet", index=False)
    meta = {
        "config_hash": config_hash(cfg, "frameworks", "chronology"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "episodes": len(episodes), "slots": names, "open": int(fc["open"]),
        "rho": round(rho, 4), "cycle_p": p_cycle, "cycle_holds": cycle_holds,
        "known_cycle": known_cycle, "known_cycle_holds": known_cycle_holds,
        "kings": len(kings), "verdicts": len(wording),
        "good": int((kings.verdict == "good").sum()), "bad": int((kings.verdict == "bad").sum()),
        "within": {k: round(v, 4) for k, v in within.items()},
        "within_all": round(float(sim[iu][same].mean()), 4) if same.any() else None,
        "between": round(float(sim[iu][~same].mean()), 4) if (~same).any() else None,
        "difference": round(diff, 4), "expected": round(float(null.mean()), 4),
        "verdict_p": p_verdict, "verdict_holds": verdict_holds,
        "known_verdicts": known_v, "known_verdicts_holds": known_v_holds,
        "regnal": [r[0] for r in fc["regnal"]], "by_kingdom": shares,
        "shuffles": reps, "alpha": alpha,
        "seconds": round(time.perf_counter() - t0, 1),
    }  # fmt: skip
    (out / "frameworks.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                              "utf-8")  # fmt: skip
    log(f"done: cycle {'holds' if cycle_holds else 'not borne out'}, verdicts"
        f" {'hold' if verdict_holds else 'not borne out'} ({meta['seconds']} s) -> {out}")
    return out / "episodes.parquet"
