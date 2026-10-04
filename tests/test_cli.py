import yaml
from typer.testing import CliRunner

from bsim.cli import app
from bsim.config import load_config

COMMANDS = [
    "download",
    "build-corpus",
    "build-links",
    "lexical",
    "embed",
    "train-simcse",
    "train-sup",
    "topk",
    "units",
    "fuse",
    "evaluate",
    "build-db",
    "serve",
    "all",
]

runner = CliRunner()


def test_help_lists_all_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in COMMANDS:
        assert cmd in result.output


def test_stub_exits_nonzero():
    result = runner.invoke(app, ["all"])
    assert result.exit_code == 1
    assert "M13" in result.output


def test_serve_without_db_exits_nonzero(tmp_path):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "db": str(tmp_path / "missing.sqlite")}
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    result = runner.invoke(app, ["serve", "--config", str(path)])
    assert result.exit_code == 1
    assert "bsim build-db" in result.output


def test_embed_unknown_system_exits_nonzero():
    result = runner.invoke(app, ["embed", "--model", "nope"])
    assert result.exit_code == 1
    assert "unknown encoder system" in result.output
