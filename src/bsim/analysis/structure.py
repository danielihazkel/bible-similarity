"""Inner-unit structure: inclusio, chiasm and Leitwort (DESIGN.md §16.2).

All scores work on a unit's verse-by-verse similarity matrix `S` (n x n, symmetric):
- `semantic`: cosine of the final semantic system's verse embeddings;
- `lexical`: cosine of tf-idf weighted content-lemma bags (`idf = log(N / df)`).

Inclusio = similarity of the opening and closing verses (the best of first-last, second-last and
first-penultimate, so a heading verse does not hide the frame), as a percentile of the best of as
many random non-adjacent pairs of the same unit.

Chiasm = mean similarity of the mirror pairs (i, n-1-i) (the adjacent centre pair left out),
compared with a null of random pairs at the same distances (similarity decays with distance, so
only same-distance pairs are a fair baseline): `pct` = share of null means below the observed one,
`z` = its distance from the null mean in null standard deviations. With thousands of units about
5 % reach pct 0.95 by chance: high scores are leads to read, not findings.

Leitwort = content lemmas over-represented in the unit by Dunning's log-likelihood (G²).

`bsim structure` scores every chapter, pericope and parasha into
`artifacts/structure/units.parquet`; the API recomputes one unit on demand with the same code.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.retrieve.topk import CSLS_SUFFIX

Log = Callable[[str], None]
BASES = ("semantic", "lexical")


def semantic_matrix(emb: np.ndarray) -> np.ndarray:
    e = np.asarray(emb, dtype=np.float64)
    return e @ e.T


def lexical_matrix(bags: Sequence[Sequence[str]], idf: dict[str, float]) -> np.ndarray:
    """Cosine of tf-idf lemma vectors; a verse without content lemmas is all zeros."""
    vocab = {t: i for i, t in enumerate(sorted({t for b in bags for t in b}))}
    m = np.zeros((len(bags), len(vocab)))
    for r, bag in enumerate(bags):
        for t, c in Counter(bag).items():
            m[r, vocab[t]] = c * idf.get(t, 0.0)
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    m = np.divide(m, norms, out=np.zeros_like(m), where=norms > 0)
    return m @ m.T


@dataclass(frozen=True)
class Score:
    value: float
    pct: float  # 0..1
    z: float | None = None
    pair: tuple[int, int] | None = None  # inclusio: the opening / closing pair that scored


def frame_pairs(n: int) -> list[tuple[int, int]]:
    """Opening / closing pairs an inclusio may use: first-last, and (for n >= 6) second-last and
    first-penultimate, so a heading verse (Psalm superscriptions) or a closing formula does not
    hide the frame."""
    return [(0, n - 1), (1, n - 1), (0, n - 2)] if n >= 6 else [(0, n - 1)]


def inclusio(s: np.ndarray, min_verses: int, samples: int, seed: int) -> Score | None:
    """Best frame pair's similarity as a percentile of the best of as many random non-adjacent
    pairs (the max over several pairs needs a max-of-several null)."""
    n = len(s)
    if n < min_verses:
        return None
    frame = frame_pairs(n)
    v, pair = max((float(s[i, j]), (i, j)) for i, j in frame)
    i, j = np.triu_indices(n, k=2)
    keep = np.ones(len(i), dtype=bool)
    for fi, fj in frame:
        keep &= ~((i == fi) & (j == fj))
    others = s[i, j][keep]
    if not len(others):
        return None
    rng = np.random.default_rng(seed)
    null = others[rng.integers(0, len(others), size=(samples, len(frame)))].max(axis=1)
    pct = (np.sum(null < v) + 0.5 * np.sum(null == v)) / samples
    return Score(v, float(pct), pair=pair)


def mirror_pairs(n: int) -> list[tuple[int, int]]:
    """(i, n-1-i) for the outer half, without an adjacent centre pair."""
    return [(i, n - 1 - i) for i in range(n // 2) if n - 1 - 2 * i >= 2]


def chiasm(s: np.ndarray, min_verses: int, samples: int, seed: int) -> Score | None:
    n = len(s)
    pairs = mirror_pairs(n)
    if n < min_verses or len(pairs) < 2:
        return None
    observed = float(np.mean([s[i, j] for i, j in pairs]))
    rng = np.random.default_rng(seed)
    dist = np.array([j - i for i, j in pairs])
    starts = rng.integers(0, n - dist, size=(samples, len(pairs)))  # pair (k, k + d)
    null = s[starts, starts + dist].mean(axis=1)
    pct = (np.sum(null < observed) + 0.5 * np.sum(null == observed)) / samples
    sd = float(null.std())
    z = (observed - float(null.mean())) / sd if sd > 0 else None
    return Score(observed, float(pct), z)


def echoes(s: np.ndarray, top: int) -> list[tuple[int, int, float]]:
    """The most similar non-adjacent verse pairs inside the unit (i < j, j - i >= 2)."""
    i, j = np.triu_indices(len(s), k=2)
    order = np.argsort(-s[i, j], kind="stable")[:top]
    return [(int(i[k]), int(j[k]), float(s[i[k], j[k]])) for k in order]


@dataclass(frozen=True)
class Keyword:
    lemma: str
    count: int
    expected: float
    g2: float


def leitworte(
    unit_counts: Counter[str],
    corpus_counts: dict[str, int],
    corpus_total: int,
    min_count: int,
    top: int,
) -> list[Keyword]:
    """Over-represented lemmas by Dunning's G² (unit vs the rest of the corpus), strongest first."""
    n = sum(unit_counts.values())
    rest_total = corpus_total - n
    out = []
    for lem, a in unit_counts.items():
        if a < min_count:
            continue
        b = corpus_counts.get(lem, a) - a  # occurrences outside the unit
        expected = (a + b) * n / corpus_total
        if a <= expected or rest_total <= 0:
            continue
        e1, e2 = expected, (a + b) * rest_total / corpus_total
        g2 = 2 * (a * math.log(a / e1) + (b * math.log(b / e2) if b > 0 else 0.0))
        out.append(Keyword(lem, a, expected, g2))
    out.sort(key=lambda k: (-k.g2, k.lemma))
    return out[:top]


def unit_scores(mats: dict[str, np.ndarray], cfg: dict[str, Any]) -> dict[str, Any]:
    """Inclusio / chiasm columns for one unit (`{basis}_{inclusio|chiasm}[_pct|_z]`)."""
    c = cfg["structure"]
    row: dict[str, Any] = {}
    for basis, s in mats.items():
        inc = inclusio(s, c["min_verses_inclusio"], c["samples"], c["seed"])
        chi = chiasm(s, c["min_verses_chiasm"], c["samples"], c["seed"])
        row[f"{basis}_inclusio"] = inc.value if inc else None
        row[f"{basis}_inclusio_pct"] = inc.pct if inc else None
        row[f"{basis}_chiasm"] = chi.value if chi else None
        row[f"{basis}_chiasm_pct"] = chi.pct if chi else None
        row[f"{basis}_chiasm_z"] = chi.z if chi else None
    return row


SCORE_COLS = [
    f"{b}_{k}"
    for b in BASES
    for k in ("inclusio", "inclusio_pct", "chiasm", "chiasm_pct", "chiasm_z")
]


def lemma_idf(words: pd.DataFrame, n_verses: int) -> dict[str, float]:
    df: Counter[str] = Counter()
    for _, lems in words.groupby("verse_id").content_lemmas:
        df.update({t for c in lems for t in c})
    return {t: math.log(n_verses / d) for t, d in df.items()}


def embeddings_path(cfg: dict[str, Any]) -> Path:
    base = cfg["final_systems"]["semantic"].removesuffix(CSLS_SUFFIX)
    return resolve_path(cfg, "artifacts") / "embeddings" / f"{base}.npy"


def run_structure(cfg: dict[str, Any], log: Log = print) -> Path:
    proc = resolve_path(cfg, "data_processed")
    units = pd.read_parquet(proc / "units.parquet")
    words = pd.read_parquet(proc / "words.parquet", columns=["verse_id", "content_lemmas"])
    n_verses = len(pd.read_parquet(proc / "verses.parquet", columns=["verse_id"]))
    emb_path = embeddings_path(cfg)
    if not emb_path.exists():
        raise RuntimeError(f"{emb_path} missing; run `bsim embed` for the semantic system first")
    emb = np.load(emb_path, mmap_mode="r")
    t0 = time.perf_counter()
    idf = lemma_idf(words, n_verses)
    bags: list[list[str]] = [[] for _ in range(n_verses)]
    for vid, lems in zip(words.verse_id, words.content_lemmas, strict=True):
        bags[vid].extend(lems)
    c = cfg["structure"]
    rows = []
    todo = units[units.unit_type.isin(c["unit_types"]) & (units.n_verses <= c["max_verses"])]
    for u in todo.itertuples(index=False):
        lo, hi = u.start_verse_id, u.end_verse_id + 1
        mats = {
            "semantic": semantic_matrix(emb[lo:hi]),
            "lexical": lexical_matrix(bags[lo:hi], idf),
        }
        rows.append(
            {
                "unit_id": u.unit_id,
                "unit_type": u.unit_type,
                "n_verses": u.n_verses,
                **unit_scores(mats, cfg),
            }
        )
    df = pd.DataFrame(rows, columns=["unit_id", "unit_type", "n_verses", *SCORE_COLS])
    out = resolve_path(cfg, "artifacts") / "structure"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "units.parquet")
    meta = {
        "config_hash": config_hash(cfg, "structure", "final_systems"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "embeddings": emb_path.name,
        "units": int(len(df)),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "units.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(f"done: {len(df)} units scored in {meta['seconds']} s -> {out / 'units.parquet'}")
    return out / "units.parquet"
