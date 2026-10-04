"""Sparse BM25 over verses (DESIGN.md §5.1).

Token weights (formula down-weighting) enter both sides:
- document: weighted term frequency `tf` and weighted length `dl`, then
  `idf · tf (k1+1) / (tf + k1 (1 − b + b·dl/avgdl))`,
  with `idf = log(1 + (N − df + 0.5)/(df + 0.5))`;
- query: binary BM25 query, each term weighted by the max token weight it has in the query verse.

All-pairs scores are `query @ doc.T`, computed in row chunks (`scores`); M5 does the top-k.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp


@dataclass
class Bm25Index:
    doc: sp.csr_matrix  # N x V document term weights
    query: sp.csr_matrix  # N x V query term weights
    vocab: list[str]


def _term_table(
    token_lists: list[list[str]], weight_lists: list[np.ndarray]
) -> tuple[pd.DataFrame, list[str]]:
    """(doc, term) -> summed weight, max weight and raw count; plus the vocabulary (sorted)."""
    docs = np.repeat(np.arange(len(token_lists)), [len(t) for t in token_lists])
    toks = [t for ts in token_lists for t in ts]
    weights = np.concatenate([np.asarray(w, dtype=np.float64) for w in weight_lists] or [[]])
    codes, vocab = pd.factorize(pd.Series(toks, dtype=object), sort=True)
    table = (
        pd.DataFrame({"doc": docs, "term": codes, "w": weights})
        .groupby(["doc", "term"], sort=True)
        .w.agg(["sum", "max", "size"])
        .reset_index()
    )
    return table, list(vocab)


def build_bm25(
    token_lists: list[list[str]], weight_lists: list[np.ndarray], k1: float, b: float
) -> Bm25Index:
    n = len(token_lists)
    table, vocab = _term_table(token_lists, weight_lists)
    shape = (n, len(vocab))
    rows, cols = table.doc.to_numpy(), table.term.to_numpy()
    tf = table["sum"].to_numpy()

    dl = np.bincount(rows, weights=tf, minlength=n)
    avgdl = dl.mean() if n else 1.0
    df = np.bincount(cols, minlength=len(vocab))
    idf = np.log1p((n - df + 0.5) / (df + 0.5))
    norm = k1 * (1 - b + b * dl[rows] / avgdl)
    doc_w = idf[cols] * tf * (k1 + 1) / (tf + norm)

    doc = sp.csr_matrix((doc_w.astype(np.float32), (rows, cols)), shape=shape)
    query = sp.csr_matrix((table["max"].to_numpy(np.float32), (rows, cols)), shape=shape)
    return Bm25Index(doc, query, vocab)


def scores(index: Bm25Index, rows: np.ndarray | slice) -> np.ndarray:
    """Dense BM25 scores of the query verses `rows` against every verse."""
    return (index.query[rows] @ index.doc.T).toarray()


def topk_cpu(index: Bm25Index, rows: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Top-k targets and scores for `rows` (self excluded), highest first. For spot checks."""
    rows = np.asarray(rows)
    s = scores(index, rows)
    s[np.arange(len(rows)), rows] = -np.inf
    k = min(k, s.shape[1] - 1)
    part = np.argpartition(-s, k - 1, axis=1)[:, :k]
    order = np.argsort(-np.take_along_axis(s, part, axis=1), axis=1, kind="stable")
    idx = np.take_along_axis(part, order, axis=1)
    return idx, np.take_along_axis(s, idx, axis=1)


def save(index: Bm25Index, out: Path, name: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    sp.save_npz(out / f"{name}.doc.npz", index.doc)
    sp.save_npz(out / f"{name}.query.npz", index.query)
    (out / f"{name}.vocab.json").write_text(json.dumps(index.vocab, ensure_ascii=False), "utf-8")


def load(out: Path, name: str) -> Bm25Index:
    return Bm25Index(
        doc=sp.load_npz(out / f"{name}.doc.npz").tocsr(),
        query=sp.load_npz(out / f"{name}.query.npz").tocsr(),
        vocab=json.loads((out / f"{name}.vocab.json").read_text("utf-8")),
    )
