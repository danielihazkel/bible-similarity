import json
import sqlite3

import pytest
from typer.testing import CliRunner

from bsim.cli import app
from bsim.store.compare import compare_builds, report

CFG = {"compare_builds": {"float_tol": 1e-9, "examples": 5, "volatile_meta": ["built_at"]}}


def _db(path, verses, pairs, meta, extra=None):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE verses (verse_id INTEGER PRIMARY KEY, ref TEXT, score REAL)")
    con.executemany("INSERT INTO verses VALUES (?, ?, ?)", verses)
    con.execute("CREATE TABLE pairs (a INTEGER, b INTEGER, g2 REAL)")  # no key
    con.executemany("INSERT INTO pairs VALUES (?, ?, ?)", pairs)
    con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    con.executemany("INSERT INTO meta VALUES (?, ?)", [(k, json.dumps(v)) for k, v in meta.items()])
    for sql in extra or []:
        con.execute(sql)
    con.commit()
    con.close()
    return path


VERSES = [(0, "Gen 1:1", 0.5), (1, "Gen 1:2", 0.25), (2, "Gen 1:3", None)]
PAIRS = [(0, 1, 3.0), (0, 2, 3.0), (1, 2, 1.5)]
META = {"built_at": "2026-10-13", "senses": {"lemmas": 120, "examples": [1, 2]}, "n": 3}


def test_identical_builds(tmp_path):
    a = _db(tmp_path / "a.sqlite", VERSES, PAIRS, META)
    b = _db(tmp_path / "b.sqlite", VERSES, PAIRS, {**META, "built_at": "2026-10-14"})
    out = compare_builds(CFG, a, b)
    assert out["identical"]
    assert out["meta"]["volatile"] == {"built_at": ["2026-10-13", "2026-10-14"]}
    assert "the same (apart from built_at)" in report(out) and "Identical." in report(out)


def test_rows_keys_tolerance_and_order(tmp_path):
    a = _db(tmp_path / "a.sqlite", VERSES, PAIRS, META, ["CREATE TABLE gone (x INTEGER)"])
    verses = [
        (0, "Gen 1:1", 0.5 + 1e-12),  # within the tolerance: changed, but not beyond it
        (1, "Gen 1:2", 0.3),  # beyond it
        (3, "Gen 1:4", 0.1),  # added; verse 2 removed
    ]
    pairs = [(1, 2, 1.5), (0, 2, 3.0), (0, 1, 3.0)]  # the same rows, another order
    meta = {**META, "senses": {"lemmas": 121, "examples": [1, 2]}, "new_key": 1}
    b = _db(tmp_path / "b.sqlite", verses, pairs, meta, ["CREATE TABLE added (x INTEGER)"])
    out = compare_builds(CFG, a, b)
    assert not out["identical"]
    assert out["tables_added"] == ["added"] and out["tables_removed"] == ["gone"]
    v = out["tables"]["verses"]
    assert v["key"] == ["verse_id"] and (v["only_old"], v["only_new"]) == (1, 1)
    assert (v["changed"], v["changed_beyond_tol"]) == (2, 1)
    assert v["examples"] == [{"key": [1], "columns": ["score"]}]
    p = out["tables"]["pairs"]
    assert p["key"] is None and (p["only_old"], p["only_new"]) == (0, 0) and p["reordered"]
    assert out["meta"]["added"] == ["new_key"]
    assert out["meta"]["changed"] == {
        "senses": {"paths": 1, "examples": [{"path": "lemmas", "old": 120, "new": 121}]}
    }
    md = report(out)
    assert "| verses | 3 | 3 | 1 | 1 | 2 (1) | [1]: score |" in md
    assert "same rows, another order" in md and "Only in NEW: added." in md


def test_duplicates_and_columns(tmp_path):
    a = _db(tmp_path / "a.sqlite", VERSES, PAIRS + [(0, 1, 3.0)], META)
    b = _db(tmp_path / "b.sqlite", VERSES, PAIRS, META)
    p = compare_builds(CFG, a, b)["tables"]["pairs"]
    assert (p["only_old"], p["only_new"]) == (1, 0) and not p["reordered"]
    c = _db(tmp_path / "c.sqlite", [], [], META)
    con = sqlite3.connect(c)
    con.execute("ALTER TABLE verses ADD COLUMN book INTEGER")
    con.commit()
    con.close()
    v = compare_builds(CFG, b, c)["tables"]["verses"]
    assert v["columns_added"] == ["book"] and (v["only_old"], v["only_new"]) == (3, 0)


def test_missing_file(tmp_path):
    with pytest.raises(RuntimeError, match="not found"):
        compare_builds(CFG, tmp_path / "a.sqlite", tmp_path / "b.sqlite")


def test_cli_report_json_and_exit_code(tmp_path):
    a = _db(tmp_path / "a.sqlite", VERSES, PAIRS, META)
    b = _db(tmp_path / "b.sqlite", VERSES[:2], PAIRS, META)
    runner = CliRunner()
    same = runner.invoke(app, ["compare-builds", str(a), str(a), "--fail-on-diff"])
    assert same.exit_code == 0 and "Identical." in same.output
    out = tmp_path / "out" / "diff.json"
    differ = runner.invoke(app, ["compare-builds", str(a), str(b), "--json", str(out)])
    assert differ.exit_code == 0 and "| verses | 3 | 2 | 1 | 0 |" in differ.output
    assert json.loads(out.read_text("utf-8"))["tables"]["verses"]["only_old"] == 1
    failed = runner.invoke(app, ["compare-builds", str(a), str(b), "--fail-on-diff"])
    assert failed.exit_code == 1
    missing = runner.invoke(app, ["compare-builds", str(a), str(tmp_path / "x.sqlite")])
    assert missing.exit_code == 1 and "not found" in missing.output
