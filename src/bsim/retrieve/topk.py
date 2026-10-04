"""`bsim topk`: verse-level top-k for a system (DESIGN.md §6.1).

Scores are computed in row chunks (`retrieval.chunk_size`) and reduced with `torch.topk` on
`retrieval.device` (cuda, or cpu when unavailable); the full N x N matrix never exists. Only self
is excluded here; neighbour / chapter / book exclusion happens at query time (`filters.py`).

- sparse (lexical) systems: `artifacts/lexical/{name}.{doc,query}.npz`, scores `query @ doc.T`
  per chunk on the CPU; hits with score <= 0 (no shared terms) are dropped.
- dense systems: `artifacts/embeddings/{name}.npy` (L2-normalized fp32), scores `E[chunk] @ E.T`.
- `{base}_csls` systems: `artifacts/embeddings/{base}.npy` scored with CSLS (`embed/csls.py`);
  `r(·)` is computed here, and the stored scores are CSLS values, not cosines.

Writes `artifacts/topk/verse/{name}.parquet` (unit_type, src_id, rank, tgt_id, score; ranks are
1-based, ids `v:{verse_id}`) and `{name}.meta.json`. `Units`, `load_units` and `write_topk` are
shared with the unit-level stages (`units.py`, `fusion.py`).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
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
CSLS_SUFFIX = "_csls"


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
    # copy: emb may be a read-only memmap
    e = torch.as_tensor(np.array(emb, dtype=np.float32), device=device)
    return lambda start, stop: e[start:stop] @ e.T


def topk_frame(
    idx: np.ndarray,
    score: np.ndarray,
    drop_nonpositive: bool = False,
    unit_type: str = "verse",
    ids: np.ndarray | None = None,
) -> pd.DataFrame:
    """Top-k arrays -> the top-k Parquet schema. Rows are verse ids unless `ids` (unit ids in
    position order) is given."""
    keep = np.isfinite(score)
    if drop_nonpositive:
        keep &= score > 0
    rank = np.cumsum(keep, axis=1)
    src = np.broadcast_to(np.arange(len(idx))[:, None], idx.shape)
    to_id = verse_ids if ids is None else (lambda pos: np.asarray(ids, dtype=object)[pos])
    return pd.DataFrame(
        {
            "unit_type": unit_type,
            "src_id": to_id(src[keep]),
            "rank": rank[keep].astype(np.int32),
            "tgt_id": to_id(idx[keep]),
            "score": score[keep].astype(np.float32),
        }
    )


def verse_ids(vids: np.ndarray) -> np.ndarray:
    return np.char.add(VERSE_PREFIX, np.asarray(vids).astype(str)).astype(object)


def parse_verse_ids(ids: pd.Series) -> np.ndarray:
    return ids.str.removeprefix(VERSE_PREFIX).astype(np.int32).to_numpy()


def read_topk(path: Path, positions: Mapping[str, int] | None = None) -> pd.DataFrame:
    """A top-k Parquet with integer `src` / `tgt` columns: verse ids for verse files, else the
    unit positions from `positions` (`Units.position()`)."""
    df = pd.read_parquet(path)
    if positions is not None:
        df["src"] = df.src_id.map(positions).astype(np.int64)
        df["tgt"] = df.tgt_id.map(positions).astype(np.int64)
    elif len(df) and (df.unit_type == "verse").all():
        df["src"] = parse_verse_ids(df.src_id)
        df["tgt"] = parse_verse_ids(df.tgt_id)
    return df


@dataclass
class Units:
    """Units of one type in canon order (position = row of every unit-level matrix)."""

    ids: np.ndarray  # unit_id strings (object)
    start: np.ndarray  # first verse_id
    end: np.ndarray  # last verse_id (inclusive)

    def __len__(self) -> int:
        return len(self.ids)

    def position(self) -> dict[str, int]:
        return {u: i for i, u in enumerate(self.ids)}


def load_units(cfg: dict[str, Any], unit_type: str) -> Units:
    path = resolve_path(cfg, "data_processed") / "units.parquet"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim build-corpus` first")
    u = pd.read_parquet(path, columns=["unit_id", "unit_type", "start_verse_id", "end_verse_id"])
    u = u[u.unit_type == unit_type].sort_values("start_verse_id", kind="stable")
    if u.empty:
        raise RuntimeError(f"no units of type {unit_type!r} in {path}")
    return Units(
        u.unit_id.to_numpy(object),
        u.start_verse_id.to_numpy(np.int64),
        u.end_verse_id.to_numpy(np.int64),
    )


def write_topk(
    cfg: dict[str, Any], unit_type: str, system: str, df: pd.DataFrame, meta: dict[str, Any]
) -> Path:
    """Write `artifacts/topk/{unit_type}/{system}.parquet` + `.meta.json`."""
    out = resolve_path(cfg, "artifacts") / "topk" / unit_type
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / f"{system}.parquet", index=False)
    meta = {
        "system": system,
        "unit_type": unit_type,
        **meta,
        "rows": len(df),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (out / f"{system}.meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return out / f"{system}.parquet"


@dataclass
class Source:
    kind: str  # sparse | dense
    path: Path
    n: int
    scorer: Callable[[torch.device], ScoreFn]
    source_hash: str | None


def _load_embeddings(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    meta_path = path.with_suffix(".meta.json")
    meta = json.loads(meta_path.read_text("utf-8")) if meta_path.exists() else {}
    return np.load(path, mmap_mode="r"), meta


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
        emb, meta = _load_embeddings(emb_path)
        return Source(
            "dense",
            emb_path,
            emb.shape[0],
            lambda device: dense_scorer(emb, device),
            meta.get("config_hash"),
        )
    base_path = art / "embeddings" / f"{name.removesuffix(CSLS_SUFFIX)}.npy"
    if name.endswith(CSLS_SUFFIX) and base_path.exists():
        from bsim.embed.csls import csls_scorer, hubness

        emb, meta = _load_embeddings(base_path)
        r = cfg["retrieval"]

        def scorer(device: torch.device) -> ScoreFn:
            return csls_scorer(
                emb, hubness(emb, r["csls_neighbors"], r["chunk_size"], device), device
            )

        return Source("dense", base_path, emb.shape[0], scorer, meta.get("config_hash"))
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
    meta = {
        "kind": src.kind,
        "source": src.path.name,
        "source_config_hash": src.source_hash,
        "config_hash": config_hash(cfg, "retrieval"),
        "k": int(r["k"]),
        "device": str(device),
    }
    path = write_topk(cfg, "verse", system, df, meta)
    short = src.n - int((df.groupby("src_id").size() >= r["k"]).sum())
    log(f"  wrote {path}: {len(df)} rows ({short} verses with < k hits)")
    return df
