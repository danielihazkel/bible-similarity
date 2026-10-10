import copy
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bsim import incremental as inc
from bsim import pipeline
from bsim.cli import app

RUNS: list[str] = []


def stage_a(cfg, log):
    RUNS.append("a")
    out = Path(cfg["paths"]["artifacts"]) / "a"
    out.mkdir(parents=True, exist_ok=True)
    (out / "out.txt").write_text(cfg["toy"]["a"], "utf-8")


def stage_b(cfg, log):
    RUNS.append("b")
    art = Path(cfg["paths"]["artifacts"])
    text = (art / "a" / "out.txt").read_text("utf-8")
    (art / "b").mkdir(exist_ok=True)
    (art / "b" / "out.txt").write_text(f"{text.upper()}{cfg['toy']['b']}", "utf-8")


def stage_c(cfg, log):
    """Checks for b's output without opening it, so only DEPS ties it to b; opens a's."""
    RUNS.append("c")
    art = Path(cfg["paths"]["artifacts"])
    seen = (art / "b" / "out.txt").exists() and (art / "a" / "out.txt").read_text("utf-8")
    (art / "c").mkdir(exist_ok=True)
    (art / "c" / "out.txt").write_text(f"c{bool(seen)}", "utf-8")


@pytest.fixture
def toy(monkeypatch, pipeline_cfg):
    cfg = pipeline_cfg
    cfg["toy"] = {"a": "x", "b": 1, "other": 0}
    monkeypatch.setattr(pipeline, "STAGES", {"a": "stage_a", "b": "stage_b", "c": "stage_c"})
    monkeypatch.setattr(pipeline, "DEPS", {"a": (), "b": ("a",), "c": ("b",)})
    for name in ("stage_a", "stage_b", "stage_c"):
        monkeypatch.setattr(pipeline, name, globals()[name], raising=False)
    RUNS.clear()
    logs: list[str] = []

    def run(**kw):
        RUNS.clear()
        logs.clear()
        pipeline.run_all(cfg, log=logs.append, **kw)
        return list(RUNS)

    return cfg, run, logs, Path(cfg["paths"]["artifacts"])


def test_tracked_config_records_what_is_read():
    cfg = inc.TrackedConfig({"a": {"x": 1, "y": {"z": 2}}, "b": 3, "c": {"k": 1}})
    assert cfg["a"]["x"] == 1 and cfg["a"]["y"] == {"z": 2} and cfg["b"] == 3
    assert cfg.get("missing", 5) == 5 and "gone" not in cfg["a"]
    assert cfg.seen == {"a.x", "a.y", "b", "missing", "a.gone"}
    json.dumps({"c": cfg["c"]})  # a section dumped whole (as `config_hash` does)
    assert "c" in cfg.seen
    copied = copy.deepcopy(cfg)  # `with_overrides` copies the config and keeps reading it
    copied["a"]["y"]["z"] = 9
    assert cfg["a"]["y"]["z"] == 2 and copied["a"]["y"]["z"] == 9
    sorted(cfg)
    assert inc.minimal_keys(cfg.seen) == ["*"]
    assert inc.minimal_keys({"a", "a.x", "b.y"}) == ["a", "b.y"]


def test_config_value():
    cfg = {"a": {"x": 1}}
    assert inc.config_value(cfg, "a.x") == 1 and inc.config_value(cfg, "*") is cfg
    assert inc.config_value(cfg, "a.y") == inc.MISSING == inc.config_value(cfg, "a.x.z")


def test_code_hash_follows_imports(tmp_path):
    root = tmp_path / "fakepkg"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "a.py").write_text("from . import b\n")
    (root / "b.py").write_text("def f():\n    from fakepkg.c import x\n")
    (root / "c.py").write_text("x = 1\n")
    (root / "d.py").write_text("y = 1\n")
    closure = inc.module_closure(["fakepkg.a"], root, "fakepkg")
    assert closure == ["fakepkg", "fakepkg.a", "fakepkg.b", "fakepkg.c"]

    def stage(cfg, log):
        from fakepkg import a  # noqa: F401

    h = inc.code_hash(stage, root, "fakepkg")
    (root / "d.py").write_text("y = 2\n")
    assert inc.code_hash(stage, root, "fakepkg") == h
    (root / "c.py").write_text("x = 2\n")
    assert inc.code_hash(stage, root, "fakepkg") != h


def test_deps_name_earlier_stages():
    order = list(pipeline.STAGES)
    assert list(pipeline.DEPS) == order
    for name, deps in pipeline.DEPS.items():
        assert all(order.index(d) < order.index(name) for d in deps), name
    assert set(pipeline.DEPS["build-db"]) == set(order) - {"build-db"}
    assert pipeline.downstream(["diffs"]) == {"borrowing", "ketiv", "build-db"}


def test_stage_code_hashes_cover_their_modules():
    """A real stage's hash covers its runner's module and what that imports."""
    closure = inc.module_closure(["bsim.analysis.mirrors"])
    assert "bsim.analysis.stats" in closure and "bsim.config" in closure
    assert inc.code_hash(pipeline.stage_mirrors) != inc.code_hash(pipeline.stage_allusions)


def test_incremental_runs(toy):
    cfg, run, logs, art = toy
    assert run() == ["a", "b", "c"]
    assert run() == []
    assert any("a: up to date, skipped" in m for m in logs)
    cfg["toy"]["other"] = 5  # a key no stage reads
    assert run() == []
    cfg["toy"]["b"] = 22  # b reads it; c depends on b's output
    assert run() == ["b", "c"]
    assert any("(config toy.b changed)" in m for m in logs)
    assert run(rerun=["a"]) == ["a"]  # same bytes again: b and c stay skipped
    (art / "c" / "out.txt").unlink()
    assert run() == ["c"]
    (art / "a" / "out.txt").write_text("edited by hand", "utf-8")
    assert run() == ["a"]  # restores the same bytes, so b's input is as recorded
    assert run(force=True) == ["a", "b", "c"]
    assert run(start="b", stop="b") == []


def test_reads_are_inputs_and_undeclared_ones_noted(toy):
    cfg, run, logs, art = toy
    run()
    assert any(m.startswith("note: c read ") and "written by a," in m for m in logs)
    state = json.loads(Path(cfg["paths"]["pipeline_state"]).read_text("utf-8"))
    a_out = next(iter(state["stages"]["a"]["outputs"]))
    assert a_out.endswith("a/out.txt")
    assert a_out in state["stages"]["b"]["inputs"] and a_out in state["stages"]["c"]["inputs"]
    assert state["stages"]["b"]["config"].keys() >= {"toy.b", "paths.artifacts"}


def test_dry_run_and_adopt(toy):
    cfg, run, logs, art = toy
    run()
    cfg["toy"]["a"] = "xyz"
    assert run(dry_run=True) == []
    assert any(m.split() == ["run", "a", "config", "toy.a", "changed"] for m in logs)
    assert any(m.split()[:2] == ["maybe", "c"] for m in logs)
    Path(cfg["paths"]["pipeline_state"]).unlink()
    assert run(adopt=True) == []
    assert run() == []
    cfg["toy"]["b"] = 333  # an adopted stage reruns on any change to a section its code names
    assert "b" in run()


def test_cli_flags(toy, monkeypatch):
    cfg, run, logs, art = toy
    result = CliRunner().invoke(app, ["all", "--dry-run"])
    assert result.exit_code == 0 and "never run" in result.output
    result = CliRunner().invoke(app, ["all", "--rerun", "nope"])
    assert result.exit_code != 0
