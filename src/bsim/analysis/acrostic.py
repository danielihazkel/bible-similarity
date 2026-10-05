"""`bsim acrostics`: alphabetic acrostics, whole or broken (DESIGN.md §16.15).

An alphabetic acrostic starts successive lines with א, ב, ג, … ת. The Bible has whole ones in
different line units (a verse in Ps 25 / 34 / 145, Prov 31, Lam 1 / 2 / 4; a half-verse in Ps 111
/ 112; a block of verses in Ps 37, Lam 3 and Ps 119) and broken ones (Ps 9–10, Nahum 1: letters
missing or out of place). Lam 2–4 put פ before ע.

- Lines: the first letter of each verse (`verse`) or of each colon (`colon`; the cola of
  `bsim parallelism`, i.e. the te'amim pauses), from the MAM display text, finals folded.
- Chain: lines i1 < i2 < … whose letters advance through the alphabet, at most `max_line_gap`
  lines apart (blocks of up to that many lines per letter); a skipped letter costs
  `missing_penalty`. Score = letters in the chain − penalty × skipped letters, the best over the
  two line units and the two orders (standard, פ before ע), by dynamic programming per chapter.
- Significance: the lines of the chapter are shuffled (its letter mix kept, their order
  destroyed) and the same best-of-variants score computed; `p` = the share of shuffles scoring
  at least as high (`stats.empirical_p`), `q` = Benjamini–Hochberg over all chapters
  (`stats.bh_q`). `null_screen` shuffles first; only a chapter that fewer than `screen_hits` of
  them reach gets all `null_reps` (the p of an ordinary chapter is already clear).

Writes `artifacts/acrostics/units.parquet`: one row per chapter with its best chain (`chain` =
JSON `[verse_id, display_idx, letter]` per line), score, letter counts, `p`, `q`; plus
`acrostics.meta.json` with the recall of the known acrostics (`acrostics.known`).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.stats import bh_q, empirical_p
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BY_OSIS
from bsim.text.normalize import consonantal, fold_finals

Log = Callable[[str], None]

ALPHABET = "אבגדהוזחטיכלמנסעפצקרשת"
ORDERS = {
    "standard": ALPHABET,
    "pe-ayin": ALPHABET.replace("עפ", "פע"),
}

Line = tuple[int, int, str]  # (verse_id, display_idx, letter)


def first_letter(tokens: list[str], start: int = 0) -> tuple[int, str] | None:
    """(display index, letter) of the first Hebrew letter at or after token `start`."""
    for i in range(start, len(tokens)):
        letters = fold_finals(consonantal(tokens[i]).replace(" ", ""))
        if letters and letters[0] in ALPHABET:
            return i, letters[0]
    return None


def chapter_lines(
    verse_ids: list[int], tokens: dict[int, list[str]], cola: dict[int, list[list[int]]]
) -> dict[str, list[Line]]:
    """The lines of a chapter in both line units."""
    out: dict[str, list[Line]] = {"verse": [], "colon": []}
    for v in verse_ids:
        toks = tokens[v]
        f = first_letter(toks)
        if f is not None:
            out["verse"].append((v, *f))
        for start, _ in cola.get(v) or [[0, len(toks) - 1]]:
            f = first_letter(toks, start)
            if f is not None and (not out["colon"] or out["colon"][-1][:2] != (v, f[0])):
                out["colon"].append((v, *f))
    return out


def positions(lines: list[Line], order: str) -> np.ndarray:
    """Alphabet position of each line's letter (every Hebrew letter has one)."""
    return np.array([order.index(letter) for *_, letter in lines], dtype=np.int64)


def chain_scores(pos: np.ndarray, max_gap: int, penalty: float) -> np.ndarray:
    """Best chain score of each row of `pos` (reps x lines), vectorized over the rows."""
    reps, n = pos.shape
    best = np.zeros((reps, n))
    for i in range(n):
        cand = np.ones(reps)
        for j in range(max(0, i - max_gap), i):
            ok = pos[:, j] < pos[:, i]
            val = best[:, j] + 1 - penalty * (pos[:, i] - pos[:, j] - 1)
            cand = np.where(ok & (val > cand), val, cand)
        best[:, i] = cand
    return best.max(axis=1) if n else np.zeros(reps)


@dataclass(frozen=True)
class Chain:
    score: float
    lines: list[int]  # indexes into the line list, in order


def best_chain(pos: np.ndarray, max_gap: int, penalty: float) -> Chain:
    """The best chain of one line sequence, with its lines (ties: the earliest ending)."""
    n = len(pos)
    if n == 0:
        return Chain(0.0, [])
    best = np.ones(n)
    prev = np.full(n, -1)
    for i in range(n):
        for j in range(max(0, i - max_gap), i):
            if pos[j] < pos[i]:
                val = best[j] + 1 - penalty * (pos[i] - pos[j] - 1)
                if val > best[i]:
                    best[i], prev[i] = val, j
    end = int(np.argmax(best))
    lines = [end]
    while prev[lines[-1]] >= 0:
        lines.append(int(prev[lines[-1]]))
    return Chain(float(best[end]), lines[::-1])


def null_scores(
    lines: dict[str, list[Line]], cfg: dict[str, Any], reps: int, rng: np.random.Generator
) -> np.ndarray:
    """Best-of-variants chain score of `reps` line-order shuffles of a chapter."""
    a = cfg["acrostics"]
    null = np.zeros(reps)
    for unit in a["granularities"]:
        ls = lines[unit]
        if len(ls) < 2:
            continue
        perms = np.argsort(rng.random((reps, len(ls))), axis=1)
        for order in ORDERS.values():
            pos = positions(ls, order)[perms]
            null = np.maximum(null, chain_scores(pos, a["max_line_gap"], a["missing_penalty"]))
    return null


def score_chapter(
    lines: dict[str, list[Line]], cfg: dict[str, Any], rng: np.random.Generator
) -> dict[str, Any] | None:
    """Best chain over line units and orders, and its shuffle p-value: `null_screen` shuffles
    first, all `null_reps` only when fewer than `screen_hits` of those reach the score."""
    a = cfg["acrostics"]
    found: tuple[float, str, str, Chain] | None = None
    for unit in a["granularities"]:
        if len(lines[unit]) < 2:
            continue
        for name, order in ORDERS.items():
            c = best_chain(positions(lines[unit], order), a["max_line_gap"], a["missing_penalty"])
            if found is None or c.score > found[0]:
                found = (c.score, unit, name, c)
    if found is None:
        return None
    score, unit, name, c = found
    null = null_scores(lines, cfg, a["null_screen"], rng)
    if np.sum(null >= score - 1e-9) < a["screen_hits"]:
        null = null_scores(lines, cfg, a["null_reps"], rng)
    chain = [lines[unit][i] for i in c.lines]
    order = ORDERS[name]
    first, last = order.index(chain[0][2]), order.index(chain[-1][2])
    return {
        "granularity": unit,
        "order_name": name,
        "score": round(score, 3),
        "n_letters": len(chain),
        "missing": last - first + 1 - len(chain),
        "first_letter": chain[0][2],
        "last_letter": chain[-1][2],
        "start_vid": chain[0][0],
        "end_vid": chain[-1][0],
        "n_lines": len(lines[unit]),
        "p": empirical_p(score - 1e-9, null),
        "chain": json.dumps([[v, i, letter] for v, i, letter in chain], ensure_ascii=False),
    }


def known_unit_ids(refs: list[str]) -> list[str]:
    """`Ps 25` -> `c:{book_id}:25`."""
    out = []
    for ref in refs:
        osis, chapter = ref.rsplit(" ", 1)
        if osis not in BY_OSIS:
            raise RuntimeError(f"acrostics.known: unknown book {osis!r}")
        out.append(f"c:{BY_OSIS[osis].book_id}:{int(chapter)}")
    return out


def run_acrostics(cfg: dict[str, Any], log: Log = print) -> Path:
    proc = resolve_path(cfg, "data_processed")
    art = resolve_path(cfg, "artifacts")
    par_path = art / "parallelism" / "verses.parquet"
    if not par_path.exists():
        raise RuntimeError(f"{par_path} missing; run `bsim parallelism` first")
    t0 = time.perf_counter()
    a = cfg["acrostics"]
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "display_tokens"])
    tokens = {int(v): list(t) for v, t in zip(verses.verse_id, verses.display_tokens, strict=True)}
    par = pd.read_parquet(par_path, columns=["verse_id", "cola"])
    cola = {int(v): json.loads(c) for v, c in zip(par.verse_id, par.cola, strict=True)}
    units = pd.read_parquet(proc / "units.parquet")
    units = units[units.unit_type == a["unit_type"]]
    rng = np.random.default_rng(a["seed"])
    rows = []
    for k, u in enumerate(units.itertuples(index=False), start=1):
        vids = list(range(u.start_verse_id, u.end_verse_id + 1))
        r = score_chapter(chapter_lines(vids, tokens, cola), cfg, rng)
        if r is not None:
            rows.append({"unit_id": u.unit_id, "book_id": int(u.book_id), **r})
        if k % 200 == 0:
            log(f"  {k}/{len(units)} units")
    df = pd.DataFrame(rows)
    df["q"] = bh_q(df.p.to_numpy())
    df = df.sort_values(["q", "score", "unit_id"], ascending=[True, False, True], ignore_index=True)

    known = known_unit_ids(list(a["known"]))
    by_id = df.set_index("unit_id")
    found = {u: float(by_id.q[u]) if u in by_id.index else None for u in known}
    hits = [u for u, q in found.items() if q is not None and q <= a["report_q"]]
    out = art / "acrostics"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "units.parquet")
    meta = {
        "config_hash": config_hash(cfg, "acrostics"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "units": int(len(df)),
        "significant": int((df.q <= a["report_q"]).sum()),
        "report_q": a["report_q"],
        "known_q": found,
        "known_recall": round(len(hits) / max(1, len(known)), 3),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "acrostics.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(
        f"done: {len(df)} units, {meta['significant']} with q <= {a['report_q']};"
        f" known acrostics found {len(hits)}/{len(known)} in {meta['seconds']} s"
    )
    return out / "units.parquet"
