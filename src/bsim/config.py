"""Load the YAML config and hash config sections so artifacts can detect staleness."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "default.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load a config file (default: configs/default.yaml)."""
    cfg_path = Path(path) if path else DEFAULT_CONFIG
    with cfg_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError(f"Config {cfg_path} must be a mapping")
    return cfg


def _lookup(cfg: dict[str, Any], key: str) -> Any:
    cur: Any = cfg
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(part)
        cur = cur[part]
    return cur


def config_hash(cfg: dict[str, Any], *sections: str) -> str:
    """Stable short hash of the given sections (all if none given); a dotted name such as
    `structure.leitwort_skip_pos` hashes one key of a section."""
    keys = sections or tuple(sorted(cfg))
    values: dict[str, Any] = {}
    missing = []
    for k in keys:
        try:
            values[k] = _lookup(cfg, k)
        except KeyError:
            missing.append(k)
    if missing:
        raise KeyError(f"Unknown config sections: {missing}")
    payload = json.dumps(values, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def resolve_path(cfg: dict[str, Any], key: str) -> Path:
    """Resolve a `paths.<key>` entry relative to the project root."""
    p = Path(cfg["paths"][key])
    return p if p.is_absolute() else PROJECT_ROOT / p
