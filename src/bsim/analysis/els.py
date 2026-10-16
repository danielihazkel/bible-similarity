"""`bsim els`: equidistant letter sequences, counted against controls (DESIGN.md §16.62)

"Bible codes" read words in the letters of the Torah at an equal skip: תורה from the ת of
Genesis 1:1 at every 50th letter (Rabbenu Bahya), and since the 1990s names and dates found at
skips in the thousands. Any long text holds such sequences by chance; the question is whether
the Torah holds more than its controls. Everything is fixed in `els` before the first run.

- **The letters:** the written text (`ketiv`, as `bsim masorah` builds it), consonants with final
  forms folded, verse after verse: 304,801 letters in the Torah.
- **Hits:** an occurrence of a term (`terms`: a list of names) at a skip from `min_skip` to
  `max_skip`, forwards or backwards (a backward hit is the reversed term forwards; a palindrome
  counts once).
- **Expected:** under a shuffle of the scope's own letters, the exact expected count is the
  number of placements (Σ over skips of n − (L − 1)·d) times the chance that L given positions
  spell the term (Π (c(letter) − earlier uses of it) / (n − k)). A term's log ratio is
  log((hits + `smooth`) / (expected + `smooth`)); a text's statistic `R` is the mean over the
  terms.
- **Controls**, per scope (`scopes`: the Torah, and Genesis alone):
  - `letters`: the scope's letters shuffled (`shuffles` draws);
  - `verses`: its verses in shuffled order, each verse's letters kept (`shuffles` draws);
  - `blocks`: blocks of the same length cut from the rest of the Bible in canon order (`rest`),
    each with its own expectation.
  One-sided: `p` is the share of a control's values at least the scope's R (+1 smoothed). The
  claim, "no more hits than the controls", holds when no control has p ≤ `alpha`.
- **Known answers** (`known`): the tradition's ELSs at the start of each book of the Torah, a
  check of the letter string; and how many times the term occurs at that skip in the Torah.

Writes `artifacts/els/`: `terms.parquet` (per scope and term: hits each way, expected, ratio,
the controls' means and ranges), `draws.parquet` (each control draw's R), and `els.meta.json`
(per scope: letters, R, each control's mean, range and `p`; the blocks; the known answers).
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

from bsim.analysis.masorah import TEXTS, texts
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BY_OSIS
from bsim.data.refs import RefIndex
from bsim.retrieve.topk import get_device
from bsim.text.normalize import fold_finals

Log = Callable[[str], None]

ALPHABET = "אבגדהוזחטיכלמנסעפצקרשת"
CODE = {c: i for i, c in enumerate(ALPHABET)}
CONTROLS = ("letters", "verses", "blocks")
CHUNK = 4_000_000  # (start, skip) pairs gathered at once


def encode(s: str) -> np.ndarray:
    """Letters as codes 0..21 (finals folded; anything else dropped)."""
    return np.array([CODE[c] for c in fold_finals(s) if c in CODE], dtype=np.int8)


def term_code(term: str) -> list[int]:
    codes = [CODE[c] for c in fold_finals(term) if c in CODE]
    if len(codes) < 2:
        raise ValueError(f"els term {term!r} needs two letters or more")
    return codes


def count_hits(s: torch.Tensor, term: list[int], min_skip: int, max_skip: int) -> int:
    """Occurrences of `term` at a skip in min_skip..max_skip, forwards only."""
    n, L = len(s), len(term)
    if max_skip < min_skip or n < 1 + (L - 1) * min_skip:
        return 0
    starts = (s == term[0]).nonzero().squeeze(1)
    skips = torch.arange(min_skip, max_skip + 1, device=s.device)
    total = 0
    step = max(1, CHUNK // len(skips))
    for a in range(0, len(starts), step):
        i0 = starts[a : a + step]
        ok = i0[:, None] + (L - 1) * skips[None, :] < n
        nxt = (i0[:, None] + skips[None, :]).clamp(max=n - 1)
        ok &= s[nxt] == term[1]
        r, c = ok.nonzero(as_tuple=True)
        i, d = i0[r], skips[c]
        for k in range(2, L):
            keep = s[i + k * d] == term[k]
            i, d = i[keep], d[keep]
        total += len(i)
    return total


def term_hits(s: torch.Tensor, term: list[int], min_skip: int, max_skip: int) -> tuple[int, int]:
    """Hits forwards and backwards (a palindrome's backward hits are its forward ones: 0)."""
    fwd = count_hits(s, term, min_skip, max_skip)
    back = 0 if term == term[::-1] else count_hits(s, term[::-1], min_skip, max_skip)
    return fwd, back


def expected_hits(counts: np.ndarray, n: int, term: list[int], min_skip: int,
                  max_skip: int) -> float:  # fmt: skip
    """The exact expected hits (both ways) when the `n` letters with these `counts` are shuffled."""
    L = len(term)
    d = np.arange(min_skip, max_skip + 1)
    placements = float(np.clip(n - (L - 1) * d, 0, None).sum())
    seen: Counter[int] = Counter()
    prob = 1.0
    for k, c in enumerate(term):
        prob *= max(0, int(counts[c]) - seen[c]) / (n - k)
        seen[c] += 1
    return placements * prob * (1 if term == term[::-1] else 2)


def ratio_stat(hits: np.ndarray, expected: np.ndarray, smooth: float) -> float:
    """The mean over terms of log((hits + smooth) / (expected + smooth))."""
    return float(np.mean(np.log((hits + smooth) / (expected + smooth))))


def scope_hits(
    s: np.ndarray, terms: list[list[int]], lo: int, hi: int, device: torch.device
) -> np.ndarray:
    """(terms, 2): hits forwards and backwards."""
    t = torch.from_numpy(s).to(device)
    return np.array([term_hits(t, term, lo, hi) for term in terms], dtype=np.int64)


def expectations(s: np.ndarray, terms: list[list[int]], lo: int, hi: int) -> np.ndarray:
    counts = np.bincount(s, minlength=len(ALPHABET))
    return np.array([expected_hits(counts, len(s), t, lo, hi) for t in terms])


def summary(values: np.ndarray, obs: float) -> dict[str, Any]:
    return {
        "n": len(values),
        "mean": round(float(values.mean()), 5),
        "q05": round(float(np.quantile(values, 0.05)), 5),
        "q95": round(float(np.quantile(values, 0.95)), 5),
        "p": float((1 + np.sum(values >= obs)) / (1 + len(values))),
    }


def find_at(s: np.ndarray, first: int, last: int, term: list[int], skip: int) -> int | None:
    """The first start in letters first..last of an ELS of `term` at `skip`."""
    L = len(term)
    for i in range(first, last + 1):
        if i + (L - 1) * skip < len(s) and all(s[i + k * skip] == term[k] for k in range(L)):
            return i
    return None


def run_els(cfg: dict[str, Any], log: Log = print) -> Path:
    ec = cfg["els"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "els"
    t0 = time.perf_counter()
    lo, hi = int(ec["min_skip"]), int(ec["max_skip"])
    reps, alpha, smooth = int(ec["shuffles"]), float(ec["alpha"]), float(ec["smooth"])
    if ec["text"] not in TEXTS:
        raise ValueError(f"els.text must be one of {TEXTS}")
    device = get_device(str(ec["device"]))
    rng = np.random.default_rng(int(ec["seed"]))
    torch.manual_seed(int(ec["seed"]))
    pairs_path = art / "ketiv" / "pairs.parquet"
    if not pairs_path.exists():
        raise FileNotFoundError(f"{pairs_path} is missing: run `bsim ketiv` first")

    verses = pd.read_parquet(
        proc / "verses.parquet",
        columns=["verse_id", "book_id", "chapter", "verse", "display_tokens"],
    ).sort_values("verse_id", ignore_index=True)
    words = pd.read_parquet(proc / "words.parquet", columns=["verse_id", "idx", "display_idx"])
    pairs = pd.read_parquet(
        pairs_path, columns=["verse_id", "pos", "n_ketiv", "n_qere", "ketiv", "qere"]
    ).sort_values(["verse_id", "pos"], kind="stable")
    index = RefIndex(verses)
    text = texts(verses, words, pairs)[0][ec["text"]]
    joined = text.groupby("verse_id").word.agg("".join)
    verse_codes = {int(v): encode(joined.get(v, "")) for v in verses.verse_id}
    book_of = dict(zip(verses.verse_id.astype(int), verses.book_id.astype(int), strict=True))

    def letters_of(books: list[str]) -> tuple[np.ndarray, list[int]]:
        ids = {BY_OSIS[b].book_id for b in books}
        vids = [v for v in verse_codes if book_of[v] in ids]
        return np.concatenate([verse_codes[v] for v in vids]), vids

    names = [str(t) for t in ec["terms"]]
    terms = [term_code(t) for t in names]
    rest, rest_vids = letters_of(ec["rest"])
    rest_starts = np.cumsum([0] + [len(verse_codes[v]) for v in rest_vids])

    term_rows, draw_rows, scopes = [], [], {}
    for scope, books in ec["scopes"].items():
        s, vids = letters_of(books)
        n = len(s)
        exp = expectations(s, terms, lo, hi)
        hits = scope_hits(s, terms, lo, hi, device)
        total = hits.sum(axis=1)
        obs = ratio_stat(total, exp, smooth)
        draws: dict[str, np.ndarray] = {}
        # letters shuffled: the expectation is the scope's own
        lt = np.empty((reps, len(terms)))
        for r in range(reps):
            lt[r] = scope_hits(s[rng.permutation(n)], terms, lo, hi, device).sum(axis=1)
        draws["letters"] = np.array([ratio_stat(x, exp, smooth) for x in lt])
        # verses shuffled: the same letters, so the same expectation
        vt = np.empty((reps, len(terms)))
        for r in range(reps):
            order = rng.permutation(len(vids))
            vt[r] = scope_hits(np.concatenate([verse_codes[vids[i]] for i in order]), terms, lo,
                               hi, device).sum(axis=1)  # fmt: skip
        draws["verses"] = np.array([ratio_stat(x, exp, smooth) for x in vt])
        # blocks of the rest, each against its own letters' expectation
        blocks, bt = [], []
        for b in range(len(rest) // n):
            block = rest[b * n : (b + 1) * n]
            bh = scope_hits(block, terms, lo, hi, device).sum(axis=1)
            be = expectations(block, terms, lo, hi)
            first = rest_vids[int(np.searchsorted(rest_starts, b * n, side="right")) - 1]
            last = rest_vids[int(np.searchsorted(rest_starts, (b + 1) * n - 1, side="right")) - 1]
            blocks.append({"block": b + 1, "first_vid": first, "last_vid": last,
                           "r": round(ratio_stat(bh, be, smooth), 5)})  # fmt: skip
            bt.append(np.log((bh + smooth) / (be + smooth)))
        draws["blocks"] = np.array([b["r"] for b in blocks])
        controls = {c: summary(v, obs) for c, v in draws.items() if len(v)}
        scopes[scope] = {
            "books": list(books), "letters": n, "verses": len(vids),
            "first_vid": vids[0], "last_vid": vids[-1],
            "hits": int(total.sum()), "expected": round(float(exp.sum()), 1),
            "r": round(obs, 5), "controls": controls, "blocks": blocks,
            "holds": all(c["p"] > alpha for c in controls.values()),
        }  # fmt: skip
        for c, v in draws.items():
            draw_rows += [(scope, c, i + 1, round(float(x), 5)) for i, x in enumerate(v)]
        log_bt = np.array(bt) if bt else np.empty((0, len(terms)))
        for j, name in enumerate(names):
            lr = math.log((total[j] + smooth) / (exp[j] + smooth))
            term_rows.append({
                "scope": scope, "term": name, "length": len(terms[j]),
                "forward": int(hits[j, 0]), "backward": int(hits[j, 1]), "hits": int(total[j]),
                "expected": round(float(exp[j]), 2), "log_ratio": round(lr, 5),
                "letters_mean": round(float(lt[:, j].mean()), 2),
                "letters_q05": float(np.quantile(lt[:, j], 0.05)),
                "letters_q95": float(np.quantile(lt[:, j], 0.95)),
                "letters_p": float((1 + np.sum(lt[:, j] >= total[j])) / (1 + reps)),
                "verses_mean": round(float(vt[:, j].mean()), 2),
                "blocks_log_ratio": round(float(log_bt[:, j].mean()), 5) if len(log_bt) else None,
            })  # fmt: skip
        log(f"  {scope}: {n:,} letters, {int(total.sum()):,} hits against {exp.sum():,.0f}"
            f" expected; R {obs:+.4f}; p " + ", ".join(f"{c} {v['p']:.3f}"
                                                      for c, v in controls.items()))  # fmt: skip

    # known answers: the letter string of the Torah
    torah, torah_vids = letters_of(ec["scopes"].get("torah", ["Gen", "Exod", "Lev", "Num", "Deut"]))
    starts = dict(zip(torah_vids, np.cumsum([0] + [len(verse_codes[v]) for v in torah_vids])[:-1],
                      strict=True))  # fmt: skip
    t_dev = torch.from_numpy(torah).to(device)
    torah_counts = np.bincount(torah, minlength=len(ALPHABET))
    known = []
    for k in ec["known"]:
        first, _ = index.resolve(k["ref"])
        code = term_code(k["term"])
        a = int(starts[first])
        at = find_at(torah, a, a + len(verse_codes[first]) - 1, code, int(k["skip"]))
        known.append({
            "ref": k["ref"], "verse_id": first, "term": k["term"], "skip": int(k["skip"]),
            "found": at is not None, "offset": None if at is None else at - a,
            "in_torah": count_hits(t_dev, code, int(k["skip"]), int(k["skip"])),
            # forwards only: half of both ways
            "expected": round(expected_hits(torah_counts, len(torah), code, int(k["skip"]),
                                            int(k["skip"])) / 2, 1),
        })  # fmt: skip

    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(term_rows).to_parquet(out / "terms.parquet")
    pd.DataFrame(draw_rows, columns=["scope", "control", "draw", "r"]).to_parquet(
        out / "draws.parquet"
    )
    meta = {
        "config_hash": config_hash(cfg, "els"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "text": ec["text"],
        "min_skip": lo,
        "max_skip": hi,
        "shuffles": reps,
        "alpha": alpha,
        "smooth": smooth,
        "terms": len(names),
        "scopes": scopes,
        "known": known,
        "holds": all(s["holds"] for s in scopes.values()),
        "device": str(device),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    meta = json.loads(json.dumps(meta, default=lambda x: x.item() if hasattr(x, "item") else x))
    (out / "els.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
    log(
        f"done: no more hits than the controls: {meta['holds']}; known"
        f" {sum(k['found'] for k in known)}/{len(known)} ({meta['seconds']} s) -> {out}"
    )
    return out
