"""Claude's notes on verse pairs, read from the series L runs (DESIGN.md §16.88, D144).

`eval/llm_notes.read_notes` gathers the calibrated runs; this keeps the result in memory and
reads it again when any of their files changes, as the label queue's suggestions are read.
"""

from __future__ import annotations

import threading
from typing import Any

from bsim.eval.llm_notes import read_notes, run_files

_cache: dict[tuple, tuple[dict[str, Any], dict[tuple[int, int], dict]]] = {}
_lock = threading.Lock()


def notes(cfg: dict[str, Any]) -> tuple[dict[str, Any], dict[tuple[int, int], dict]]:
    """(runs, undirected verse pair -> note); ({}, {}) when no run is there."""
    key = tuple((str(p), p.stat().st_mtime_ns) for p in run_files(cfg) if p.exists())
    with _lock:
        if key not in _cache:
            _cache.clear()
            _cache[key] = read_notes(cfg) if key else ({}, {})
        return _cache[key]


def note_for(cfg: dict[str, Any], a: int, b: int) -> dict[str, Any] | None:
    return notes(cfg)[1].get((min(a, b), max(a, b)))
