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
from bsim.config import config_hash, resolve_path, write_meta
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
    options = chapter_options(verse_ids, tokens, cola)
    return {u: [opts[0] for opts in ls] for u, ls in options.items()}


def chapter_options(
    verse_ids: list[int], tokens: dict[int, list[str]], cola: dict[int, list[list[int]]]
) -> dict[str, list[list[Line]]]:
    """The lines of a chapter in both line units, each with the letter of its first word and, as
    a second option, of its next word (a title or a leading word before the letter: Ps 25:1
    לדוד, Nahum 1:3 יהוה בסופה, 1:6 לפני זעמו)."""
    out: dict[str, list[list[Line]]] = {"verse": [], "colon": []}

    def options(v: int, toks: list[str], start: int) -> list[Line] | None:
        f = first_letter(toks, start)
        if f is None:
            return None
        g = first_letter(toks, f[0] + 1)
        return [(v, *f)] + ([(v, *g)] if g is not None else [])

    for v in verse_ids:
        toks = tokens[v]
        o = options(v, toks, 0)
        if o is not None:
            out["verse"].append(o)
        for start, _ in cola.get(v) or [[0, len(toks) - 1]]:
            o = options(v, toks, start)
            if o is not None and (not out["colon"] or out["colon"][-1][0][:2] != o[0][:2]):
                out["colon"].append(o)
    return out


def option_positions(lines: list[list[Line]], order: str, k: int) -> np.ndarray:
    """(lines x k) alphabet positions of each line's first `k` options; -1 where it has none."""
    pos = np.full((len(lines), k), -1, dtype=np.int64)
    for i, opts in enumerate(lines):
        for j, (*_, letter) in enumerate(opts[:k]):
            pos[i, j] = order.index(letter)
    return pos


def positions(lines: list[Line], order: str) -> np.ndarray:
    """Alphabet position of each line's letter (every Hebrew letter has one)."""
    return np.array([order.index(letter) for *_, letter in lines], dtype=np.int64)


def chain_scores(pos: np.ndarray, max_gap: int, penalty: float) -> np.ndarray:
    """Best chain score of each row of `pos` (reps x lines, or reps x lines x options with -1
    for an option a line lacks), vectorized over the rows."""
    if pos.ndim == 2:
        pos = pos[:, :, None]
    reps, n, k = pos.shape
    valid = pos >= 0
    best = np.where(valid, 1.0, -np.inf)
    for i in range(1, n):
        lo = max(0, i - max_gap)
        pj, bj, vj = pos[:, lo:i], best[:, lo:i], valid[:, lo:i]  # the window: reps x w x k
        for b in range(k):
            pi = pos[:, i, b][:, None, None]
            ok = vj & valid[:, i, b][:, None, None] & (pj < pi)
            val = np.where(ok, bj + 1 - penalty * (pi - pj - 1), -np.inf)
            best[:, i, b] = np.maximum(best[:, i, b], val.max(axis=(1, 2)))
    return best.reshape(reps, -1).max(axis=1) if n else np.zeros(reps)


@dataclass(frozen=True)
class Chain:
    score: float
    lines: list[int]  # indexes into the line list, in order
    picks: list[int] | None = None  # the option used at each of those lines (0: the first word)


def best_chain(pos: np.ndarray, max_gap: int, penalty: float) -> Chain:
    """The best chain of one line sequence (lines, or lines x options with -1 where a line has
    no such option), with its lines (ties: the earliest ending, the first option)."""
    single = pos.ndim == 1
    if single:
        pos = pos[:, None]
    n, k = pos.shape
    if n == 0:
        return Chain(0.0, [])
    best = np.where(pos >= 0, 1.0, -np.inf)
    prev = np.full((n, k, 2), -1)
    for i in range(n):
        for b in range(k):
            if pos[i, b] < 0:
                continue
            for j in range(max(0, i - max_gap), i):
                for a in range(k):
                    if 0 <= pos[j, a] < pos[i, b]:
                        val = best[j, a] + 1 - penalty * (pos[i, b] - pos[j, a] - 1)
                        if val > best[i, b]:
                            best[i, b], prev[i, b] = val, (j, a)
    end = np.unravel_index(int(np.argmax(best)), best.shape)
    steps = [(int(end[0]), int(end[1]))]
    while prev[steps[-1]][0] >= 0:
        steps.append((int(prev[steps[-1]][0]), int(prev[steps[-1]][1])))
    steps.reverse()
    picks = None if single else [b for _, b in steps]
    return Chain(float(best[end]), [i for i, _ in steps], picks)


def null_scores(
    lines: dict[str, list[list[Line]]], cfg: dict[str, Any], reps: int, rng: np.random.Generator
) -> np.ndarray:
    """Best-of-variants chain score of `reps` line-order shuffles of a chapter."""
    a = cfg["acrostics"]
    k = 2 if a["second_word"] else 1
    null = np.zeros(reps)
    for unit in a["granularities"]:
        ls = lines[unit]
        if len(ls) < 2:
            continue
        perms = np.argsort(rng.random((reps, len(ls))), axis=1)
        for order in ORDERS.values():
            pos = option_positions(ls, order, k)[perms]
            null = np.maximum(null, chain_scores(pos, a["max_line_gap"], a["missing_penalty"]))
    return null


def span(lines: list[list[Line]], chained: list[int], first: str, last: str) -> tuple[int, int]:
    """The acrostic's first and last line (M159). The chain takes the earliest line of its first
    letter that reaches the second, so Prov 31's starts at the א of 31:3; the span starts instead
    at the last line opening with that letter before the chain's second line (31:10 אשת חיל), and
    runs back over the lines before it opening alike (Ps 119:1-8, Lam 3:1-3) and on after its last
    line the same way (Ps 119:169-176). A line's letter here is its first word's."""
    i0, i1 = chained[0], chained[-1]
    if len(chained) > 1:
        i0 = max(j for j in range(i0, chained[1]) if lines[j][0][2] == first or j == i0)
    while i0 > 0 and lines[i0 - 1][0][2] == first:
        i0 -= 1
    while i1 < len(lines) - 1 and lines[i1 + 1][0][2] == last:
        i1 += 1
    return i0, i1


def score_chapter(
    lines: dict[str, list[list[Line]]], cfg: dict[str, Any], rng: np.random.Generator
) -> dict[str, Any] | None:
    """Best chain over line units and orders, and its shuffle p-value: `null_screen` shuffles
    first, all `null_reps` only when fewer than `screen_hits` of those reach the score."""
    a = cfg["acrostics"]
    k = 2 if a["second_word"] else 1
    found: tuple[float, str, str, Chain] | None = None
    for unit in a["granularities"]:
        if len(lines[unit]) < 2:
            continue
        for name, order in ORDERS.items():
            pos = option_positions(lines[unit], order, k)
            c = best_chain(pos, a["max_line_gap"], a["missing_penalty"])
            if found is None or c.score > found[0]:
                found = (c.score, unit, name, c)
    if found is None:
        return None
    score, unit, name, c = found
    null = null_scores(lines, cfg, a["null_screen"], rng)
    if np.sum(null >= score - 1e-9) < a["screen_hits"]:
        null = null_scores(lines, cfg, a["null_reps"], rng)
    picks = c.picks or [0] * len(c.lines)
    chain = [lines[unit][i][b] for i, b in zip(c.lines, picks, strict=True)]
    order = ORDERS[name]
    first, last = order.index(chain[0][2]), order.index(chain[-1][2])
    ls = lines[unit]
    i0, i1 = span(ls, c.lines, chain[0][2], chain[-1][2]) if a["span_trim"] else (0, 0)
    return {
        "granularity": unit,
        "order_name": name,
        "score": round(score, 3),
        "n_letters": len(chain),
        "missing": last - first + 1 - len(chain),
        "first_letter": chain[0][2],
        "last_letter": chain[-1][2],
        "start_vid": ls[i0][0][0] if a["span_trim"] else chain[0][0],
        "end_vid": ls[i1][0][0] if a["span_trim"] else chain[-1][0],
        "n_lines": len(lines[unit]),
        "second_words": int(sum(picks)),  # letters read on a line's second word
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
        r = score_chapter(chapter_options(vids, tokens, cola), cfg, rng)
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
    write_meta(out / "acrostics.meta.json", meta)
    log(
        f"done: {len(df)} units, {meta['significant']} with q <= {a['report_q']};"
        f" known acrostics found {len(hits)}/{len(known)} in {meta['seconds']} s"
    )
    return out / "units.parquet"
