"""`bsim units`: chapter / pericope / parasha top-k (DESIGN.md §6.2).

Units of a type are disjoint, contiguous verse ranges (`retrieve/topk.py:load_units`); parashiyot
cover the Torah only, so parasha is compared with parasha. Self is excluded; same-book filtering
is a query-time option.

- `tfidf` (the unit lexical system) and `tfidf_morph` (unit structural): `artifacts/lexical/
  {system}_{type}.npz` rows (L2-normalized), cosine `X @ X.T`, zero-score hits dropped ->
  `{type}/{system}.parquet`.
- semantic systems (any `bsim topk` dense or `*_csls` system), one file per aggregation in
  `units.aggregations`:
  - `bma`: best-match average over the system's verse scores (CSLS values for `*_csls`):
    `s(A→B) = mean_{a∈A} max_{b∈B} score(a, b)`, `BMA = ½(s(A→B) + s(B→A))`. Verse score rows are
    computed in chunks; the max over each target unit is a `scatter_reduce('amax')` with a
    verse -> unit index, the mean over each source unit an `index_add_`.
  - `mean`: unit vector = normalized mean of the member verse vectors; cosine, or CSLS over the
    unit vectors (unit-level `r(·)`) for `*_csls`.
  -> `{type}/{system}_{agg}.parquet`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
import scipy.sparse as sp
import torch

from bsim.config import config_hash, resolve_path
from bsim.embed.csls import csls_scorer, hubness
from bsim.retrieve.topk import (
    ScoreFn,
    Units,
    dense_scorer,
    get_device,
    load_units,
    resolve_system,
    topk_chunks,
    topk_frame,
    write_topk,
)

Log = Callable[[str], None]

AGGREGATIONS = ("bma", "mean")


def unit_types(cfg: dict[str, Any]) -> list[str]:
    return [t for t in cfg["units"]["types"] if t != "verse"]


def member_index(units: Units) -> tuple[np.ndarray, np.ndarray]:
    """(member verse ids, unit position of each) for disjoint contiguous units."""
    sizes = units.end - units.start + 1
    if (units.start[1:] <= units.end[:-1]).any():
        raise RuntimeError("units of one type overlap; BMA expects disjoint verse ranges")
    verses = np.concatenate(
        [np.arange(s, e + 1) for s, e in zip(units.start, units.end, strict=True)]
    )
    return verses, np.repeat(np.arange(len(units)), sizes)


def bma_matrix(
    score_fn: ScoreFn, units: Units, chunk_size: int, device: torch.device
) -> np.ndarray:
    """Symmetric `n_units x n_units` best-match-average matrix from verse-level scores."""
    verses, unit_of = member_index(units)
    n_units = len(units)
    lo, hi = int(units.start[0]), int(units.end[-1]) + 1
    row_unit = np.full(hi - lo, -1, np.int64)
    row_unit[verses - lo] = unit_of

    cols = torch.as_tensor(verses, device=device)
    col_unit = torch.as_tensor(unit_of, device=device)
    s_dir = torch.zeros((n_units, n_units), dtype=torch.float32, device=device)
    for start in range(lo, hi, chunk_size):
        stop = min(start + chunk_size, hi)
        ru = torch.as_tensor(row_unit[start - lo : stop - lo], device=device)
        keep = ru >= 0
        if not keep.any():
            continue
        block = torch.as_tensor(score_fn(start, stop), dtype=torch.float32, device=device)
        block = block[keep][:, cols]
        best = torch.full((len(block), n_units), -torch.inf, dtype=torch.float32, device=device)
        best.scatter_reduce_(1, col_unit.expand(len(block), -1), block, "amax")
        s_dir.index_add_(0, ru[keep], best)
    sizes = torch.as_tensor(units.end - units.start + 1, dtype=torch.float32, device=device)
    s_dir /= sizes[:, None]
    return ((s_dir + s_dir.T) / 2).cpu().numpy()


def mean_vectors(emb: np.ndarray, units: Units) -> np.ndarray:
    """L2-normalized mean of each unit's member rows (units are contiguous ranges)."""
    cs = np.zeros((emb.shape[0] + 1, emb.shape[1]), np.float64)
    np.cumsum(emb, axis=0, out=cs[1:])
    u = cs[units.end + 1] - cs[units.start]
    return (u / np.linalg.norm(u, axis=1, keepdims=True)).astype(np.float32)


def sparse_cosine_scorer(x: sp.csr_matrix) -> ScoreFn:
    xt = x.T.tocsr()
    return lambda start, stop: (x[start:stop] @ xt).toarray()


def matrix_scorer(m: np.ndarray, device: torch.device) -> ScoreFn:
    t = torch.as_tensor(m, dtype=torch.float32, device=device)
    # clone: topk_chunks writes -inf on the diagonal of each block
    return lambda start, stop: t[start:stop].clone()


def _topk(
    score_fn: ScoreFn,
    units: Units,
    unit_type: str,
    cfg: dict[str, Any],
    device: torch.device,
    sparse: bool,
) -> pd.DataFrame:
    r = cfg["retrieval"]
    idx, score = topk_chunks(score_fn, len(units), r["k"], r["chunk_size"], device)
    return topk_frame(idx, score, drop_nonpositive=sparse, unit_type=unit_type, ids=units.ids)


def _meta(cfg: dict[str, Any], device: torch.device, **extra: Any) -> dict[str, Any]:
    return {
        **extra,
        "config_hash": config_hash(cfg, "retrieval", "units"),
        "k": int(cfg["retrieval"]["k"]),
        "device": str(device),
    }


def run_tfidf_units(cfg: dict[str, Any], log: Log = print, system: str = "tfidf") -> None:
    lex_dir = resolve_path(cfg, "artifacts") / "lexical"
    device = get_device(cfg["retrieval"]["device"])
    meta_path = lex_dir / "lexical_meta.json"
    lex_meta = json.loads(meta_path.read_text("utf-8")) if meta_path.exists() else {}
    for unit_type in unit_types(cfg):
        npz = lex_dir / f"{system}_{unit_type}.npz"
        if not npz.exists():
            raise RuntimeError(f"{npz} missing; run `bsim lexical` first")
        units = load_units(cfg, unit_type)
        ids = json.loads((lex_dir / f"{system}_{unit_type}.ids.json").read_text("utf-8"))
        pos = {u: i for i, u in enumerate(ids)}
        if set(pos) != set(units.ids):
            raise RuntimeError(f"{npz.name} units differ from units.parquet; rerun `bsim lexical`")
        x = sp.load_npz(npz).tocsr()[[pos[u] for u in units.ids]]
        df = _topk(sparse_cosine_scorer(x), units, unit_type, cfg, device, True)
        meta = _meta(
            cfg,
            device,
            kind="sparse",
            source=npz.name,
            source_config_hash=lex_meta.get("config_hash"),
        )
        path = write_topk(cfg, unit_type, system, df, meta)
        log(f"  {unit_type}: {len(units)} units -> {path} ({len(df)} rows)")


def run_semantic_units(cfg: dict[str, Any], system: str, log: Log = print) -> None:
    src = resolve_system(cfg, system)
    if src.kind != "dense":
        raise RuntimeError(
            f"{system!r} is a lexical verse system; unit-level lexical is `--system tfidf`"
        )
    r = cfg["retrieval"]
    aggs = cfg["units"]["aggregations"]
    unknown = set(aggs) - set(AGGREGATIONS)
    if unknown:
        raise RuntimeError(f"unknown aggregations {sorted(unknown)}; choose from {AGGREGATIONS}")
    device = get_device(r["device"])
    csls = src.path.stem != system  # `{base}_csls` resolved from `{base}.npy`
    emb = np.load(src.path, mmap_mode="r")
    verse_scorer = src.scorer(device) if "bma" in aggs else None
    for unit_type in unit_types(cfg):
        units = load_units(cfg, unit_type)
        for agg in aggs:
            if agg == "bma":
                m = bma_matrix(verse_scorer, units, r["chunk_size"], device)
                score_fn = matrix_scorer(m, device)
            else:
                u = mean_vectors(np.asarray(emb, dtype=np.float32), units)
                if csls:
                    rr = hubness(u, r["csls_neighbors"], r["chunk_size"], device)
                    score_fn = csls_scorer(u, rr, device)
                else:
                    score_fn = dense_scorer(u, device)
            df = _topk(score_fn, units, unit_type, cfg, device, False)
            meta = _meta(
                cfg,
                device,
                kind="dense",
                aggregation=agg,
                verse_system=system,
                source=src.path.name,
                source_config_hash=src.source_hash,
            )
            name = f"{system}_{agg}"
            path = write_topk(cfg, unit_type, name, df, meta)
            log(f"  {unit_type}/{name}: {len(units)} units -> {path} ({len(df)} rows)")


def run_units(cfg: dict[str, Any], system: str, log: Log = print) -> None:
    log(f"{system}: unit top-{cfg['retrieval']['k']} for {', '.join(unit_types(cfg))}")
    fs = cfg["final_systems"]
    if system in (fs["unit_lexical"], fs["unit_structural"]):
        run_tfidf_units(cfg, log, system)
    else:
        run_semantic_units(cfg, system, log)
