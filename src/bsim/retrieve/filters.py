"""Query-time exclusion filters over stored top-k lists (DESIGN.md §6.1), shared by eval and API.

- `neighbors`: same book and within ±`retrieval.neighbor_window` verses
- `chapter`:   same book and chapter
- `book`:      same book
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

EXCLUDES = ("neighbors", "chapter", "book")


def same_book_mask(src: np.ndarray, tgt: np.ndarray, book_id: np.ndarray) -> np.ndarray:
    return book_id[src] == book_id[tgt]


def neighbor_mask(src: np.ndarray, tgt: np.ndarray, book_id: np.ndarray, window: int) -> np.ndarray:
    src, tgt = np.asarray(src, np.int64), np.asarray(tgt, np.int64)
    return same_book_mask(src, tgt, book_id) & (np.abs(src - tgt) <= window)


def same_chapter_mask(
    src: np.ndarray, tgt: np.ndarray, book_id: np.ndarray, chapter: np.ndarray
) -> np.ndarray:
    return same_book_mask(src, tgt, book_id) & (chapter[src] == chapter[tgt])


def exclusion_mask(
    src: np.ndarray,
    tgt: np.ndarray,
    book_id: np.ndarray,
    chapter: np.ndarray,
    exclude: Iterable[str],
    window: int,
) -> np.ndarray:
    exclude = set(exclude)
    unknown = exclude - set(EXCLUDES)
    if unknown:
        raise ValueError(f"unknown filters {sorted(unknown)}; choose from {EXCLUDES}")
    mask = np.zeros(len(src), dtype=bool)
    if "neighbors" in exclude:
        mask |= neighbor_mask(src, tgt, book_id, window)
    if "chapter" in exclude:
        mask |= same_chapter_mask(src, tgt, book_id, chapter)
    if "book" in exclude:
        mask |= same_book_mask(src, tgt, book_id)
    return mask


def apply_filters(
    df: pd.DataFrame,
    book_id: np.ndarray,
    chapter: np.ndarray,
    exclude: Iterable[str],
    window: int,
) -> pd.DataFrame:
    """Drop excluded rows of a verse top-k frame (integer `src`/`tgt`) and re-rank from 1."""
    src, tgt = df.src.to_numpy(), df.tgt.to_numpy()
    out = df[~exclusion_mask(src, tgt, book_id, chapter, exclude, window)]
    out = out.sort_values(["src", "rank"], kind="stable").reset_index(drop=True)
    out["rank"] = (out.groupby("src").cumcount() + 1).astype(np.int32)
    return out
