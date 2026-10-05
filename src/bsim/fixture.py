"""A tiny synthetic `results.sqlite` built through `run_build_db`.

Six verses over two books, made-up top-k lists, links and analysis outputs: enough to exercise
every API route and viewer page without the real corpus. Used by the pytest suite
(`tests/conftest.py`), `bsim fixture-serve` (CI end-to-end tests) and `bsim openapi` (the
viewer's generated API types).
"""

import json

import numpy as np
import pandas as pd

from bsim.analysis.acrostic import run_acrostics
from bsim.analysis.corpus_map import run_map
from bsim.analysis.diffs import run_diffs
from bsim.analysis.network import run_network
from bsim.analysis.sound import run_sound
from bsim.analysis.structure import run_structure
from bsim.analysis.stylometry import run_stylometry
from bsim.analysis.typescenes import run_typescenes
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
# Gold links (both directions): v0 <-> v5 verse-level quotation; v1-v2 <-> v3-v4 passage-level.
# So v:0 -> v:5 is a known hit and v:0 -> v:3 the one unlinked (discovery) verse pair.
# One shared phrase: v0 words 0-1 ~ v5 word 0 (made up; only the plumbing is tested).
PHRASES = [(0, 5, 15.0, 3, [0, 1], [0], 2)]
LINKS = [(0, 5, 0, 5, "verse", "positional", "quotation"), (1, 3, 2, 4, "unit", "unit", "")]


def fixture_cfg(tmp_path, semantic="sm"):
    cfg = load_config()
    proc, art = tmp_path / "processed", tmp_path / "artifacts"
    cfg["paths"] = {
        **cfg["paths"],
        "data_processed": str(proc),
        "artifacts": str(art),
        "db": str(art / "results.sqlite"),
        "web_dist": str(tmp_path / "web_dist"),
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
    cfg["structure"] = {**cfg["structure"], "unit_types": ["chapter"], "leitwort_min_count": 2}
    cfg["map"] = {**cfg["map"], "clusters": {"chapter": 2}}
    cfg["network"] = {**cfg["network"], "unit_types": ["chapter"]}
    cfg["typescenes"] = {
        **cfg["typescenes"],
        "unit_type": "chapter",
        "min_matches": 1,
        "min_shared_idf": 0.0,
        "max_df": 1.0,
        "null_reps": 2,
    }
    cfg["stylometry"] = {**cfg["stylometry"], "min_words": 1}
    cfg["acrostics"] = {**cfg["acrostics"], "null_reps": 99, "null_screen": 19, "known": ["Gen 1"]}
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
    links = [
        r for a, b, ae, be, *rest in LINKS for r in ((a, b, ae, be, *rest), (b, a, be, ae, *rest))
    ]
    pd.DataFrame(
        links,
        columns=[
            "src_vid",
            "tgt_vid",
            "src_end_vid",
            "tgt_end_vid",
            "level",
            "rule",
            "connection_type",
        ],
    ).assign(split="train").to_parquet(proc / "links.parquet")
    (proc / "corpus_meta.json").write_text(json.dumps({"config_hash": "c0"}), encoding="utf-8")
    # SDBH senses (`bsim lexicon`): ראשית "Begin" everywhere, אלהים and יהוה "Deities"
    pd.DataFrame(
        [
            ("002", 1, None, "Events"),
            ("002001", 2, "002", "Description"),
            ("002001001", 3, "002001", "Begin"),
            ("001", 1, None, "Objects"),
            ("001001", 2, "001", "Beings"),
            ("001001002", 3, "001001", "Deities"),
        ],
        columns=["code", "level", "parent", "label_en"],
    ).to_parquet(proc / "lexicon_domains.parquet")
    senses = [(0, 0, 1, "7225", "002001001"), (0, 1, 0, "430", "001001002")]
    senses += [(0, 3, 0, "3068", "001001002"), (1, 0, 0, "430", "001001002")]
    senses += [(1, 2, 0, "3068", "001001002")]
    senses += [(v, 0, 0, "7225", "002001001") for v in range(2, n)]
    pd.DataFrame(
        {
            "verse_id": [s[0] for s in senses],
            "idx": [s[1] for s in senses],
            "part": [s[2] for s in senses],
            "strong": [s[3] for s in senses],
            "lex_ids": [["x"] for _ in senses],
            "domains": [[s[4]] for s in senses],
            "weights": [[1.0] for _ in senses],
            "source": "sdbh",
        }
    ).to_parquet(proc / "word_senses.parquet")
    (proc / "lexicon_meta.json").write_text(json.dumps({"refs": 8, "matched": 8}), "utf-8")

    for unit_type, rows in (("verse", VERSE_ROWS), ("chapter", CHAPTER_ROWS)):
        for mode, name in final_systems(cfg, unit_type).items():
            write_topk(art, unit_type, name, rows, fused=mode == "fused")
    (art / "phrases").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [(a, b, sc, n, json.dumps(wa), json.dumps(wb), s) for a, b, sc, n, wa, wb, s in PHRASES],
        columns=["a", "b", "score", "n_tokens", "a_words", "b_words", "spread"],
    ).to_parquet(art / "phrases" / "verse.parquet")
    (art / "sequences").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            (1, 0, 1, 3, 4, 0, 0, False, 2, 1.9, 0.01, json.dumps([[0, 3, 1.0], [1, 4, 0.9]])),
            (2, 1, 2, 5, 5, 0, 1, False, 2, 1.2, 0.30, json.dumps([[1, 5, 0.6], [2, 5, 0.6]])),
        ],
        columns=[
            "seq_id",
            "a_start",
            "a_end",
            "b_start",
            "b_end",
            "a_book",
            "b_book",
            "same_chapter",
            "n_pairs",
            "score",
            "q",
            "pairs",
        ],
    ).to_parquet(art / "sequences" / "verse.parquet")
    # verse halves: v0 and v3 split in two (v0 strongly parallel), the rest one colon
    (art / "parallelism").mkdir(parents=True, exist_ok=True)
    par = pd.DataFrame(
        {
            "verse_id": range(n),
            "n_cola": [2, 1, 1, 2, 1, 1],
            "cola": [
                json.dumps(c)
                for c in (
                    [[0, 1], [2, 3]],
                    [[0, 2]],
                    [[0, 1]],
                    [[0, 0], [1, 1]],
                    [[0, 1]],
                    [[0, 1]],
                )
            ],
            "pauses": [json.dumps(p) for p in (["etnahta"], [], [], ["etnahta"], [], [])],
        }
    )
    for col, vals in (
        ("cos", (0.8, 0.3)),
        ("shared", (0, 1)),
        ("shape", (0.5, 0.2)),
        ("balance", (1.0, 1.0)),
        ("prob", (0.9, 0.2)),
    ):
        par[col] = [vals[0], None, None, vals[1], None, None]
    # v0's halves: אלהים // יהוה typed as synonymous through their shared domain
    par["relation"] = ["synonymous", None, None, None, None, None]
    par["relation_pairs"] = [json.dumps([["430", "3068", "domain"]]), None, None, None, None, None]
    par.to_parquet(art / "parallelism" / "verses.parquet")
    (art / "parallelism" / "parallelism.meta.json").write_text(
        json.dumps(
            {
                "coefficients": {"cos": 1.0},
                "held_out_auc": {},
                "known_poems": {},
                "book_means": {"Gen": 0.55},
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        [("430", "3068", 4, 0.5, 9.1, 0.002, 0.004, 1, json.dumps([0, 1]))],
        columns=["a_lemma", "b_lemma", "n", "expected", "g2", "p", "q", "reverse", "examples"],
    ).to_parquet(art / "parallelism" / "word_pairs.parquet")
    # sound-alike pairs (made up): inside v0, and across v4 -> v5 is impossible (other chapter)
    (art / "wordplay").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            (0, 1, 0, 3, "430", "3068", "אלהים", "יהוה", "substitution", 2, 6.0, 0.2),
            (3, 0, 4, 0, "7225", "7225", "ראשית", "ראשית", "extension", 1, 3.0, 0.6),
        ],
        columns=[
            "a_vid",
            "a_idx",
            "b_vid",
            "b_idx",
            "a_lemma",
            "b_lemma",
            "a_form",
            "b_form",
            "kind",
            "gap",
            "score",
            "q",
        ],
    ).to_parquet(art / "wordplay" / "pairs.parquet")
    (art / "wordplay" / "wordplay.meta.json").write_text(
        json.dumps({"pairs": 2, "null_pairs_per_rep": 1.5, "kinds": {}}), encoding="utf-8"
    )
    # names: v0 and v1 mention 430 (as a stand-in name) with 3068; v5 mentions 7225 alone
    ent_dir = art / "entities"
    ent_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            ("430", "אלהים", "person", 2, 2, 0, 1, 0.0, 0.5),
            ("559", "אמר", "place", 2, 2, 0, 1, 0.6, 0.0),
            ("7225", "ראשית", "unclear", 1, 1, 5, 5, 0.0, 0.0),
        ],
        columns=[
            "lemma",
            "he",
            "kind",
            "n_mentions",
            "n_verses",
            "first_vid",
            "last_vid",
            "place",
            "person",
        ],
    ).assign(
        kind_cues=["person", "place", "unclear"], kind_source=["lexicon", "cues", "cues"]
    ).to_parquet(ent_dir / "entities.parquet")
    pd.DataFrame(
        [("430", 0, 1), ("430", 1, 1), ("559", 0, 1), ("559", 1, 1), ("7225", 5, 1)],
        columns=["lemma", "verse_id", "n"],
    ).to_parquet(ent_dir / "mentions.parquet")
    pd.DataFrame(
        [("430", "559", 2, 0.67, 5.2), ("559", "430", 2, 0.67, 5.2)],
        columns=["a", "b", "n_verses", "expected", "g2"],
    ).to_parquet(ent_dir / "links.parquet")
    (ent_dir / "entities.meta.json").write_text(json.dumps({"names": 3}), encoding="utf-8")
    # senses (`bsim senses`): ראשית in two uses (v0 / v2 against v3-v5) and one SDBH meaning
    sense_dir = art / "senses"
    sense_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "lemma": "7225",
                "n": 5,
                "groups": json.dumps({"torah": 5}),
                "k": 2,
                "silhouette": 0.6,
                "use_mi": 0.3,
                "use_excess": 0.2,
                "use_p": 0.01,
                "use_q": 0.01,
                "sense_n": 5,
                "n_senses": 2,
                "sense_mi": 0.2,
                "sense_excess": 0.1,
                "sense_p": 0.04,
                "sense_q": 0.04,
                "nmi": 0.5,
                "nmi_null": 0.05,
            }
        ]
    ).to_parquet(sense_dir / "lemmas.parquet")
    pd.DataFrame(
        [
            ("7225", "use", "0", 2, json.dumps({"torah": 2}), json.dumps(["430"]),
             json.dumps([[0, 0], [2, 0]]), json.dumps([])),
            ("7225", "use", "1", 3, json.dumps({"torah": 3}), json.dumps(["3068"]),
             json.dumps([[3, 0], [4, 0], [5, 0]]), json.dumps([])),
            ("7225", "sdbh", "m1", 5, json.dumps({"torah": 5}), json.dumps([]),
             json.dumps([[0, 0]]), json.dumps(["002001001"])),
        ],
        columns=["lemma", "kind", "sense", "n", "groups", "collocates", "examples", "domains"],
    ).to_parquet(sense_dir / "senses.parquet")
    (sense_dir / "senses.meta.json").write_text(
        json.dumps({"groups": {"torah": ["Gen", "Exod"]}, "nmi_mean": 0.5, "nmi_null_mean": 0.05}),
        encoding="utf-8",
    )
    # style shifts: a curve over book 0 and one seam before v3 (chapter 2)
    seam_dir = art / "seams"
    seam_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {"book_id": 0, "verse_id": [1, 2, 3, 4], "shift": [0.2, 0.3, 0.9, 0.4]}
    ).to_parquet(seam_dir / "curve.parquet")
    feats = json.dumps(
        [["aramaic", "ארמית", -9.7], ["lemma:430", "אלהים", 2.0]], ensure_ascii=False
    )
    pd.DataFrame(
        [(0, 3, 0.9, 0.6, 1, feats)],
        columns=["book_id", "verse_id", "shift", "threshold", "rank", "features"],
    ).to_parquet(seam_dir / "seams.parquet")
    (seam_dir / "seams.meta.json").write_text(
        json.dumps({"thresholds": {"0": 0.6}}), encoding="utf-8"
    )
    emb_dir = art / "embeddings"
    emb_dir.mkdir(parents=True, exist_ok=True)
    np.save(emb_dir / f"{cfg['final_systems']['semantic'].removesuffix('_csls')}.npy", EMB)


def build_fixture_db(tmp_path, semantic="sm"):
    cfg = fixture_cfg(tmp_path, semantic)
    write_inputs(cfg, tmp_path)
    run_diffs(cfg, log=lambda _: None)
    run_typescenes(cfg, log=lambda _: None)
    run_structure(cfg, log=lambda _: None)
    run_acrostics(cfg, log=lambda _: None)
    run_sound(cfg, log=lambda _: None)
    run_map(cfg, log=lambda _: None)
    run_network(cfg, log=lambda _: None)
    run_stylometry(cfg, log=lambda _: None)
    return cfg, run_build_db(cfg, log=lambda _: None)


def fixture_encoder(texts):
    """A stand-in query encoder: every query lands exactly on verse 3."""
    return np.stack([EMB[3] for _ in texts])
