"""Speaker and family-tree gold (series L6, §16.87):
the helpers, the draws, the claims, and runs with a fake batch client."""

from __future__ import annotations

import pandas as pd

from bsim.config import load_config, resolve_path
from bsim.eval import llm_genealogy as lg
from bsim.eval import llm_speakers as ls
from llm_fakes import fake_client

# --- speakers -------------------------------------------------------------------------------------


def test_consonants_and_lemma_match():
    assert ls.consonants("יְהֹוָ֣ה") == "יהוה" and ls.consonants("מֶ֫לֶךְ") == "מלכ"
    words = pd.DataFrame(
        {"verse_id": [5, 5, 6], "surface": ["וַיֹּ֥אמֶר", "מֹשֶׁ֖ה", "הַמֶּ֫לֶךְ"],
         "content_lemmas": ["559", "4872", "4428"]}
    )  # fmt: skip
    refs = {5: "Exodus 3:13", 6: "Exodus 3:14"}
    assert ls.match_lemma("משה", "Exodus 3:13", words, refs) == "4872"
    assert ls.match_lemma("מלך", "Exodus 3:14", words, refs) == "4428"  # after ה, final form
    assert ls.match_lemma("מלך", "nowhere", words, refs) == "4428"  # any verse of the passage
    assert ls.match_lemma("אהרן", "Exodus 3:13", words, refs) is None
    assert ls.match_lemma("", "", words, refs) is None
    assert (
        ls.lemma_key("430") == "430" and ls.lemma_key(430.0) == "430" and ls.lemma_key(None) is None
    )


def test_draw_by_source():
    q = pd.DataFrame(
        {"quote": range(9), "speaker_source": ["explicit"] * 5 + ["carried"] * 2 + [None] * 2}
    )
    d = ls.draw(q, 3, seed=0)
    assert d.source.value_counts().to_dict() == {"explicit": 3, "carried": 2, "none": 2}
    assert d.equals(ls.draw(q, 3, seed=0))


def test_passage():
    v = pd.DataFrame({"book_id": [0] * 6, "chapter": [1, 1, 2, 2, 2, 2]}, index=range(6))
    assert ls.passage(v, 4, 4, before=5, cap=10) == [2, 3, 4]  # not into the chapter before
    assert ls.passage(v, 3, 5, before=1, cap=2) == [2, 3]  # the end cut first


def test_agreement():
    df = pd.DataFrame(
        {"status": ["ok"] * 5, "source": ["explicit", "explicit", "carried", "none", "none"],
         "speaker": ["430", "430", "4872", None, None],
         "answer_lemma": ["430", "4872", "4872", "430", None], "book_id": [0, 5, 0, 0, 0]}
    )  # fmt: skip
    a = ls.agreement(df, dev_books={5})
    assert a["explicit"] == {"answered": 2, "named": 2, "agree": 1, "share": 0.5,
                             "dev_named": 1, "dev_agree": 0}  # fmt: skip
    assert a["none"]["named"] == 1 and a["none"]["agree"] is None


# --- the family tree ------------------------------------------------------------------------------


def _tree():
    persons = pd.DataFrame(
        {"person_id": [0, 1, 2, 3, 4, 9], "key": ["a", "b", "c", "d", "e", "root"],
         "he": ["אב", "בן", "בת", "אח", "לוי", "" ]}
    )  # fmt: skip
    links = pd.DataFrame(
        {"link_id": [1, 2, 3, 4, 5, 6, 7],
         "parent_id": [0, 0, 1, 1, 4, 9, 0], "child_id": [1, 2, 2, 3, 3, 2, 3],
         "role": ["father", "father", "sibling", "sibling", "unstated", "unstated", "father"],
         "status": ["confirmed", "confirmed", "tipnr", "tipnr", "tipnr", "tipnr", "rejected"]}
    )  # fmt: skip
    mentions = pd.DataFrame({"person_id": [1, 2, 3, 3], "verse_id": [10, 10, 11, 12]})
    proofs = pd.DataFrame({"link_id": [1, 2, 7], "rank": [1, 1, 1], "verse_id": [20, 21, 22]})
    return links, persons, mentions, proofs


def test_candidates():
    links, persons, mentions, _ = _tree()
    c = lg.candidates(links, persons, mentions, cap=4)
    # 1 / 2 share their reviewed father 0: no reading; 1 / 3 do not; 3 -> לוי is a claim, the
    # attachment to the virtual root is not
    assert list(zip(c.kind, c.link_id, strict=True)) == [("sibling", 4), ("attachment", 5)]
    assert c.vids[0] == [10, 11, 12] and "לוי" in c.claim[1] and c.vids[1] == [11, 12]


def test_calibration():
    links, persons, _, proofs = _tree()
    cal = lg.calibration(links, persons, proofs, n_confirmed=1, seed=0, cap=4)
    assert cal.gold.tolist().count(True) == 1 and cal.gold.tolist().count(False) == 1
    assert cal[~cal.gold.astype(bool)].vids.iloc[0] == [22]


def test_genealogy_run(tmp_path, monkeypatch):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "artifacts": str(tmp_path)}
    links, persons, mentions, proofs = _tree()
    (tmp_path / "genealogy").mkdir()
    persons.to_parquet(tmp_path / "genealogy" / "persons.parquet")
    items = pd.DataFrame(
        {"kind": ["calibration", "calibration", "sibling", "attachment"], "link_id": [1, 7, 4, 5],
         "a": [0, 0, 1, 4], "b": [1, 3, 3, 3], "claim": ["c1", "c7", "c4", "c5"],
         "vids": [[20], [22], [10], [11]], "gold": [True, False, None, None],
         "custom_id": ["gen-0", "gen-1", "gen-2", "gen-3"]}
    )  # fmt: skip
    monkeypatch.setattr(
        lg, "build_items", lambda cfg, log: (items, dict.fromkeys(items.custom_id, "p"))
    )
    ans = lambda v, p: {"verdict": v, "p_right": p, "rationale": "כתוב"}  # noqa: E731
    client, _ = fake_client({"gen-0": ans("right", 0.9), "gen-1": ans("wrong", 0.1),
                             "gen-2": ans("wrong", 0.2), "gen-3": ans("right", 0.8)})  # fmt: skip
    meta = lg.run_llm_genealogy(cfg, log=lambda s: None, client=client, sleep=lambda s: None)
    assert meta["calibration"]["auc"] == 1.0 and meta["calibration"]["holds"]
    assert meta["checked"]["sibling"]["wrong"] == 1
    sheet = (tmp_path / "llm_genealogy" / "review.md").read_text("utf-8")
    assert "link 4 (sibling; b / d): c4" in sheet and "holds" in sheet
    assert not (resolve_path(cfg, "curation") / "genealogy" / "llm").exists()
