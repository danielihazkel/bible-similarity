"""BM25 hard negatives for the supervised fine-tune (DESIGN.md §7.2).

For each train-split (anchor, positive) verse link, one negative is drawn uniformly from the
anchor's `bm25_lemma` list (±window neighbours removed, as in the eval report) within ranks
`train.supervised.hard_negative_rank_range`. A candidate is excluded when it
- is verse-linked (any split) to the anchor or to the positive,
- lies in a non-train book (dev/test books never enter training),
- is within ±window same-book verses of the anchor or the positive,
- has the same `text_model` as the anchor or the positive (repeated formula verses).
When nothing is eligible, a random train-book verse passing the same checks is used (`fallback`).

Writes `paths.artifacts/train/hard_negatives.parquet` (anchor_vid, positive_vid, negative_vid,
negative_rank (0 for fallbacks), fallback) and a `.meta.json` with counts.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.data.canon import BY_SEFARIA
from bsim.retrieve.filters import apply_filters
from bsim.retrieve.topk import read_topk
from bsim.train.common import Log

LEXICAL_SYSTEM = "bm25_lemma"
MAX_FALLBACK_TRIES = 1000


def linked_sets(links: pd.DataFrame) -> dict[int, set[int]]:
    """Verse-level links of every split: verse -> linked verses (both directions stored)."""
    v = links[links.level == "verse"]
    out: dict[int, set[int]] = {}
    for s, t in zip(v.src_vid.to_numpy(), v.tgt_vid.to_numpy(), strict=True):
        out.setdefault(int(s), set()).add(int(t))
    return out


def mine_hard_negatives(
    anchors: np.ndarray,
    positives: np.ndarray,
    candidates: pd.DataFrame,
    book_id: np.ndarray,
    train_book: np.ndarray,
    linked: dict[int, set[int]],
    text_key: np.ndarray,
    rank_range: tuple[int, int],
    window: int,
    seed: int,
) -> pd.DataFrame:
    """One negative per (anchor, positive) row.

    `candidates`: neighbour-filtered lexical top-k with integer `src`, `tgt`, `rank`.
    `train_book`: bool per book_id. `text_key`: per-verse id of its text (equal text = equal key).
    """
    lo, hi = rank_range
    cand = candidates[(candidates["rank"] >= lo) & (candidates["rank"] <= hi)]
    cand = cand.sort_values(["src", "rank"], kind="stable")
    by_src = {
        int(s): (g.tgt.to_numpy(), g["rank"].to_numpy()) for s, g in cand.groupby("src", sort=False)
    }
    train_vids = np.flatnonzero(train_book[book_id])
    rng = np.random.default_rng(seed)

    def ok(c: int, a: int, p: int) -> bool:
        if not train_book[book_id[c]] or c in (a, p):
            return False
        if c in linked.get(a, ()) or c in linked.get(p, ()):
            return False
        for x in (a, p):
            if book_id[x] == book_id[c] and abs(x - c) <= window:
                return False
        return text_key[c] != text_key[a] and text_key[c] != text_key[p]

    neg = np.empty(len(anchors), np.int32)
    rank = np.zeros(len(anchors), np.int32)
    fallback = np.zeros(len(anchors), bool)
    for i, (a, p) in enumerate(zip(anchors.tolist(), positives.tolist(), strict=True)):
        tgts, ranks = by_src.get(a, (np.zeros(0, np.int32), np.zeros(0, np.int32)))
        keep = [j for j, c in enumerate(tgts.tolist()) if ok(c, a, p)]
        if keep:
            j = keep[rng.integers(len(keep))]
            neg[i], rank[i] = tgts[j], ranks[j]
            continue
        for _ in range(MAX_FALLBACK_TRIES):
            c = int(train_vids[rng.integers(len(train_vids))])
            if ok(c, a, p):
                break
        else:
            raise RuntimeError(f"no eligible negative for anchor {a}, positive {p}")
        neg[i], fallback[i] = c, True
    return pd.DataFrame(
        {
            "anchor_vid": anchors.astype(np.int32),
            "positive_vid": positives.astype(np.int32),
            "negative_vid": neg,
            "negative_rank": rank,
            "fallback": fallback,
        }
    )


def run_hard_negatives(cfg: dict[str, Any], log: Log = print) -> pd.DataFrame:
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    topk_path = art / "topk" / "verse" / f"{LEXICAL_SYSTEM}.parquet"
    if not topk_path.exists():
        raise RuntimeError(f"{topk_path} missing; run `bsim topk --system {LEXICAL_SYSTEM}` first")
    for name, cmd in (("verses.parquet", "build-corpus"), ("links.parquet", "build-links")):
        if not (proc / name).exists():
            raise RuntimeError(f"{proc / name} missing; run `bsim {cmd}` first")

    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "text_model"]
    ).sort_values("verse_id")
    book_id, chapter = verses.book_id.to_numpy(), verses.chapter.to_numpy()
    text_key, _ = pd.factorize(verses.text_model)
    splits = json.loads((proc / "splits.json").read_text("utf-8"))
    train_book = np.zeros(int(book_id.max()) + 1, bool)
    for name, split in splits["books"].items():
        train_book[BY_SEFARIA[name].book_id] = split == "train"

    links = pd.read_parquet(proc / "links.parquet")
    train = links[(links.level == "verse") & (links.split == "train")]
    sup, window = cfg["train"]["supervised"], cfg["retrieval"]["neighbor_window"]
    candidates = apply_filters(read_topk(topk_path), book_id, chapter, {"neighbors"}, window)
    lo, hi = sup["hard_negative_rank_range"]
    df = mine_hard_negatives(
        train.src_vid.to_numpy(),
        train.tgt_vid.to_numpy(),
        candidates,
        book_id,
        train_book,
        linked_sets(links),
        text_key,
        (int(lo), int(hi)),
        window,
        cfg["seed"],
    )

    out = art / "train"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "hard_negatives.parquet", index=False)
    n_fb = int(df.fallback.sum())
    meta = {
        "source": LEXICAL_SYSTEM,
        "rows": len(df),
        "fallbacks": n_fb,
        "distinct_negatives": int(df.negative_vid.nunique()),
        "rank_range": [int(lo), int(hi)],
        "config_hash": config_hash(cfg, "train", "retrieval", "seed"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (out / "hard_negatives.meta.json").write_text(json.dumps(meta, indent=2) + "\n", "utf-8")
    log(
        f"hard negatives: {len(df)} train rows, {n_fb} fallbacks, "
        f"{meta['distinct_negatives']} distinct negatives"
    )
    return df
