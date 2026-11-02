"""Shared pytest fixtures: the tiny `results.sqlite` of `bsim.fixture` (test_store, test_api)
and an isolated config for `bsim all` (test_pipeline, test_incremental)."""

import shutil

import pytest

from bsim.config import load_config
from bsim.fixture import EMB, TEXTS, build_fixture_db, fixture_cfg

__all__ = ["EMB", "TEXTS", "build_fixture_db"]


@pytest.fixture(scope="session")
def built_once(tmp_path_factory):
    """The fixture build, run once per session (it takes seconds); tests get a copy of it."""
    root = tmp_path_factory.mktemp("fixture")
    _, db = build_fixture_db(root)
    return root, db.relative_to(root)


@pytest.fixture
def built(built_once, tmp_path):
    """(cfg, db) of a fresh copy of the fixture build under `tmp_path`, free to change."""
    root, db = built_once
    shutil.copytree(root, tmp_path, dirs_exist_ok=True)
    return fixture_cfg(tmp_path), tmp_path / db


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
