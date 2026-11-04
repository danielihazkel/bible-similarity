"""`bsim llm-triage` (DESIGN.md §16.81, D134) with a fake Message Batches client: the prompt, the
answers read, the calibration pairs, a batch submitted, resumed and collected; the queue's
suggestions over the fixture DB."""

from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.config import load_config, resolve_path
from bsim.eval import llm_triage as lt
from bsim.fixture import fixture_encoder

CFG = load_config()["llm_triage"]


def _msg(text, stop="end_turn", tin=100, tout=50):
    return NS(
        stop_reason=stop,
        content=[NS(type="thinking", thinking=""), NS(type="text", text=text)],
        usage=NS(input_tokens=tin, output_tokens=tout),
    )


def test_pointed_keeps_the_points_and_drops_the_accents():
    assert lt.pointed("בְּרֵאשִׁ֖ית בָּרָ֣א") == "בְּרֵאשִׁית בָּרָא"


def test_request_and_prompt():
    a, b = {"ref": "Genesis 1:1", "text": "בראשית"}, {"ref": "Jeremiah 23:24", "text": "השמים"}
    r = lt.request("tri-0", a, b, CFG)
    p = r["params"]
    assert r["custom_id"] == "tri-0" and p["model"] == CFG["model"]
    assert p["output_config"]["format"]["schema"]["required"] == [
        "verdict",
        "p_real",
        "kind",
        "rationale",
    ]
    assert (
        p["messages"][0]["content"]
        == "Verse A: Genesis 1:1\nבראשית\n\nVerse B: Jeremiah 23:24\nהשמים"
    )
    assert "Never translate" in p["system"] and "temperature" not in p


def test_parse():
    ok = lt.parse(_msg(json.dumps({"verdict": "real", "p_real": 1.3, "kind": "allusion",
                                   "rationale": "ככוכבי השמים" * 100})), 40)  # fmt: skip
    assert (ok["status"], ok["verdict"], ok["p_real"], ok["kind"]) == (
        "ok",
        "real",
        1.0,
        "allusion",
    )
    assert len(ok["rationale"]) == 40 and ok["input_tokens"] == 100
    assert lt.parse(_msg("", stop="refusal"), 40)["status"] == "refusal"
    assert lt.parse(_msg("{", stop="max_tokens"), 40)["status"] == "max_tokens"
    assert lt.parse(_msg("not json"), 40)["status"] == "unreadable"
    bad = json.dumps({"verdict": "maybe", "p_real": 0.5, "kind": "none", "rationale": ""})
    assert lt.parse(_msg(bad), 40)["status"] == "unreadable"


def test_calibration_pairs():
    # 20 verses: book 5 (dev) = 0-9, book 6 (dev) = 10-19; 3 and 4 share their text
    verses = pd.DataFrame(
        {"book_id": [5] * 10 + [6] * 10, "text_plain": [f"t{i}" for i in range(20)]}
    )
    verses.loc[4, "text_plain"] = "t3"
    sefaria = pd.DataFrame({"src_vid": [0, 12, 1, 3], "tgt_vid": [15, 0, 2, 4]})  # 1-2 neighbours
    linked = {(0, 15), (0, 12), (1, 2), (3, 4), (5, 16)}
    df = lt.calibration_pairs(verses, sefaria, linked, {5, 6}, 2, 6, 2, 0)
    gold = df[df.gold]
    assert sorted(zip(gold.a, gold.b, strict=True)) == [(0, 12), (0, 15)]
    rand = list(zip(df.a[~df.gold], df.b[~df.gold], strict=True))
    assert len(set(rand)) == 6
    for a, b in rand:
        assert (a, b) not in linked and not (
            verses.book_id[a] == verses.book_id[b] and abs(a - b) <= 2
        )
    assert df.equals(lt.calibration_pairs(verses, sefaria, linked, {5, 6}, 2, 6, 2, 0))
    with pytest.raises(RuntimeError, match="only 2 gold pairs"):
        lt.calibration_pairs(verses, sefaria, linked, {5, 6}, 3, 6, 2, 0)


class FakeBatches:
    def __init__(self, answers, rounds=1):
        self.answers, self.rounds, self.created, self.retrieved = answers, rounds, [], 0

    def create(self, requests):
        self.created.append(requests)
        return NS(id="msgbatch_1")

    def retrieve(self, batch_id):
        self.retrieved += 1
        done = self.retrieved > self.rounds
        return NS(
            processing_status="ended" if done else "in_progress",
            request_counts=NS(processing=0 if done else 1, succeeded=1 if done else 0),
        )

    def results(self, batch_id):
        for cid, ans in self.answers.items():
            if ans is None:
                yield NS(custom_id=cid, result=NS(type="errored"))
            else:
                yield NS(custom_id=cid, result=NS(type="succeeded", message=_msg(json.dumps(ans))))


def _ans(verdict, p):
    return {"verdict": verdict, "p_real": p, "kind": "allusion", "rationale": "הבט נא השמימה"}


@pytest.fixture
def run_cfg(tmp_path, monkeypatch):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "artifacts": str(tmp_path / "artifacts")}
    cfg["llm_triage"] = {
        **cfg["llm_triage"],
        "calibration": {**CFG["calibration"], "min_auc": 0.75},
    }
    pairs = pd.DataFrame(
        {
            "set": ["calibration"] * 4 + ["triage"] * 2,
            "custom_id": ["cal-0", "cal-1", "cal-2", "cal-3", "tri-0", "tri-1"],
            "a": [0, 1, 2, 3, 0, 1],
            "b": [5, 6, 7, 8, 3, 2],
            "gold": [True, True, False, False, None, None],
        }
    )
    monkeypatch.setattr(lt, "build_pairs", lambda cfg, log: pairs)
    monkeypatch.setattr(
        lt, "verse_texts", lambda cfg: {i: {"ref": f"R {i}", "text": "א"} for i in range(10)}
    )
    return cfg


def test_dry_run_sends_nothing(run_cfg):
    out = lt.run_llm_triage(run_cfg, log=lambda s: None, dry_run=True, client=NS())
    assert out["dry_run"] and out["requests"] == 6 and out["max_usd"] >= out["typical_usd"] > 0
    art = resolve_path(run_cfg, "artifacts") / "llm"
    assert len((art / "requests.jsonl").read_text("utf-8").splitlines()) == 6
    assert not (art / "batch.json").exists()


def test_a_batch_submitted_polled_and_collected(run_cfg):
    answers = {
        "cal-0": _ans("real", 0.9), "cal-1": _ans("real", 0.6), "cal-2": _ans("not", 0.2),
        "cal-3": _ans("unsure", 0.7), "tri-0": _ans("not", 0.1), "tri-1": None,
    }  # fmt: skip
    fake = FakeBatches(answers, rounds=2)
    sleeps = []
    meta = lt.run_llm_triage(run_cfg, log=lambda s: None, client=NS(messages=NS(batches=fake)),
                             sleep=sleeps.append)  # fmt: skip
    assert len(fake.created) == 1 and len(fake.created[0]) == 6 and len(sleeps) == 2
    c = meta["calibration"]
    assert (c["gold"], c["random"], c["auc"], c["holds"]) == (2, 2, 0.75, True)
    assert meta["triage"] == {"pairs": 2, "ok": 1, "verdicts": {"real": 0, "not": 1, "unsure": 0}}
    assert meta["status"] == {"ok": 5, "errored": 1} and meta["usage"]["input_tokens"] == 500
    art = resolve_path(run_cfg, "artifacts") / "llm"
    tri = pd.read_parquet(art / "triage.parquet")
    assert tri.a_id.tolist() == ["v:0", "v:1"] and tri.status.tolist() == ["ok", "errored"]
    assert json.loads((art / "batch.json").read_text("utf-8"))["collected"]
    # a new run starts a new batch; a stopped one is resumed, not sent again
    state = json.loads((art / "batch.json").read_text("utf-8"))
    (art / "batch.json").write_text(json.dumps({**state, "collected": False}), "utf-8")
    again = FakeBatches(answers)
    lt.run_llm_triage(
        run_cfg, log=lambda s: None, client=NS(messages=NS(batches=again)), sleep=lambda s: None
    )
    assert again.created == []


# --- the queue's suggestions over the fixture DB ---------------------------------------------


def _write_run(cfg, holds=True):
    out = resolve_path(cfg, "artifacts") / "llm"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {"a_id": ["v:0"], "b_id": ["v:3"], "status": ["ok"], "verdict": ["real"], "p_real": [0.8],
         "kind": ["allusion"], "rationale": ["ויאמר יהוה, twice"]}
    ).to_parquet(out / "triage.parquet")  # fmt: skip
    meta = {"model": "claude-sonnet-5-5", "collected_at": "2026-11-04T12:00:00+00:00",
            "calibration": {"auc": 0.9 if holds else 0.6, "min_auc": 0.75, "holds": holds},
            "triage": {"pairs": 1}}  # fmt: skip
    (out / "llm_triage.meta.json").write_text(json.dumps(meta), "utf-8")


@pytest.fixture
def client(built):
    cfg, db = built
    with sqlite3.connect(
        db
    ) as conn:  # the fixture's one train-book discovery, as in test_label_queue
        conn.execute(
            "UPDATE matches SET lex_rank = 1, sem_rank = NULL WHERE unit_type = 'verse'"
            " AND mode = 'fused' AND src_id = 'v:0' AND tgt_id = 'v:3'"
        )
    return cfg, TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_queue_without_a_run(client):
    cfg, c = client
    for f in (resolve_path(cfg, "artifacts") / "llm").iterdir():  # the fixture's run
        f.unlink()
    body = c.get("/api/labels/queue").json()
    assert body["llm"] is None and body["items"][0]["suggestion"] is None
    assert c.get("/api/labels/queue?suggested=true").json()["total"] == 0


def test_queue_shows_suggestions_when_the_calibration_holds(client):
    cfg, c = client
    _write_run(cfg)
    body = c.get("/api/labels/queue").json()
    assert body["llm"]["holds"] and body["llm"]["auc"] == 0.9
    assert body["llm"]["rationale"] == "english"  # a run from before the choice
    assert body["items"][0]["suggestion"] == {
        "verdict": "real", "p_real": 0.8, "kind": "allusion", "rationale": "ויאמר יהוה, twice",
    }  # fmt: skip
    assert c.get("/api/labels/queue?suggested=true").json()["total"] == 1
    _write_run(cfg, holds=False)
    body = c.get("/api/labels/queue").json()
    assert not body["llm"]["holds"] and body["items"][0]["suggestion"] is None
    # suggestions are never labels
    assert c.get("/api/labels").json()["items"] == []


def test_auc_needs_both_kinds():
    assert lt.auc(np.array([True, True]), np.array([0.1, 0.2])) is None


def test_clean_rationale_removes_glosses():
    c = lt.clean_rationale
    assert c('the phrase מִיֶּדְכֶם ("from your hand"). Thematic.') == "the phrase מִיֶּדְכֶם. Thematic."
    assert (
        c("the pair אֶת־צֹאנ- וְאֶת־בְּקָר- (flock and herd), ordinary")
        == "the pair אֶת־צֹאנ- וְאֶת־בְּקָר-, ordinary"
    )
    assert c("the verb תֶּאֱנַף “be angry” with לָנֶצַח") == "the verb תֶּאֱנַף with לָנֶצַח"
    # a context in parentheses after English is no gloss; a gloss in prose hides the rationale
    assert c("the contexts differ (exile vs. return)") == "the contexts differ (exile vs. return)"
    assert c("in Isaiah בָּנִים means rebellious children") is None
    assert c("") is None
    assert c("ארבה משותף.</rationale>") == "ארבה משותף."


def test_the_rationale_language():
    assert "only in Hebrew" in lt.system_prompt("hebrew") and "{rationale}" not in lt.system_prompt(
        "hebrew"
    )
    assert "in English naming" in lt.system_prompt("english")
    with pytest.raises(RuntimeError, match="llm_triage.rationale"):
        lt.system_prompt("french")
    assert lt.request(
        "x", {"ref": "", "text": ""}, {"ref": "", "text": ""}, {**CFG, "rationale": "hebrew"}
    )["params"]["system"] == lt.system_prompt("hebrew")
