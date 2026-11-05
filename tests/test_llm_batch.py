"""The Message Batches core (series L1): the request, an answer read by its check, the
estimate and the budget, submit / poll / collect / resume, and the cost of a run."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from bsim.config import load_config
from bsim.eval import llm_batch as lb
from llm_fakes import fake_client, msg

LC = {**load_config()["llm_triage"], "budget_usd": 1.0}
SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}


def check(data):
    return {"ok": data["ok"]} if isinstance(data.get("ok"), bool) else None


def prepare():
    items = pd.DataFrame({"custom_id": ["a-0", "a-1", "a-2"], "x": [1, 2, 3]})
    reqs = [lb.make_request(c, "system", f"item {x}", SCHEMA, LC) for c, x in zip(
        items.custom_id, items.x, strict=True)]  # fmt: skip
    return items, reqs


def test_make_request():
    r = lb.make_request("a-0", "sys", "user", SCHEMA, LC)
    p = r["params"]
    assert r["custom_id"] == "a-0" and p["system"] == "sys"
    assert p["output_config"] == {
        "effort": LC["effort"],
        "format": {"type": "json_schema", "schema": SCHEMA},
    }
    assert p["messages"] == [{"role": "user", "content": "user"}] and "temperature" not in p


def test_parse_message():
    ok = lb.parse_message(msg('{"ok": true}', tin=7, tout=3), check)
    assert ok == {"input_tokens": 7, "output_tokens": 3, "status": "ok", "ok": True}
    assert lb.parse_message(msg('{"ok": 1}'), check)["status"] == "unreadable"
    assert lb.parse_message(msg("[1]"), check)["status"] == "unreadable"
    assert lb.parse_message(msg("{"), check)["status"] == "unreadable"
    assert lb.parse_message(msg("", stop="refusal"), check)["status"] == "refusal"
    assert lb.parse_message(msg("{", stop="max_tokens"), check)["status"] == "max_tokens"


def test_estimate_and_budget():
    _, reqs = prepare()
    est = lb.estimate(reqs, LC)
    assert est["max_usd"] >= est["typical_usd"] >= 0 and est["budget_usd"] == 1.0
    assert lb.within_budget(est)
    assert not lb.within_budget({**est, "typical_usd": 1.01})
    assert lb.usd(1e6, 1e6, {"input": 1.0, "output": 5.0}) == 6.0


def test_dry_run_writes_and_sends_nothing(tmp_path):
    client, batches = fake_client({})
    got = lb.run_batch(tmp_path, LC, prepare, check, log=lambda s: None, dry_run=True,
                       client=client)  # fmt: skip
    assert got["dry_run"] and got["requests"] == 3 and batches.created == []
    assert len((tmp_path / "requests.jsonl").read_text("utf-8").splitlines()) == 3
    assert (tmp_path / "items.parquet").exists() and not (tmp_path / "batch.json").exists()


def test_over_budget_is_refused(tmp_path):
    client, batches = fake_client({})
    with pytest.raises(RuntimeError, match="above budget_usd"):
        lc = {**LC, "budget_usd": 0.0, "typical_output_tokens": 10**6}
        lb.run_batch(tmp_path, lc, prepare, check, log=lambda s: None, client=client)
    assert batches.created == [] and not (tmp_path / "batch.json").exists()


def test_submitted_polled_collected_and_resumed(tmp_path):
    answers = {"a-0": {"ok": True}, "a-1": "not json", "a-2": None}
    client, batches = fake_client(answers, rounds=2)
    sleeps = []
    got = lb.run_batch(tmp_path, LC, prepare, check, log=lambda s: None, client=client,
                       sleep=sleeps.append)  # fmt: skip
    assert isinstance(got, lb.Collected) and len(batches.created) == 1 and len(sleeps) == 2
    df = got.df.set_index("custom_id")
    assert df.status.to_dict() == {"a-0": "ok", "a-1": "unreadable", "a-2": "errored"}
    assert df.x.tolist() == [1, 2, 3] and df.input_tokens.tolist() == [100, 100, 0]
    u = lb.usage(got.df, LC)
    assert (u["input_tokens"], u["output_tokens"], u["mean_output_tokens"]) == (200, 100, 50)
    # written before polling, so a stopped run resumes the same batch instead of paying again
    state = json.loads((tmp_path / "batch.json").read_text("utf-8"))
    assert state["batch_id"] == "msgbatch_1" and not state["collected"]
    again, again_batches = fake_client(answers)
    lb.run_batch(tmp_path, LC, lambda: pytest.fail("prepared again"), check,
                 log=lambda s: None, client=again, sleep=lambda s: None)  # fmt: skip
    assert again_batches.created == []
    # once collected, a new run starts a new batch
    lb.mark_collected(tmp_path, state)
    third, third_batches = fake_client(answers)
    lb.run_batch(tmp_path, LC, prepare, check, log=lambda s: None, client=third,
                 sleep=lambda s: None)  # fmt: skip
    assert len(third_batches.created) == 1


def test_a_batch_of_errors_still_has_its_columns(tmp_path):
    client, _ = fake_client({"a-0": None, "a-1": None, "a-2": None})
    got = lb.run_batch(tmp_path, LC, prepare, check, log=lambda s: None, client=client,
                       sleep=lambda s: None)  # fmt: skip
    df = lb.ensure_columns(got.df, {"ok": None})
    assert df.status.eq("errored").all() and df.ok.isna().all()
    assert lb.usage(df, LC)["mean_output_tokens"] is None


def test_missing_answers_are_marked(tmp_path):
    client, _ = fake_client({"a-0": {"ok": False}})
    got = lb.run_batch(tmp_path, LC, prepare, check, log=lambda s: None, client=client,
                       sleep=lambda s: None)  # fmt: skip
    assert got.df.status.tolist() == ["ok", "missing", "missing"]


def test_pointed_and_clean_rationale_are_shared():
    assert lb.pointed("בְּרֵאשִׁ֖ית") == "בְּרֵאשִׁית"
    assert lb.clean_rationale('השמים ("heavens") שניהם') == "השמים שניהם"
