import json
import sqlite3

import pandas as pd
import pytest

from bsim.store.db import (
    connect_readonly,
    formula_flags,
    gold_verse_pairs,
    lemma_display_forms,
    run_build_db,
    similar,
    strip_prefixes,
)
from conftest import TEXTS


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
    assert count("SELECT COUNT(*) FROM discoveries") == 3
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
    assert json.loads(v[0]) == TEXTS[5].split() and v[1] == "כתיב"
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
            "verse_id": [0, 0, 1, 2],
            "surface": ["הָאָרֶץ", "אֶרֶץ", "אַרְצָה", "וְאֶרֶץ"],
            "lemma": ["d/776", "776", "776", "c/776"],
            "content_lemmas": [["776"]] * 4,
        }
    )
    assert lemma_display_forms(words).to_dict("records") == [
        {"lemma": "776", "he_lemma": "ארץ", "n_words": 4, "n_verses": 3}
    ]


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


def test_gold_verse_pairs_expand_units():
    links = pd.DataFrame(
        {
            "src_vid": [0, 0],
            "tgt_vid": [5, 4],
            "src_end_vid": [0, 1],
            "tgt_end_vid": [5, 5],
            "level": ["verse", "unit"],
            "connection_type": ["quotation", "related"],
        }
    )
    pairs = gold_verse_pairs(links).set_index(["src", "tgt"]).sort_index()
    assert list(pairs.index) == [(0, 4), (0, 5), (1, 4), (1, 5)]
    assert pairs.loc[(0, 5)].tolist() == [True, "quotation,related"]  # direct wins, types merged
    assert pairs.loc[(1, 4)].tolist() == [False, "related"]


def test_link_flags_and_discoveries(built):
    _, db = built
    conn = connect_readonly(db)
    rows = conn.execute(
        "SELECT unit_type, src_id, tgt_id, link_level, link_type FROM matches"
        " WHERE mode='semantic' AND link_level IS NOT NULL ORDER BY unit_type, src_id, tgt_id"
    ).fetchall()
    assert rows == [
        ("chapter", "c:0:1", "c:0:2", "unit", ""),
        ("chapter", "c:0:1", "c:1:1", "verse", "quotation"),
        ("chapter", "c:1:1", "c:0:1", "verse", "quotation"),
        ("verse", "v:0", "v:5", "verse", "quotation"),
        ("verse", "v:5", "v:0", "verse", "quotation"),
    ]
    # v:0 -> v:1 / v:2 are neighbours, v:5 is linked: v:0 - v:3 is the one verse discovery
    found = conn.execute(
        "SELECT unit_type, mode, a_id, b_id, rank_ab, rank_ba, a_book, b_book FROM discoveries"
        " ORDER BY unit_type, mode"
    ).fetchall()
    assert found == [
        ("verse", m, "v:0", "v:3", 2, None, 0, 0) for m in ("fused", "lexical", "semantic")
    ]
    hits = similar(conn, "verse", "semantic", "v:0", k=10, exclude=["known"])
    assert [h["tgt_id"] for h in hits] == ["v:1", "v:3", "v:2"]
    assert similar(conn, "verse", "semantic", "v:0", k=10)[2]["link_type"] == "quotation"
