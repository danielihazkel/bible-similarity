import json

import pytest
from typer.testing import CliRunner

from bsim import pipeline
from bsim.cli import app
from bsim.config import load_config

runner = CliRunner()


@pytest.fixture
def calls(monkeypatch):
    """Replace every stage with a recorder."""
    seen: list[str] = []
    for name, fn in pipeline.STAGES.items():
        monkeypatch.setattr(pipeline, fn, lambda cfg, log, name=name: seen.append(name))
    return seen


def test_all_runs_every_stage_in_order(calls):
    result = runner.invoke(app, ["all"])
    assert result.exit_code == 0, result.output
    assert calls == list(pipeline.STAGES)
    assert "total" in result.output


def test_all_from_to_slice(calls):
    result = runner.invoke(app, ["all", "--from", "embed", "--to", "units"])
    assert result.exit_code == 0, result.output
    assert calls == ["embed", "topk", "units"]


def test_all_skip(calls):
    result = runner.invoke(app, ["all", "--skip", "train-simcse", "--skip", "download"])
    assert result.exit_code == 0, result.output
    assert calls == [s for s in pipeline.STAGES if s not in {"train-simcse", "download"}]


@pytest.mark.parametrize(
    "args", [["--from", "nope"], ["--skip", "nope"], ["--from", "units", "--to", "embed"]]
)
def test_all_bad_stage_selection(calls, args):
    result = runner.invoke(app, ["all", *args])
    assert result.exit_code != 0
    assert calls == []


def test_all_failing_stage_names_it(monkeypatch, calls):
    def boom(cfg, log):
        raise RuntimeError("no verses")

    monkeypatch.setattr(pipeline, pipeline.STAGES["lexical"], boom)
    result = runner.invoke(app, ["all"])
    assert result.exit_code == 1
    assert "stage 'lexical' failed: no verses" in result.output
    assert calls == ["download", "build-corpus", "build-links", "lexicon", "syntax"]


def test_dense_systems_adds_csls():
    cfg = load_config()
    cfg["encoders"] = {"systems": {"a": {}, "b": {}}}
    cfg["pipeline"] = {**cfg["pipeline"], "csls": True}
    assert pipeline.dense_systems(cfg) == ["a", "a_csls", "b", "b_csls"]
    cfg["pipeline"]["csls"] = False
    assert pipeline.dense_systems(cfg) == ["a", "b"]


@pytest.mark.parametrize("has_test", [False, True])
def test_evaluate_stage_runs_test_split_once(monkeypatch, tmp_path, has_test):
    import bsim.eval.report as report

    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "artifacts": str(tmp_path)}
    if has_test:
        (tmp_path / "eval").mkdir()
        metrics = {"splits": {"test": {"evaluated_at": "2026-10-04"}}}
        (tmp_path / "eval" / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    splits: list[str] = []
    monkeypatch.setattr(
        report, "run_evaluate", lambda cfg, split, log, force=False: splits.append(split)
    )
    logs: list[str] = []
    pipeline.stage_evaluate(cfg, logs.append)
    assert splits == (["dev"] if has_test else ["dev", "test"])
    assert any("skipped" in m for m in logs) == has_test
