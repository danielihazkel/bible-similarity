"""`bsim topk`: verse-level top-k for a system (DESIGN.md §6.1).

Scores are computed in row chunks (`retrieval.chunk_size`) and reduced with `torch.topk` on
`retrieval.device` (cuda, or cpu when unavailable); the full N x N matrix never exists. Only self
is excluded here; neighbour / chapter / book exclusion happens at query time (`filters.py`).

- sparse (lexical) systems: `artifacts/lexical/{name}.{doc,query}.npz`, scores `query @ doc.T`
  per chunk on the CPU; hits with score <= 0 (no shared terms) are dropped.
- dense systems: `artifacts/embeddings/{name}.npy` (L2-normalized fp32), scores `E[chunk] @ E.T`.

Writes `artifacts/topk/verse/{name}.parquet` (unit_type, src_id, rank, tgt_id, score; ranks are
1-based, ids `v:{verse_id}`) and `{name}.meta.json`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

from bsim.config import config_hash, resolve_path
from bsim.lexical import bm25

Log = Callable[[str], None]
ScoreFn = Callable[[int, int], "np.ndarray | torch.Tensor"]

VERSE_PREFIX = "v:"


def get_device(name: str) -> torch.device:
    if name.startswith("cuda") and torch.cuda.is_available():
        return torch.device(name)
    return torch.device("cpu")


def topk_chunks(
    score_fn: ScoreFn, n_rows: int, k: int, chunk_size: int, device: torch.device
) -> tuple[np.ndarray, np.ndarray]:
    """Top-k columns per row of an `n_rows x n_rows` score matrix, self (the diagonal) excluded.

    Returns (idx int32, score float32), each `n_rows x k`, sorted by score descending, ties by
    target id ascending.
    """
    k = min(k, n_rows - 1)
    idx_parts, score_parts = [], []
    for start in range(0, n_rows, chunk_size):
        stop = min(start + chunk_size, n_rows)
        block = torch.as_tensor(score_fn(start, stop), dtype=torch.float32, device=device)
        rows = torch.arange(stop - start, device=device)
        block[rows, rows + start] = -torch.inf
        sc, ix = torch.topk(block, k, dim=1)
        idx_parts.append(ix.cpu().numpy().astype(np.int32))
        score_parts.append(sc.cpu().numpy())
    idx = np.concatenate(idx_parts) if idx_parts else np.zeros((0, k), np.int32)
    score = np.concatenate(score_parts) if score_parts else np.zeros((0, k), np.float32)
    order = np.lexsort((idx, -score), axis=1)
    return np.take_along_axis(idx, order, axis=1), np.take_along_axis(score, order, axis=1)


def sparse_scorer(index: bm25.Bm25Index) -> ScoreFn:
    return lambda start, stop: bm25.scores(index, slice(start, stop))


def dense_scorer(emb: np.ndarray, device: torch.device) -> ScoreFn:
    e = torch.as_tensor(np.ascontiguousarray(emb, dtype=np.float32), device=device)
    return lambda start, stop: e[start:stop] @ e.T


def topk_frame(idx: np.ndarray, score: np.ndarray, drop_nonpositive: bool = False) -> pd.DataFrame:
    """Top-k arrays -> the verse top-k Parquet schema."""
    keep = np.isfinite(score)
    if drop_nonpositive:
        keep &= score > 0
    rank = np.cumsum(keep, axis=1)
    src = np.broadcast_to(np.arange(len(idx))[:, None], idx.shape)
    return pd.DataFrame(
        {
            "unit_type": "verse",
            "src_id": verse_ids(src[keep]),
            "rank": rank[keep].astype(np.int32),
            "tgt_id": verse_ids(idx[keep]),
            "score": score[keep].astype(np.float32),
        }
    )


def verse_ids(vids: np.ndarray) -> np.ndarray:
    return np.char.add(VERSE_PREFIX, np.asarray(vids).astype(str)).astype(object)


def parse_verse_ids(ids: pd.Series) -> np.ndarray:
    return ids.str.removeprefix(VERSE_PREFIX).astype(np.int32).to_numpy()


def read_topk(path: Path) -> pd.DataFrame:
    """A top-k Parquet; verse files get integer `src` / `tgt` columns."""
    df = pd.read_parquet(path)
    if len(df) and (df.unit_type == "verse").all():
        df["src"] = parse_verse_ids(df.src_id)
        df["tgt"] = parse_verse_ids(df.tgt_id)
    return df


@dataclass
class Source:
    kind: str  # sparse | dense
    path: Path
    n: int
    scorer: Callable[[torch.device], ScoreFn]
    source_hash: str | None


def resolve_system(cfg: dict[str, Any], name: str) -> Source:
    art = resolve_path(cfg, "artifacts")
    lex_dir, emb_path = art / "lexical", art / "embeddings" / f"{name}.npy"
    if (lex_dir / f"{name}.doc.npz").exists():
        index = bm25.load(lex_dir, name)
        meta_path = lex_dir / "lexical_meta.json"
        meta = json.loads(meta_path.read_text("utf-8")) if meta_path.exists() else {}
        return Source(
            "sparse",
            lex_dir / f"{name}.doc.npz",
            index.doc.shape[0],
            lambda _device: sparse_scorer(index),
            meta.get("config_hash"),
        )
    if emb_path.exists():
        emb = np.load(emb_path, mmap_mode="r")
        meta_path = emb_path.with_suffix(".meta.json")
        meta = json.loads(meta_path.read_text("utf-8")) if meta_path.exists() else {}
        return Source(
            "dense",
            emb_path,
            emb.shape[0],
            lambda device: dense_scorer(emb, device),
            meta.get("config_hash"),
        )
    raise RuntimeError(
        f"unknown system {name!r}: neither {lex_dir / (name + '.doc.npz')} nor {emb_path} "
        "exists; run `bsim lexical` or `bsim embed` first"
    )


def run_topk(cfg: dict[str, Any], system: str, log: Log = print) -> pd.DataFrame:
    r = cfg["retrieval"]
    src = resolve_system(cfg, system)
    device = get_device(r["device"])
    log(f"{system}: {src.kind} top-{r['k']} over {src.n} verses on {device}")
    idx, score = topk_chunks(src.scorer(device), src.n, r["k"], r["chunk_size"], device)
    df = topk_frame(idx, score, drop_nonpositive=src.kind == "sparse")

    out = resolve_path(cfg, "artifacts") / "topk" / "verse"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / f"{system}.parquet", index=False)
    meta = {
        "system": system,
        "kind": src.kind,
        "source": src.path.name,
        "source_config_hash": src.source_hash,
        "config_hash": config_hash(cfg, "retrieval"),
        "k": int(r["k"]),
        "device": str(device),
        "rows": len(df),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (out / f"{system}.meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    short = src.n - int((df.groupby("src_id").size() >= r["k"]).sum())
    log(f"  wrote {out / (system + '.parquet')}: {len(df)} rows ({short} verses with < k hits)")
    return df
