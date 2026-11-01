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
    (root / "c.py").write_bytes(b"# a comment\r\nx = 1  # one\r\n")  # layout and CRLF only
    assert inc.code_hash(stage, root, "fakepkg") == h
    (root / "c.py").write_text("x = 2\n")
    assert inc.code_hash(stage, root, "fakepkg") != h


def test_deps_name_earlier_stages():
    order = list(pipeline.STAGES)
    assert list(pipeline.DEPS) == order
    for name, deps in pipeline.DEPS.items():
        assert all(order.index(d) < order.index(name) for d in deps), name
    assert set(pipeline.DEPS["build-db"]) == set(order) - {"build-db"}
    assert pipeline.downstream(["diffs"]) == {"borrowing", "ketiv", "echoes", "masorah", "els",
                                              "build-db"}


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


def test_adopt_keeps_a_record(toy):
    cfg, run, logs, art = toy
    run()
    cfg["toy"]["b"] = 22
    assert run(adopt=True, start="b", stop="b") == []
    assert run() == []  # b's new config accepted; its inputs and outputs still tracked
    (art / "a" / "out.txt").write_text("other", "utf-8")
    assert run() == ["a"]  # a restores "x": b's recorded input is unchanged
    state = json.loads(Path(cfg["paths"]["pipeline_state"]).read_text("utf-8"))
    assert state["stages"]["b"]["inputs"] and state["stages"]["b"]["outputs"]


def test_adopt_takes_a_new_dependency(toy):
    cfg, run, logs, art = toy
    run()
    path = Path(cfg["paths"]["pipeline_state"])
    state = json.loads(path.read_text("utf-8"))
    b_out = next(iter(state["stages"]["b"]["outputs"]))
    del state["stages"]["c"]["inputs"][b_out]  # as if c had declared b only after it ran
    path.write_text(json.dumps(state), "utf-8")
    run(dry_run=True)
    assert any(m.split()[:3] == ["run", "c", "new"] for m in logs)
    assert run(adopt=True, start="c", stop="c") == []
    assert run() == []
    assert b_out in json.loads(path.read_text("utf-8"))["stages"]["c"]["inputs"]


def test_server_cache_is_never_a_stage_file(toy):
    cfg, run, logs, art = toy
    run()
    cache = art / cfg["serve"]["cache_dir"] / "surface_bm25.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text("1", "utf-8")
    key = inc.file_key(cache)
    assert inc.Scope.from_config(cfg).ignored(key)
    path = Path(cfg["paths"]["pipeline_state"])
    state = json.loads(path.read_text("utf-8"))
    state["stages"]["a"]["outputs"][key] = "stale"  # as if the server rewrote it during a's run
    path.write_text(json.dumps(state), "utf-8")
    cache.write_text("2", "utf-8")  # `bsim serve` after a rebuild
    assert run() == []  # ignored: nothing is stale
    assert run(rerun=["a"]) == ["a"]  # and the next record drops it
    assert key not in json.loads(path.read_text("utf-8"))["stages"]["a"]["outputs"]


def stage_meta(cfg, log):
    """Writes a meta file stamped with a new build time on every run."""
    RUNS.append("meta")
    out = Path(cfg["paths"]["artifacts"]) / "meta"
    out.mkdir(parents=True, exist_ok=True)
    meta = {"rows": cfg["toy"]["a"], "built_at": f"t{len(RUNS)}-{id(RUNS)}", "seconds": 0.1}
    (out / "m.meta.json").write_text(json.dumps(meta), "utf-8")


def stage_reader(cfg, log):
    RUNS.append("reader")
    art = Path(cfg["paths"]["artifacts"])
    rows = json.loads((art / "meta" / "m.meta.json").read_text("utf-8"))["rows"]
    raw = Path(cfg["paths"]["data_raw"])
    seen = (raw / "lex" / "dict.xml").exists()  # checked, never opened: only RAW ties them
    (art / "reader").mkdir(exist_ok=True)
    (art / "reader" / "out.txt").write_text(f"{rows}{seen}", "utf-8")


@pytest.fixture
def toy2(monkeypatch, pipeline_cfg):
    cfg = pipeline_cfg
    cfg["toy"] = {"a": "x"}
    stages = {"download": "stage_download", "meta": "stage_meta", "reader": "stage_reader"}
    monkeypatch.setattr(pipeline, "STAGES", stages)
    monkeypatch.setattr(pipeline, "DEPS", {"download": (), "meta": (),
                                           "reader": ("download", "meta")})  # fmt: skip
    monkeypatch.setattr(pipeline, "RAW", {"reader": ("lex/*",)})
    monkeypatch.setattr(pipeline, "UNTRACKED", {})

    def stage_download(cfg, log):
        raw = Path(cfg["paths"]["data_raw"])
        raw.mkdir(parents=True, exist_ok=True)
        (raw / "manifest.json").write_text(json.dumps({"updated_at": str(len(RUNS))}), "utf-8")

    monkeypatch.setattr(pipeline, "stage_download", stage_download, raising=False)
    for name in ("stage_meta", "stage_reader"):
        monkeypatch.setattr(pipeline, name, globals()[name], raising=False)
    logs: list[str] = []

    def run(**kw):
        RUNS.clear()
        logs.clear()
        pipeline.run_all(cfg, log=logs.append, **kw)
        return list(RUNS)

    raw = Path(cfg["paths"]["data_raw"])
    (raw / "lex").mkdir(parents=True)
    (raw / "lex" / "dict.xml").write_text("<d/>", "utf-8")
    return cfg, run, logs, raw


def test_restamped_meta_leaves_dependents_skipped(toy2):
    cfg, run, logs, raw = toy2
    assert run() == ["meta", "reader"]
    assert run(rerun=["meta"]) == ["meta"]  # only its built_at changed
    cfg["toy"]["a"] = "y"
    assert run() == ["meta", "reader"]  # a real change still reaches it


def test_json_hashes_migrate_without_turning_stale(toy2):
    cfg, run, logs, raw = toy2
    cfg["pipeline"]["volatile_keys"] = []  # hashed byte for byte, as before
    run()
    cfg["pipeline"]["volatile_keys"] = ["built_at", "seconds"]
    assert run() == []
    state = json.loads(Path(cfg["paths"]["pipeline_state"]).read_text("utf-8"))
    assert state["volatile"] == ["built_at", "seconds"]
    assert run(rerun=["meta"]) == ["meta"]


def test_downloads_are_inputs_by_raw_pattern(toy2):
    cfg, run, logs, raw = toy2
    run()
    assert run(rerun=["download"]) == []  # the manifest is rewritten: no stage reads it
    (raw / "geo").mkdir()
    (raw / "geo" / "places.txt").write_text("new group", "utf-8")
    assert run() == []  # another group's files
    (raw / "lex" / "more.xml").write_text("<m/>", "utf-8")
    run(dry_run=True)
    assert any(m.split()[:3] == ["run", "reader", "new"] for m in logs)
    assert run() == ["reader"]
    (raw / "lex" / "dict.xml").write_text("<d>edited</d>", "utf-8")
    assert run() == ["reader"]


def test_read_outside_raw_is_noted(toy2, monkeypatch):
    cfg, run, logs, raw = toy2
    monkeypatch.setattr(pipeline, "RAW", {})
    (raw / "lex" / "dict.xml").write_text("<d/>", "utf-8")

    def stage_reader(cfg, log):
        RUNS.append("reader")
        (Path(cfg["paths"]["data_raw"]) / "lex" / "dict.xml").read_text("utf-8")

    monkeypatch.setattr(pipeline, "stage_reader", stage_reader, raising=False)
    run()
    assert any(m.startswith("note: reader read ") and "pipeline.RAW" in m for m in logs)


def test_untracked_adopt_takes_its_declared_config_and_outputs(toy2, monkeypatch):
    cfg, run, logs, raw = toy2
    cfg["train"]["simcse"]["output"] = "toy-model"
    model = Path(cfg["paths"]["models"]) / "toy-model"
    model.mkdir(parents=True)
    (model / "weights.bin").write_bytes(b"w1")
    monkeypatch.setattr(pipeline, "UNTRACKED", {"meta": (("toy",), "simcse")})
    assert run(adopt=True) == []
    state = json.loads(Path(cfg["paths"]["pipeline_state"]).read_text("utf-8"))["stages"]
    assert list(state["meta"]["config"]) == ["toy"]
    assert any(k.endswith("toy-model/weights.bin") for k in state["meta"]["outputs"])
    cfg["syntax"]["speaker_lookback"] = 99  # a section its imports name, not one it reads
    assert run(dry_run=True) == [] and any(m.split()[:2] == ["skip", "meta"] for m in logs)
    (model / "weights.bin").write_bytes(b"w2")  # retrained by hand
    run(dry_run=True)
    assert any(m.split()[:2] == ["run", "meta"] and "output" in m for m in logs)


def test_reports_are_no_stage_input(toy2, monkeypatch):
    cfg, run, logs, raw = toy2

    def stage_meta(cfg, log):
        RUNS.append("meta")
        out = Path(cfg["paths"]["artifacts"]) / "meta"
        out.mkdir(parents=True, exist_ok=True)
        (out / "m.meta.json").write_text(json.dumps({"rows": cfg["toy"]["a"]}), "utf-8")
        (out / "report.md").write_text(f"Built {len(RUNS)}-{id(RUNS)}", "utf-8")

    monkeypatch.setattr(pipeline, "stage_meta", stage_meta, raising=False)
    assert run() == ["meta", "reader"]
    state = json.loads(Path(cfg["paths"]["pipeline_state"]).read_text("utf-8"))["stages"]
    assert any(k.endswith("report.md") for k in state["meta"]["outputs"])
    assert not any(k.endswith("report.md") for k in state["reader"]["inputs"])
    assert run(rerun=["meta"]) == ["meta"]  # a new "Built" line reaches no one
    (Path(cfg["paths"]["artifacts"]) / "meta" / "report.md").unlink()
    assert run() == ["meta"]  # still meta's own output
