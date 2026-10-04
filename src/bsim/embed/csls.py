"""CSLS hubness correction (DESIGN.md §5.2).

`csls(x, y) = 2·cos(x, y) − r(x) − r(y)`, with `r(·)` the mean cosine of a vector to its
`retrieval.csls_neighbors` nearest neighbours (self excluded). Verses that are close to
everything ("hubs") get a large `r` and drop out of other verses' top-k.
"""

from __future__ import annotations

import numpy as np
import torch

from bsim.retrieve.topk import ScoreFn, dense_scorer, topk_chunks


def hubness(emb: np.ndarray, k: int, chunk_size: int, device: torch.device) -> np.ndarray:
    """r(x) for every row of an L2-normalized matrix."""
    _, score = topk_chunks(dense_scorer(emb, device), len(emb), k, chunk_size, device)
    return score.mean(axis=1).astype(np.float32)


def csls_scorer(emb: np.ndarray, r: np.ndarray, device: torch.device) -> ScoreFn:
    # copy: emb may be a read-only memmap
    e = torch.as_tensor(np.array(emb, dtype=np.float32), device=device)
    rt = torch.as_tensor(r, dtype=torch.float32, device=device)
    return lambda start, stop: 2 * (e[start:stop] @ e.T) - rt[start:stop, None] - rt[None, :]
