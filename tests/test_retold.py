"""Retold speech (`bsim retold`, `/retold`, DESIGN.md §16.68)."""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from scipy import sparse

from bsim.analysis.brackets import Tok
from bsim.analysis.retold import (
    NARRATOR,
    Piece,
    Text,
    find_in_piece,
    group_of,
    pieces,
    run_retold,
    seeds_of,
    stratified_p,
    teller_units,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder

RC = {**load_config()["retold"], "seed_min": 1, "min_tokens": 3, "min_score": 2, "margin": 0}
PC = load_config()["phrases"]


def test_teller_units():
    # narration, a narrated quotation (clauses 1-3) that quotes another (clause 2), narration
    clauses = pd.DataFrame({"clause": [0, 1, 2, 3, 4], "verse_id": 0, "words": [[0]] * 5,
                            "quote": [-1, 1, 2, 1, -1]})  # fmt: skip
    quotes = pd.DataFrame({"quote": [1, 2], "narrated": [True, False], "start": [1, 2],
                           "end": [3, 2]})  # fmt: skip
    # the quoted words belong to the one who quotes them
    assert teller_units(clauses, quotes).tolist() == [NARRATOR, 1, 1, 1, NARRATOR]


def test_pieces_cut_runs_evenly():
    unit = np.array([-1] * 5 + [7] * 3 + [-1] * 2)
    book = np.zeros(10, dtype=int)
    verse = np.arange(10)
    ps = pieces(unit, book, verse, 3)
    assert [(p.t0, p.t1, p.unit, p.run) for p in ps] == [
        (0, 2, -1, 0), (2, 5, -1, 0), (5, 8, 7, 1), (8, 10, -1, 2)]  # fmt: skip
    # the narrator's two runs are told apart
    assert ps[0].run != ps[-1].run


def test_group_of():
    assert group_of("speech", "divine", "speech", "802") == "retold"
    assert group_of("speech", "85", "speech", "85") == "repeated"
    assert group_of("speech", "85", "speech", None) == "unclear"
    assert group_of("speech", "divine", "narration", None) == "carried"
    assert group_of("narration", None, "speech", "6547") == "told"
    assert group_of("narration", None, "narration", None) == "narrated"


def test_seeds_of_scores_windows():
    # verses 0-9 before a two-verse piece at 10-11: 3 and 4 share a little each, 8 more alone
    row = sparse.csr_matrix(np.array([[0, 0, 0, 3, 3, 0, 0, 0, 5, 0, 0, 0]], dtype=float))
    p = Piece(0, 10, 7, 0, 0, 10, 11)
    rc = {**RC, "seed_min": 5, "seeds": 2}
    # a window of two verses (3 and 4, centred on 4) outranks 8 alone
    assert seeds_of(p, row, 0, rc) == [4, 8]
    assert seeds_of(p, row, 0, {**rc, "seed_min": 6}) == [4]


def test_find_in_piece_masks_and_skips_its_own_run():
    toks = [Tok(x, x) for x in ["a", "b", "c", "d", "x", "a", "b", "c", "d"]]
    run = np.array([0, 0, 0, 0, 1, 2, 2, 2, 2])
    verse_tok = np.array([0, 4, 5, 9])  # verse 0: tokens 0-3, verse 1: 4, verse 2: 5-8
    text = Text(toks, [1.0] * 9, run, verse_tok)
    p = Piece(5, 9, 3, 2, 0, 2, 2)
    (found,) = find_in_piece(p, [0], 0, text, RC, PC)
    assert found[0] == [0, 1, 2, 3] and found[1] == [5, 6, 7, 8]
    # its own run is never a source
    own = Text(toks, [1.0] * 9, np.array([2] * 9), verse_tok)
    assert find_in_piece(p, [0], 0, own, RC, PC) == []


def test_stratified_p():
    rng = np.random.default_rng(1)
    rate = np.array([0.9, 0.8, 0.9, 0.1, 0.2, 0.1])
    is_a = np.array([True, True, True, False, False, False])
    diff, p = stratified_p(rate, is_a, np.zeros(6, dtype=int), 999, rng)
    assert diff == pytest.approx(0.7333, abs=1e-3) and p < 0.1
    # within strata that hold one label each, nothing can move
    _, p1 = stratified_p(rate, is_a, is_a.astype(int), 99, rng)
    assert p1 == 1.0


def corpus(tmp_path):
    """Ten verses: God speaks at v1, a woman retells it at v5 with one word changed, the narrator
    tells it as done at v8; the rest says other things."""
    letters = str.maketrans("0123456789", "אבגדהוזחטי")
    said = ["601", "602", "603", "604", "605", "606"]
    lemmas = {1: said, 5: [*said[:3], "699", *said[4:]], 8: said}
    rows = []
    for v in range(10):
        for k, x in enumerate(lemmas.get(v, [f"7{v}1", f"7{v}2"])):
            rows.append((v, k, x.translate(letters), x, [x], "HNcmsa", k))
    words = pd.DataFrame(rows, columns=["verse_id", "idx", "surface", "lemma", "content_lemmas",
                                        "morph", "display_idx"])  # fmt: skip
    proc = tmp_path / "processed"
    (tmp_path / "artifacts" / "dialogue").mkdir(parents=True)
    proc.mkdir()
    words.to_parquet(proc / "words.parquet")
    pd.DataFrame({"verse_id": range(10), "book_id": 0, "chapter": 1,
                  "verse": range(1, 11)}).to_parquet(proc / "verses.parquet")  # fmt: skip
    quote = [101 if v == 1 else 105 if v == 5 else -1 for v in range(10)]
    pd.DataFrame({"clause": [100 + v for v in range(10)], "verse_id": range(10),
                  "words": [list(range(len(lemmas.get(v, [0, 0])))) for v in range(10)],
                  "quote": quote}).to_parquet(proc / "syntax_clauses.parquet")  # fmt: skip
    pd.DataFrame({"quote": [101, 105], "narrated": [True, True], "start": [1, 5], "end": [1, 5],
                  "speaker_party": ["divine", "802"]}).to_parquet(
        tmp_path / "artifacts" / "dialogue" / "quotations.parquet")  # fmt: skip
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc),
                    "artifacts": str(tmp_path / "artifacts")}  # fmt: skip
    cfg["retold"] = {**RC, "seed_df": 1.0, "shuffles": 99,
                     "known": [{"source": "Genesis 1:2", "retelling": "Genesis 1:6"},
                               {"source": "Genesis 1:3", "retelling": "Genesis 1:4"}]}  # fmt: skip
    return cfg


def test_run_retold(tmp_path):
    cfg = corpus(tmp_path)
    run_retold(cfg, log=lambda _: None)
    out = tmp_path / "artifacts" / "retold"
    d = pd.read_parquet(out / "pairs.parquet")
    got = d[["group", "src_first", "later_first", "src_teller", "later_teller"]].fillna("-")
    # the narrator has no teller
    assert got.values.tolist() == [
        ["retold", 1, 5, "divine", "802"],
        ["carried", 1, 8, "divine", "-"],
    ]
    assert d.rate.round(4).tolist() == [round(1 / 6, 4), 0.0]
    assert d.substitution.tolist() == [1, 0] and d.known.tolist() == [True, False]
    marks = pd.read_parquet(out / "marks.parquet")
    assert marks.values.tolist() == [[0, "a", 1, 3, "substitution"], [0, "b", 5, 3, "substitution"]]
    meta = json.loads((out / "retold.meta.json").read_text("utf-8"))
    assert meta["groups"]["retold"] == 1 and meta["groups"]["carried"] == 1
    assert [k["found"] for k in meta["known"]] == [True, False] and not meta["known_holds"]


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_retold_endpoints(client):
    r = client.get("/api/retold").json()
    assert r["claim"] == ["retold", "carried"] and not r["holds"] and r["groups"]["retold"] == 1
    page = client.get("/api/retold/items").json()
    assert page["total"] == 2
    first = page["items"][0]
    assert first["group"] == "retold" and first["known"] and first["unit_id"] == "c:0:1"
    assert first["source"]["teller"]["key"] == "divine" and first["source"]["kind"] == "speech"
    assert [v["verse_id"] for v in first["source"]["verses"]] == [0]
    assert first["source"]["marks"] == [{"0": "omitted"}] and first["retelling"]["marks"] == [{}]
    carried = page["items"][1]
    assert carried["retelling"]["kind"] == "narration" and carried["retelling"]["teller"] is None
    assert carried["retelling"]["marks"] == [{"0": "form", "1": "added"}]
    assert carried["ops"] == {"same": 1, "form": 1, "added": 1}
    assert client.get("/api/retold/items?group=carried").json()["total"] == 1
    assert client.get("/api/retold/items?known=true").json()["total"] == 1
    assert [i["pair"] for i in client.get("/api/retold/items?order=most").json()["items"]] == [0, 1]
    assert client.get("/api/retold/items?group=nope").status_code == 422


def test_retold_findings(client):
    found = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    assert found["retold_claim"]["verdict"] == "fails"
    assert found["retold_claim"]["values"]["a_n"] == 1
    assert found["retold_known"]["verdict"] == "fails"
    assert found["retold_known"]["values"] == {"known_found": 1, "known": 2}
