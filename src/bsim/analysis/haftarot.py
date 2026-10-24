"""`bsim haftarot`: the sages' haftarah for each parasha, against the Prophets as the systems rank
them (DESIGN.md §16.69).

Every Sabbath's Torah reading has a reading from the Prophets chosen to match it: Noach is read
with Isaiah 54 ("as the waters of Noah", 54:9), Vayera with II Kings 4 (a son promised to a woman
without one). The pairing is an independent judgement of which passages belong together, the
only one the project has for the parashot (§16.33 has no parasha gold).

- **Pairs.** Hebcal's leyning list (`sources.hebcal_leyning`, `haftarot.pairing`: the Ashkenazi
  haftarot) gives each of the 54 parashot its haftarah; aligned with the parasha units by their
  order. A chapter of the Prophets (Joshua..Malachi, 380 chapters) is the haftarah's when it holds
  `min_verses` of its verses. Ten haftarot are fixed by the calendar, not by their parasha
  (Hebcal's `haftTheme`: three of rebuke before the Ninth of Av, seven of consolation after).
- **Ranks.** Each parasha against every chapter of the Prophets: `lexical` (TF-IDF of the lemma
  streams as `bsim lexical`, idf over the parashot and the chapters), `semantic` (the final
  semantic system's best-match average of verse scores, `bsim units`) and `fused` (their RRF with
  `fusion.rrf_k`, `w_lex`, `w_sem`, over all 380). A haftarah's rank is the best of its chapters'.
- **Claims fixed in advance** (`claim_mode`): (1) the haftarot not fixed by the calendar rank
  higher (mean rank percentile) than the same haftarot shuffled among their parashot
  (`shuffles`); (2) they rank higher than the ten the calendar fixes, labels shuffled. Each mode's
  MRR and hits within `list` are reported: the parasha level's first gold.
- **Known answers.** `known` parashot have their haftarah within `known_rank` (fused).

Writes `artifacts/haftarot/`: `pairs.parquet` (`parasha` (unit id), `num, name, theme, haft,
seph` (refs), `chapters` (JSON unit ids), a rank per mode, `pct`, `known`), `lists.parquet` (per
parasha its top `list` chapters: `parasha, rank, chapter, fused, lex_rank, sem_rank, haftarah`)
and `haftarot.meta.json`.
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

from bsim.analysis.stats import empirical_p
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS
from bsim.data.refs import RefIndex

Log = Callable[[str], None]
MODES = ("lexical", "semantic", "fused")


def parts(entry: Any) -> list[dict[str, str]]:
    """A Hebcal haftarah (one part or several) as a list of {k, b, e}."""
    if entry is None:
        return []
    return list(entry) if isinstance(entry, list) else [entry]


def ref_of(p: dict[str, str]) -> str:
    return f"{p['k']} {p['b']}-{p['e']}"


def haftarah_verses(entry: Any, index: RefIndex) -> list[int]:
    out: list[int] = []
    for p in parts(entry):
        s, e = index.resolve(ref_of(p))
        out += range(s, e + 1)
    return out


def chapters_of(vids: list[int], start: np.ndarray, end: np.ndarray, min_verses: int) -> list[int]:
    """Positions of the candidate chapters holding at least `min_verses` of these verses (the
    one holding most when none does)."""
    v = np.asarray(vids)
    counts = np.array([((v >= s) & (v <= e)).sum() for s, e in zip(start, end, strict=True)])
    hit = np.flatnonzero(counts >= min_verses)
    return hit.tolist() if len(hit) else [int(np.argmax(counts))] if counts.max() > 0 else []


def ranks(scores: np.ndarray) -> np.ndarray:
    """Rank of every column per row, 1 = highest score (ties: the first column first)."""
    order = np.argsort(-scores, axis=1, kind="stable")
    r = np.empty_like(order)
    rows = np.arange(scores.shape[0])[:, None]
    r[rows, order] = np.arange(1, scores.shape[1] + 1)[None, :]
    return r


def best_rank(rank_row: np.ndarray, chapters: list[int]) -> int:
    return int(min(rank_row[c] for c in chapters))


def rrf_scores(
    lex: np.ndarray, sem: np.ndarray, k: float, w_lex: float, w_sem: float
) -> np.ndarray:
    return w_lex / (k + ranks(lex)) + w_sem / (k + ranks(sem))


def shuffle_p(pct: np.ndarray, chapters: list[list[int]], rank_rows: np.ndarray, reps: int,
              rng: np.random.Generator) -> tuple[float, float]:  # fmt: skip
    """Mean percentile of each parasha's own haftarah against haftarot shuffled among the
    parashot (lower is better): (mean of the shuffles, p)."""
    n_cand = rank_rows.shape[1]
    obs = float(pct.mean())
    m = len(chapters)
    best = np.array([[best_rank(rank_rows[i], chapters[j]) for j in range(m)] for i in range(m)])
    to_pct = (best - 1) / (n_cand - 1)
    null = np.empty(reps)
    for r in range(reps):
        perm = rng.permutation(m)
        null[r] = to_pct[np.arange(m), perm].mean()
    return float(null.mean()), empirical_p(-obs - 1e-12, -null)


def label_p(
    pct: np.ndarray, is_a: np.ndarray, reps: int, rng: np.random.Generator
) -> tuple[float, float]:
    """mean(pct | not a) - mean(pct | a) and its one-sided p, labels shuffled (a ranks higher)."""

    def diff(lab: np.ndarray) -> float:
        return float(pct[~lab].mean() - pct[lab].mean())

    obs = diff(is_a)
    null = np.array([diff(rng.permutation(is_a)) for _ in range(reps)])
    return obs, empirical_p(obs - 1e-12, null)


def score_matrices(cfg: dict[str, Any], par, chap) -> dict[str, np.ndarray]:  # noqa: ANN001
    """Parashot x chapters: lexical (TF-IDF cosine) and semantic (best-match average)."""
    import scipy.sparse as sp

    from bsim.lexical.build import prepare
    from bsim.lexical.tfidf import unit_tfidf
    from bsim.lexical.tokens import lemma_streams
    from bsim.retrieve.topk import Units, get_device, resolve_system
    from bsim.retrieve.units import bma_matrix

    proc = resolve_path(cfg, "data_processed")
    words = pd.read_parquet(proc / "words.parquet", columns=["verse_id", "idx", "content_lemmas"])
    n = len(pd.read_parquet(proc / "verses.parquet", columns=["verse_id"]))
    members = pd.read_parquet(proc / "unit_members.parquet")
    tokens, weights, _ = prepare(lemma_streams(words, n), cfg["lexical"])
    ids = [*par.ids, *chap.ids]
    x = unit_tfidf(tokens, weights, members, ids)
    xp, xc = x[: len(par)], x[len(par) :]
    lex = np.asarray(sp.csr_matrix(xp @ xc.T).todense())

    both = Units(np.array(ids, dtype=object), np.concatenate([par.start, chap.start]),
                 np.concatenate([par.end, chap.end]))  # fmt: skip
    order = np.argsort(both.start, kind="stable")
    both = Units(both.ids[order], both.start[order], both.end[order])
    r = cfg["retrieval"]
    device = get_device(r["device"])
    src = resolve_system(cfg, cfg["final_systems"]["semantic"])
    m = bma_matrix(src.scorer(device), both, r["chunk_size"], device)
    pos = both.position()
    sem = m[np.ix_([pos[u] for u in par.ids], [pos[u] for u in chap.ids])]
    return {"lexical": lex, "semantic": sem}


def run_haftarot(cfg: dict[str, Any], log: Log = print) -> Path:
    from bsim.retrieve.topk import Units, load_units

    hc, fc = cfg["haftarot"], cfg["fusion"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    raw = resolve_path(cfg, "data_raw")
    t0 = time.perf_counter()
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter",
                                                               "verse"])  # fmt: skip
    index = RefIndex(verses)
    leyning = json.loads((raw / "leyning" / "aliyot.json").read_text("utf-8"))
    single = sorted(((k, v) for k, v in leyning.items() if isinstance(v.get("num"), int)),
                    key=lambda kv: kv[1]["num"])  # fmt: skip

    par = load_units(cfg, "parasha")
    if len(par) != len(single):
        raise RuntimeError(f"{len(par)} parasha units against {len(single)} in the leyning list")
    chapters = load_units(cfg, "chapter")
    prophets = {b.book_id for b in BOOKS if b.section == "Prophets"}
    book_of = dict(zip(verses.verse_id, verses.book_id, strict=True))
    keep = np.array([book_of[int(s)] in prophets for s in chapters.start])
    chap = Units(chapters.ids[keep], chapters.start[keep], chapters.end[keep])
    log(f"{len(par)} parashot against {len(chap)} chapters of the Prophets")

    gold = [chapters_of(haftarah_verses(v[hc["pairing"]], index), chap.start, chap.end,
                        int(hc["min_verses"])) for _, v in single]  # fmt: skip
    scores = score_matrices(cfg, par, chap)
    scores["fused"] = rrf_scores(scores["lexical"], scores["semantic"], fc["rrf_k"], fc["w_lex"],
                                 fc["w_sem"])  # fmt: skip
    rank_of = {m: ranks(scores[m]) for m in MODES}
    best = {m: np.array([best_rank(rank_of[m][i], g) for i, g in enumerate(gold)]) for m in MODES}
    n_cand = len(chap)
    theme = [next(iter(v.get("haftTheme") or {}), None) for _, v in single]
    thematic = np.array([t is None for t in theme])
    rng = np.random.default_rng(hc["seed"])
    reps, alpha, mode = int(hc["shuffles"]), float(hc["alpha"]), hc["claim_mode"]
    pct = (best[mode] - 1) / (n_cand - 1)

    # claim 1: the thematic haftarot against themselves shuffled
    idx = np.flatnonzero(thematic)
    null1, p1 = shuffle_p(pct[idx], [gold[i] for i in idx], rank_of[mode][idx], reps, rng)
    holds1 = bool(pct[idx].mean() < null1 and p1 <= alpha)
    # claim 2: thematic against the calendar's
    diff2, p2 = label_p(pct, thematic, reps, rng)
    holds2 = bool(diff2 > 0 and p2 <= alpha)
    log(f"thematic haftarot at percentile {pct[idx].mean():.3f} against {null1:.3f} shuffled"
        f" (p {p1:.4g}); the calendar's {pct[~thematic].mean():.3f} (p {p2:.4g})")  # fmt: skip

    # each mode as a retrieval of the haftarah
    k = int(hc["list"])
    evals = {
        m: {
            "mrr": float((1 / best[m][idx]).mean()),
            "hits": int((best[m][idx] <= k).sum()),
            "median": float(np.median(best[m][idx])),
            "pct": float(((best[m][idx] - 1) / (n_cand - 1)).mean()),
        }
        for m in MODES
    }
    log("  " + "; ".join(f"{m} MRR {e['mrr']:.3f}, {e['hits']} in the top {k}"
                         for m, e in evals.items()))  # fmt: skip

    names = [name for name, _ in single]
    known_rows = []
    for kn in hc["known"]:
        i = names.index(kn)
        known_rows.append({"parasha": kn, "rank": int(best["fused"][i]),
                           "holds": bool(best["fused"][i] <= hc["known_rank"])})  # fmt: skip
    known_holds = all(r["holds"] for r in known_rows)

    pairs = pd.DataFrame({
        "parasha": par.ids, "num": [v["num"] for _, v in single], "name": names,
        "theme": theme,
        "haft": [" + ".join(ref_of(p) for p in parts(v.get(hc["pairing"]))) for _, v in single],
        "seph": [" + ".join(ref_of(p) for p in parts(v.get("seph"))) or None for _, v in single],
        "chapters": [json.dumps([str(chap.ids[c]) for c in g]) for g in gold],
        **{f"rank_{m}": best[m] for m in MODES},
        "pct": pct.round(4),
        "known": [n in hc["known"] for n in names],
    })  # fmt: skip
    rows = []
    for i, pid in enumerate(par.ids):
        top = np.argsort(rank_of["fused"][i])[:k]
        for c in top:
            rows.append((pid, int(rank_of["fused"][i][c]), str(chap.ids[c]),
                         round(float(scores["fused"][i][c]), 6), int(rank_of["lexical"][i][c]),
                         int(rank_of["semantic"][i][c]), bool(c in gold[i])))  # fmt: skip
    lists = pd.DataFrame(rows, columns=["parasha", "rank", "chapter", "fused", "lex_rank",
                                        "sem_rank", "haftarah"])  # fmt: skip

    out = art / "haftarot"
    out.mkdir(parents=True, exist_ok=True)
    pairs.to_parquet(out / "pairs.parquet", index=False)
    lists.to_parquet(out / "lists.parquet", index=False)
    meta = {
        "config_hash": config_hash(cfg, "haftarot", "fusion", "final_systems", "lexical",
                                   "sources"),  # fmt: skip
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "parashot": len(par), "candidates": n_cand, "thematic": int(thematic.sum()),
        "claim_mode": mode, "shuffles": reps, "alpha": alpha, "list": k,
        "thematic_pct": round(float(pct[idx].mean()), 4), "shuffled_pct": round(null1, 4),
        "p": p1, "holds": holds1,
        "calendar_pct": round(float(pct[~thematic].mean()), 4), "difference": round(diff2, 4),
        "calendar_p": p2, "calendar_holds": holds2,
        "modes": evals, "known": known_rows, "known_rank": int(hc["known_rank"]),
        "known_holds": known_holds,
        "seconds": round(time.perf_counter() - t0, 1),
    }  # fmt: skip
    (out / "haftarot.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
    log(f"done: claim {'holds' if holds1 else 'not borne out'}, calendar"
        f" {'holds' if holds2 else 'not borne out'}, known {[r['rank'] for r in known_rows]}"
        f" ({meta['seconds']} s) -> {out}")  # fmt: skip
    return out / "pairs.parquet"
