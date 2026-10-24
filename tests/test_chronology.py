"""The text's own chronology (`bsim chronology`, `/chronology`, DESIGN.md §16.70)."""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.chronology import (
    agreeing,
    best_rules,
    date_of,
    phrases,
    reign_of,
    run_chronology,
    starts,
    sync_times,
    words_of,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder

NUMBERS = {str(k): int(v) for k, v in load_config()["chronology"]["numbers"].items()}


def ws(*pairs):
    return [words_of(lemma, morph, i) for i, (lemma, morph) in enumerate(pairs)]


def read(*pairs):
    return [(p.value, p.kind, p.unit) for p in phrases(ws(*pairs), NUMBERS)]


YEAR, YEARS_C = ("8141", "HNcfsa"), ("b/8141", "HR/Ncfsc")


def test_genesis_style_numbers():
    # תשע מאות שנה ושלשים שנה (Gen 5:5): a hundred multiplies the unit, שנה carries on to ו
    assert read(("8672", "HAcfsa"), ("3967", "HAcbpa"), YEAR, ("c/7970", "HC/Acbpa"), YEAR) == [
        (930, "span", "year")
    ]
    # שלשים ומאת שנה (Gen 5:3), the smaller first
    assert read(("7970", "HAcbpa"), ("c/3967", "HC/Acbsc"), YEAR) == [(130, "span", "year")]
    # בשמונים שנה וארבע מאות שנה (1 Kgs 6:1): the hundred multiplies only its own unit
    assert read(("b/8084", "HR/Acbpa"), YEAR, ("c/702", "HC/Acfsa"), ("3967", "HAcbpa"), YEAR) == [
        (480, "span", "year")
    ]
    # חמש שנים ומאתים שנה (Gen 11:32): the dual hundred is two hundred
    assert read(("2568", "HAcfsa"), ("8141", "HNcfpa"), ("c/3967", "HC/Acbda"), YEAR) == [
        (205, "span", "year")
    ]
    # ששה וארבעים אלף וחמש מאות: a thousand multiplies everything before it
    assert read(("8337", "HAcmsa"), ("c/705", "HC/Acbpa"), ("505", "HAcbsa"),
                ("c/2568", "HC/Acfsa"), ("3967", "HAcbpa")) == [(46500, "span", None)]  # fmt: skip


def test_ages_dates_and_units():
    # בן שתים עשרה שנה (the homonym letter of בן dropped): an age; the teens add
    assert read(("1121 a", "HNcmsc"), ("8147", "HAcfdc"), ("6240", "HAcfsa"), YEAR) == [
        (12, "age", "year")
    ]
    # בשנת שלשים ותשע שנה: a date
    assert read(YEARS_C, ("7970", "HAcbpa"), ("c/8672", "HC/Acfsa"), YEAR) == [(39, "date", "year")]
    # שנתים is two years; שני חיי (construct) is not
    assert read(("8141", "HNcfda")) == [(2, "span", "year")]
    assert read(("8141", "HNcfdc"), ("2416", "HNcmpc")) == []
    # ששה חדשים; ושנה אחת (the unit before)
    assert read(("8337", "HAcmsa"), ("2320", "HNcmpa")) == [(6, "span", "month")]
    assert read(("c/8141", "HC/Ncfsa"), ("259", "HAcfsa")) == [(1, "span", "year")]
    # a name is not a number
    assert read(("7969", "HNp")) == []


def test_reign_and_date():
    # בשנת שמנה עשרה ... בן עשרים שנה ... ושבע עשרה שנה מלך
    w = ws(YEARS_C, ("8083", "HAcfsa"), ("6240", "HAcfsa"), ("4427 a", "HVqp3ms"),
           ("1121 a", "HNcmsc"), ("6242", "HAcbpa"), YEAR, ("b/4427 a", "HR/Vqc"),
           ("c/7651", "HC/Acfsa"), ("6240", "HAcfsa"), YEAR)  # fmt: skip
    ph = phrases(w, NUMBERS)
    assert date_of(ph) == 18 and reign_of(w, ph) == (17, False)
    # שבעת ימים; ירח ימים: under a year
    w = ws(("7651", "HAcmsc"), ("3117", "HNcmpa"))
    assert reign_of(w, phrases(w, NUMBERS)) == (0, True)
    w = ws(("3391", "HNcmsc"), ("3117", "HNcmpa"))
    assert reign_of(w, phrases(w, NUMBERS)) == (0, True) and date_of([]) is None


def test_starts():
    reign, short = np.array([17, 3, 0, 41]), np.array([False, False, True, False])
    first, acc = starts(reign, short, "accession")
    assert first.tolist() == [1, 18, 21, 21] and acc.tolist() == [0, 17, 20, 20]
    first, acc = starts(reign, short, "non-accession")
    assert first.tolist() == [0, 16, 18, 18] and acc.tolist() == first.tolist()


def test_synchronisms():
    reigns = {"judah": (np.array([17, 3, 41]), np.zeros(3, bool)),
              "israel": (np.array([22, 2]), np.zeros(2, bool))}  # fmt: skip
    # Abijam in Jeroboam's 18th; Asa in Jeroboam's 20th; Nadab in Asa's 2nd (1 Kgs 15)
    syncs = [("judah", 1, "israel", 0, 18), ("judah", 2, "israel", 0, 20),
             ("israel", 1, "judah", 2, 2)]  # fmt: skip
    tj, ti = sync_times(reigns, {"judah": "accession", "israel": "non-accession"}, syncs)
    assert tj.tolist() == [17, 20, 22] and ti.tolist() == [17, 19, 21]
    assert agreeing(tj, ti, 1).tolist() == [True, True] and agreeing(tj, ti, 0).tolist() == [
        False, True
    ]  # fmt: skip
    rules, counts = best_rules(reigns, syncs, 0)
    assert counts["accession/non-accession"] == 1 and len(counts) == 4
    assert rules == {"judah": "accession", "israel": "accession"} or counts[
        f"{rules['judah']}/{rules['israel']}"
    ] == max(counts.values())


def corpus(tmp_path):
    """Genesis 1:1-8: Seth's 130, the Flood twice (600 after Seth, 700 after Adam), three kings of
    Judah and two of Israel, two synchronisms."""
    words = [
        [("c/2421", "HC/Vqw3ms"), ("121", "HNp"), ("7970", "HAcbpa"), ("c/3967", "HC/Acbsc"), YEAR],
        [("1121 a", "HNcmsc"), ("8337", "HAcfsa"), ("3967", "HAcbpa"), YEAR],
        [("7651", "HAcfsa"), ("3967", "HAcbpa"), YEAR],
        [("1121 a", "HNcmsc"), ("6242", "HAcbpa"), YEAR, ("b/4427 a", "HR/Vqc"),
         ("c/7651", "HC/Acfsa"), ("6240", "HAcfsa"), YEAR],
        [("6242", "HAcbpa"), ("c/8147", "HC/Acfpa"), YEAR],
        [YEARS_C, ("8083", "HAcfsa"), ("6240", "HAcfsa"), ("l/3379", "HR/Np"), ("7969", "HAcfsa"),
         ("8141", "HNcfpa")],
        [YEARS_C, ("702", "HAcfsa"), ("l/609", "HR/Np"), ("8141", "HNcfda")],
        [("3391", "HNcmsc"), ("3117", "HNcmpa")],
    ]  # fmt: skip
    proc = tmp_path / "processed"
    proc.mkdir()
    pd.DataFrame({"verse_id": range(8), "book_id": 0, "chapter": 1,
                  "verse": range(1, 9)}).to_parquet(proc / "verses.parquet")  # fmt: skip
    rows = [(v, i, lem, mo, i) for v, w in enumerate(words) for i, (lem, mo) in enumerate(w)]
    pd.DataFrame(rows, columns=["verse_id", "idx", "lemma", "morph", "display_idx"]).to_parquet(
        proc / "words.parquet"
    )
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc),
                    "artifacts": str(tmp_path / "artifacts")}  # fmt: skip
    cfg["chronology"] = {
        **cfg["chronology"],
        "names": {"adam": "אדם", "seth": "שת"},
        "events": [["adam", None, None], ["seth", "adam", "Genesis 1:1", 1],
                   ["flood", "seth", "Genesis 1:2", 1], ["flood", "adam", "Genesis 1:3", 1]],
        "known": {"flood": 730},
        "tradition": {},
        "division": "seth",
        "kings": [["a", "א", "judah", "Genesis 1:4"], ["b", "ב", "judah", "Genesis 1:6"],
                  ["c", "ג", "judah", "Genesis 1:8"], ["x", "ך", "israel", "Genesis 1:5"],
                  ["y", "ם", "israel", "Genesis 1:7"]],
        "syncs": [["y", "b", "Genesis 1:7"], ["b", "x", "Genesis 1:6"]],
        "digits": {**cfg["chronology"]["digits"], "chapter": "Genesis 1:1-2",
                   "compare": "Genesis 1:3-4"},
        "shuffles": 99,
    }  # fmt: skip
    return cfg


def test_run_chronology(tmp_path):
    cfg = corpus(tmp_path)
    run_chronology(cfg, log=lambda _: None)
    out = tmp_path / "artifacts" / "chronology"
    ev = pd.read_parquet(out / "events.parquet")
    assert ev.year.tolist() == [0, 130, 730, 700]
    assert ev.used.tolist() == [True, True, True, False]
    assert ev.conflict.tolist() == [False, False, False, True]
    assert ev.value.tolist()[1:] == [130, 600, 700] and ev.name.tolist()[:2] == ["אדם", "שת"]
    kings = pd.read_parquet(out / "kings.parquet")
    assert kings.reign.tolist() == [17, 3, 0, 22, 2]
    assert kings.short.tolist() == [False, False, True, False, False]
    syncs = pd.read_parquet(out / "syncs.parquet")
    # in the text's order: Abijam-like b (Gen 1:6) before y (Gen 1:7)
    assert syncs.king.tolist() == ["b", "y"] and syncs.year.tolist() == [18, 4]
    assert syncs.agrees.isna().tolist() == [True, False] and bool(syncs.agrees.iloc[1])
    meta = json.loads((out / "chronology.meta.json").read_text("utf-8"))
    assert meta["known_holds"] and meta["conflicts"] == 1 and meta["agree"] == 1
    assert meta["intervals"] == 1 and meta["division"] == 130
    # 130 and 600 in Gen 1:1-2; 700, 20, 17 and 22 elsewhere (the date 18 left out)
    assert meta["digits"]["n"] == 2 and meta["digits"]["rest_n"] == 4
    assert pd.read_parquet(out / "numbers.parquet").value.tolist() == [130, 600]


def test_run_chronology_needs_a_reign(tmp_path):
    cfg = corpus(tmp_path)
    cfg["chronology"]["kings"][0][3] = "Genesis 1:3-1:3"  # 700 years: a span, so read
    cfg["chronology"]["kings"][1][3] = "Genesis 1:1"  # 130: read too
    cfg["chronology"]["kings"].append(["z", "ז", "judah", "Genesis 1:2"])  # only an age
    with pytest.raises(RuntimeError, match="no reign length for z"):
        run_chronology(cfg, log=lambda _: None)


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_chronology_endpoint(client):
    r = client.get("/api/chronology").json()
    assert r["known_holds"] and r["holds"] and r["conflicts"] == 1
    assert [e["year"] for e in r["events"]] == [0, 130, 1042, 1656, 1600]
    assert r["events"][0]["verse"] is None and r["events"][1]["verse"]["verse_id"] == 0
    assert [e["conflict"] for e in r["events"]] == [False, False, False, False, True]
    assert r["lives"] == [{"person": "adam", "name": "אדם", "born": 0, "died": None},
                          {"person": "seth", "name": "שת", "born": 130, "died": 1042}]  # fmt: skip
    assert [k["king"] for k in r["kings"]] == ["rehoboam", "abijam", "jeroboam", "nadab"]
    assert r["kings"][3]["short"] and r["kings"][0]["verse"]["verse_id"] == 3
    assert [s["agrees"] for s in r["syncs"]] == [None, True]
    assert r["digits"]["by_digit"]["0"] == 1 and r["numbers"][0]["value"] == 130
    assert r["rules"] == {"judah": "accession", "israel": "non-accession"}


def test_chronology_findings(client):
    found = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    assert found["chronology_known"]["verdict"] == "holds"
    assert found["chronology_known"]["values"] == {"flood": 1656, "flood_expected": 1656,
                                                   "conflicts": 1}  # fmt: skip
    assert found["chronology_syncs"]["values"]["israel_accession"] == 0.0
    assert found["chronology_digits"]["values"]["hits"] == 2
