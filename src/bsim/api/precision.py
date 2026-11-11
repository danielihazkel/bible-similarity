"""Detector precision by Claude's reading, read from the `bsim llm-audit` runs (DESIGN.md
§16.86, D147): kept in memory and read again when a run's meta file changes, as the notes are."""

from __future__ import annotations

import threading
from typing import Any

from bsim.eval.llm_audit import read_precision, run_files

_cache: dict[tuple, dict[str, Any]] = {}
_lock = threading.Lock()


def precision(cfg: dict[str, Any]) -> dict[str, Any]:
    """`runs` and `detectors` of the calibrated runs; both empty when none is there."""
    key = tuple((str(p), p.stat().st_mtime_ns) for p in run_files(cfg) if p.exists())
    with _lock:
        if key not in _cache:
            _cache.clear()
            _cache[key] = read_precision(cfg) if key else {"runs": [], "detectors": {}}
        return _cache[key]
