"""`bsim citations`: the passages that say they quote or fulfil another (DESIGN.md §16.31).

A *citation* is a verse with an explicit formula of reference (`citations.families`, regular
expressions over the consonantal text):

- `written`: "as it is written (in the book of the law of Moses)" — ככתוב, ככל הכתוב, כתוב בספר;
  its source is sought in the Torah;
- `word`: "according to the word of the LORD which he spoke (by his servant …)" — the fulfilment
  notices of Kings; its source is sought anywhere earlier in the canon;
- `command`: "as the LORD commanded Moses" — compliance with an earlier command, sought in the
  Torah before the verse.

**Source.** Every allowed verse (`target`: `torah` or `earlier`, never within `min_distance`
verses of the citation) is scored by the citing verse's BM25 (final lexical lemma index) and
embedding cosine (final semantic system), each z-scored over the allowed verses; the score is
their mean, the best verse is the source, and the next `candidates` are kept.

**Resolved** when the two signals agree: the best verse by BM25 alone and by cosine alone both
lie within `agree_window` verses of the source. A best match is not evidence by itself — almost
any verse finds a close match among ten thousand (the corpus repeats its formulas) — so each
family's agreement rate is compared with the rate of `null_samples` random verses of the same
books (no formula, the same rules; binomial, one-sided), and each citation's score gets its
percentile among those verses' best scores (`pct`, descriptive). **Check:** `citations.gold`,
sources named by scholarship, scored as hits at rank 1 and within the candidates
(± `gold_window` verses), and as resolved or not.

The resolved citations form a directed graph — the one direction in the corpus that the text
itself states — summed per book pair.

Writes `artifacts/citations/`: `citations.parquet`, `books.parquet` and `citations.meta.json`.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS
from bsim.data.refs import parse_range
from bsim.lexical import bm25

Log = Callable[[str], None]

TORAH = {b.book_id for b in BOOKS if b.section == "Torah"}
CITATION_COLUMNS = [
    "cite_id",
    "family",
    "verse_id",
    "book_id",
    "formula",
    "target_vid",
    "target_book",
    "score",
    "pct",
    "resolved",
    "candidates",
    "gold",
    "gold_rank",
]


def find_formulas(verses: pd.DataFrame, families: dict[str, dict[str, Any]]) -> pd.DataFrame:
    """(verse_id, book_id, family, formula) for every verse matching a family's pattern; a verse
    matching several families keeps the first in config order."""
    rows, seen = [], set()
    for fam, spec in families.items():
        pat = re.compile(spec["pattern"])
        for v, b, text in zip(verses.verse_id, verses.book_id, verses.text_plain, strict=True):
            m = pat.search(text)
            if m and v not in seen:
                seen.add(v)
                rows.append((int(v), int(b), fam, m.group(0)))
    return pd.DataFrame(rows, columns=["verse_id", "book_id", "family", "formula"])


def allowed(target: str, source: int, book_of: np.ndarray, min_distance: int) -> np.ndarray:
    """Verses a citation in `source` may point to: earlier, at least `min_distance` away, and in
    the Torah when `target` is `torah`."""
    n = len(book_of)
    ok = np.arange(n) <= source - min_distance
    if target == "torah":
        ok &= np.isin(book_of, list(TORAH))
    return ok


def zscore(x: np.ndarray) -> np.ndarray:
    sd = x.std()
    return (x - x.mean()) / sd if sd > 0 else np.zeros_like(x)


def best_sources(
    rows: list[int],
    masks: list[np.ndarray],
    index: bm25.Bm25Index,
    emb: np.ndarray,
    keep: int,
    agree_window: int,
    chunk: int = 256,
) -> list[tuple[list[int], list[float], bool]]:
    """For each query verse, its `keep` best allowed verses, their scores (mean z of BM25 and
    cosine over the allowed verses) and whether BM25 alone and cosine alone pick a verse within
    `agree_window` of the best."""
    out: list[tuple[list[int], list[float], bool]] = []
    for lo in range(0, len(rows), chunk):
        r = np.asarray(rows[lo : lo + chunk])
        lex = bm25.scores(index, r)
        sem = emb[r] @ emb.T
        for i, mask in enumerate(masks[lo : lo + chunk]):
            ci = np.flatnonzero(mask)
            if len(ci) == 0:
                out.append(([], [], False))
                continue
            li, si = lex[i, ci], sem[i, ci]
            s = (zscore(li) + zscore(si)) / 2
            top = np.argsort(-s, kind="stable")[:keep]
            best = ci[top[0]]
            agree = all(abs(int(ci[x.argmax()]) - best) <= agree_window for x in (li, si))
            out.append(([int(ci[t]) for t in top], [float(s[t]) for t in top], bool(agree)))
    return out


def gold_targets(
    gold: list[list[str]], key: dict[tuple[int, int, int], int]
) -> dict[int, list[tuple[int, int]]]:
    """source verse id -> the (first, last) verse ids of its named sources."""
    out: dict[int, list[tuple[int, int]]] = {}
    for src, *targets in gold:
        b, (c1, v1), _ = parse_range(src)
        s = key[(b.book_id, c1, v1)]
        for t in targets:
            tb, (a1, b1), (a2, b2) = parse_range(t)
            out.setdefault(s, []).append((key[(tb.book_id, a1, b1)], key[(tb.book_id, a2, b2)]))
    return out


def gold_rank(cands: list[int], spans: list[tuple[int, int]], window: int) -> int | None:
    """1-based rank of the first candidate within `window` verses of a named source."""
    for i, c in enumerate(cands, start=1):
        if any(a - window <= c <= b + window for a, b in spans):
            return i
    return None


def run_citations(cfg: dict[str, Any], log: Log = print) -> Path:
    from bsim.analysis.structure import embeddings_path

    cc = cfg["citations"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    t0 = time.perf_counter()
    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "verse", "text_plain"]
    ).sort_values("verse_id")
    book_of = verses.book_id.to_numpy()
    index = bm25.load(art / "lexical", cfg["final_systems"]["lexical"])
    emb_path = embeddings_path(cfg)
    if not emb_path.exists():
        raise RuntimeError(f"{emb_path} missing; run `bsim embed` for the semantic system first")
    emb = np.load(emb_path).astype(np.float32)
    emb /= np.maximum(np.linalg.norm(emb, axis=1, keepdims=True), 1e-12)

    fams = cc["families"]
    found = find_formulas(verses, fams)
    rng = np.random.default_rng(cc["seed"])
    keep, dist, aw = cc["candidates"], cc["min_distance"], cc["agree_window"]

    def masks_for(vids: list[int], fam: str) -> list[np.ndarray]:
        return [allowed(fams[fam]["target"], v, book_of, dist) for v in vids]

    best = []
    for fam, g in found.groupby("family", sort=False):
        vids = g.verse_id.tolist()
        best += list(
            zip(
                g.index, best_sources(vids, masks_for(vids, fam), index, emb, keep, aw), strict=True
            )
        )
    best = [b for _, b in sorted(best, key=lambda x: x[0])]
    found["candidates"] = [
        json.dumps([[c, round(s, 3)] for c, s in zip(b[0], b[1], strict=True)]) for b in best
    ]
    found["resolved"] = [int(b[2]) for b in best]
    found["target_vid"] = [b[0][0] if b[0] else None for b in best]
    found["score"] = [b[1][0] if b[1] else np.nan for b in best]

    # null: random verses of the same books without a formula, resolved the same way
    nulls: dict[str, np.ndarray] = {}
    null_agree: dict[str, float] = {}
    formula_vids = set(found.verse_id)
    for fam, g in found.groupby("family"):
        pool = verses[verses.book_id.isin(g.book_id) & ~verses.verse_id.isin(formula_vids)]
        sample = rng.choice(
            pool.verse_id.to_numpy(), min(cc["null_samples"], len(pool)), replace=False
        )
        sample = [int(v) for v in sample]
        res = [r for r in best_sources(sample, masks_for(sample, fam), index, emb, 1, aw) if r[1]]
        nulls[fam] = np.array([r[1][0] for r in res])
        null_agree[fam] = float(np.mean([r[2] for r in res])) if res else 0.0
    found["pct"] = [
        float((nulls[f] < s).mean()) if not np.isnan(s) else np.nan
        for s, f in zip(found.score, found.family, strict=True)
    ]
    found["target_book"] = [int(book_of[t]) if t is not None else None for t in found.target_vid]

    key = {
        (int(b), int(c), int(v)): int(i)
        for i, b, c, v in verses[["verse_id", "book_id", "chapter", "verse"]].itertuples(
            index=False
        )
    }
    gold = gold_targets(cc["gold"], key)
    window = cc["gold_window"]
    found["gold"] = [json.dumps(gold[v]) if v in gold else None for v in found.verse_id]
    found["gold_rank"] = [
        gold_rank([c for c, _ in json.loads(cands)], gold[v], window) if v in gold else None
        for v, cands in zip(found.verse_id, found.candidates, strict=True)
    ]
    found = found.sort_values("verse_id", kind="stable").reset_index(drop=True)
    found.insert(0, "cite_id", np.arange(1, len(found) + 1))
    for c in ("target_vid", "target_book", "gold_rank"):
        found[c] = found[c].astype("Int64")

    res = found[found.resolved == 1]
    books = (
        res.groupby(["book_id", "target_book"]).size().rename("n").reset_index()
        .sort_values(["n", "book_id"], ascending=[False, True])
    )  # fmt: skip
    in_gold = found[found.gold.notna()]
    missing_gold = sorted(set(gold) - set(found.verse_id))
    by_family = {}
    for fam in fams:
        g = found[found.family == fam]
        k, n, rate = int(g.resolved.sum()), int(len(g)), null_agree.get(fam)
        by_family[fam] = {
            "verses": n,
            "resolved": k,
            "share": k / n if n else None,
            "null_share": rate,
            "p": float(binomtest(k, n, rate, alternative="greater").pvalue)
            if n and rate is not None and 0 < rate < 1
            else None,
            "pct_median": float(g.pct.median()) if n else None,
        }
    word = res[res.family == "word"]
    lag = word.verse_id.to_numpy() - word.target_vid.to_numpy(dtype=float)
    meta = {
        "config_hash": config_hash(cfg, "citations", "final_systems"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "citations": int(len(found)),
        "resolved": int(found.resolved.sum()),
        "families": by_family,
        "gold": {
            "named": len(gold),
            "found": int(len(in_gold)),
            "missing": [_ref(verses, v) for v in missing_gold],
            "top1": int((in_gold.gold_rank == 1).sum()),
            "top_k": int(in_gold.gold_rank.notna().sum()),
            "k": keep,
            "resolved": int(in_gold.resolved.sum()),
            "resolved_right": int(((in_gold.resolved == 1) & (in_gold.gold_rank == 1)).sum()),
        },
        "word_lag_median": float(np.median(lag)) if len(lag) else None,
        "book_pairs": int(len(books)),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    out = art / "citations"
    out.mkdir(parents=True, exist_ok=True)
    found[CITATION_COLUMNS].to_parquet(out / "citations.parquet")
    books.to_parquet(out / "books.parquet")
    (out / "citations.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    g = meta["gold"]
    log(
        f"done: {meta['citations']} citations, {meta['resolved']} resolved; gold {g['top1']} / "
        f"{g['found']} at rank 1, {g['top_k']} in the top {keep} ({meta['seconds']} s) -> {out}"
    )
    return out


def _ref(verses: pd.DataFrame, vid: int) -> str:
    r = verses[verses.verse_id == vid].iloc[0]
    return f"{BOOKS[int(r.book_id)].sefaria} {r.chapter}:{r.verse}"
