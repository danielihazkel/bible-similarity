import math

import numpy as np
import pandas as pd
import pytest

from bsim.config import load_config, resolve_path
from bsim.lexical import bm25
from bsim.lexical.build import EXPECTED_FORMULA, EXPECTED_PARALLEL, prepare
from bsim.lexical.formulas import closed, formula_weights, formulas_frame, frequent_ngrams
from bsim.lexical.tfidf import unit_tfidf
from bsim.lexical.tokens import Stream, lemma_streams, surface_streams, with_bigrams


def _words() -> pd.DataFrame:
    rows = [
        (0, 0, "וַ/יְדַבֵּר", ["1696"]),
        (0, 1, "יְהוָה", ["3068"]),
        (0, 2, "בְּ/אֶרֶץ", ["776"]),
        (1, 1, "עַמֵּךְ", ["5971a", "9999"]),  # out of order on purpose; two content lemmas
        (1, 0, "אֶל", ["413"]),
        (1, 2, "וְ/", []),
    ]
    return pd.DataFrame(rows, columns=["verse_id", "idx", "surface", "content_lemmas"])


def _streams(*verses: str) -> list[Stream]:
    out = []
    for v in verses:
        toks = v.split()
        out.append(Stream(toks, list(range(len(toks)))))
    return out


def test_lemma_streams_flatten_in_word_order():
    s = lemma_streams(_words(), 3)
    assert s[0].tokens == ["1696", "3068", "776"]
    assert s[1].tokens == ["413", "5971a", "9999"]
    assert s[1].word_idx == [0, 1, 1]
    assert s[2].tokens == []


def test_surface_streams_fold_finals_and_keep_prefixes():
    s = surface_streams(_words(), 2)
    assert s[0].tokens == ["וידבר", "יהוה", "בארצ"]
    assert s[1].tokens == ["אל", "עמכ", "ו"]


def test_with_bigrams_min_weight():
    toks, w = with_bigrams(["a", "b", "c"], np.array([1.0, 0.2, 1.0]))
    assert toks == ["a", "b", "c", "a_b", "b_c"]
    assert w.tolist() == [1.0, 0.2, 1.0, 0.2, 0.2]
    assert with_bigrams(["a"], np.array([1.0]))[0] == ["a"]


def test_frequent_ngrams_strict_threshold_and_distinct_verses():
    streams = _streams("x a b c y", "a b c", "a b c a b c", "z a b")
    ngrams = frequent_ngrams(streams, 3, 4, min_verses=2)
    assert ngrams == {("a", "b", "c"): 3}  # repeat inside verse 2 counts once
    assert frequent_ngrams(streams, 3, 4, min_verses=3) == {}


def test_closed_drops_absorbed_subgrams():
    ngrams = {("a", "b", "c"): 5, ("a", "b", "c", "d"): 5, ("b", "c", "d"): 7}
    assert closed(ngrams) == {("a", "b", "c", "d"): 5, ("b", "c", "d"): 7}


def test_formula_weights():
    streams = _streams("x a b c y", "a b")
    w = formula_weights(streams, {("a", "b", "c"): 3}, alpha=0.2)
    assert w[0].tolist() == [1.0, 0.2, 0.2, 0.2, 1.0]
    assert w[1].tolist() == [1.0, 1.0]


def test_formulas_frame_hebrew_form():
    streams = _streams("a b c", "a b c x")
    surfaces = [["וידבר", "יהוה", "אל"], ["וידבר", "יהוה", "אל", "משה"]]
    df = formulas_frame({("a", "b", "c"): 2}, streams, surfaces, ["G 1:1", "G 1:2"])
    row = df.iloc[0]
    assert (row.formula, row.n, row.n_verses, row.he, row.example_ref) == (
        "a b c",
        3,
        2,
        "וידבר יהוה אל",
        "G 1:1",
    )


def test_bm25_hand_computed():
    docs = [["a", "b"], ["a"], ["c", "c"]]
    weights = [np.ones(len(d)) for d in docs]
    k1, b = 1.2, 0.75
    index = bm25.build_bm25(docs, weights, k1, b)
    assert index.vocab == ["a", "b", "c"]

    avgdl = 5 / 3
    idf_a = math.log1p((3 - 2 + 0.5) / (2 + 0.5))
    idf_c = math.log1p((3 - 1 + 0.5) / (1 + 0.5))

    def w(idf, tf, dl):
        return idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl))

    assert index.doc[0, 0] == pytest.approx(w(idf_a, 1, 2))
    assert index.doc[1, 0] == pytest.approx(w(idf_a, 1, 1))
    assert index.doc[2, 2] == pytest.approx(w(idf_c, 2, 2))
    s = bm25.scores(index, np.array([1]))
    assert s[0].tolist() == pytest.approx([w(idf_a, 1, 2), w(idf_a, 1, 1), 0.0])


def test_bm25_query_uses_max_weight():
    index = bm25.build_bm25([["a", "a", "b"]], [np.array([0.2, 1.0, 0.2])], 1.2, 0.75)
    assert index.query.toarray()[0].tolist() == pytest.approx([1.0, 0.2])


def test_topk_cpu_excludes_self(tmp_path):
    docs = [["a", "b"], ["a", "b"], ["a"], ["c"]]
    index = bm25.build_bm25(docs, [np.ones(len(d)) for d in docs], 1.2, 0.75)
    idx, sc = bm25.topk_cpu(index, np.array([0, 1]), k=2)
    assert idx.tolist() == [[1, 2], [0, 2]]
    assert (np.diff(sc, axis=1) <= 0).all()

    bm25.save(index, tmp_path, "toy")
    loaded = bm25.load(tmp_path, "toy")
    assert loaded.vocab == index.vocab
    assert (loaded.doc != index.doc).nnz == 0


def test_unit_tfidf_cosine():
    docs = [["a", "b"], ["a", "b"], ["c"], ["a"], ["b"]]
    weights = [np.ones(len(d)) for d in docs]
    members = pd.DataFrame({"unit_id": ["u0", "u1", "u2", "u3", "u3"], "verse_id": [0, 1, 2, 3, 4]})
    x = unit_tfidf(docs, weights, members, ["u0", "u1", "u2", "u3"])
    assert np.linalg.norm(x.toarray(), axis=1) == pytest.approx(np.ones(4))
    cos = (x @ x.T).toarray()
    assert cos[0, 1] == pytest.approx(1.0)
    assert cos[0, 3] == pytest.approx(1.0)  # same bag spread over two verses
    assert cos[0, 2] == pytest.approx(0.0)


def test_unit_tfidf_downweight_stays_positive():
    docs = [["a", "a", "b"], ["b"]]
    weights = [np.array([0.2, 0.2, 1.0]), np.ones(1)]
    members = pd.DataFrame({"unit_id": ["u0", "u1"], "verse_id": [0, 1]})
    x = unit_tfidf(docs, weights, members, ["u0", "u1"])
    assert (x.data > 0).all()


def test_real_corpus_acceptance():
    """M4 acceptance on the real corpus, if `bsim build-corpus` has been run."""
    cfg = load_config()
    proc = resolve_path(cfg, "data_processed")
    if not (proc / "words.parquet").exists():
        pytest.skip("words.parquet not built")
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "ref"])
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "idx", "surface", "content_lemmas"]
    )
    streams = lemma_streams(words, len(verses))
    tokens, weights, ngrams = prepare(streams, cfg["lexical"])
    assert tuple(EXPECTED_FORMULA.split()) in closed(ngrams)

    refs = verses.sort_values("verse_id").ref.tolist()
    lex = cfg["lexical"]["bm25"]
    index = bm25.build_bm25(tokens, weights, lex["k1"], lex["b"])
    src, tgt = EXPECTED_PARALLEL
    idx, _ = bm25.topk_cpu(index, np.array([refs.index(src)]), k=5)
    assert tgt in [refs[i] for i in idx[0]]
