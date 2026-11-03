"""The vocabulary over the canon (`bsim vocabulary`, `/vocabulary`, DESIGN.md §16.76)."""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.vocabulary import counted_word, excess, heaps, run_vocabulary, walk
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.data.canon import BY_OSIS
from bsim.fixture import fixture_encoder


def test_counted_word():
    assert counted_word("HNcmpa") and counted_word("HR/Ncfsa") and counted_word("HVqp3ms")
    assert not counted_word("HNp") and not counted_word("HC/Np")  # proper names
    assert not counted_word("ANcmsa")  # Aramaic
    assert not counted_word(None)


def test_heaps_fits_a_power_law():
    n = np.array([100.0, 400.0, 900.0, 1600.0])
    k, b = heaps(n, 2 * n**0.5)
    assert k == pytest.approx(2.0) and b == pytest.approx(0.5)


def test_walk_and_excess():
    sets = {0: np.array([0, 1, 2]), 1: np.array([1, 3]), 2: np.array([0, 1])}
    sizes = {0: 10, 1: 5, 2: 5}
    new, ends_n, ends_v = walk([0, 1, 2], sets, sizes, 4)
    assert new == {0: 3, 1: 1, 2: 0}
    assert ends_n.tolist() == [10, 15, 20] and ends_v.tolist() == [3, 4, 4]
    ex = excess([0, 1, 2], new, sizes, ends_n, ends_v)
    assert ex[2][1] < 0 < ex[0][1] + 1  # the last book brings in nothing


def corpus(tmp_path):
    """Genesis (early) with five common words, 1 Chronicles (late) with two new ones, a name and
    an Aramaic word; Psalms in between."""
    gen, ps, chr_ = BY_OSIS["Gen"].book_id, BY_OSIS["Ps"].book_id, BY_OSIS["1Chr"].book_id
    verses = [
        (
            gen,
            [("1", "HNcmsa"), ("2", "HNcmsa"), ("3", "HVqp3ms"), ("4", "HNcmsa"), ("5", "HNcmsa")],
        ),
        (gen, [("1", "HNcmsa"), ("2", "HNcmsa")]),
        (ps, [("1", "HNcmsa"), ("6", "HNcmsa"), ("6", "HNcmsa")]),
        (chr_, [("1", "HNcmsa"), ("7", "HNcmsa"), ("8", "HNcmsa"), ("9", "HNp"), ("10", "ANcmsa")]),
    ]
    proc = tmp_path / "processed"
    proc.mkdir()
    pd.DataFrame({"verse_id": range(len(verses)), "book_id": [b for b, _ in verses]}).to_parquet(
        proc / "verses.parquet"
    )
    rows = [
        (v, i, mo, [lem], i) for v, (_, ws) in enumerate(verses) for i, (lem, mo) in enumerate(ws)
    ]
    pd.DataFrame(
        rows, columns=["verse_id", "idx", "morph", "content_lemmas", "display_idx"]
    ).to_parquet(proc / "words.parquet")
    cfg = load_config()
    cfg["paths"] = {
        **cfg["paths"],
        "data_processed": str(proc),
        "artifacts": str(tmp_path / "artifacts"),
    }
    cfg["vocabulary"] = {**cfg["vocabulary"], "orders": 19, "known": [["Ps", 1]]}
    return cfg


def test_run_vocabulary(tmp_path):
    cfg = corpus(tmp_path)
    run_vocabulary(cfg, log=lambda _: None)
    out = tmp_path / "artifacts" / "vocabulary"
    books = pd.read_parquet(out / "books.parquet").set_index("book_id")
    gen, ps, chr_ = BY_OSIS["Gen"].book_id, BY_OSIS["Ps"].book_id, BY_OSIS["1Chr"].book_id
    # the name and the Aramaic word are not counted
    assert books.loc[chr_, "words"] == 3 and books.loc[chr_, "new"] == 2
    assert books.loc[gen, "new"] == 5 and books.loc[ps, "new"] == 1
    assert (books.loc[gen, "period"], books.loc[chr_, "period"]) == ("early", "late")
    assert pd.isna(books.loc[ps, "period"])
    # hapax: 3, 4, 5 (Genesis), 7, 8 (Chronicles); 6 twice in Psalms is not one
    assert books.loc[gen, "hapax"] == 3 and books.loc[ps, "hapax"] == 0
    lem = pd.read_parquet(out / "lemmas.parquet").set_index("lemma")
    assert lem.loc["1", "first_verse"] == 0 and lem.loc["1", "n_books"] == 3
    assert lem.loc["6", "first_verse"] == 2 and lem.loc["6", "section"] == "Writings"
    assert pd.isna(lem.loc["1", "section"])  # found in Torah and Writings
    assert not lem.loc["9", "counted"] and not lem.loc["10", "counted"]
    assert lem.loc["3", "hapax"] and not lem.loc["6", "hapax"]
    meta = json.loads((out / "vocabulary.meta.json").read_text("utf-8"))
    assert meta["words"] == 13 and meta["lemmas"] == 8 and meta["hapax"] == 5
    assert meta["splits"] == 2  # one early book, one late: two ways to split them
    assert meta["known"][0]["rank"] == 3 and not meta["known_holds"]


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_vocabulary_endpoint(client):
    r = client.get("/api/vocabulary").json()
    assert not r["late_holds"] and r["heaps_b"] == 0.56
    assert [b["book_id"] for b in r["books"]] == [0, 1]
    assert r["books"][1]["period"] == "late" and r["known"][0]["book"] == "Gen"


def test_concordance_first(client):
    first = client.get("/api/lemma/430").json()["first"]
    assert first["first_verse"]["verse_id"] == 0 and first["first_tok"] == 1
    assert first["n_books"] == 2 and first["section"] is None and not first["hapax"]
    hapax = client.get("/api/lemma/7225").json()["first"]
    assert hapax["hapax"] and hapax["section"] == "Torah"


def test_vocabulary_findings(client):
    found = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    assert found["vocabulary_late"]["verdict"] == "fails"
    assert found["vocabulary_late"]["values"]["difference"] == 0.7
    assert found["vocabulary_known"]["values"]["rank_0"] == 2
