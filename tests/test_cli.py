import json

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
    "embed-context",
    "maxsim",
    "retrieval-exp",
    "senses",
    "build-db",
    "serve",
    "fixture-serve",
    "openapi",
    "all",
]

runner = CliRunner()


def test_help_lists_all_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in COMMANDS:
        assert cmd in result.output


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


def test_openapi_writes_the_viewer_schema(tmp_path):
    out = tmp_path / "openapi.json"
    result = runner.invoke(app, ["openapi", "--out", str(out)])
    assert result.exit_code == 0, result.output
    schema = json.loads(out.read_text(encoding="utf-8"))
    assert "/api/books" in schema["paths"] and "/api/similar/{unit_id}" in schema["paths"]
    # a field with a default is always in the response, so the generated type requires it
    unit = schema["components"]["schemas"]["UnitSummary"]
    assert "marker" in unit["required"]
