"""Score an in-memory embedding matrix exactly as `bsim topk` + `bsim evaluate` would (§8.3).

Used for epoch / checkpoint selection during training: dense top-k (self excluded), the ±window
same-book neighbour filter, then the macro-averaged verse metrics of a split.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from bsim.config import resolve_path
from bsim.eval.metrics import evaluate_system
from bsim.eval.report import gold_pairs, ranked_lists
from bsim.retrieve.filters import apply_filters
from bsim.retrieve.topk import (
    dense_scorer,
    get_device,
    parse_verse_ids,
    topk_chunks,
    topk_frame,
)


class DevEvaluator:
    def __init__(self, cfg: dict[str, Any], split: str = "dev") -> None:
        proc = resolve_path(cfg, "data_processed")
        for name, cmd in (("verses.parquet", "build-corpus"), ("links.parquet", "build-links")):
            if not (proc / name).exists():
                raise RuntimeError(f"{proc / name} missing; run `bsim {cmd}` first")
        verses = pd.read_parquet(
            proc / "verses.parquet", columns=["verse_id", "book_id", "chapter"]
        ).sort_values("verse_id")
        self.book_id = verses.book_id.to_numpy()
        self.chapter = verses.chapter.to_numpy()
        self.gold = gold_pairs(pd.read_parquet(proc / "links.parquet"), split)
        if not self.gold:
            raise RuntimeError(f"no verse-level gold links in split {split!r}")
        self.split = split
        r, ev = cfg["retrieval"], cfg["eval"]
        self.k, self.chunk_size, self.window = r["k"], r["chunk_size"], r["neighbor_window"]
        self.device = get_device(r["device"])
        self.ks, self.rank_k = ev["ks"], ev["rank_k"]

    def __call__(self, emb: np.ndarray) -> dict[str, float]:
        if emb.shape[0] != len(self.book_id):
            raise RuntimeError(f"{emb.shape[0]} embeddings for {len(self.book_id)} verses")
        idx, score = topk_chunks(
            dense_scorer(emb, self.device), emb.shape[0], self.k, self.chunk_size, self.device
        )
        df = topk_frame(idx, score)
        df["src"] = parse_verse_ids(df.src_id)
        df["tgt"] = parse_verse_ids(df.tgt_id)
        filtered = apply_filters(df, self.book_id, self.chapter, {"neighbors"}, self.window)
        return evaluate_system(ranked_lists(filtered), self.gold, self.ks, self.rank_k)
