"""Shared pytest fixtures: the tiny `results.sqlite` of `bsim.fixture` (test_store, test_api)."""

import pytest

from bsim.fixture import EMB, TEXTS, build_fixture_db

__all__ = ["EMB", "TEXTS", "build_fixture_db"]


@pytest.fixture
def built(tmp_path):
    return build_fixture_db(tmp_path)
