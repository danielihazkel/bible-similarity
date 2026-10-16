"""Do equal letter values link related words? (`bsim gematria-links`, `/gematria-links`, §16.59)"""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.gematria_links import (
    holds,
    largest_prime_factor,
    matched_draws,
    prime_factors,
    run_gematria_links,
    triangular,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.fixture import fixture_encoder


def test_numbers():
    assert largest_prime_factor(2701) == 73 and largest_prime_factor(1752) == 73
    assert largest_prime_factor(1) == 1 and largest_prime_factor(97) == 97
    assert prime_factors(2701) == 2 and prime_factors(8) == 3 and prime_factors(1) == 0
    assert triangular(2701) and triangular(1) and not triangular(2700)
    assert holds({"kind": "multiple", "n": 37}, 2701, 7, 28)
    assert holds({"kind": "words", "n": 7}, 0, 7, 0)
    assert not holds({"kind": "letters", "n": 28}, 0, 7, 27)
    with pytest.raises(ValueError, match="unknown kind"):
        holds({"kind": "square"}, 4, 1, 1)


def test_matched_draws():
    rng = np.random.default_rng(0)
    # six lemmas in two cells; pair (0, 1) has value 5
    cell = np.array([1, 1, 1, 2, 2, 2])
    value = np.array([5, 5, 5, 7, 9, 5])
    spelled = np.array([0, 1, 2, 3, 4, 0])
    kept, drawn = matched_draws(np.array([0]), np.array([3]), cell, value, spelled, 200, rng)
    found = drawn >= 0
    assert found.mean() > 0.9
    k, d = kept[found], drawn[found]
    assert (cell[d] == np.where(k == 0, cell[3], cell[0])).all()  # the other side's cell
    assert (value[d] != value[k]).all() and (spelled[d] != spelled[k]).all() and (d != k).all()
    assert set(k) == {0, 3}  # either side kept


def corpus(tmp_path):
    """Eight lemmas valued: three traditional pairs of equal value, two lemmas spelled alike, a
    name (left out) and אהב of the root of אהבה; four verses, the first Gen 1:1's numbers and the
    second its twin (7 words, 28 letters, 1679 = 23 × 73)."""
    proc, art = tmp_path / "processed", tmp_path / "art"
    for d in (proc, art / "gematria", art / "roots"):
        d.mkdir(parents=True)
    lemmas = [("3196", "יַיִן", 70), ("5475", "סוֹד", 70), ("5175", "נָחָשׁ", 358),
              ("4899", "מָשִׁיחַ", 358), ("259", "אֶחָד", 13), ("160", "אַהֲבָה", 13),
              ("157", "אָהַב", 8), ("1004a", "בַּיִת", 412), ("1004b", "בַּיִת", 412),
              ("3068", "יהוה", 26)]  # fmt: skip
    pd.DataFrame(
        [(lem, he, "strong", v, v, 1, 1, 5) for lem, he, v in lemmas],
        columns=["lemma", "he", "source", "standard", "gadol", "ordinal", "katan", "n_words"],
    ).to_parquet(art / "gematria" / "lemmas.parquet")
    roots = {"157": "157", "160": "157", "1004a": "1004", "1004b": "1004", "3068": "1961"}
    pd.DataFrame(
        [(lem, lem, roots.get(lem, lem), "", None) for lem, _, _ in lemmas],
        columns=["lemma", "strong", "root", "root_he", "link"],
    ).to_parquet(art / "roots" / "lemmas.parquet")
    pd.DataFrame({"strong": ["3068"], "pos": ["np"], "name_kind": ["person"]}).to_parquet(
        proc / "lexicon_lemmas.parquet"
    )
    doms = {"3196": "001", "5475": "002", "5175": "003", "4899": "002", "259": "004",
            "160": "005", "157": "005", "1004": "006", "3068": "007"}  # fmt: skip
    pd.DataFrame(
        [(s, [d], [1.0]) for s, d in doms.items()], columns=["strong", "domains", "weights"]
    ).to_parquet(proc / "word_senses.parquet")
    words = {"verse_id": [0], "idx": [0], "surface": ["x"], "content_lemmas": [["157"]]}
    pd.DataFrame(words).to_parquet(proc / "words.parquet")
    pd.DataFrame(
        [(0, 0, 2701, 7, 28), (1, 0, 1679, 7, 28), (2, 0, 100, 3, 10), (3, 0, 999, 5, 20)],
        columns=["verse_id", "book_id", "standard", "n_words", "n_letters"],
    ).to_parquet(art / "gematria" / "verses.parquet")
    pd.DataFrame(
        [(i, 0, 1, i + 1) for i in range(4)], columns=["verse_id", "book_id", "chapter", "verse"]
    ).to_parquet(proc / "verses.parquet")
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art)}
    cfg["gematria_links"] = {
        **cfg["gematria_links"], "min_count": 1, "bands": [1, 10], "draws": 99,
        "equivalences": [["נחש", "משיח"], ["יין", "סוד"], ["שלום", "אין"]],
    }  # fmt: skip
    rng = np.random.default_rng(3)
    vectors = {lem: v / np.linalg.norm(v) for lem, v in
               ((lem, rng.normal(size=8)) for lem, _, _ in lemmas)}  # fmt: skip
    return cfg, vectors


def test_run_gematria_links(tmp_path):
    cfg, vectors = corpus(tmp_path)
    out = run_gematria_links(cfg, log=lambda _: None, vectors=vectors)
    pairs = pd.read_parquet(out / "pairs.parquet")
    got = {(a, b): s for a, b, s in zip(pairs.a, pairs.b, pairs.same_letters, strict=True)}
    assert got == {("160", "259"): False, ("3196", "5475"): False, ("4899", "5175"): False,
                   ("1004a", "1004b"): True}  # the name left out  # fmt: skip
    p = pairs.set_index(["a", "b"])
    assert p.loc[("1004a", "1004b"), "root"] == 1 and p.loc[("1004a", "1004b"), "domains"] == 1
    cos = float(vectors["3196"] @ vectors["5475"])
    assert p.loc[("3196", "5475"), "vector"] == pytest.approx(cos, abs=1e-4)
    meta = json.loads((out / "gematria_links.meta.json").read_text("utf-8"))
    assert (meta["lemmas"], meta["pairs"], meta["same_letters"], meta["tested"]) == (9, 4, 1, 3)
    eq = meta["tests"]["equal"]
    assert set(eq) == {"domains", "root", "vector"} and eq["root"]["observed"] == 0
    tested = p[~p.same_letters]
    assert eq["vector"]["observed"] == pytest.approx(tested.vector.mean(), abs=1e-3)
    assert 0 < eq["vector"]["p"] <= 1 and eq["domains"]["n"] == 3
    # one root family: אהב and אהבה (בית's two lemmas are spelled alike)
    assert meta["root_pairs"] == 1 and set(meta["tests"]["root_family"]) == {"domains", "vector"}
    e = meta["equivalences"]
    assert [(x["found"], x.get("a"), x.get("b"), x.get("equal")) for x in e] == [
        (True, "5175", "4899", True), (True, "3196", "5475", True), (False, None, None, None),
    ]  # fmt: skip
    assert 0 <= e[0]["vector_rank"] <= 1
    v = meta["verse"]
    assert (v["value"], v["words"], v["letters"], v["largest_prime"]) == (2701, 7, 28, 73)
    assert v["all"] == 1 and v["twins"] == [1] and not v["unique_here"] and v["unique_share"] == 0.5
    props = {x["key"]: x["verses"] for x in meta["properties"]}
    assert props == {"words7": 2, "letters28": 2, "multiple37": 2, "two_primes": 2, "triangular": 1}
    first = (out / "pairs.parquet").read_bytes()
    run_gematria_links(cfg, log=lambda _: None, vectors=vectors)
    assert (out / "pairs.parquet").read_bytes() == first


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_api(client):
    r = client.get("/api/gematria-links").json()
    assert r["meta"]["tested"] == 1 and "tests" not in r["meta"]
    assert r["equal"]["vector"]["p"] == 0.03 and set(r["root_family"]) == {"domains", "vector"}
    e = r["equivalences"]
    assert e[0]["a"] == {"lemma": "430", "he": "אלהים", "n_words": 2} and e[1]["a"] is None
    v = r["verse"]
    assert v["verse"]["verse_id"] == 0 and [t["verse_id"] for t in v["twins"]] == [3]
    assert [p["key"] for p in v["properties"]] == ["words7", "triangular"]
    pairs = client.get("/api/gematria-links/pairs").json()
    assert pairs["total"] == 1 and pairs["items"][0]["a"]["he"] == "אלהים"
    assert pairs["items"][0]["root"] is False and pairs["items"][0]["vector"] == 0.71
    both = client.get("/api/gematria-links/pairs", params={"same_letters": True, "sort": "value"})
    assert [p["value"] for p in both.json()["items"]] == [26, 86]
    assert client.get("/api/gematria-links/pairs", params={"value": 26}).json()["total"] == 0
    assert client.get("/api/gematria-links/pairs", params={"sort": "nope"}).status_code == 422


def test_findings(client):
    items = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    # the vector's p 0.03 is above 0.05 / 3: no link
    assert items["gematria_links"]["verdict"] == "fails"
    assert items["gematria_links"]["values"]["vector_p"] == 0.03
    assert items["gematria_measures"]["verdict"] == "holds"
    g = items["gematria_genesis"]
    assert g["verdict"] == "fails" and g["values"]["twins"] == 1
    assert g["values"]["unique_share"] == 0.5
