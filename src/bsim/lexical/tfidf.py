"""Unit-level TF-IDF cosine (DESIGN.md §5.1).

A unit's bag is the union of its member verses' tokens. With raw count `c` and formula-weighted
count `w` of a term, tf = `(1 + log c) · (w / c)` (sublinear in the count, scaled by the mean
token weight; `1 + log w` would go negative for down-weighted terms). idf is the smooth
`log((1 + N)/(1 + df)) + 1` over the units of one type. Rows are L2-normalized, so `X @ X.T` is
the cosine.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.preprocessing import normalize

from bsim.lexical.bm25 import _term_table


def unit_tfidf(
    token_lists: list[list[str]],
    weight_lists: list[np.ndarray],
    members: pd.DataFrame,
    unit_ids: list[str],
) -> sp.csr_matrix:
    """L2-normalized TF-IDF rows for `unit_ids` (in that order); `members` maps unit -> verse."""
    table, vocab = _term_table(token_lists, weight_lists)
    shape = (len(token_lists), len(vocab))
    rows, cols = table.doc.to_numpy(), table.term.to_numpy()
    counts = sp.csr_matrix((table["size"].to_numpy(np.float64), (rows, cols)), shape=shape)
    weighted = sp.csr_matrix((table["sum"].to_numpy(), (rows, cols)), shape=shape)

    pos = {u: i for i, u in enumerate(unit_ids)}
    m = members[members.unit_id.isin(pos)]
    member = sp.csr_matrix(
        (np.ones(len(m)), (m.unit_id.map(pos).to_numpy(), m.verse_id.to_numpy())),
        shape=(len(unit_ids), len(token_lists)),
    )
    c = (member @ counts).tocsr()
    w = member @ weighted
    log_c, inv_c = c.copy(), c.copy()
    log_c.data = 1 + np.log(log_c.data)
    inv_c.data = 1 / inv_c.data

    tf = log_c.multiply(w).multiply(inv_c).tocsr()
    tf.eliminate_zeros()
    df = np.bincount(tf.indices, minlength=len(vocab))
    idf = np.log((1 + len(unit_ids)) / (1 + df)) + 1
    tf.data *= idf[tf.indices]
    return normalize(tf, norm="l2", copy=False).astype(np.float32).tocsr()
