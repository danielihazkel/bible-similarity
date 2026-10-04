import pytest

from bsim.config import config_hash, load_config, resolve_path


def test_default_config_loads():
    cfg = load_config()
    assert cfg["retrieval"]["k"] == 50
    assert cfg["retrieval"]["neighbor_window"] == 2
    assert cfg["text"]["kq"] in {"qere", "ketiv"}


def test_config_hash_is_stable_and_section_sensitive():
    cfg = load_config()
    h = config_hash(cfg, "lexical")
    assert h == config_hash(cfg, "lexical")
    cfg["lexical"]["bm25"]["k1"] = 2.0
    assert config_hash(cfg, "lexical") != h


def test_config_hash_unknown_section():
    with pytest.raises(KeyError):
        config_hash(load_config(), "nope")


def test_resolve_path_is_absolute():
    assert resolve_path(load_config(), "data_raw").is_absolute()
