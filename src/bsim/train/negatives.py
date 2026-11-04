"""Hard negatives for the supervised fine-tune (DESIGN.md §7.2, §16.80).

For each training pair (`train/pairs.py`: Sefaria's train-split verse links, plus the
`extra_pairs` sources), one negative is drawn uniformly from the anchor's list (±window
neighbours removed, as in the eval report) within ranks
`train.supervised.hard_negative_rank_range`. A candidate is excluded when it
- is verse-linked (any split, any source used) to the anchor or to the positive,
- lies in a non-train book (dev/test books never enter training),
- is within ±window same-book verses of the anchor or the positive,
- has the same `text_model` as the anchor or the positive (repeated formula verses).
When nothing is eligible, a random train-book verse passing the same checks is used (`fallback`).
With `extra_pairs: [labels]` (D132), a verse you labelled `not` connected to the anchor (both
train books) is taken first when it passes the same checks (`from_label`, rank -1): a negative
known to be one, where a BM25 neighbour is only presumed to be.

The list is `train.supervised.negatives_from` (D133):
- `bm25`: the `bm25_lemma` list, verses that share words with the anchor (the pipeline's model);
- `self`: the model in use's own semantic list (`self_system`), the verses it wrongly ranks
  near the anchor;
- `self_ce`: the same, and a drawn negative the cross-encoder (`rerank.output`, §16.3) scores
  above `ce_max` is taken for a link no gold records and drawn again (`redrawn` counts the
  draws refused). Its scores come from the `fused_rerank` list where it has the pair, else the
  cross-encoder is run (on the GPU) for the pairs drawn. Fallbacks are not screened.

Writes `paths.artifacts/train/{name}.parquet` (anchor_vid, positive_vid, source, negative_vid,
negative_rank (0 for fallbacks, -1 for your labels), fallback, from_label, redrawn) and a
`.meta.json`
with counts; `name` is `hard_negatives` for the pipeline's model, another for an experiment's
(§16.41).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path, write_meta
from bsim.data.canon import BY_SEFARIA
from bsim.retrieve.filters import apply_filters
from bsim.retrieve.topk import read_topk
from bsim.train.common import Log
from bsim.train.pairs import LABELS, label_negatives, training_pairs

LEXICAL_SYSTEM = "bm25_lemma"
NEGATIVES_FROM = ("bm25", "self", "self_ce")
# (anchors, candidates) -> whether each pair may be a negative (`self_ce`'s screen)
Accept = Callable[[np.ndarray, np.ndarray], np.ndarray]
MAX_FALLBACK_TRIES = 1000


def linked_sets(links: pd.DataFrame) -> dict[int, set[int]]:
    """Verse-level links of every split: verse -> linked verses (both directions stored).
    A frame without `level` holds verse pairs only."""
    v = links[links.level == "verse"] if "level" in links else links
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
    labelled_not: dict[int, set[int]] | None = None,
    accept: Accept | None = None,
) -> pd.DataFrame:
    """One negative per (anchor, positive) row.

    `candidates`: a neighbour-filtered top-k with integer `src`, `tgt`, `rank`.
    `train_book`: bool per book_id. `text_key`: per-verse id of its text (equal text = equal key).
    `labelled_not`: verse -> verses you labelled not connected to it, taken first when eligible.
    `accept`: a screen of the negatives drawn from the list, asked once per (anchor, candidate);
    a refused one is drawn again from what is left, in rounds, until every draw is accepted (or
    the row falls back). Without it the draws are those of a single pass.
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

    def random_negative(a: int, p: int) -> int:
        for _ in range(MAX_FALLBACK_TRIES):
            c = int(train_vids[rng.integers(len(train_vids))])
            if ok(c, a, p):
                return c
        raise RuntimeError(f"no eligible negative for anchor {a}, positive {p}")

    n = len(anchors)
    anchors_l, positives_l = anchors.tolist(), positives.tolist()
    neg = np.empty(n, np.int32)
    rank = np.zeros(n, np.int32)
    fallback = np.zeros(n, bool)
    from_label = np.zeros(n, bool)
    redrawn = np.zeros(n, np.int32)
    pools: dict[int, list[int]] = {}  # row -> the list positions still eligible (list draws only)
    labelled_not = labelled_not or {}
    empty = (np.zeros(0, np.int32), np.zeros(0, np.int32))
    for i, (a, p) in enumerate(zip(anchors_l, positives_l, strict=True)):
        mine = [c for c in sorted(labelled_not.get(a, ())) if ok(c, a, p)]
        if mine:
            neg[i], rank[i], from_label[i] = mine[rng.integers(len(mine))], -1, True
            continue
        tgts, ranks = by_src.get(a, empty)
        keep = [j for j, c in enumerate(tgts.tolist()) if ok(c, a, p)]
        if keep:
            j = keep[rng.integers(len(keep))]
            neg[i], rank[i] = tgts[j], ranks[j]
            pools[i] = keep
            continue
        neg[i], fallback[i] = random_negative(a, p), True

    verdict: dict[tuple[int, int], bool] = {}
    while accept is not None and pools:
        ask = sorted({(anchors_l[i], int(neg[i])) for i in pools} - verdict.keys())
        if ask:
            a_arr, c_arr = (np.array(x, np.int64) for x in zip(*ask, strict=True))
            verdict.update(zip(ask, map(bool, accept(a_arr, c_arr)), strict=True))
        refused = sorted(i for i in pools if not verdict[(anchors_l[i], int(neg[i]))])
        pools = {i: pools[i] for i in refused}  # the others are settled
        if not refused:
            break
        for i in refused:
            a, p = anchors_l[i], positives_l[i]
            tgts, ranks = by_src[a]
            keep = [j for j in pools[i] if verdict.get((a, int(tgts[j])), True)]
            redrawn[i] += 1
            if keep:
                j = keep[rng.integers(len(keep))]
                neg[i], rank[i] = tgts[j], ranks[j]
                pools[i] = keep
            else:
                neg[i], rank[i], fallback[i] = random_negative(a, p), 0, True
                del pools[i]
    return pd.DataFrame(
        {
            "anchor_vid": anchors.astype(np.int32),
            "positive_vid": positives.astype(np.int32),
            "negative_vid": neg,
            "negative_rank": rank,
            "fallback": fallback,
            "from_label": from_label,
            "redrawn": redrawn,
        }
    )


def ce_accept(cfg: dict[str, Any], texts: list[str], log: Log) -> Accept:
    """`self_ce`'s screen: a pair is accepted when the cross-encoder scores it at most
    `train.supervised.ce_max`. Scores of the stored `fused_rerank` list are reused (same
    direction, anchor first); the others are computed, loading the cross-encoder on first need."""
    from bsim.train.rerank import load_reranker, score_pairs

    art = resolve_path(cfg, "artifacts")
    ce_max, batch = cfg["train"]["supervised"]["ce_max"], cfg["rerank"]["eval_batch_size"]
    path = art / "topk" / "verse" / f"{cfg['rerank']['system']}.parquet"
    stored: dict[tuple[int, int], float] = {}
    if path.exists():
        df = read_topk(path)
        stored = dict(
            zip(
                zip(df.src.tolist(), df.tgt.tolist(), strict=True),
                df.ce_score.tolist(),
                strict=True,
            )
        )
    model: list[Any] = []

    def accept(a: np.ndarray, c: np.ndarray) -> np.ndarray:
        score = np.array(
            [stored.get(k, np.nan) for k in zip(a.tolist(), c.tolist(), strict=True)], np.float32
        )
        todo = np.flatnonzero(np.isnan(score))
        if len(todo):
            if not model:
                model.append(load_reranker(cfg))
            score[todo] = score_pairs(model[0], texts, a[todo], c[todo], batch)
        log(
            f"  cross-encoder: {len(a)} drawn negatives ({len(todo)} scored now), "
            f"{int((score > ce_max).sum())} above {ce_max}"
        )
        return score <= ce_max

    accept.release = model.clear  # type: ignore[attr-defined]
    return accept


def run_hard_negatives(
    cfg: dict[str, Any], log: Log = print, name: str = "hard_negatives"
) -> pd.DataFrame:
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    sup = cfg["train"]["supervised"]
    source = sup["negatives_from"]
    if source not in NEGATIVES_FROM:
        raise RuntimeError(f"negatives_from must be one of {NEGATIVES_FROM}, not {source!r}")
    system = LEXICAL_SYSTEM if source == "bm25" else sup["self_system"]
    topk_path = art / "topk" / "verse" / f"{system}.parquet"
    if not topk_path.exists():
        raise RuntimeError(f"{topk_path} missing; run `bsim topk --system {system}` first")
    for file, cmd in (("verses.parquet", "build-corpus"), ("links.parquet", "build-links")):
        if not (proc / file).exists():
            raise RuntimeError(f"{proc / file} missing; run `bsim {cmd}` first")

    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "text_model"]
    ).sort_values("verse_id")
    book_id, chapter = verses.book_id.to_numpy(), verses.chapter.to_numpy()
    text_key, _ = pd.factorize(verses.text_model)
    splits = json.loads((proc / "splits.json").read_text("utf-8"))
    train_book = np.zeros(int(book_id.max()) + 1, bool)
    for book, split in splits["books"].items():
        train_book[BY_SEFARIA[book].book_id] = split == "train"

    train, linked = training_pairs(cfg)
    window = cfg["retrieval"]["neighbor_window"]
    candidates = apply_filters(read_topk(topk_path), book_id, chapter, {"neighbors"}, window)
    lo, hi = sup["hard_negative_rank_range"]
    labelled_not = label_negatives(cfg) if LABELS in sup["extra_pairs"] else {}
    accept = ce_accept(cfg, verses.text_model.tolist(), log) if source == "self_ce" else None
    df = mine_hard_negatives(
        train.src_vid.to_numpy(),
        train.tgt_vid.to_numpy(),
        candidates,
        book_id,
        train_book,
        linked_sets(linked),
        text_key,
        (int(lo), int(hi)),
        window,
        cfg["seed"],
        labelled_not,
        accept,
    )
    if accept is not None:
        accept.release()  # type: ignore[attr-defined]
        _free_gpu()
    df.insert(2, "source", train.source.to_numpy())

    out = art / "train"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / f"{name}.parquet", index=False)
    n_fb = int(df.fallback.sum())
    meta = {
        "source": system,
        "negatives_from": source,
        "redrawn": int(df.redrawn.sum()),
        "rows_redrawn": int((df.redrawn > 0).sum()),
        "rows": len(df),
        "by_source": {str(k): int(v) for k, v in df.source.value_counts().sort_index().items()},
        "fallbacks": n_fb,
        "from_labels": int(df.from_label.sum()),
        "label_not_pairs": sum(map(len, labelled_not.values())) // 2,
        "label_not_pairs_used": len(
            {
                (min(a, n), max(a, n))
                for a, n in zip(
                    df.anchor_vid[df.from_label], df.negative_vid[df.from_label], strict=True
                )
            }
        ),
        "distinct_negatives": int(df.negative_vid.nunique()),
        "rank_range": [int(lo), int(hi)],
        "config_hash": config_hash(cfg, "train", "retrieval", "seed"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    write_meta(out / f"{name}.meta.json", meta)
    log(
        f"hard negatives: {len(df)} train rows ({meta['by_source']}), {n_fb} fallbacks, "
        f"{meta['distinct_negatives']} distinct negatives from {system}"
        + (f"; {meta['redrawn']} draws refused by the cross-encoder" if accept is not None else "")
        + (
            f"; {meta['from_labels']} from your labels"
            f" ({meta['label_not_pairs_used']} of {meta['label_not_pairs']} not pairs)"
            if labelled_not
            else ""
        )
    )
    return df


def _free_gpu() -> None:
    import gc

    gc.collect()
    try:
        import torch
    except ImportError:  # pragma: no cover
        return
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
