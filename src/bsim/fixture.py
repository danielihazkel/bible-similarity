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
from bsim.analysis.gematria import run_gematria
from bsim.analysis.network import run_network
from bsim.analysis.sound import run_sound
from bsim.analysis.structure import run_structure
from bsim.analysis.stylometry import run_stylometry
from bsim.analysis.typescenes import run_typescenes
from bsim.config import load_config, resolve_path
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
        "data_raw": str(tmp_path / "raw"),  # none: no stage reads the real downloads
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
    # the reader's mood layer: ראשית ("Begin") counts as distress, אלהים / יהוה ("Deities") praise
    cfg["psalms"] = {**cfg["psalms"], "distress": ["002001001"], "praise": ["001001002"]}
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
    side = {"config_hash": "abc"}
    if fused and unit_type == "chapter":  # chapters are fused with the phrase list too (§16.50)
        df["phr_score"] = np.float32(2.0)
        df["phr_rank"] = pd.array([1] + [None] * (len(df) - 1), dtype="Int32")
        side["w_phr"] = 1.0
    df.to_parquet(d / f"{name}.parquet")
    (d / f"{name}.meta.json").write_text(json.dumps(side), encoding="utf-8")


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
    # BHSA syntax (`bsim syntax`): Genesis 1:1 narration, 1:2 speech by יהוה to משה, Exodus by
    # משה to יהוה
    pd.DataFrame(
        [
            (10, 0, [0, 1], "xQtX", "VC", "N", "N", "NA", None, None, -1, None, None),
            (11, 0, [2, 3], "WayX", "VC", "N", "N", "NA", None, None, -1, None, None),
            (12, 1, [0, 1, 2], "NmCl", "NC", "Q", "NQ", "NA", "3068", "explicit", 12, "4872",
             "explicit"),
            (13, 3, [0, 1], "NmCl", "NC", "Q", "Q", "NA", None, None, 13, None, None),
            (14, 5, [0, 1], "NmCl", "NC", "Q", "NQ", "NA", "4872", "carried", 14, "3068",
             "pronoun"),
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
            "quote",
            "addressee",
            "addressee_source",
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
    # the gazetteer (`bsim places`), made up: אמר a town named in v0-v1, ראשית a region in v5
    place_dir = art / "places"
    place_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [(1, "Amar@Gen.1.1", "אמר", '["559"]', '["אמר", "אמרה"]', 2, 0, "town", "openbible",
          "location", 31.78, 35.23, 640, "openbible", 0.2, 2, "a000001", '["settlement"]'),
         (2, "Reshit@Gen.2.2", "ראשית", '["7225"]', '["ראשית"]', 1, 5, "region", "openbible",
          "location", 30.1, 31.3, None, "tipnr", None, 0, None, "[]")],
        columns=["place_id", "tipnr", "he", "lemmas", "names", "n_verses", "first_vid", "kind",
                 "kind_source", "sdbh_kind", "lat", "lon", "score", "coord_source", "runner_up",
                 "n_identifications", "openbible", "ob_types"],
    ).astype({"score": "Int64"}).to_parquet(place_dir / "places.parquet")  # fmt: skip
    pd.DataFrame(
        [("559", 0, 1, "exact", 0), ("559", 1, 1, "shifted", 1), ("7225", 5, 2, "only", None)],
        columns=["lemma", "verse_id", "place_id", "how", "shift"],
    ).astype({"shift": "Int64"}).to_parquet(place_dir / "mentions.parquet")
    pd.DataFrame(
        [("430", 1.0, 0.0, 0.0, 0.0, 0.0, "person", 2), ("559", 0.0, 0.0, 1.0, 0.0, 0.0,
          "location", 2), ("7225", 0.0, 0.0, 1.0, 0.0, 0.0, "location", 1)],
        columns=["lemma", "person", "people", "location", "landform", "water", "kind", "n_verses"],
    ).to_parquet(place_dir / "name_kinds.parquet")  # fmt: skip
    pd.DataFrame(
        [(1, "land", "Land", 0.0, "[[[34,29],[37,29],[37,34],[34,34],[34,29]]]"),
         (2, "lakes", "Lake", 5.0, "[[[35.4,31.2],[35.6,31.2],[35.6,31.8],[35.4,31.2]]]"),
         (3, "rivers", "River", 6.0, "[[[35.5,32.7],[35.55,31.8]]]")],
        columns=["shape_id", "layer", "name", "rank", "rings"],
    ).to_parquet(place_dir / "basemap.parquet")  # fmt: skip
    (place_dir / "places.meta.json").write_text(
        json.dumps({
            "max_shift": 3, "tipnr": {"PLACE": 2, "PERSON": 1, "OTHER": 0}, "openbible": 1,
            "mentions": 5, "how": {"exact": 1, "shifted": 1, "only": 1, "person": 2, "none": 0},
            "places": 2, "placed_names": 2, "located": 2, "located_openbible": 1,
            "kinds": {"town": 1, "region": 1, "landform": 0, "water": 0}, "unkinded": 0,
            "multi_site_strongs": 0, "name_kinds": {"person": 1, "people": 0, "location": 2,
                                                    "landform": 0, "water": 0},
            "hand_check": {"site": [49, 50], "low_score": 4},
            "map": {"box": [33, 28, 38, 35], "shapes": {"land": 1, "lakes": 1, "rivers": 1},
                    "points": 11},
        }),
        encoding="utf-8",
    )  # fmt: skip
    # place lists (`bsim place-lists`), made up: one list over v0-v5 naming אמר then ראשית, and a
    # grouping of two districts (v0-v2, v3-v5) of one town each
    pl_dir = art / "place_lists"
    pl_dir.mkdir(parents=True, exist_ok=True)
    hist = json.dumps({"lo": 400.0, "hi": 900.0, "counts": [1, 3, 5, 2]})
    pd.DataFrame(
        [("trek", "all", "Genesis 1:1-Exodus 1:1", "itinerary", 0, 5, 2, 2, 441.2, 700.0, 80.0,
          0.002, 441.2, 1.0, hist),
         ("trek", "sure", "Genesis 1:1-Exodus 1:1", "itinerary", 0, 5, 2, 1, None, None, None,
          None, None, None, None)],
        columns=["list_key", "variant", "ref", "kind", "first_vid", "last_vid", "n_named", "n",
                 "path_km", "null_mean", "null_sd", "p", "short_km", "order_score", "hist"],
    ).to_parquet(pl_dir / "lists.parquet")  # fmt: skip
    pd.DataFrame(
        [("trek", 1, 1, 0, None, True, 1), ("trek", 2, 2, 5, 441.2, False, 2)],
        columns=["list_key", "pos", "place_id", "verse_id", "km", "sure", "short_pos"],
    ).to_parquet(pl_dir / "steps.parquet")
    pd.DataFrame(
        [("halves", "all", 1, "Genesis 1:1-3", 0, 2, 1, None, None, None),
         ("halves", "all", 2, "Genesis 2:1-Exodus 1:1", 3, 5, 1, None, None, None),
         ("halves", "sure", 1, "Genesis 1:1-3", 0, 2, 1, None, None, None)],
        columns=["grouping", "variant", "district", "ref", "first_vid", "last_vid", "n",
                 "within_km", "null_mean", "p"],
    ).to_parquet(pl_dir / "districts.parquet")  # fmt: skip
    pd.DataFrame(
        [("halves", 1, 1, 0, True), ("halves", 2, 2, 5, False)],
        columns=["grouping", "district", "place_id", "verse_id", "sure"],
    ).to_parquet(pl_dir / "members.parquet")
    (pl_dir / "place_lists.meta.json").write_text(
        json.dumps({
            "shuffles": 999, "alpha": 0.05, "sure_score": 500, "min_places": 2,
            "lists": {"trek": {"n": 2, "path_km": 441.2, "null_mean": 700.0, "p": 0.002,
                               "short_km": 441.2, "order_score": 1.0}},
            "order": {"all": {"n": 1, "held": 1}, "sure": {"n": 0, "held": 0}},
            "districts": {"halves": {
                "groups": ["Genesis 1:1-3", "Genesis 2:1-Exodus 1:1"], "n_named": 2,
                "all": {"n": 2, "districts": 2, "within_km": 0.0, "null_mean": 220.6, "p": 0.5,
                        "all_km": 441.2, "nearest_same": 0.0},
                "sure": {"n": 1},
            }},
        }),
        encoding="utf-8",
    )  # fmt: skip
    # the geographic arc (`bsim place-arc`), made up: Genesis 1 at אמר, Genesis 2 by ראשית in
    # Egypt, Exodus 1 an "oracle" at ראשית; Genesis tested, one known move (Genesis 1 -> 2)
    arc_dir = art / "place_arc"
    arc_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [(0, 1, 0, 2, 2, 1, 31.78, 35.23, 0.0, 0.0, 1, None, None, False, False),
         (0, 2, 3, 4, 3, 2, 30.6, 32.6, 120.5, 270.2, 2, 270.2, 1, False, False),
         (1, 1, 5, 5, 2, 1, 30.1, 31.3, 0.0, 410.4, 2, None, None, True, True)],
        columns=["book_id", "chapter", "first_vid", "last_vid", "n_mentions", "n_places", "lat",
                 "lon", "spread_km", "reach_km", "top_place", "step_km", "prev_chapter", "oracle",
                 "prophetic"],
    ).astype({"step_km": float, "prev_chapter": "Int64"}).to_parquet(
        arc_dir / "chapters.parquet"
    )  # fmt: skip
    pd.DataFrame(
        [(0, "Gen", 2, 2, 270.2, 300.0, 0.9, 0.5), (1, "Exod", 1, 1, None, None, None, None)],
        columns=["book_id", "abbr", "chapters", "n", "mean_step", "null_mean", "ratio", "p"],
    ).to_parquet(arc_dir / "books.parquet")
    end = {"n_places": 1, "spread_km": 0.0, "top_place": 1}
    (arc_dir / "place_arc.meta.json").write_text(
        json.dumps({
            "shuffles": 999, "alpha": 0.05, "min_mentions": 2, "min_chapters": 2,
            "regions": {"canaan": {"lat": 31.78, "lon": 35.23},
                        "egypt": {"lat": 30.13, "lon": 31.31}},
            "arc": {"chapters": 3, "placed": 3, "books": 1, "steps": 1, "mean_step": 270.2,
                    "null_mean": 300.0, "p": 0.5, "books_held": 0},
            "moves": [{
                "key": "descent", "from_ref": "Genesis 1", "to_ref": "Genesis 2",
                "from_region": "canaan", "to_region": "egypt", "from_vids": [0, 2],
                "to_vids": [3, 4], "km": 270.2, "holds": True,
                "from": end | {"n_mentions": 2, "lat": 31.78, "lon": 35.23, "to_from_region": 0.0,
                               "to_to_region": 384.0, "nearest": "canaan"},
                "to": end | {"n_mentions": 3, "n_places": 2, "lat": 30.6, "lon": 32.6,
                             "spread_km": 120.5, "top_place": 2, "to_from_region": 270.2,
                             "to_to_region": 127.5, "nearest": "egypt"},
            }],
            "oracles": {
                "refs": ["Exodus 1"], "chapters": 1, "placed": 1, "alpha": 0.025,
                "spread": {"n": 1, "n_other": 0, "observed": 0.0, "other": 0.0, "median": 0.0,
                           "other_median": 0.0, "null_mean": 0.0, "p": 1.0},
                "reach": {"n": 1, "n_other": 0, "observed": 410.4, "other": 0.0, "median": 410.4,
                          "other_median": 0.0, "null_mean": 410.4, "p": 0.01},
                "holds": True,
            },
        }),
        encoding="utf-8",
    )  # fmt: skip
    # places named together (`bsim place-links`), made up: אמר and ראשית linked, far apart
    links_dir = art / "place_links"
    links_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [(1, 2, 2, 2, 3, 0.4, 9.3, 441.2, 1)],
        columns=["a", "b", "n_together", "n_a", "n_b", "expected", "g2", "km", "lead_rank"],
    ).astype({"lead_rank": "Int64"}).to_parquet(links_dir / "pairs.parquet")
    pd.DataFrame(
        [("all", 1, 0.0, 100.0, 4, 0, 0.0, None), ("all", 2, 100.0, None, 2, 1, 0.5, 9.3),
         ("no_lists", 1, 0.0, 100.0, 4, 0, 0.0, None), ("no_lists", 2, 100.0, None, 2, 0, 0.0,
                                                         None)],
        columns=["variant", "bin", "lo_km", "hi_km", "pairs", "linked", "share", "median_g2"],
    ).to_parquet(links_dir / "bins.parquet")  # fmt: skip
    (links_dir / "place_links.meta.json").write_text(
        json.dumps({
            "shuffles": 999, "alpha": 0.05, "min_together": 2, "sure_score": 500,
            "lists": ["Exodus 1"], "far_km": 150.0, "leads": 25, "top": 10, "far_pairs": 1,
            "tests": {
                "all": {"places": 2, "pairs": 1, "rho": -0.5, "null_mean": 0.0, "null_q05": -0.4,
                        "null_q95": 0.4, "p": 0.03, "median_km": 441.2, "verses": 6},
                "sure": {"pairs": 0},
                "no_lists": {"places": 2, "pairs": 1, "rho": -0.1, "null_mean": 0.0,
                             "null_q05": -0.4, "null_q95": 0.4, "p": 0.4, "median_km": 441.2,
                             "verses": 5},
            },
            "known": [{"a": "אמר", "b": "ראשית", "found": True, "a_id": 1, "b_id": 2,
                       "km": 441.2, "g2": 9.3, "rank": 1, "holds": True}],
        }),
        encoding="utf-8",
    )  # fmt: skip
    # the family tree (`bsim genealogy`), made up: Adam (Eve beside him) -> Cain, Seth; Seth ->
    # Enosh (a conflict: Cain the other reading), Shimei (on his tribe, link not stated); Cain ->
    # Lamech (a descendant), whose two wives Adah and Zillah each bore a son, and an unnamed
    # daughter (mother not named, a doubtful link); Balaam under "unattached", by Exodus
    gen_dir = art / "genealogy"
    gen_dir.mkdir(parents=True, exist_ok=True)
    person_rows = [
        (1, "Adam@Gen", "אדם", "m", "person", None, 0, 3, True, "root", None),
        (2, "Eve@Gen", "חוה", "f", "person", None, 0, 1, True, "spouse", None),
        (3, "Cain@Gen", "קין", "m", "person", None, 1, 2, True, "tree", None),
        (4, "Seth@Gen", "שת", "m", "person", None, 2, 2, False, "tree", None),
        (5, "Lamech@Gen", "למך", "m", "person", None, 3, 1, False, "tree", None),
        (6, "Adah@Gen", "עדה", "f", "person", None, 3, 1, True, "spouse", None),
        (7, "Zillah@Gen", "צלה", "f", "person", None, 3, 1, True, "spouse", None),
        (8, "Jabal@Gen", "יבל", "m", "person", None, 4, 1, False, "tree", None),
        (9, "Tubal@Gen", "תובל", "m", "person", None, 4, 1, False, "tree", None),
        (10, "Enosh@Gen", "אנוש", "m", "person", None, 2, 1, True, "tree", None),
        (11, "daughter_of_Lamech@Gen", "", "f", "anon", None, 4, 0, False, "tree", None),
        (12, "Shimei@Gen", "שמעי", "m", "person", "Tribe of Seth", 3, 1, True, "tribe", None),
        (13, "Balaam@Exo", "בלעם", "m", "person", None, 5, 1, True, "unattached", None),
        (14, "virtual:unattached", "", None, "virtual", None, None, 0, False, "virtual", None),
        (15, "virtual:book:1", "", None, "virtual", None, None, 0, False, "virtual", 1),
    ]
    pd.DataFrame(
        [(*r, "[]") for r in person_rows],
        columns=["person_id", "key", "he", "sex", "kind", "tribe", "first_vid", "n_verses",
                 "reviewed", "placement", "book_id", "founded"],
    ).astype({"first_vid": "Int64", "book_id": "Int64"}).to_parquet(
        gen_dir / "persons.parquet"
    )  # fmt: skip
    T, C = ("tipnr", "tipnr"), ("confirmed", "curated")
    link_rows = [  # id, parent, child, role, kind, drawn, doubt, marker, status, source, ...
        (1, 1, 2, "spouse", "spouse", False, False, "", *T, None, None, None, 1, "wife"),
        (2, 1, 3, "father", "son", True, False, "", *C, "b01-gen-1-11", None, 0, 1, "begot"),
        (3, 2, 3, "mother", "son", False, False, "", *T, None, None, 0, 1, "begot"),
        (4, 1, 4, "father", "son", True, False, "", *T, None, None, 1, 2, "construct"),
        (5, 2, 4, "mother", "son", False, False, "", *T, None, None, 1, 1, "kin"),
        (6, 3, 5, "father", "descendant", True, False, "a", *T, None, None, 0, 0, None),
        (7, 5, 6, "spouse", "spouse", False, False, "", *T, None, None, None, 0, None),
        (8, 5, 7, "spouse", "spouse", False, False, "", *T, None, None, None, 0, None),
        (9, 5, 8, "father", "son", True, False, "", *T, None, None, 0, 1, "sons_of"),
        (10, 6, 8, "mother", "son", False, False, "", *T, None, None, 0, 0, None),
        (11, 5, 9, "father", "son", True, False, "", *T, None, None, 1, 0, None),
        (12, 7, 9, "mother", "son", False, False, "", *T, None, None, 0, 0, None),
        (13, 5, 11, "father", "son", True, True, "?", *T, None, None, 2, 0, "nearby"),
        (14, 4, 10, "father", "son", True, False, "", "reading", "curated", "b01-gen-1-11", 1,
         0, 1, "construct"),
        (15, 3, 10, "father", "son", False, False, "", "reading", "curated", "b01-gen-1-11", 1,
         None, 1, "together"),
        (16, 3, 4, "sibling", "sibling", False, False, "", *T, None, None, None, 0, None),
        (17, 4, 12, "unstated", "unstated", True, False, "", "tipnr", "tribe", None, None, None,
         0, None),
        (18, 14, 15, "unstated", "unstated", True, False, "", "tipnr", "tribe", None, None, None,
         0, None),
        (19, 15, 13, "unstated", "unstated", True, False, "", "tipnr", "tribe", None, None, None,
         0, None),
    ]  # fmt: skip
    pd.DataFrame(
        link_rows,
        columns=["link_id", "parent_id", "child_id", "role", "kind", "drawn", "doubt", "marker",
                 "status", "source", "block", "conflict_id", "seq", "n_candidates", "cue"],
    ).astype({"conflict_id": "Int64", "seq": "Int64"}).to_parquet(
        gen_dir / "links.parquet"
    )  # fmt: skip
    pd.DataFrame(
        [(1, 1, 0, "wife", "[0, 1]", "auto"), (2, 1, 1, "begot", "[0, 1]", "curated"),
         (3, 1, 1, "begot", "[0]", "auto"), (4, 1, 2, "construct", "[0, 1]", "auto"),
         (4, 2, 3, "kin", "[0]", "auto"), (5, 1, 2, "kin", "[0]", "auto"),
         (9, 1, 4, "sons_of", "[0, 1]", "auto"), (13, 1, 4, "nearby", "[1]", "auto"),
         (14, 1, 2, "construct", "[0, 1]", "curated"), (15, 1, 3, "together", "[0]", "curated")],
        columns=["link_id", "rank", "verse_id", "cue", "tokens", "source"],
    ).to_parquet(gen_dir / "proofs.parquet")  # fmt: skip
    pd.DataFrame(
        [(1, "bible", 10, "b01-gen-1-11", "[14, 15]", "Two passages differ.",
          "שני כתובים חלוקים.")],
        columns=["conflict_id", "kind", "child_id", "block", "readings", "note_en", "note_he"],
    ).to_parquet(gen_dir / "conflicts.parquet")  # fmt: skip
    pd.DataFrame(
        [("b01-gen-1-11", 0, 4, "draft", 2, 1, 0, "01-b01-gen-1-11.yaml"),
         ("b02-exodus", 5, 5, "todo", 0, 0, 0, None)],
        columns=["block", "first_vid", "last_vid", "status", "n_links", "n_conflicts", "n_missed",
                 "file"],
    ).to_parquet(gen_dir / "blocks.parquet")  # fmt: skip
    # identities: Enosh read as one person from two entries; Shimei perhaps Balaam
    pd.DataFrame(
        [(1, "merged", 10, None, '["Enosh@Gen", "Enosh@Gen.5"]', '[{"verse_id": 2, "tokens": [0]}]',
          "x03-edom", "One man.", "איש אחד."),
         (2, "possible", 12, 13, '["Shimei@Gen", "Balaam@Exo"]', '[{"verse_id": 3, "tokens": [1]}]',
          "x03-edom", None, None)],
        columns=["identity_id", "status", "person_id", "other_id", "keys", "proofs", "block",
                 "note_en", "note_he"],
    ).astype({"other_id": "Int64"}).to_parquet(gen_dir / "identities.parquet")  # fmt: skip
    (gen_dir / "genealogy.meta.json").write_text(
        json.dumps({
            "persons": 13, "kinds": {"person": 12, "group": 0, "anon": 1},
            "links": {"father": 8, "mother": 4, "spouse": 3, "sibling": 1, "unstated": 3},
            "parent_links": 12, "proved": 6,
            "best_cue": {"construct": 2, "sons_of": 1, "wife": 0, "begot": 2, "kin": 1,
                         "together": 1, "nearby": 1, "unproved": 4},
            "descendant_links": 1, "doubtful_links": 1,
            "placement": {"root": 1, "tree": 8, "tribe": 1, "spouse": 3, "unattached": 1},
            "unmatched_refs": 0, "conflicts": {"bible": 1, "descendant": 0},
            "identities": {"merged": 1, "possible": 1}, "reviewed_links": 3,
            "blocks": {"todo": 1, "draft": 1, "reviewed": 0},
        }),
        encoding="utf-8",
    )  # fmt: skip
    # equidistant letter sequences (`bsim els`), made up: one scope (v0-v4), two names, the
    # letters' and verses' shuffles and one block; the known sequence at v0
    els_dir = art / "els"
    els_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [("torah", "משה", 3, 40, 38, 78, 80.5, -0.031, 81.0, 70.0, 92.0, 0.6, 79.5, -0.02),
         ("torah", "אהרן", 4, 3, 1, 4, 3.2, 0.211, 3.1, 1.0, 6.0, 0.35, 3.3, 0.05)],
        columns=["scope", "term", "length", "forward", "backward", "hits", "expected",
                 "log_ratio", "letters_mean", "letters_q05", "letters_q95", "letters_p",
                 "verses_mean", "blocks_log_ratio"],
    ).to_parquet(els_dir / "terms.parquet")  # fmt: skip
    pd.DataFrame(
        [("torah", "letters", 1, -0.05), ("torah", "letters", 2, 0.12), ("torah", "letters", 3,
          0.01), ("torah", "verses", 1, 0.02), ("torah", "verses", 2, 0.2), ("torah", "blocks",
          1, 0.04)],
        columns=["scope", "control", "draw", "r"],
    ).to_parquet(els_dir / "draws.parquet")  # fmt: skip
    ctl = {"n": 3, "mean": 0.027, "q05": -0.04, "q95": 0.11, "p": 0.5}
    (els_dir / "els.meta.json").write_text(
        json.dumps({
            "text": "ketiv", "min_skip": 2, "max_skip": 1000, "shuffles": 3, "alpha": 0.05,
            "smooth": 0.5, "terms": 2, "holds": True,
            "scopes": {"torah": {
                "books": ["Gen", "Exod"], "letters": 120, "verses": 5, "first_vid": 0,
                "last_vid": 4, "hits": 82, "expected": 83.7, "r": 0.09, "holds": True,
                "controls": {"letters": ctl, "verses": ctl | {"n": 2, "p": 0.67},
                             "blocks": ctl | {"n": 1, "p": 1.0}},
                "blocks": [{"block": 1, "first_vid": 5, "last_vid": 5, "r": 0.04}],
            }},
            "known": [{"ref": "Genesis 1:1", "verse_id": 0, "term": "תורה", "skip": 50,
                       "found": True, "offset": 5, "in_torah": 12, "expected": 11.4}],
        }),
        encoding="utf-8",
    )  # fmt: skip
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
    # chiasm at the small scale (`bsim mirrors`): v0 mirrors two lemmas; v1 holds a mirrored
    # clause pair, v4 a parallel one
    mir_dir = art / "mirrors"
    mir_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [(0, False, 1, 2, 0.2, 0.4, '["430", "559", "559", "430"]', "[0, 1, 2, 3]")],
        columns=["verse_id", "poetic", "n_pairs", "n_words", "p", "q", "lemmas", "idxs"],
    ).to_parquet(mir_dir / "verses.parquet")
    pd.DataFrame(
        [
            (1, False, "Objc-Pred", "Pred", "Objc", 1, '{"Pred": [1], "Objc": [0]}',
             '{"Objc": [2], "Pred": [1]}'),
            (4, True, "Objc-Pred", "Pred", "Objc", 0, '{"Pred": [0]}', '{"Objc": [0]}'),
        ],
        columns=["verse_id", "poetic", "pair", "first", "second", "mirrored", "a_words",
                 "b_words"],
    ).to_parquet(mir_dir / "clauses.parquet")  # fmt: skip
    side = {"verses_chiastic": 1, "verses_parallel": 3, "pairs_chiastic": 2, "pairs_parallel": 5,
            "share": 0.29, "p": 0.6, "verses": 4, "bigrams": 1, "interval": [0.1, 0.5]}  # fmt: skip
    (mir_dir / "mirrors.meta.json").write_text(
        json.dumps(
            {
                "words": {"all": side, "poetry": {**side, "verses": 1}, "prose": side},
                "clauses": {
                    "poetry": 0.0, "poetry_n": 1, "prose": 1.0, "prose_n": 1, "diff": -1.0,
                    "p": 1.0, "pairs": 2,
                    "by_pair": [{"pair": "Objc-Pred", "n": 2, "poetry": 0.0, "poetry_n": 1,
                                 "prose": 1.0, "prose_n": 1}],
                },
                "full_mirrors": 1,
                "full_mirrors_q": 0,
                "min_words": 2,
            }  # fmt: skip
        ),
        encoding="utf-8",
    )
    # stresses per line (`bsim meter`): chapter 0:1 is the test chapter (its lines fall), 0:2 the
    # poetry pool, 1:1 the control; 0:2 names a lament
    met_dir = art / "meter"
    met_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [(0, 0, 0, 3, 4, 3, 1), (1, 0, 0, 2, 3, 2, 1), (2, 0, 0, 1, 2, None, None),
         (3, 0, 0, 1, 2, 1, 1), (4, 0, 0, 1, 2, 1, 1), (5, 0, 0, 1, 2, None, None)],
        columns=["verse_id", "idx", "first", "last", "stresses", "a", "b"],
    ).astype({"a": "Int64", "b": "Int64"}).to_parquet(met_dir / "lines.parquet")  # fmt: skip
    pd.DataFrame(
        [(0, 1, "test", 2, 1.0, 0.0, 1.0, 0.0, 0.2, 1.0),
         (0, 2, "pool", 2, 0.0, 0.0, 0.0, 0.0, 0.3, 0.0),
         (1, 1, "control", 1, 0.0, 0.0, 0.0, 0.0, None, 0.0)],
        columns=["book_id", "chapter", "group", "n_lines", "fall", "rise", "net", "share32",
                 "prob", "pct"],
    ).to_parquet(met_dir / "chapters.parquet")  # fmt: skip
    group = {"n": 1, "pool_n": 1, "mean": 1.0, "pool_mean": 0.0, "null_mean": 0.5, "p": 0.5}
    (met_dir / "meter.meta.json").write_text(
        json.dumps(
            {
                "min_stresses": 2, "max_stresses": 7, "min_lines": 1, "pool_quantile": 0.75,
                "pool_prob": 0.25, "lines": 6, "split": 4,
                "test": {**group, "p": 0.04}, "test_poetic": group,
                "test_chapters": [{"book_id": 0, "chapter": 1, "net": 1.0, "pct": 1.0,
                                   "n_lines": 2}],
                "control": [{"book_id": 1, "chapter": 1, "net": 0.0, "pct": 0.0, "n_lines": 1}],
                "named": {**group, "mean": 0.0, "p": 1.0,
                          "chapters": [{"book_id": 0, "chapter": 2, "net": 0.0, "pct": 0.0,
                                        "n_lines": 2}]},
                "grid": [{"min": 3, "max": 8, "mean": 1.0, "pool_mean": 0.0, "pool_p": 0.04,
                          "poetic_p": 0.5}],
                "groups": {"test": {"chapters": 1, "lines": 2, "fall": 1.0, "rise": 0.0,
                                    "patterns": [["3:1", 1], ["2:1", 1]]}},
            }  # fmt: skip
        ),
        encoding="utf-8",
    )
    # atbash and albam (`bsim ciphers`), made up: v0's יהוה read through atbash (named in
    # advance) and v5's ראשית through albam; only the plumbing is tested
    cipher_dir = art / "ciphers"
    cipher_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [("atbash", 0, 0, 3, 3, "יהוה", "יהוה", "מצפץ", "9999", "Genesis 1:1"),
         ("albam", 5, 1, 0, 0, "ראשית", "ראשית", "טלגיכ", "9998", None)],
        columns=["cipher", "verse_id", "book_id", "first_tok", "last_tok", "span", "letters",
                 "reads", "name_lemma", "known"],
    ).to_parquet(cipher_dir / "hits.parquet")  # fmt: skip
    pd.DataFrame(
        [("atbash", "c:0:1", 0, 1, 0.2, 0.04, 0.12), ("albam", "c:1:1", 1, 1, 0.5, 0.4, 1.0)],
        columns=["cipher", "unit_id", "book_id", "hits", "expected", "p", "q"],
    ).to_parquet(cipher_dir / "chapters.parquet")  # fmt: skip
    (cipher_dir / "ciphers.meta.json").write_text(
        json.dumps(
            {
                "min_letters": 3, "rare_form": 2, "shuffles": 99, "alpha": 0.05, "names": 2,
                "spans": 9, "single_spans": 3, "distinct_spans": 9, "chapters": ["Genesis 1"],
                "n_chapters": 3, "hits": {"atbash": 1, "albam": 1}, "random_hits": 0.7,
                "known": [{"ref": "Genesis 1:1", "verse_id": 0, "cipher": "atbash",
                           "text": "יהוה", "name": "מצפץ", "found": True}],
                "known_found": 1,
                "tests": {
                    "jeremiah": {"observed": 1, "expected": 0.2, "p": 0.04},
                    "elsewhere": {"observed": 0, "expected": 0.5, "p": 1.0},
                    "albam": {"observed": 1, "expected": 0.7, "p": 0.5},
                },
                "chapters_q": {"atbash": 0, "albam": 0},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )  # fmt: skip
    # the Masorah's counts (`bsim masorah`), made up: the middle letter off by 4.5, the middle word
    # and verse landing; book 0 one verse short of its total (a verse split), book 1 agreeing
    mas_dir = art / "masorah"
    mas_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [(0, "Torah", "letter", "ketiv", "talmud", "Genesis 1:3", False, 2, 0, "ראשית", 3, 1,
          "אלהים", 2, 52, 30.0, 25.5, 4.5, 0, 2),
         (0, "Torah", "letter", "qere", "talmud", "Genesis 1:3", False, 2, 0, "ראשית", 3, 1,
          "אלהים", 2, 53, 30.0, 26.0, 4.0, 0, 2),
         (1, "Torah", "word", "ketiv", "talmud", "Genesis 1:2", True, 1, 1, "ויאמר", None, 2,
          "יהוה", None, 13, 5.0, 6.0, -1.0, 1, 0),
         (1, "Torah", "word", "qere", "talmud", "Genesis 1:2", True, 1, 1, "ויאמר", None, 2,
          "יהוה", None, 13, 5.0, 6.0, -1.0, 1, 0),
         (2, "Torah", "verse", None, "masorah", "Genesis 1:3", True, 2, None, None, None, None,
          None, None, 5, 2.0, 2.0, 0.0, 2, 0),
         (3, "Genesis", "verse", None, "talmud", "Genesis 2:2", False, 4, None, None, None, None,
          None, None, 5, 4.0, 2.0, 2.0, 2, 2)],
        columns=["claim", "span", "unit", "text", "source", "ref", "holds", "trad_vid", "trad_tok",
                 "trad_word", "trad_letter", "mid_tok", "mid_word", "mid_letter", "n", "trad_pos",
                 "mid_pos", "distance", "mid_vid", "verses_apart"],
    ).astype({c: "Int64" for c in ("trad_tok", "trad_letter", "mid_tok", "mid_letter")}).to_parquet(
        mas_dir / "middles.parquet"
    )  # fmt: skip
    pd.DataFrame(
        [("book", None, 0, 0, "verses", None, "masorah", 6, 5, -1, None, "split", "Genesis 1:3", 2,
          2, "[]"),
         ("book", None, 1, 1, "verses", None, "masorah", 1, 1, 0, None, None, None, None, None,
          "[2]"),
         ("section", "torah", 0, 1, "verses", None, "masorah", 7, 6, -1, 7, None, None, None, None,
          "[]"),
         ("section", "torah", 0, 1, "words", "ketiv", "masorah", 15, 15, 0, None, None, None, None,
          None, "[]"),
         ("section", "torah", 0, 1, "words", "qere", "masorah", 15, 16, 1, None, None, None, None,
          None, "[]")],
        columns=["scope", "name", "first_book", "last_book", "unit", "text", "source", "tradition",
                 "ours", "diff", "book_sum", "reason", "ref", "ref_first", "ref_last", "also"],
    ).astype({c: "Int64" for c in ("book_sum", "ref_first", "ref_last")}).to_parquet(
        mas_dir / "totals.parquet"
    )  # fmt: skip
    pd.DataFrame(
        [(0, 5, 13, 13, 52, 53), (1, 1, 2, 2, 9, 9)],
        columns=["book_id", "verses", "words_ketiv", "words_qere", "letters_ketiv", "letters_qere"],
    ).to_parquet(mas_dir / "books.parquet")
    (mas_dir / "masorah.meta.json").write_text(
        json.dumps(
            {
                "tolerance": 1.0, "text": "ketiv",
                "kq": {"pairs": 3, "changed": {"ketiv": 2, "qere": 0}, "unaligned": 0},
                "torah": {"verses": 6, "words_ketiv": 15, "words_qere": 15, "letters_ketiv": 61,
                          "letters_qere": 62},
                "bible": {"verses": 6, "words_ketiv": 15, "words_qere": 15, "letters_ketiv": 61,
                          "letters_qere": 62},
                "checks": {
                    "letter": {"ref": "Genesis 1:3", "n": 52, "distance": 4.5, "verses_apart": 2,
                               "holds": False},
                    "word": {"ref": "Genesis 1:2", "n": 13, "distance": -1.0, "verses_apart": 0,
                             "holds": True},
                    "verse": {"ref": "Genesis 1:3", "n": 5, "distance": 0.0, "verses_apart": 0,
                              "holds": True},
                    "books": {"n": 2, "agree": 1, "max_diff": 1, "reasoned": 1},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )  # fmt: skip
    # root families (`bsim roots`): ראשית joins the root ראש; v0 holds a cognate pair, v1 an
    # infinitive absolute; chapter 0:1 has a hidden Leitwort by root
    root_dir = art / "roots"
    root_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [("7218", "7218", "7218", "רֹאשׁ", None), ("7225", "7225", "7218", "רֹאשׁ", "from"),
         ("430", "430", "430", "אֱלֹהִים", None), ("559", "559", "559", "אָמַר", None),
         ("3068", "3068", "3068", "יְהֹוָה", None)],
        columns=["lemma", "strong", "root", "root_he", "link"],
    ).to_parquet(root_dir / "lemmas.parquet")  # fmt: skip
    pd.DataFrame(
        [(0, 0, 2, "7218", "cognate", "7225", "559"), (1, 1, 2, "559", "inf_abs", "559", "559")],
        columns=["verse_id", "a_idx", "b_idx", "root", "kind", "a_lemma", "b_lemma"],
    ).to_parquet(root_dir / "pairs.parquet")
    pd.DataFrame(
        {"book_id": [0, 1], "words": [9, 1], "cognate": [1, 0], "expected": [0.5, 0.0],
         "inf_abs": [1, 0]}
    ).to_parquet(root_dir / "books.parquet")  # fmt: skip
    pd.DataFrame(
        [("c:0:1", 1, "7218", 3, 5.0, 2, 14, True), ("c:0:2", 1, "7218", 2, 3.0, 1, 1, False)],
        columns=["unit_id", "rank", "root", "count", "g2", "n_words", "lemma_rank", "hidden"],
    ).astype({"lemma_rank": "Int64"}).to_parquet(root_dir / "leitworte.parquet")
    (root_dir / "roots.meta.json").write_text(
        json.dumps(
            {
                "entries": 5, "derived": 1, "joined": 1, "lemmas": 4, "families": 1,
                "family_lemmas": 2, "window": 3, "shuffles": 20,
                "pairs": {"cognate": 1, "other": 0, "inf_abs": 1},
                "tests": {
                    "cognate": {"observed": 1, "expected": 0.5, "ratio": 2.0, "p": 0.01},
                    "other": {"observed": 0, "expected": 0.2, "ratio": 0.0, "p": 1.0},
                },
                "known": [{"chapter": "B0 1", "book_id": 0, "chapter_no": 1, "root": "7218",
                           "he": "רֹאשׁ", "lemma_rank": 14, "root_rank": 1}],
                "known_top_lemma": 0, "known_top_root": 1, "known_better": 1, "top": 12,
                "hidden": 1,
            },  # fmt: skip
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # refrains (`bsim refrains`): אלהים ויאמר יהוה in v0-v2 (named in advance, the strongest), ראשית
    # in v2-v4 (shares v2, so not the strongest of its group); a second named refrain not found
    ref_dir = art / "refrains"
    ref_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [(1, 0, 3, 0, 2, 3, 1e-6, 0.001, 0.0, 0.04, 0.7, True, "ויהי ערב ויהי בקר",
          "אֱלֹהִים וַיֹּאמֶר יְהוָה", "430 559 3068"),
         (2, 0, 3, 2, 4, 1, 1e-4, 0.03, 0.0, None, 0.5, False, None, "רֵאשִׁית", "7225")],
        columns=["refrain_id", "book_id", "k", "first_vid", "last_vid", "n_tokens", "p", "q", "cv",
                 "regular_p", "turn", "strongest", "known", "text", "lemmas"],
    ).astype({"regular_p": "Float64"}).to_parquet(ref_dir / "refrains.parquet")  # fmt: skip
    pd.DataFrame(
        [(1, 0, 1, 3), (1, 1, 0, 2), (1, 2, 0, 1), (2, 2, 0, 0), (2, 3, 0, 0), (2, 4, 0, 0)],
        columns=["refrain_id", "verse_id", "first", "last"],
    ).to_parquet(ref_dir / "occurrences.parquet")
    (ref_dir / "refrains.meta.json").write_text(
        json.dumps(
            {
                "min_tokens": 3, "min_count": 3, "max_gap": 20, "alpha": 0.05, "shuffles": 20,
                "candidates": 5, "detect": {"observed": 2, "expected": 0.1}, "refrains": 2,
                "distinct": 1, "known_found": 1, "known_share": 0.5,
                "known": [
                    {"name": "ויהי ערב ויהי בקר", "verses": [0, 1, 2], "first": "B0 1:1",
                     "last": "B0 1:3", "refrain_id": 1, "text": "אֱלֹהִים וַיֹּאמֶר יְהוָה", "k": 3,
                     "q": 0.001},
                    {"name": "השבעתי אתכם בנות ירושלם", "verses": [3, 4, 5],
                     "first": "B0 2:1", "last": "B1 1:1", "refrain_id": None, "text": None,
                     "k": None, "q": None},
                ],
                "regular": {"testable": 1, "regular": 1, "share": 1.0, "p": 0.05},
                "turns": {"n": 3, "observed": 0.7, "expected": 0.6, "p": 0.04},
            },  # fmt: skip
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # psalms (`bsim psalms`): chapter 0:1 an individual lament turning at v2 (a named turn, found),
    # chapter 0:2 a hymn without a turn; a second named turn (v4) is in a psalm too short to test
    ps_dir = art / "psalms"
    ps_dir.mkdir(parents=True, exist_ok=True)
    feats = ["first_singular", "first_plural", "second", "imperative", "imperative_plural",
             "question", "distress", "praise"]  # fmt: skip
    pd.DataFrame(
        [("c:0:1", 1, "lament_individual", 1, 12, 0.3, 0.0, 0.2, 0.05, 0.0, 0.02, 0.2, 0.1,
          2, 3, 0.5, 0.01, -0.2, 0.3),
         ("c:0:2", 2, "hymn", 2, 8, 0.0, 0.05, 0.1, 0.1, 0.1, 0.0, 0.0, 0.3,
          None, None, None, None, None, None)],
        columns=["unit_id", "chapter", "genre", "cluster", "words", *feats, "turn_vid",
                 "turn_verse", "turn_stat", "turn_p", "before", "after"],
    ).astype({"turn_vid": "Int64", "turn_verse": "Int64", "turn_stat": "Float64",
              "turn_p": "Float64", "before": "Float64", "after": "Float64"}).to_parquet(
        ps_dir / "psalms.parquet"
    )  # fmt: skip
    pd.DataFrame(
        [(0, "c:0:1", 1, 4, 2, 0), (1, "c:0:1", 2, 4, 1, 0), (2, "c:0:1", 3, 4, 0, 2),
         (3, "c:0:2", 1, 4, 0, 1), (4, "c:0:2", 2, 4, 0, 1)],
        columns=["verse_id", "unit_id", "verse", "words", "distress", "praise"],
    ).to_parquet(ps_dir / "verses.parquet")  # fmt: skip
    check = {"mean": 0.3, "rest": 0.1, "p": 0.01, "q": 0.02}
    (ps_dir / "psalms.meta.json").write_text(
        json.dumps(
            {
                "psalms": 2, "labelled": 2, "genres": {"hymn": 1, "lament_individual": 1},
                "features": feats, "k": 2, "alpha": 0.05, "draws": 1000, "title_words": 3,
                "genre_test": {"nmi": 0.4, "null": 0.1, "p": 0.002},
                "crosstab": [{"genre": "hymn", "cluster": 2, "n": 1},
                             {"genre": "lament_individual", "cluster": 1, "n": 1}],
                "checks": [
                    {"genre": "lament_individual", "feature": "first_singular",
                     "direction": "higher", **check},
                    {"genre": "hymn", "feature": "praise", "direction": "higher", **check,
                     "q": 0.3},
                ],
                "checks_held": 1,
                "profiles": {"hymn": dict.fromkeys(feats, 0.1),
                             "lament_individual": dict.fromkeys(feats, 0.2)},
                "cluster_profiles": {"1": dict.fromkeys(feats, 0.2),
                                     "2": dict.fromkeys(feats, 0.1)},
                "known_turns": {
                    "found": 1, "n": 2, "expected": 0.4, "p": 0.03,
                    "rows": [
                        {"ref": "B0 1:3", "chapter": 1, "verse": 3, "verse_id": 2,
                         "turn_verse": 3, "turn_vid": 2, "p": 0.01, "found": True,
                         "chance": 0.4},
                        {"ref": "B0 2:2", "verse_id": 4, "found": None},
                    ],
                },
                "laments_vs_hymns": {"laments": 1, "n_laments": 1, "hymns": 0, "n_hymns": 1,
                                     "p": 0.5},
                "tolerance": 1, "min_side": 2,
                "robustness": {
                    "titles_kept": {"nmi": 0.4, "known": 1, "laments_vs_hymns_p": 0.5},
                    "form_only": {"nmi": 0.3, "null": 0.1, "p": 0.01},
                    "domains_only": {"nmi": 0.2, "null": 0.1, "p": 0.1},
                    "tolerance": {"0": {"found": 1, "expected": 0.2, "p": 0.2},
                                  "1": {"found": 1, "expected": 0.4, "p": 0.03},
                                  "2": {"found": 1, "expected": 0.6, "p": 0.6}},
                },
            },  # fmt: skip
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # the P / non-P split (`bsim pentateuch`): v0-v2 P-like (v1 against the reference), v3-v5 not
    # (v5 unassigned); chapter 0:1 mostly P-like
    src_dir = art / "pentateuch"
    src_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [(0, 0, 1, 1, 0.9, "P", "P", True), (1, 0, 1, 2, 0.7, "P", "nonP", True),
         (2, 0, 1, 3, 0.6, "P", "P", False), (3, 0, 2, 1, 0.2, "nonP", "nonP", False),
         (4, 0, 2, 2, 0.1, "nonP", "nonP", True), (5, 1, 1, 1, 0.4, "nonP", None, False)],
        columns=["verse_id", "book_id", "chapter", "verse", "prob", "side", "reference", "core"],
    ).to_parquet(src_dir / "verses.parquet")  # fmt: skip
    pd.DataFrame(
        [("c:0:1", 0, 1, 3, 1.0, 3, 2 / 3), ("c:0:2", 0, 2, 2, 0.0, 2, 0.0),
         ("c:1:1", 1, 1, 1, 0.0, 0, None)],
        columns=["unit_id", "book_id", "chapter", "verses", "p_like", "assigned", "p_ref"],
    ).to_parquet(src_dir / "chapters.parquet")  # fmt: skip
    (src_dir / "pentateuch.meta.json").write_text(
        json.dumps(
            {
                "verses": 6, "assigned": 5, "reference_p": 2, "p_like": 3, "chunks": 2,
                "core_verses": 3, "synonym_sets": 1, "alpha": 0.05, "draws": 1000,
                "agreement": 0.8,
                "tests": {"kappa": {"observed": 0.6, "null": 0.1, "p": 0.01},
                          "kappa_genesis": {"observed": 0.6, "null": 0.0, "p": 0.02},
                          "names": {"observed": 0.05, "null": 0.0, "p": 0.3}},
                "confusion": {"p_like_p": 2, "p_like_non": 1, "non_p": 0, "non_non": 2},
                "books": {"Genesis": {"verses": 5, "agree": 0.8, "p_like": 0.6, "p_ref": 0.4}},
                "names": {"p_like": {"yhwh": 1, "elohim": 3, "share": 0.25},
                          "non_p": {"yhwh": 2, "elohim": 2, "share": 0.5},
                          "reference_p": 0.0, "reference_non": 0.6},
                "features": {"p_like": [{"token": "7225", "weight": 0.5},
                                        {"token": "p:l", "weight": 0.2}],
                             "non_p": [{"token": "430", "weight": -0.4}]},
                "synonyms": [{"name": "make", "members": ["1254", "3068@q"], "p_like": [2, 0],
                              "non_p": [0, 1]}],
                "grid": [{"chunk_verses": 10, "smooth": 2, "kappa": 0.6, "kappa_genesis": 0.6,
                          "names": 0.05, "kappa_p": 0.01, "kappa_genesis_p": 0.02,
                          "names_p": 0.3}],
                "prefixes": {"l": "ל"},
            },  # fmt: skip
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # who speaks to whom (`bsim dialogue`): God and Moses in book 0 (one exchange, Moses last),
    # Moses to God in book 1
    dl_dir = art / "dialogue"
    dl_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [(0, "divine", "4872", 2, 9, 1), (0, "4872", "divine", 1, 4, 0),
         (1, "4872", "divine", 1, 2, 0)],
        columns=["book_id", "speaker", "addressee", "n_quotes", "n_words", "n_reliable"],
    ).to_parquet(dl_dir / "pairs.parquet")  # fmt: skip
    pd.DataFrame(
        [(0, 0, 1, 1, 2, "divine", "4872", 2, 0, 3, 2, 9, 4, "4872")],
        columns=["exchange", "book_id", "chapter", "verse_id", "last_verse_id", "a", "b",
                 "a_rank", "b_rank", "turns", "a_turns", "a_words", "b_words", "last"],
    ).to_parquet(dl_dir / "exchanges.parquet")  # fmt: skip
    (dl_dir / "dialogue.meta.json").write_text(
        json.dumps(
            {
                "quotations": 3, "with_addressee": 2,
                "addressee": {"explicit": 1, "vocative": 0, "pronoun": 1, "turn": 0},
                "reliable": ["explicit", "vocative"],
                "hand_check": {"explicit": [21, 21], "vocative": [11, 11], "turn": [6, 9],
                               "pronoun": [4, 9]},
                "pairs": 3, "exchanges": 1, "unequal": 1, "shuffles": 999, "alpha": 0.05,
                "tests": {
                    "deference": {"observed": 11.6, "null": 1.1, "p": 0.001, "holds": True,
                                  "up": {"rate": 13.1, "count": 99, "of": 7548, "quotations": 229},
                                  "rest": {"rate": 1.5, "count": 108, "of": 70124,
                                           "quotations": 974}},
                    "particle": {"observed": 0.098, "null": 0.002, "p": 0.003, "holds": True,
                                 "up": {"rate": 0.14, "count": 26, "of": 185, "quotations": 229},
                                 "rest": {"rate": 0.043, "count": 86, "of": 2008,
                                          "quotations": 974}},
                    "last_word": {"observed": 96, "expected": 89.42, "exchanges": 170,
                                  "p": 0.166, "holds": False},
                },
                "sensitivity": {
                    "deference": {"observed": 10.4, "null": 0.4, "p": 0.001,
                                  "up": {"rate": 11.9, "count": 113, "of": 9507,
                                         "quotations": 381},
                                  "rest": {"rate": 1.5, "count": 125, "of": 82452,
                                           "quotations": 1733}},
                    "particle": {"observed": 0.081, "null": -0.01, "p": 0.001,
                                 "up": {"rate": 0.13, "count": 30, "of": 231, "quotations": 381},
                                 "rest": {"rate": 0.049, "count": 117, "of": 2382,
                                          "quotations": 1733}},
                },
                "opener": {"observed": 84, "expected": 89.42, "exchanges": 170, "p": 0.82},
                "lengths": {"longer": 75, "shorter": 90, "median_higher": 11.7,
                            "median_lower": 11.0, "p": 0.28},
            },  # fmt: skip
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # graded numerical sayings and lists (`bsim forms`): v0 a saying named in advance (3 / 4), v4
    # one not named (1 / 2); a genealogy over v1-v3 (named in advance), a list of names in v5
    fm_dir = art / "forms"
    fm_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [(0, 0, 1, "3 / 4", 0.8, "שלשה … ארבעה (Amos 1–2)"), (4, 0, 1, "1 / 2", None, None)],
        columns=["verse_id", "book_id", "n_pairs", "steps", "prob", "known"],
    ).astype({"prob": "Float64"}).to_parquet(fm_dir / "sayings.parquet")
    pd.DataFrame(
        [(0, 1, 3, 3, 4), (4, 0, None, 1, 2)],
        columns=["verse_id", "a_tok", "b_tok", "a_value", "b_value"],
    ).astype({"a_tok": "Int64", "b_tok": "Int64"}).to_parquet(fm_dir / "pairs.parquet")
    pd.DataFrame(
        [(1, 0, 1, 3, 3, 0.9, "genealogy", "Adam to Noah"), (2, 1, 5, 5, 1, 0.8, "names", None)],
        columns=["list_id", "book_id", "first_vid", "last_vid", "n_like", "likeness", "kind",
                 "known"],
    ).to_parquet(fm_dir / "lists.parquet")  # fmt: skip
    pd.DataFrame(
        [(0, 6, 4, 2, 1, 3), (1, 0, 0, 0, 1, 1)],
        columns=["book_id", "numbers", "free", "sayings", "lists", "list_verses"],
    ).to_parquet(fm_dir / "books.parquet")
    (fm_dir / "forms.meta.json").write_text(
        json.dumps(
            {
                "window": 8, "alpha": 0.05, "shuffles": 999, "numbers": 6, "free": 4,
                "sayings": 2, "graded_pairs": 2, "steps": {"1 / 2": 1, "3 / 4": 1},
                "chance": {"pairs": 1286, "observed": 105, "expected": 96.2, "p": 0.196,
                           "without": ["1 / 2"], "without_observed": 48,
                           "without_expected": 37.0, "without_p": 0.037},
                "parallel": {"sayings": 91, "others": 511, "saying_prob": 0.19,
                             "other_prob": 0.15, "saying_parallel": 0.12,
                             "other_parallel": 0.05, "p": 0.026},
                "known": [
                    {"name": "שלשה … ארבעה (Amos 1–2)", "verses": [0, 1], "hits": [0],
                     "found": True},
                    {"name": "אחד … ושנים (Deut 32:30)", "verses": [3], "hits": [],
                     "found": False},
                ],
                "known_found": 1, "known_share": 0.67,
                "lists": {
                    "threshold": 0.73, "like_verses": 4, "observed": 2, "expected": 0.7,
                    "verses": 4, "kinds": {"genealogy": 1, "names": 1},
                    "known": [
                        {"name": "Adam to Noah", "first_vid": 1, "last_vid": 3, "covered": 3,
                         "found": True, "list_ids": [1]},
                        {"name": "the chieftains' offerings", "first_vid": 4, "last_vid": 5,
                         "covered": 1, "found": True, "list_ids": [2]},
                    ],
                    "known_found": 2, "known_share": 0.67, "shuffles": 20, "min_verses": 5,
                    "quantile": 0.99,
                },
            },  # fmt: skip
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # rare words over a few verses (`bsim allusions`): v0-v1 and v3-v4 (known), v1-v2 and v5 (new)
    allu_dir = art / "allusions"
    allu_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            (1, 0, 1, 3, 4, 0, 0, 3, 24.5, 0.04, 1, '[["7225", "ראשית"], ["430", "אלהים"]]'),
            (2, 1, 2, 5, 5, 0, 1, 3, 20.1, 0.8, 0, '[["7225", "ראשית"]]'),
        ],
        columns=[
            "allusion_id", "a_start", "a_end", "b_start", "b_end", "a_book", "b_book",
            "n_shared", "score", "q", "known", "lemmas",
        ],
    ).to_parquet(allu_dir / "pairs.parquet")  # fmt: skip
    (allu_dir / "allusions.meta.json").write_text(
        json.dumps(
            {"rare_lemmas": 3, "window": 2, "pairs": 2, "known": 1, "max_q": 0.05, "strong": 1,
             "strong_known": 1, "best_new_q": 0.8}  # fmt: skip
        ),
        encoding="utf-8",
    )
    # directed echoes (`bsim echoes`): book 1 borrowed from chapter 0:1 (a parallel sequence);
    # chapter 0:2 looks later than 1:1 by its language, against the canon
    echo_dir = art / "echoes"
    echo_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            (1, "c:0:1", "c:1:1", 0, 1, 0, 2, 5, 5, 0.8, 0, 1, 0.4, 1, 1, "borrowed"),
            (2, "c:0:2", "c:1:1", 0, 1, 3, 4, 5, 5, 0.5, 0, 0, -0.5, -1, -1, "language"),
        ],
        columns=[
            "edge_id", "a", "b", "a_book", "b_book", "a_start", "a_end", "b_start", "b_end",
            "weight", "n_cited", "borrowed", "gap", "language", "direction", "basis",
        ],
    ).to_parquet(echo_dir / "edges.parquet")  # fmt: skip
    pd.DataFrame(
        [(0, 1, 0, 1, 0), (1, 0, 0, 0, 1)],
        columns=["src_book", "dst_book", "cited", "borrowed", "language"],
    ).to_parquet(echo_dir / "books.parquet")
    pd.DataFrame(
        [("c:0:1", 0, 1, 0, 1, 0), ("c:0:2", 0, 0, 1, 0, 0), ("c:1:1", 1, 1, 1, 0, 1)],
        columns=["unit_id", "book_id", "lends", "borrows", "lends_explicit", "borrows_explicit"],
    ).to_parquet(echo_dir / "chapters.parquet")
    (echo_dir / "echoes.meta.json").write_text(
        json.dumps(
            {
                "language_gap": 0.3, "pairs": 2, "network_pairs": 2, "in_domain": 2,
                "bases": {"cited": 0, "borrowed": 1, "language": 1, "conflict": 0, "none": 0},
                "checks": {
                    "cited": {"n": 0, "agree": 0, "p": 1.0, "underpowered": True},
                    "spelling": {"n": 1, "agree": 1, "p": 1.0, "underpowered": True},
                    "borrowed": {"n": 1, "agree": 1, "p": 1.0, "underpowered": True},
                },
                "language_forward": 0, "language_backward": 1, "cycles": [],
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


def write_gematria_links(cfg):
    """Do equal values link related words (`bsim gematria-links`), made up over the lemmas
    `bsim gematria` valued: one pair spelled apart, one alike; v0 as the verse named, v3 its
    twin."""
    out = resolve_path(cfg, "artifacts") / "gematria_links"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [("430", "559", 86, False, 0.12, 0, 0.71), ("3068", "7225", 26, True, 0.0, 1, 0.55)],
        columns=["a", "b", "value", "same_letters", "domains", "root", "vector"],
    ).to_parquet(out / "pairs.parquet")

    def t(n, obs, null, p):
        return {"n": n, "observed": obs, "null_mean": null, "null_q05": null - 0.01,
                "null_q95": null + 0.01, "p": p, "unmatched": 0.0}

    meta = {
        "system": "standard", "draws": 99, "alpha": 0.05, "min_count": 1, "lemmas": 4,
        "pairs": 2, "same_letters": 1, "tested": 1, "root_pairs": 3,
        "tests": {
            "equal": {"domains": t(1, 0.12, 0.1, 0.4), "root": t(1, 0.0, 0.02, 1.0),
                      "vector": t(1, 0.71, 0.6, 0.03)},
            "root_family": {"domains": t(3, 0.3, 0.01, 0.01), "vector": t(3, 0.7, 0.6, 0.01)},
        },
        "equivalences": [
            {"a_text": "אלהים", "b_text": "יאמר", "found": True, "a": "430", "b": "559",
             "value": 86, "equal": False, "domains": 0.12, "root": 0.0, "vector": 0.71,
             "domains_rank": 1.0, "root_rank": 0.0, "vector_rank": 1.0},
            {"a_text": "יין", "b_text": "סוד", "found": False},
        ],
        "verse": {"ref": "Genesis 1:1", "verse_id": 0, "value": 2701, "words": 7, "letters": 28,
                  "largest_prime": 73, "n_verses": 6, "all": 1, "expected_all": 0.02,
                  "unique_here": False, "unique_share": 0.5, "twins": [3]},
        "properties": [
            {"key": "words7", "kind": "words", "n": 7, "holds_here": True, "verses": 2},
            {"key": "triangular", "kind": "triangular", "n": None, "holds_here": True,
             "verses": 1},
        ],
    }
    (out / "gematria_links.meta.json").write_text(json.dumps(meta, ensure_ascii=False), "utf-8")


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
    run_gematria(cfg, log=lambda _: None)
    write_gematria_links(cfg)
    return cfg, run_build_db(cfg, log=lambda _: None)


def fixture_encoder(texts):
    """A stand-in query encoder: every query lands exactly on verse 3."""
    return np.stack([EMB[3] for _ in texts])
