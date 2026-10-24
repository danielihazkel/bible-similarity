"""The narrative frameworks (`bsim frameworks`, `/frameworks`, DESIGN.md §16.71)."""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.chronology import words_of
from bsim.analysis.frameworks import (
    cosine_sets,
    find_slot,
    ordered_rho,
    run_frameworks,
    verdict_of,
    within_between,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.data.canon import BY_SEFARIA
from bsim.fixture import fixture_encoder

VC = {k: str(v) for k, v in load_config()["frameworks"]["verdict"].items()}


def ws(*lemmas):
    return [words_of(lem, "HVqw3ms", None) for lem in lemmas]


def test_find_slot():
    lemmas = {0: {"6213", "7451"}, 1: {"6213", "7451", "5869"}, 2: {"2199"}}
    assert find_slot(range(3), lemmas, [["6213", "7451", "5869"]]) == 1
    assert find_slot(range(3), lemmas, [["6817"], ["2199"]]) == 2
    assert find_slot(range(2), lemmas, [["2199"]]) is None
    assert find_slot(range(3), lemmas, [["6213"]], years=lambda v: v == 1) == 1


def test_ordered_rho():
    rho, p = ordered_rho([1.0, 1.0, 5 / 6, 5 / 6, 4 / 6, 3 / 6])
    assert rho < -0.9 and p < 0.01
    rho, p = ordered_rho([0.5, 1.0, 0.5, 1.0])
    assert p > 0.2
    assert ordered_rho([1.0, 1.0]) == (0.0, 1.0)


def test_wording():
    sim = cosine_sets([{"a", "b"}, {"a", "b"}, {"c"}, {"c", "d"}])
    assert sim[0, 1] == pytest.approx(1.0) and sim[0, 2] == 0
    labels = np.array(["j", "j", "i", "i"])
    assert within_between(sim, labels) == pytest.approx((1 + 1 / np.sqrt(2)) / 2)
    assert within_between(sim, np.array(["j", "i", "j", "i"])) < 0


def test_verdict_of():
    # ויעש הרע בעיני יהוה
    assert verdict_of(ws("c/6213", "d/7451", "b/5869", "3068"), VC) == "bad"
    # ויעש הישר בעיני יהוה ... ולא סר (Josiah): still good
    assert verdict_of(ws("c/6213", "d/3477", "b/5869", "3068", "c/3808", "5493"), VC) == "good"
    # ולא עשה הישר בעיני יהוה (Ahaz)
    assert verdict_of(ws("c/3808", "6213", "d/3477", "b/5869", "3068"), VC) == "bad"
    # no eyes: no verdict
    assert verdict_of(ws("c/6213", "d/7451"), VC) is None


def corpus(tmp_path):
    """Judges 1:1-6 (two episodes) and I Kings 1:1-6 (three kings)."""
    judg, kgs = BY_SEFARIA["Judges"].book_id, BY_SEFARIA["I Kings"].book_id
    words = {
        # Judges: Othniel 1:1-3 with every slot, Samson 1:4-6 with evil, oppression and years
        (judg, 1): ["c/6213", "d/7451", "b/5869", "c/4376", "b/3027", "c/5647", "8083", "8141"],
        (judg, 2): ["c/2199", "c/6965", "3467"],
        (judg, 3): ["c/8252", "d/776", "705", "8141"],
        (judg, 4): ["c/6213", "d/7451", "b/5869", "c/5414", "b/3027", "705", "8141"],
        (judg, 5): ["2088"],
        (judg, 6): ["c/4191"],
        # Kings: Asa (1:1-2) good, with his mother and the high places; Nadab (1:3-4) bad, with
        # the sins of Jeroboam; Zimri (1:5-6) no verdict
        (kgs, 1): ["1121 a", "7970", "8141", "c/8034", "517"],
        (kgs, 2): ["c/6213", "d/3477", "b/5869", "3068", "d/1116", "3808", "5493"],
        (kgs, 3): ["c/6213", "d/7451", "b/5869", "3068", "3379", "b/2403"],
        (kgs, 4): ["c/6912"],
        (kgs, 5): ["2088"],
        (kgs, 6): ["c/4191"],
    }
    keys = list(words)
    proc = tmp_path / "processed"
    proc.mkdir()
    pd.DataFrame({"verse_id": range(len(keys)), "book_id": [b for b, _ in keys], "chapter": 1,
                  "verse": [v for _, v in keys]}).to_parquet(proc / "verses.parquet")  # fmt: skip
    rows = [(i, j, lem, "HC/Vqw3ms" if lem.startswith("c/") else "HNcmsa", j)
            for i, k in enumerate(keys) for j, lem in enumerate(words[k])]  # fmt: skip
    pd.DataFrame(rows, columns=["verse_id", "idx", "lemma", "morph", "display_idx"]).to_parquet(
        proc / "words.parquet"
    )
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc),
                    "artifacts": str(tmp_path / "artifacts")}  # fmt: skip
    cfg["frameworks"] = {
        **cfg["frameworks"],
        "episodes": [["othniel", "עתניאל", "Judges 1:1-3"], ["samson", "שמשון", "Judges 1:4-6"]],
        "known_verdicts": {"asa": "good", "nadab": "bad"},
        "shuffles": 99,
    }  # fmt: skip
    cfg["chronology"] = {
        **cfg["chronology"],
        "kings": [["asa", "אסא", "judah", "I Kings 1:1"], ["nadab", "נדב", "israel", "I Kings 1:3"],
                  ["zimri", "זמרי", "israel", "I Kings 1:5"]],
    }  # fmt: skip
    return cfg


def test_run_frameworks(tmp_path):
    cfg = corpus(tmp_path)
    run_frameworks(cfg, log=lambda _: None)
    out = tmp_path / "artifacts" / "frameworks"
    ep = pd.read_parquet(out / "episodes.parquet")
    assert ep.episode.tolist() == ["othniel", "samson"] and ep.n_slots.tolist() == [6, 3]
    sl = pd.read_parquet(out / "slots.parquet")
    sam = sl[sl.episode == "samson"].set_index("slot").verse_id
    assert sam.isna().tolist() == [False, False, False, True, True, True]
    kings = pd.read_parquet(out / "kings.parquet").set_index("king")
    assert kings.verdict.fillna("-").tolist() == ["good", "bad", "-"]
    assert kings.loc["asa", "mother"] == 6 and kings.loc["asa", "high_places"] == 7
    assert kings.loc["asa", "age"] == 6 and pd.isna(kings.loc["nadab", "age"])
    assert kings.loc["nadab", "jeroboam"] == 8 and kings.loc["nadab", "burial"] == 9
    assert kings.loc["nadab", "last_vid"] == 9 and kings.loc["zimri", "last_vid"] == 11
    meta = json.loads((out / "frameworks.meta.json").read_text("utf-8"))
    assert meta["known_cycle_holds"] and meta["known_verdicts_holds"]
    assert meta["verdicts"] == 2 and meta["good"] == 1 and meta["bad"] == 1
    assert meta["by_kingdom"]["judah"]["mother"] == 1.0
    assert meta["by_kingdom"]["israel"]["verdict_vid"] == 0.5


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_frameworks_endpoint(client):
    r = client.get("/api/frameworks").json()
    assert not r["cycle_holds"] and r["verdict_holds"] and r["known_cycle_holds"]
    oth, sam = r["episodes"]
    assert oth["judge"] == "עתניאל" and oth["ref"] and len(oth["slots"]) == 6
    assert [s["verse_id"] for s in sam["slots"]] == [2, 2, 2, None, None, None]
    assert sam["slots"][0]["ref_he"] and sam["slots"][3]["ref"] is None
    jer, asa, nadab = r["kings"]
    assert jer["verdict"] is None and jer["verdict_verse"] is None
    assert asa["verdict"] == "good" and asa["verdict_verse"]["verse_id"] == 3
    assert [s["slot"] for s in asa["slots"]] == ["age", "mother", "high_places", "jeroboam",
                                                 "burial"]  # fmt: skip
    assert nadab["slots"][3]["verse_id"] == 4


def test_frameworks_findings(client):
    found = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    assert found["frameworks_cycle"]["verdict"] == "fails"
    known = found["frameworks_cycle_known"]["values"]
    assert known == {"othniel_missing": 0, "samson_missing": 3, "slots": 6}
    assert found["frameworks_verdicts"]["values"]["within_judah"] == 0.3
    assert found["frameworks_verdicts_known"]["values"] == {"known": 1, "found": 1}
