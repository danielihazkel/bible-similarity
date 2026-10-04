"""A tiny `results.sqlite` built through `run_build_db` (used by test_store and test_api)."""

import json

import numpy as np
import pandas as pd
import pytest

from bsim.config import load_config
from bsim.retrieve.fusion import final_systems
from bsim.store.db import run_build_db
from bsim.text.normalize import consonantal

# Six verses: book 0 chapter 1 = v0-v2, book 0 chapter 2 = v3-v4, book 1 chapter 1 = v5.
BOOK = [0, 0, 0, 0, 0, 1]
CHAPTER = [1, 1, 1, 2, 2, 1]
CHAPTERS = [("c:0:1", 0, 0, 2), ("c:0:2", 0, 3, 4), ("c:1:1", 1, 5, 5)]
TEXTS = [
    "בְּרֵאשִׁית אֱלֹהִים וַיֹּאמֶר יְהוָה",
    "אֱלֹהִים וַיֹּאמֶר יְהוָה",
    "רֵאשִׁית הַשָּׁנָה",
    "רֵאשִׁית דָּגָן",
    "רֵאשִׁית פְּרִי",
    "רֵאשִׁית חָכְמָה",
]
# Verse embeddings (L2-normalized rows): v0 ~ v1, v3 ~ v4 ~ v5.
EMB = np.array(
    [
        [1.0, 0.0, 0.0, 0.0],
        [0.8, 0.6, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.6, 0.8],
        [0.0, 0.0, 0.0, 1.0],
    ],
    dtype=np.float32,
)
# v:0's list: v:1 (neighbour), v:3 (same book, other chapter), v:5 (other book),
# v:2 (same chapter)
VERSE_ROWS = [("v:0", "v:1", 1), ("v:0", "v:3", 2), ("v:0", "v:5", 3), ("v:0", "v:2", 4)]
VERSE_ROWS += [("v:5", "v:0", 1)]
CHAPTER_ROWS = [("c:0:1", "c:0:2", 1), ("c:0:1", "c:1:1", 2), ("c:1:1", "c:0:1", 1)]


def fixture_cfg(tmp_path, semantic="sm"):
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
        "semantic": semantic,
        "unit_lexical": "tfidf",
        "unit_aggregation": "bma",
    }
    cfg["lexical"] = {**cfg["lexical"], "formulas": {**cfg["lexical"]["formulas"], "min_verses": 1}}
    cfg["store"] = {**cfg["store"], "bench_queries": 2}
    cfg["serve"] = {**cfg["serve"], "device": "cpu"}
    return cfg


def write_topk(art, unit_type, name, rows, fused=False):
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


def write_inputs(cfg, tmp_path):
    proc, art = tmp_path / "processed", tmp_path / "artifacts"
    proc.mkdir(exist_ok=True)
    n = len(BOOK)
    pd.DataFrame(
        {
            "verse_id": range(n),
            "book_id": BOOK,
            "chapter": CHAPTER,
            "verse": [1, 2, 3, 1, 2, 1],
            "ref": [f"B{b} {c}:{i}" for i, (b, c) in enumerate(zip(BOOK, CHAPTER, strict=True))],
            "osis": [f"B.{i}" for i in range(n)],
            "text_display": TEXTS,
            "text_plain": [consonantal(t) for t in TEXTS],
            "ketiv_note": [None] * (n - 1) + ["כתיב"],
            "display_tokens": [t.split() for t in TEXTS],
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
            # every word aligned to its own display token except v1's last word
            "display_idx": pd.array(
                [w[1] if (w[0], w[1]) != (1, 2) else None for w in words], dtype="Int32"
            ),
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

    for unit_type, rows in (("verse", VERSE_ROWS), ("chapter", CHAPTER_ROWS)):
        for mode, name in final_systems(cfg, unit_type).items():
            write_topk(art, unit_type, name, rows, fused=mode == "fused")
    emb_dir = art / "embeddings"
    emb_dir.mkdir(parents=True, exist_ok=True)
    np.save(emb_dir / f"{cfg['final_systems']['semantic'].removesuffix('_csls')}.npy", EMB)


def build_fixture_db(tmp_path, semantic="sm"):
    cfg = fixture_cfg(tmp_path, semantic)
    write_inputs(cfg, tmp_path)
    return cfg, run_build_db(cfg, log=lambda _: None)


@pytest.fixture
def built(tmp_path):
    return build_fixture_db(tmp_path)
