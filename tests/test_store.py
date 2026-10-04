import json
import sqlite3

import numpy as np
import pandas as pd
import pytest

from bsim.config import load_config
from bsim.store.db import (
    connect_readonly,
    formula_flags,
    lemma_display_forms,
    run_build_db,
    similar,
    strip_prefixes,
)

# Six verses: book 0 chapter 1 = v0-v2, book 0 chapter 2 = v3-v4, book 1 chapter 1 = v5.
BOOK = [0, 0, 0, 0, 0, 1]
CHAPTER = [1, 1, 1, 2, 2, 1]
CHAPTERS = [("c:0:1", 0, 0, 2), ("c:0:2", 0, 3, 4), ("c:1:1", 1, 5, 5)]


def _cfg(tmp_path):
    cfg = load_config()
    proc, art = tmp_path / "processed", tmp_path / "artifacts"
    cfg["paths"] = {
        **cfg["paths"],
        "data_processed": str(proc),
        "artifacts": str(art),
        "db": str(art / "results.sqlite"),
    }
    cfg["units"] = {**cfg["units"], "types": ["verse", "chapter"]}
    cfg["final_systems"] = {
        **cfg["final_systems"],
        "lexical": "lx",
        "semantic": "sm",
        "unit_lexical": "tfidf",
        "unit_aggregation": "bma",
    }
    cfg["lexical"] = {**cfg["lexical"], "formulas": {**cfg["lexical"]["formulas"], "min_verses": 1}}
    cfg["store"] = {**cfg["store"], "bench_queries": 2}
    return cfg


def _write_topk(art, unit_type, name, rows, fused=False):
    d = art / "topk" / unit_type
    d.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        {
            "unit_type": unit_type,
            "src_id": [r[0] for r in rows],
            "rank": np.array([r[2] for r in rows], dtype=np.int32),
            "tgt_id": [r[1] for r in rows],
            "score": np.float32(0.5),
        }
    )
    if fused:
        df["lex_score"] = np.float32(1.0)
        df["lex_rank"] = pd.array([1] + [None] * (len(df) - 1), dtype="Int32")
        df["sem_score"] = np.float32(np.nan)
        df["sem_rank"] = pd.array([None] * len(df), dtype="Int32")
    df.to_parquet(d / f"{name}.parquet")
    (d / f"{name}.meta.json").write_text(json.dumps({"config_hash": "abc"}), encoding="utf-8")


@pytest.fixture
def built(tmp_path):
    cfg = _cfg(tmp_path)
    proc, art = tmp_path / "processed", tmp_path / "artifacts"
    proc.mkdir()
    n = len(BOOK)
    pd.DataFrame(
        {
            "verse_id": range(n),
            "book_id": BOOK,
            "chapter": CHAPTER,
            "verse": [1, 2, 3, 1, 2, 1],
            "ref": [f"B{b} {c}:{i}" for i, (b, c) in enumerate(zip(BOOK, CHAPTER, strict=True))],
            "osis": [f"B.{i}" for i in range(n)],
            "text_display": "בְּרֵאשִׁית",
            "text_plain": "בראשית",
            "ketiv_note": [None] * (n - 1) + ["כתיב"],
            "display_tokens": [["בְּרֵאשִׁית"]] * n,
        }
    ).to_parquet(proc / "verses.parquet")
    # The trigram 430 559 3068 repeats in v0 and v1: a formula with min_verses = 1.
    words = [
        (0, 0, "בְּרֵאשִׁית", "b/7225", ["7225"]),
        (0, 1, "אֱלֹהִים", "430", ["430"]),
        (0, 2, "וַיֹּאמֶר", "c/559", ["559"]),
        (0, 3, "יְהוָה", "3068", ["3068"]),
        (1, 0, "אֱלֹהִים", "430", ["430"]),
        (1, 1, "וַיֹּאמֶר", "c/559", ["559"]),
        (1, 2, "יְהוָה", "3068", ["3068"]),
    ] + [(v, 0, "רֵאשִׁית", "7225", ["7225"]) for v in range(2, n)]
    pd.DataFrame(
        {
            "verse_id": [w[0] for w in words],
            "idx": [w[1] for w in words],
            "oshb_id": "x",
            "surface": [w[2] for w in words],
            "lemma": [w[3] for w in words],
            "content_lemmas": [w[4] for w in words],
            "morph": "H",
            "kq": None,
            "display_idx": pd.array([0] + [None] * (len(words) - 1), dtype="Int32"),
        }
    ).to_parquet(proc / "words.parquet")
    units = [(f"v:{i}", "verse", BOOK[i], i, i, None) for i in range(n)] + [
        (u, "chapter", b, s, e, None) for u, b, s, e in CHAPTERS
    ]
    pd.DataFrame(
        {
            "unit_id": [u[0] for u in units],
            "unit_type": [u[1] for u in units],
            "label_en": [u[0] for u in units],
            "label_he": [u[0] for u in units],
            "book_id": [u[2] for u in units],
            "start_verse_id": [u[3] for u in units],
            "end_verse_id": [u[4] for u in units],
            "n_verses": [u[4] - u[3] + 1 for u in units],
            "marker": [u[5] for u in units],
        }
    ).to_parquet(proc / "units.parquet")
    members = [(f"v:{i}", i) for i in range(n)] + [
        (u, v) for u, _, s, e in CHAPTERS for v in range(s, e + 1)
    ]
    pd.DataFrame(members, columns=["unit_id", "verse_id"]).to_parquet(proc / "unit_members.parquet")
    (proc / "corpus_meta.json").write_text(json.dumps({"config_hash": "c0"}), encoding="utf-8")

    # v:0's list: v:1 (neighbour), v:3 (same book, other chapter), v:5 (other book),
    # v:2 (same chapter)
    verse_rows = [("v:0", "v:1", 1), ("v:0", "v:3", 2), ("v:0", "v:5", 3), ("v:0", "v:2", 4)]
    verse_rows += [("v:5", "v:0", 1)]
    for name in ("lx", "sm"):
        _write_topk(art, "verse", name, verse_rows)
    _write_topk(art, "verse", "fused", verse_rows, fused=True)
    chapter_rows = [("c:0:1", "c:0:2", 1), ("c:0:1", "c:1:1", 2), ("c:1:1", "c:0:1", 1)]
    for name in ("tfidf", "sm_bma"):
        _write_topk(art, "chapter", name, chapter_rows)
    _write_topk(art, "chapter", "fused", chapter_rows, fused=True)
    db = run_build_db(cfg, log=lambda _: None)
    return cfg, db


def test_build_counts_and_meta(built):
    cfg, db = built
    assert not db.with_name(db.name + ".tmp").exists()
    conn = connect_readonly(db)
    count = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731
    assert count("SELECT COUNT(*) FROM verses") == 6
    assert count("SELECT COUNT(*) FROM units") == 9
    assert count("SELECT COUNT(*) FROM unit_members") == 12
    assert count("SELECT COUNT(*) FROM books") == 39
    assert count("SELECT COUNT(*) FROM matches") == 3 * 5 + 3 * 3
    assert count("SELECT COUNT(*) FROM matches WHERE unit_type='chapter' AND mode='fused'") == 3
    # breakdown only on fused rows; NaN stored as NULL
    assert count("SELECT COUNT(*) FROM matches WHERE mode!='fused' AND lex_rank IS NOT NULL") == 0
    row = conn.execute(
        "SELECT lex_rank, sem_score FROM matches WHERE mode='fused' AND src_id='v:0' AND rank=1"
    ).fetchone()
    assert row == (1, None)
    meta = {k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM meta")}
    assert meta["systems"]["verse"]["lexical"]["system"] == "lx"
    assert meta["row_counts"]["matches/verse/semantic"] == 5
    assert meta["similar_benchmark"]["queries"] == 0  # spot-check refs absent from the fixture
    assert {"built_at", "config_hash", "oshb_commit", "size_mb", "semantic_encoder"} <= set(meta)
    v = conn.execute("SELECT display_tokens, ketiv_note FROM verses WHERE verse_id=5").fetchone()
    assert json.loads(v[0]) == ["בְּרֵאשִׁית"] and v[1] == "כתיב"
    assert conn.execute("SELECT he_lemma FROM lemma_gloss WHERE lemma='7225'").fetchone() == (
        "ראשית",
    )
    flags = dict(conn.execute("SELECT verse_id || ':' || idx, in_formula FROM words"))
    assert flags["0:1"] == 1 and flags["0:0"] == 0 and flags["2:0"] == 0
    conn.close()


def test_rebuild_from_scratch(built):
    cfg, db = built
    run_build_db(cfg, log=lambda _: None)
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM verses").fetchone()[0] == 6
    conn.close()


def test_missing_topk_names_the_command(built, tmp_path):
    cfg, db = built
    (tmp_path / "artifacts" / "topk" / "chapter" / "sm_bma.parquet").unlink()
    with pytest.raises(RuntimeError, match="bsim units"):
        run_build_db(cfg, log=lambda _: None)
    assert db.exists()  # the previous DB is untouched


def test_similar_filters(built):
    _, db = built
    conn = connect_readonly(db)

    def tgts(**kw):
        return [h["tgt_id"] for h in similar(conn, "verse", "fused", "v:0", **kw)]

    assert tgts() == ["v:1", "v:3", "v:5", "v:2"]
    assert tgts(k=2) == ["v:1", "v:3"]
    assert tgts(exclude=["neighbors"], window=2) == ["v:3", "v:5"]
    assert tgts(exclude=["neighbors"], window=0) == ["v:1", "v:3", "v:5", "v:2"]
    assert tgts(exclude=["chapter"]) == ["v:3", "v:5"]
    assert tgts(exclude=["book"]) == ["v:5"]
    hit = similar(conn, "verse", "fused", "v:0", k=1)[0]
    assert hit["rank"] == 1 and hit["lex_rank"] == 1 and hit["label_en"] == "v:1"
    ch = similar(conn, "chapter", "lexical", "c:0:1", exclude=["book"])
    assert [h["tgt_id"] for h in ch] == ["c:1:1"]
    with pytest.raises(ValueError):
        similar(conn, "chapter", "lexical", "c:0:1", exclude=["neighbors"])
    with pytest.raises(ValueError):
        similar(conn, "verse", "lexical", "v:0", exclude=["nope"])
    conn.close()


def test_strip_prefixes():
    assert strip_prefixes("בְּרֵאשִׁ֖ית", "b/7225") == "ראשית"
    assert strip_prefixes("וְהָאָ֗רֶץ", "c/d/776") == "ארץ"
    assert strip_prefixes("בַּשָּׁמַיִם", "b/d/8064") == "שמים"  # article elided after ב
    assert strip_prefixes("אֱלֹהִים", "430") == "אלהים"
    assert strip_prefixes("שָׁמַיִם", "b/8064") == "שמים"  # unexpected letters: whole word


def test_lemma_display_forms_most_common():
    words = pd.DataFrame(
        {
            "surface": ["הָאָרֶץ", "אֶרֶץ", "אַרְצָה", "וְאֶרֶץ"],
            "lemma": ["d/776", "776", "776", "c/776"],
            "content_lemmas": [["776"]] * 4,
        }
    )
    assert lemma_display_forms(words).to_dict("records") == [{"lemma": "776", "he_lemma": "ארץ"}]


def test_formula_flags():
    words = pd.DataFrame(
        {
            "verse_id": [0, 0, 1, 1, 2],
            "idx": [0, 1, 0, 1, 0],
            "content_lemmas": [["1"], ["2"], ["1"], ["2"], ["1"]],
        }
    )
    f = {"min_n": 2, "max_n": 2, "min_verses": 1, "weight": 0.2}
    assert formula_flags(words, 3, f).tolist() == [True, True, True, True, False]
