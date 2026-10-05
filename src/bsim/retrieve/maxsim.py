"""`bsim maxsim`: ColBERT-style late-interaction scores for the fused verse lists (DESIGN.md
§16.21, roadmap A9).

Every verse is encoded alone with each encoder in `maxsim.encoders` (`encoders.systems` entries);
its token vectors (last hidden state, special tokens dropped, each L2-normalized) are kept. A
(source, candidate) pair of the fused top `maxsim.depth` scores

    MaxSim(a -> b) = mean over a's tokens of the best cosine with any token of b

and, with `maxsim.symmetric`, the mean of both directions, so a short verse inside a long one is
not favoured one way only. No training: the scores reorder the fused list, combined with the
fused rank by RRF like the cross-encoder (`train/rerank.py:combine`).

Writes `artifacts/maxsim/{encoder}.parquet` (src, tgt, rank = fused rank, maxsim) for every
encoder, read by `bsim retrieval-exp`, and the list of `maxsim.encoder` blended with weight
`maxsim.w` as `artifacts/topk/verse/{maxsim.system}.parquet` (fused breakdown kept, plus
`maxsim_score` and `fused_rank`), so `bsim evaluate` reports it next to the other systems. fp32.
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
import torch

from bsim.config import config_hash, resolve_path
from bsim.embed.context import load_verses, token_batches
from bsim.embed.encoders import load_encoder
from bsim.retrieve.topk import get_device, read_topk, verse_ids

Log = Callable[[str], None]


class TokenStore:
    """All verses' token vectors in one `(T + 1) x dim` tensor (row 0 = padding) and an
    `N x max_len` index of each verse's rows (0 = none)."""

    def __init__(self, vectors: torch.Tensor, index: torch.Tensor) -> None:
        self.vectors, self.index = vectors, index

    @classmethod
    def build(cls, parts: list[np.ndarray], device: torch.device) -> TokenStore:
        lengths = np.array([len(p) for p in parts])
        if (lengths == 0).any():
            raise RuntimeError(f"{int((lengths == 0).sum())} verses have no tokens")
        dim = parts[0].shape[1]
        flat = np.concatenate([np.zeros((1, dim), np.float32), *parts]).astype(np.float32)
        index = np.zeros((len(parts), int(lengths.max())), np.int64)
        starts = np.concatenate([[1], 1 + np.cumsum(lengths)[:-1]])
        for i, (s, n) in enumerate(zip(starts, lengths, strict=True)):
            index[i, :n] = np.arange(s, s + n)
        return cls(torch.as_tensor(flat, device=device), torch.as_tensor(index, device=device))

    def gather(self, rows: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Padded vectors (`*rows.shape x len x dim`) and their validity mask."""
        idx = self.index[rows]
        return self.vectors[idx], idx > 0


def maxsim_scores(
    q: torch.Tensor, q_mask: torch.Tensor, d: torch.Tensor, d_mask: torch.Tensor, symmetric: bool
) -> torch.Tensor:
    """`B x C` scores: B queries (`B x Lq x dim`), C candidates each (`B x C x Ld x dim`)."""
    sim = torch.einsum("bqh,bclh->bcql", q, d)
    neg = torch.finfo(sim.dtype).min
    qm = q_mask[:, None, :].float()  # B x 1 x Lq
    to_d = sim.masked_fill(~d_mask[:, :, None, :], neg).amax(-1)  # B x C x Lq
    fwd = (to_d * qm).sum(-1) / qm.sum(-1).clamp(min=1)
    if not symmetric:
        return fwd
    dm = d_mask.float()
    to_q = sim.masked_fill(~q_mask[:, None, :, None], neg).amax(-2)  # B x C x Ld
    bwd = (to_q * dm).sum(-1) / dm.sum(-1).clamp(min=1)
    return (fwd + bwd) / 2


def token_vectors(
    cfg: dict[str, Any], encoder: str, texts: list[str], device: torch.device
) -> list[np.ndarray]:
    """Per verse: its non-special token vectors, L2-normalized."""
    mc = cfg["maxsim"]
    model = load_encoder(
        cfg["encoders"]["systems"][encoder], cfg["text"]["max_seq_length"], str(device)
    )
    model.eval()
    out: list[np.ndarray] = [np.empty(0)] * len(texts)
    for b, hidden, enc in token_batches(
        model, texts, cfg["text"]["max_seq_length"], mc["batch_size"]
    ):
        keep = enc["attention_mask"] & ~enc["special"]
        for j in range(len(hidden)):
            v = hidden[j][keep[j]]
            out[b + j] = v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)
    del model
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return out


def fused_candidates(cfg: dict[str, Any], depth: int) -> pd.DataFrame:
    path = (
        resolve_path(cfg, "artifacts")
        / "topk"
        / "verse"
        / f"{cfg['final_systems']['fused']}.parquet"
    )
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim fuse` first")
    df = read_topk(path)
    return (
        df[df["rank"] <= depth].sort_values(["src", "rank"], kind="stable").reset_index(drop=True)
    )


def score_lists(
    store: TokenStore, cand: pd.DataFrame, batch: int, symmetric: bool, device: torch.device
) -> np.ndarray:
    """MaxSim of every (src, tgt) row of `cand` (sorted by src), in row order."""
    src = cand.src.to_numpy()
    starts = np.flatnonzero(np.r_[True, src[1:] != src[:-1]])
    bounds = np.r_[starts, len(src)]
    width = int(np.diff(bounds).max())
    tgt = np.zeros((len(starts), width), np.int64)
    valid = np.zeros((len(starts), width), bool)
    for i, (a, b) in enumerate(zip(bounds[:-1], bounds[1:], strict=True)):
        tgt[i, : b - a] = cand.tgt.to_numpy()[a:b]
        valid[i, : b - a] = True
    out = np.empty(len(src), np.float32)
    with torch.no_grad():
        for b in range(0, len(starts), batch):
            rows = slice(b, b + batch)
            q, qm = store.gather(torch.as_tensor(src[starts[rows]], device=device))
            d, dm = store.gather(torch.as_tensor(tgt[rows], device=device))
            s = maxsim_scores(q, qm, d, dm, symmetric).cpu().numpy()
            # sources are contiguous in `cand`: this batch's rows, flattened row-major
            out[bounds[b] : bounds[min(b + batch, len(starts))]] = s[valid[rows]]
    return out


def run_maxsim(cfg: dict[str, Any], log: Log = print) -> dict[str, Path]:
    from bsim.train.rerank import combine

    mc = cfg["maxsim"]
    systems = cfg["encoders"]["systems"]
    unknown = [e for e in [*mc["encoders"], mc["encoder"]] if e not in systems]
    if unknown:
        raise RuntimeError(f"maxsim encoders {unknown} are not in encoders.systems")
    device = get_device(cfg["encoders"].get("device", "cuda"))
    texts = load_verses(cfg).text_model.tolist()
    cand = fused_candidates(cfg, mc["depth"])
    art = resolve_path(cfg, "artifacts")
    (art / "maxsim").mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    scored: dict[str, pd.DataFrame] = {}
    for enc in dict.fromkeys([*mc["encoders"], mc["encoder"]]):
        t0 = time.perf_counter()
        log(f"{enc}: token vectors of {len(texts)} verses on {device}")
        store = TokenStore.build(token_vectors(cfg, enc, texts, device), device)
        log(
            f"  {store.vectors.shape[0] - 1} tokens; scoring {len(cand)} pairs"
            f" (fused top {mc['depth']})"
        )
        s = score_lists(store, cand, mc["batch_size"], mc["symmetric"], device)
        del store
        if device.type == "cuda":
            torch.cuda.empty_cache()
        df = cand[["src", "tgt", "rank"]].assign(maxsim=s)
        paths[enc] = art / "maxsim" / f"{enc}.parquet"
        df.to_parquet(paths[enc], index=False)
        scored[enc] = cand.assign(ce_score=s)
        log(f"  {time.perf_counter() - t0:.0f} s -> {paths[enc]}")
    meta = {
        "encoders": list(dict.fromkeys(mc["encoders"])),
        "depth": mc["depth"],
        "symmetric": mc["symmetric"],
        "config_hash": config_hash(cfg, "maxsim", "encoders", "text", "fusion", "final_systems"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (art / "maxsim" / "maxsim.meta.json").write_text(json.dumps(meta, indent=2) + "\n", "utf-8")

    out = combine(scored[mc["encoder"]], mc["w"], mc["rrf_k"])
    frame = pd.DataFrame(
        {
            "unit_type": "verse",
            "src_id": verse_ids(out.src.to_numpy()),
            "rank": out["rank"].astype(np.int32),
            "tgt_id": verse_ids(out.tgt.to_numpy()),
            "score": out.new_score.astype(np.float32),
            "lex_score": out.lex_score.astype(np.float32),
            "lex_rank": out.lex_rank.astype("Int32"),
            "sem_score": out.sem_score.astype(np.float32),
            "sem_rank": out.sem_rank.astype("Int32"),
            "maxsim_score": out.ce_score.astype(np.float32),
            "fused_rank": out.fused_rank.astype(np.int32),
        }
    ).sort_values(["src_id", "rank"], kind="stable")
    path = art / "topk" / "verse" / f"{mc['system']}.parquet"
    frame.to_parquet(path, index=False)
    path.with_suffix(".meta.json").write_text(
        json.dumps(
            {
                "system": mc["system"],
                "unit_type": "verse",
                "encoder": mc["encoder"],
                "w": mc["w"],
                **meta,
                "rows": len(frame),
            },
            indent=2,
        )
        + "\n",
        "utf-8",
    )
    log(f"done: {mc['encoder']} blended at w={mc['w']}: {len(frame)} rows -> {path}")
    paths["system"] = path
    return paths
