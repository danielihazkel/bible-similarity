"""Paths and script loading shared by the video tools (video/README.md)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

VIDEO = Path(__file__).resolve().parents[1]
SCRIPTS = {"a": VIDEO / "script" / "a-general.yaml", "b": VIDEO / "script" / "b-dev.yaml"}
OUT = VIDEO / "out"
RATE = 48_000  # Hz, every audio file the tools write


def load_script(film: str) -> dict[str, Any]:
    return yaml.safe_load(SCRIPTS[film].read_text(encoding="utf-8"))


def film_dir(film: str) -> Path:
    path = OUT / film
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def ffmpeg(*args: str) -> bytes:
    """Run ffmpeg quietly and return its stdout."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *args]
    return subprocess.run(cmd, check=True, capture_output=True, timeout=600).stdout
