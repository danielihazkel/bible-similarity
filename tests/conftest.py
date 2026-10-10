"""Shared pytest fixtures: the tiny `results.sqlite` of `bsim.fixture` (test_store, test_api)
and an isolated config for `bsim all` (test_pipeline, test_incremental)."""

import pytest

from bsim.config import load_config
from bsim.fixture import EMB, TEXTS, build_fixture_db

__all__ = ["EMB", "TEXTS", "build_fixture_db"]


@pytest.fixture
def built(tmp_path):
    return build_fixture_db(tmp_path)


@pytest.fixture
def pipeline_cfg(monkeypatch, tmp_path):
    """The default config with `bsim all`'s folders and state under `tmp_path` (CLI too)."""
    cfg = load_config()
    cfg["paths"] = {
        **cfg["paths"],
        **{k: str(tmp_path / k) for k in cfg["pipeline"]["roots"]},
        "pipeline_state": str(tmp_path / "state.json"),
        "labels": str(tmp_path / "labels.sqlite"),
    }
    monkeypatch.setattr("bsim.cli.load_config", lambda path=None: cfg)
    return cfg
