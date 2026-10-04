from typer.testing import CliRunner

from bsim.cli import app

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
    result = runner.invoke(app, ["build-links"])
    assert result.exit_code == 1
    assert "M3" in result.output
