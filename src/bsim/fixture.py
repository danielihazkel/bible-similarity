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
        "labels": str(tmp_path / "labels.sqlite"),
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
    # BHSA syntax (`bsim syntax`): Genesis 1:1 narration, 1:2 speech by יהוה, Exodus by משה
    pd.DataFrame(
        [
            (10, 0, [0, 1], "xQtX", "VC", "N", "N", "NA", None, None),
            (11, 0, [2, 3], "WayX", "VC", "N", "N", "NA", None, None),
            (12, 1, [0, 1, 2], "NmCl", "NC", "Q", "NQ", "NA", "3068", "explicit"),
            (13, 3, [0, 1], "NmCl", "NC", "Q", "Q", "NA", None, None),
            (14, 5, [0, 1], "NmCl", "NC", "Q", "NQ", "NA", "4872", "carried"),
        ],
        columns=[
            "clause",
            "verse_id",
            "words",
            "typ",
            "kind",
            "domain",
            "txt",
            "rela",
            "speaker",
            "speaker_source",
        ],
    ).assign(speech=lambda d: d.txt.str.endswith("Q")).to_parquet(proc / "syntax_clauses.parquet")
    pd.DataFrame(
        [
            (20, 10, 0, [0], "PP", "Time"),
            (21, 10, 0, [1], "NP", "Subj"),
            (22, 11, 0, [2], "CP", "Conj"),
            (23, 11, 0, [2], "VP", "Pred"),
            (24, 11, 0, [3], "PrNP", "Subj"),
            (25, 12, 1, [0], "NP", "Subj"),
            (26, 12, 1, [1, 2], "VP", "Pred"),
            (27, 13, 3, [0, 1], "NP", "PreC"),
            (28, 14, 5, [0, 1], "NP", "PreC"),
        ],
        columns=["phrase", "clause", "verse_id", "words", "typ", "function"],
    ).to_parquet(proc / "syntax_phrases.parquet")
    (proc / "syntax_meta.json").write_text(
        json.dumps({"clauses": 5, "speech_clauses": 3, "verses_aligned": 6}), "utf-8"
    )
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
    # which side borrowed (`bsim borrowing`): the cross-book sequence 2 (Genesis -> Exodus)
    bor = art / "borrowing"
    bor.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [(2, 0, 1, 1, 2, 5, 5, 2, 0.8, 0.5, None, None, 2, 0, None, 2, 2, "a_to_b")],
        columns=[
            "seq_id",
            "a_book",
            "b_book",
            "a_start",
            "a_end",
            "b_start",
            "b_end",
            "n_pairs",
            "language",
            "spelling",
            "smoothing",
            "expansion",
            "n_spelling",
            "n_substitution",
            "known",
            "votes",
            "n_votes",
            "direction",
        ],
    ).to_parquet(bor / "sequences.parquet")
    pd.DataFrame(
        [(0, 1, 1, 2, 2, 1, 0, None, "a_to_b")],
        columns=[
            "a_book",
            "b_book",
            "sequences",
            "n_pairs",
            "votes",
            "a_to_b",
            "b_to_a",
            "known",
            "direction",
        ],
    ).to_parquet(bor / "books.parquet")
    check = {"agree": 30, "n": 35, "p": 2.2e-05}
    (bor / "borrowing.meta.json").write_text(
        json.dumps(
            {
                "sequences": 1,
                "known_sequences": 0,
                "checks": {
                    "language": check,
                    "spelling": {"agree": 29, "n": 31, "p": 1e-07},
                    "smoothing": {"agree": 15, "n": 28, "p": 0.85},
                    "expansion": {"agree": 15, "n": 33, "p": 0.73},
                    "all_signs": {"agree": 21, "n": 24, "p": 0.0003},
                },
                "used_signs": ["language", "spelling"],
                "held_out": {"agree": 30, "n": 32, "unclear": 3, "p": 1e-07},
                "used_vote": {"agree": 32, "n": 33, "p": 1e-08},
            }
        ),
        encoding="utf-8",
    )
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
            (
                "7225",
                "use",
                "0",
                2,
                json.dumps({"torah": 2}),
                json.dumps(["430"]),
                json.dumps([[0, 0], [2, 0]]),
                json.dumps([]),
            ),
            (
                "7225",
                "use",
                "1",
                3,
                json.dumps({"torah": 3}),
                json.dumps(["3068"]),
                json.dumps([[3, 0], [4, 0], [5, 0]]),
                json.dumps([]),
            ),
            (
                "7225",
                "sdbh",
                "m1",
                5,
                json.dumps({"torah": 5}),
                json.dumps([]),
                json.dumps([[0, 0]]),
                json.dumps(["002001001"]),
            ),
        ],
        columns=["lemma", "kind", "sense", "n", "groups", "collocates", "examples", "domains"],
    ).to_parquet(sense_dir / "senses.parquet")
    (sense_dir / "senses.meta.json").write_text(
        json.dumps({"groups": {"torah": ["Gen", "Exod"]}, "nmi_mean": 0.5, "nmi_null_mean": 0.05}),
        encoding="utf-8",
    )
    # Late Biblical Hebrew profile (`bsim dating`): Genesis 1 standard, Genesis 2 later-looking
    feats = [
        "lbh_lexemes",
        "anokhi",
        "inf_abs",
        "et_suffix",
        "directional_he",
        "cohortative_wayyiqtol",
        "david_plene",
    ]
    date_dir = art / "dating"
    date_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            ("c:0:1", 0, 1, 12, "early", False, 0.1, json.dumps([])),
            ("c:0:2", 0, 2, 4, "early", False, 0.7, json.dumps(["david_plene"])),
            ("c:1:1", 1, 1, 2, "scored", True, None, json.dumps([])),
        ],
        columns=[
            "unit_id",
            "book_id",
            "chapter",
            "n_words",
            "role",
            "out_of_domain",
            "score",
            "drivers",
        ],
    ).assign(**{f: 0.1 for f in feats}).to_parquet(date_dir / "chapters.parquet")
    pd.DataFrame(
        [(0, "early", False, 2, 0.4, 0.1, 0.7), (1, "scored", True, 0, None, None, None)],
        columns=["book_id", "role", "out_of_domain", "n_chapters", "score", "low", "high"],
    ).assign(**{f: 0.1 for f in feats}).to_parquet(date_dir / "books.parquet")
    (date_dir / "dating.meta.json").write_text(
        json.dumps(
            {
                "features": feats,
                "coefficients": {f: 0.5 for f in feats},
                "held_out_auc": 0.95,
                "held_out_auc_grammar": 0.9,
                "held_out_books": {"0": 0.1},
                "train_chapters": {"early": 2, "late": 0},
                "synoptic": {
                    "pairs": 1,
                    "later": 1,
                    "p": 1.0,
                    "later_grammar": 1,
                    "p_grammar": 1.0,
                    "examples": [
                        {"early": [0, 1], "late": [5, 5], "early_score": 0.1, "late_score": 0.8}
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    # speaker voices (`bsim voices`): God (Genesis) distinct, Moses (Exodus) not
    voice_dir = art / "voices"
    voice_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            ("divine", 3, 3, 1, 0, [0], 0.9, 0.3, 4.2, 0.001, 0.002),
            ("4872", 2, 0, 1, 1, [1], 0.4, 0.38, 0.2, 0.41, 0.41),
        ],
        columns=[
            "key", "n_words", "n_explicit", "n_clauses", "main_book", "books", "delta",
            "null_mean", "effect", "p", "q",
        ],
    ).to_parquet(voice_dir / "speakers.parquet")  # fmt: skip
    pd.DataFrame(
        [
            ("divine", "over", 0, "verb:q", "וקטל (עבר מהופך)", 0.05, 0.02, 1.2),
            ("divine", "under", 1, "lemma:4100", "מה", 0.001, 0.008, -1.4),
            ("4872", "over", 0, "lemma:430", "אלהים", 0.5, 0.2, 0.6),
        ],
        columns=["key", "side", "rank", "feature", "label", "rate", "rate_ref", "z"],
    ).to_parquet(voice_dir / "features.parquet")
    pd.DataFrame(
        [("divine", "4872", 0.7), ("divine", "narrator", 0.9), ("4872", "narrator", 0.5)],
        columns=["a", "b", "delta"],
    ).to_parquet(voice_dir / "pairs.parquet")
    (voice_dir / "voices.meta.json").write_text(
        json.dumps(
            {
                "speakers": 2,
                "features": 125,
                "speech_clauses": 2,
                "words": {"attributed": 5, "profiled": 5, "narration": 4, "unattributed": 2},
                "significant": 1,
                "calibration": {"significant": 0, "of": 2},
                "sensitivity": {"speakers": 1, "rho": None},
                "order": ["divine", "4872", "narrator"],
                "checks": {
                    "author": [
                        {
                            "speaker": "divine",
                            "a": ["Gen"],
                            "b": ["Exod"],
                            "cross": 0.15,
                            "p_cross": 0.001,
                            "d_ab": 0.6,
                            "p_ab": 0.001,
                            "words_a": 400,
                            "words_b": 350,
                            "verdict": "author",
                        },
                        {
                            "speaker": "4872",
                            "a": ["Gen"],
                            "b": ["Exod"],
                            "cross": 0.0,
                            "p_cross": 0.5,
                            "d_ab": 0.1,
                            "p_ab": 0.9,
                            "words_a": 0,
                            "words_b": 2,
                            "verdict": "underpowered",
                        },
                    ],
                    "distinct": [
                        {
                            "book": "Gen",
                            "speaker": "divine",
                            "rank": 1,
                            "of": 1,
                            "ranking": [{"key": "divine", "effect": 4.2, "q": 0.002}],
                        }
                    ],
                },
            }  # fmt: skip
        ),
        encoding="utf-8",
    )
    # divisions (`bsim segments`): in book 0 a quiet samekh before v1, an unmarked turn before
    # v2, chapter 2 starting inside cohesive text at v3 (also the style seam), a pe before v4
    seg_dir = art / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            (0, 1, 0.9, 0.95, 0.0, 0.0, 0.03, "samekh", None, 0, 0, 0, "quiet"),
            (0, 2, 0.1, 0.4, 0.6, 0.5, 0.98, None, None, 0, 0, 0, "turn"),
            (0, 3, 0.7, 0.9, 0.1, 0.05, 0.1, None, None, 1, 0, 1, "cut"),
            (0, 4, 0.3, 0.6, 0.3, 0.2, 0.5, "pe", "pe", 0, 0, 0, None),
        ],
        columns=[
            "book_id", "verse_id", "lex", "sem", "lex_depth", "sem_depth", "score", "mam",
            "oshb", "chapter", "parasha", "seam", "kind",
        ],
    ).to_parquet(seg_dir / "gaps.parquet")  # fmt: skip
    pd.DataFrame(
        [(0, "mam", 2, 0.3, 0.45, 0.04, 0.35, 0.5, 0.03)],
        columns=["book_id", "ref", "k", "pk", "pk_null", "pk_p", "wd", "wd_null", "wd_p"],
    ).to_parquet(seg_dir / "books.parquet")
    group = {"n": 2, "score": 0.27, "null": 0.5, "p": 0.6, "lex": 0.3, "sem": 0.3}
    (seg_dir / "segments.meta.json").write_text(
        json.dumps(
            {
                "window": 4,
                "window_grid": {"2": 0.55, "4": 0.57},
                "gaps": 4,
                "groups": {
                    "mam": group,
                    "mam_pe": {**group, "n": 1, "score": 0.5},
                    "mam_samekh": {**group, "n": 1, "score": 0.03},
                    "chapter_only": {**group, "n": 1, "score": 0.1},
                    "unmarked": {**group, "n": 1, "score": 0.98},
                },
                "contrasts": {"pe_samekh": {"a": 0.5, "b": 0.03, "diff": 0.47, "p": 0.3}},
                "calibration": {"n": 2, "score": 0.5, "null": 0.5, "p": 0.5},
                "seams": {"n": 1, "share": 1.0, "null": 0.5, "p": 0.4, "near": 2},
                "agreement": {
                    "mam": {
                        "books": 1, "pk": 0.3, "pk_null": 0.45, "wd": 0.35, "wd_null": 0.5,
                        "better": 1,
                    }
                },
                "kinds": {"turn": 1, "cut": 1, "quiet": 1},
            }  # fmt: skip
        ),
        encoding="utf-8",
    )
    # citations (`bsim citations`): v3 says it fulfils v0 (resolved, a named source), v5 cites
    # the Torah without a source both signals agree on
    cite_dir = art / "citations"
    cite_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            (1, "word", 3, 0, "דבר יהוה אשר דבר", 0, 0, 12.5, 0.97, 1, "[[0, 12.5], [1, 9.1]]",
             "[[0, 0]]", 1),
            (2, "written", 5, 1, "ככתוב", 1, 0, 4.2, 0.4, 0, "[[1, 4.2], [2, 4.0]]", None, None),
        ],
        columns=[
            "cite_id", "family", "verse_id", "book_id", "formula", "target_vid", "target_book",
            "score", "pct", "resolved", "candidates", "gold", "gold_rank",
        ],
    ).astype({"gold_rank": "Int64"}).to_parquet(cite_dir / "citations.parquet")  # fmt: skip
    pd.DataFrame([(0, 0, 1)], columns=["book_id", "target_book", "n"]).to_parquet(
        cite_dir / "books.parquet"
    )
    fam = {"verses": 1, "share": 1.0, "null_share": 0.25, "p": 0.25, "pct_median": 0.97}
    (cite_dir / "citations.meta.json").write_text(
        json.dumps(
            {
                "citations": 2,
                "resolved": 1,
                "families": {
                    "written": {**fam, "resolved": 0, "share": 0.0, "p": 1.0, "pct_median": 0.4},
                    "word": {**fam, "resolved": 1},
                    "command": {**fam, "verses": 0, "resolved": 0, "share": None, "p": None},
                },
                "gold": {"named": 1, "found": 1, "missing": [], "top1": 1, "top_k": 1, "k": 5,
                         "resolved": 1, "resolved_right": 1},
                "word_lag_median": 3.0,
                "book_pairs": 1,
            }  # fmt: skip
        ),
        encoding="utf-8",
    )
    # ketiv / qere (`bsim ketiv`): a fuller reading in v4 that the parallel v5 writes, a ו > י
    # swap in v5, a word read but not written in v2
    kq_dir = art / "ketiv"
    kq_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            (1, 2, 0, 0, 0, 1, "", "רֵאשִׁית", "", "ראשית", "", "7225", "", "HNcfsa",
             "qere_only", None, None, None, "[]", 0, None, None, None),
            (2, 4, 0, 0, 1, 1, "ראשת", "רֵאשִׁית", "ראשת", "ראשית", "7225", "7225", "HNcfsa",
             "HNcfsa", "vowel_letter", "qere", None, "spelling", "[]", 0, "qere", 5, "ראשית"),
            (3, 5, 1, 0, 1, 1, "ראשות", "רֵאשִׁית", "ראשות", "ראשית", "7225", "7225", "HNcfsa",
             "HNcfpa", "swap", None, "ו>י", "form", '["number s>p"]', 1, None, None, None),
        ],
        columns=[
            "kq_id", "verse_id", "book_id", "pos", "n_ketiv", "n_qere", "ketiv", "qere",
            "ketiv_c", "qere_c", "ketiv_lemma", "qere_lemma", "ketiv_morph", "qere_morph", "cls",
            "fuller", "letters", "grammar", "features", "euphemism", "parallel", "partner_vid",
            "partner_form",
        ],
    ).astype({"partner_vid": "Int64"}).to_parquet(kq_dir / "pairs.parquet")  # fmt: skip
    pd.DataFrame(
        [("וי", 1, 0.1, 10.0, 0.01, 0.02, True), ("אב", 0, 0.2, 0.0, 1.0, 1.0, False)],
        columns=["pair", "n", "expected", "ratio", "p", "q", "lookalike"],
    ).to_parquet(kq_dir / "letters.parquet")
    pd.DataFrame(
        [(0, 2, 6, 333.3, 1, 0.0, 0, 1, 0, 0, 0), (1, 1, 1, 1000.0, 0, None, 1, 0, 0, 1, 0)],
        columns=[
            "book_id", "n", "words", "rate", "vowel_letter", "ketiv_fuller", "swap", "division",
            "other_cls", "form", "word",
        ],
    ).to_parquet(kq_dir / "books.parquet")  # fmt: skip
    (kq_dir / "ketiv.meta.json").write_text(
        json.dumps(
            {
                "pairs": 3,
                "classes": {"qere_only": 1, "vowel_letter": 1, "swap": 1},
                "grammar": {"spelling": 1, "form": 1},
                "euphemisms": 1,
                "features": [["number s>p", 1]],
                "checks": {
                    "lookalike": {
                        "all": {"n": 1, "lookalike": 1, "share": 1.0, "expected": 0.04, "p": 0.04},
                        "without_wy": {"n": 0, "lookalike": 0, "share": None, "expected": 0.01,
                                       "p": 1.0},
                    },
                    "late_fuller": {"late": 0.6, "late_n": 10, "other": 0.4, "other_n": 20,
                                    "diff": 0.2, "p": 0.04, "books": 2},
                    "parallel": {"qere": 1, "ketiv": 0, "neither": 0, "p": 1.0},
                    "plural_suffix": {"plural": 1, "waw_yw": 0},
                    "books": {"chi2": 3.2, "p": 0.07},
                },
            },  # fmt: skip
            ensure_ascii=False,
        ),
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
