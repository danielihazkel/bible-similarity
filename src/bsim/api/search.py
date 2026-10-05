"""Free-text Hebrew search over verses (DESIGN.md §10.1).

- `lexical`: OSHB lemmas do not exist for arbitrary text, so the API builds a surface-form BM25
  index over the consonantal MAM text (`verses.text_plain`) at startup. Tokens are finals-folded
  and greedily prefix-stripped (`text.normalize.strip_prefix`) on both the query and the corpus,
  plus adjacent-token bigrams. The query is binary: each known term counts once.
- `semantic`: the query is encoded with the final encoder and scored against the verse matrix.
  When the final semantic system is a `*_csls` one, the score is `2·cos − r(q) − r(y)`, with
  `r(q)` the mean of the query's top-`csls_neighbors` cosines and `r(y)` the verses' hubness.
- `fused`: weighted RRF of the two top-`retrieval.k` lists (`retrieve.fusion.rrf`).

Ranks are 1-based; ties are ordered by verse id, as in `retrieve.topk`.
"""

from __future__ import annotations

import json
import pickle
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy.sparse as sp

from bsim.lexical.bm25 import Bm25Index, build_bm25
from bsim.lexical.tokens import with_bigrams
from bsim.retrieve.fusion import rrf
from bsim.text.normalize import consonantal, fold_finals, strip_prefix

Encoder = Callable[[list[str]], np.ndarray]  # texts -> float32 [n, d], L2-normalized


def search_tokens(text: str, min_root: int) -> list[str]:
    """Consonantal, finals-folded, prefix-stripped tokens of any (pointed or plain) text."""
    return [t for w in consonantal(text).split() if (t := strip_prefix(fold_finals(w), min_root))]


@dataclass
class SurfaceIndex:
    index: Bm25Index
    doc_t: sp.csr_matrix  # V x N: one row of document weights per term
    terms: dict[str, int]
    min_root: int
    bigrams: bool

    def query_terms(self, text: str) -> tuple[list[str], list[str]]:
        """(unigram tokens, all query terms incl. bigrams)."""
        tokens = search_tokens(text, self.min_root)
        terms = with_bigrams(tokens, np.ones(len(tokens)))[0] if self.bigrams else tokens
        return tokens, terms

    def scores(self, terms: list[str]) -> np.ndarray:
        cols = sorted({self.terms[t] for t in terms if t in self.terms})
        if not cols:
            return np.zeros(self.doc_t.shape[1], dtype=np.float32)
        return np.asarray(self.doc_t[cols].sum(axis=0), dtype=np.float32).ravel()


def build_surface_index(
    texts: list[str], k1: float, b: float, min_root: int, bigrams: bool
) -> SurfaceIndex:
    token_lists, weight_lists = [], []
    for text in texts:
        tokens = search_tokens(text, min_root)
        weights = np.ones(len(tokens))
        if bigrams:
            tokens, weights = with_bigrams(tokens, weights)
        token_lists.append(tokens)
        weight_lists.append(weights)
    index = build_bm25(token_lists, weight_lists, k1, b)
    return SurfaceIndex(
        index=index,
        doc_t=index.doc.T.tocsr(),
        terms={t: i for i, t in enumerate(index.vocab)},
        min_root=min_root,
        bigrams=bigrams,
    )


def load_surface_index(
    texts: Callable[[], list[str]],
    db_path: Path,
    cache_dir: Path,
    k1: float,
    b: float,
    min_root: int,
    bigrams: bool,
) -> SurfaceIndex:
    """`build_surface_index`, cached next to a sidecar that pins the DB file and parameters."""
    stat = db_path.stat()
    key = {
        "db": db_path.name,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "k1": k1,
        "b": b,
        "min_root": min_root,
        "bigrams": bigrams,
    }
    path = cache_dir / "surface_bm25.pkl"
    side = path.with_suffix(".json")
    if path.exists() and side.exists() and json.loads(side.read_text("utf-8")) == key:
        with path.open("rb") as f:
            cached = pickle.load(f)
        if isinstance(cached, SurfaceIndex):
            return cached
    surface = build_surface_index(texts(), k1, b, min_root, bigrams)
    cache_dir.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(surface, f, protocol=pickle.HIGHEST_PROTOCOL)
    side.write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    return surface


def top(scores: np.ndarray, k: int, positive_only: bool = False) -> pd.DataFrame:
    """`src` (0), `tgt`, `rank`, `score` of the best `k` entries; ties by target id."""
    ids = np.arange(len(scores))
    if positive_only:
        ids = ids[scores > 0]
    order = ids[np.lexsort((ids, -scores[ids]))][:k]
    return pd.DataFrame(
        {
            "src": np.zeros(len(order), dtype=np.int64),
            "tgt": order.astype(np.int64),
            "rank": np.arange(1, len(order) + 1, dtype=np.int32),
            "score": scores[order].astype(np.float32),
        }
    )


def semantic_scores(
    emb: np.ndarray, q: np.ndarray, hubness: np.ndarray | None, csls_k: int
) -> np.ndarray:
    cos = np.asarray(emb @ q, dtype=np.float32)
    if hubness is None:
        return cos
    kk = min(csls_k, len(cos))
    r_q = float(np.partition(cos, len(cos) - kk)[-kk:].mean())
    return 2 * cos - r_q - hubness


class StEncoder:
    """A SentenceTransformer as an `Encoder` (one query at a time: the model is shared)."""

    def __init__(self, model: Any):
        self.model = model
        self._lock = threading.Lock()

    def __call__(self, texts: list[str]) -> np.ndarray:
        with self._lock:
            emb = self.model.encode(
                texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
            )
        return np.asarray(emb, dtype=np.float32)


class BackgroundEncoder:
    """An `Encoder` loaded on a daemon thread. Calls fail fast instead of holding a worker:
    `EncoderLoading` while it loads, `EncoderUnavailable` if it failed."""

    def __init__(self, load: Callable[[], Encoder], log: Callable[[str], None] = print):
        self._done = threading.Event()
        self._encoder: Encoder | None = None
        self._error: BaseException | None = None

        def run() -> None:
            t0 = time.perf_counter()
            try:
                self._encoder = load()
                log(f"encoder ready ({time.perf_counter() - t0:.1f} s)")
            except Exception as e:  # reported on use
                self._error = e
                log(f"encoder failed to load: {e}")
            finally:
                self._done.set()

        threading.Thread(target=run, name="encoder-load", daemon=True).start()

    @property
    def ready(self) -> bool:
        return self._done.is_set() and self._error is None

    @property
    def error(self) -> str | None:
        """Why loading failed (None while loading or once loaded)."""
        return None if self._error is None else str(self._error)

    def wait(self, timeout: float | None = None) -> bool:
        """Block until loading has finished (either way); False on timeout."""
        return self._done.wait(timeout)

    def __call__(self, texts: list[str]) -> np.ndarray:
        if not self._done.is_set():
            raise EncoderLoading("the query encoder is still loading; retry shortly")
        if self._encoder is None:
            raise EncoderUnavailable(f"the query encoder failed to load: {self._error}")
        return self._encoder(texts)


class EncoderUnavailable(RuntimeError):
    pass


class EncoderLoading(EncoderUnavailable):
    """The encoder has not finished loading yet (temporary)."""


def search(
    state: Any, query: str, mode: str, k: int, book_mask: np.ndarray | None = None
) -> tuple[str, list[str], pd.DataFrame]:
    """(normalized query, lexical tokens, ranked frame `tgt, rank, score` [+ breakdown]);
    `book_mask`: only these verses compete (a book filter applied before ranking)."""
    cfg = state.cfg
    depth = max(k, cfg["retrieval"]["k"])
    normalized = consonantal(query)
    tokens, terms = state.surface.query_terms(normalized)
    lists: dict[str, pd.DataFrame] = {}
    if mode in ("lexical", "fused"):
        lex = state.surface.scores(terms)
        if book_mask is not None:
            lex = np.where(book_mask, lex, 0.0).astype(np.float32)
        lists["lexical"] = top(lex, depth, positive_only=True)
    if mode in ("semantic", "fused"):
        cache = getattr(state, "query_cache", None)
        q = cache.get(normalized) if cache is not None else None
        if q is None:
            q = state.encoder([normalized])[0]
            if cache is not None:
                cache.put(normalized, q)
        scores = semantic_scores(state.emb, q, state.hubness, cfg["retrieval"]["csls_neighbors"])
        if book_mask is not None:
            ids = np.flatnonzero(book_mask)
            sub = top(scores[ids], depth)
            lists["semantic"] = sub.assign(tgt=ids[sub.tgt.to_numpy()])
        else:
            lists["semantic"] = top(scores, depth)
    if mode == "fused":
        f = cfg["fusion"]
        df = rrf(lists["lexical"], lists["semantic"], f["w_lex"], f["w_sem"], f["rrf_k"], depth)
    else:
        df = lists[mode]
    return normalized, tokens, df.head(k).reset_index(drop=True)


def load_hubness(
    emb: np.ndarray, emb_path: Path, cache_dir: Path, k: int, chunk_size: int, device: Any
) -> np.ndarray:
    """CSLS `r(y)` of every verse, cached next to a sidecar that pins its inputs."""
    from bsim.embed.csls import hubness

    stat = emb_path.stat()
    key = {
        "embeddings": emb_path.name,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "csls_neighbors": k,
    }
    path = cache_dir / f"{emb_path.stem}.hubness.npy"
    side = path.with_suffix(".json")
    if path.exists() and side.exists() and json.loads(side.read_text("utf-8")) == key:
        r = np.load(path)
        if r.shape == (len(emb),):
            return r
    r = hubness(emb, k, chunk_size, device)
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(path, r)
    side.write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    return r
