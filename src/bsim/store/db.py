"""`bsim build-db`: processed tables + final top-k lists -> `results.sqlite` (DESIGN.md §9).

The DB is rebuilt from scratch into `{db}.tmp` and moved into place only after every table's row
count matches its source; a failed build leaves any previous DB untouched. Only the final systems
go in (`retrieve/fusion.py:final_systems`: one per mode and unit type).

Derived columns:
- `words.in_formula`: the word carries a token inside a frequent-formula occurrence, found with the
  same `lexical.formulas` code and config as `bsim lexical` (formula words are shown dimmer).
- `lemma_gloss.he_lemma`: OSHB lemmas are Strong's numbers and no lexicon is downloaded, so each
  lemma is shown as its most common consonantal surface form with the prefix particles stripped.
- `matches.link_level / link_type`: whether the pair is a Sefaria gold link (`links.parquet`, all
  splits). `verse`: a verse-level link joins a verse of the source to a verse of the target;
  `unit`: only a passage-level link covers them (its ranges expanded to verse pairs).
- `discoveries`: the strong pairs Sefaria does not link (`discoveries()`).
- `phrases`: `bsim phrases` output (`artifacts/phrases/verse.parquet`) plus both verses' books.
- `sequences`: `bsim sequences` chains (`artifacts/sequences/verse.parquet`); each aligned pair
  gains a gold flag (`gold_verse_pairs`, either direction) and `n_gold` counts them.
- `diff_changes` + `meta.diffs`: `bsim diffs` word-level changes (`artifacts/diffs/`).
- `parallelism` + `meta.parallelism`: `bsim parallelism` cola and scores.
- `wordplay`: `bsim wordplay` sound-alike pairs plus the book.
- `entities`, `entity_mentions`, `entity_links` + `meta.entities`: `bsim entities`.
- `seam_curve`, `seams` + `meta.seams`: `bsim seams`.
- `structure`: `bsim structure` scores (`artifacts/structure/units.parquet`).
- `map_points`, `map_clusters`, `book_affinity`, `book_examples` + `meta.book_order`: `bsim map`.
- `stylo_points`, `stylo_delta`, `stylo_features` + `meta.stylometry`: `bsim stylometry`.

`similar()` is the `/api/similar` query: the stored top-k of one unit with query-time filters in
SQL, matching `retrieve/filters.py`, plus `known` (drop gold-linked hits).
"""

from __future__ import annotations

import json
import os
import sqlite3
import statistics
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.structure import SCORE_COLS
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS
from bsim.lexical.formulas import formula_weights, frequent_ngrams
from bsim.lexical.tokens import lemma_streams
from bsim.retrieve.filters import EXCLUDES
from bsim.retrieve.fusion import final_systems
from bsim.retrieve.topk import CSLS_SUFFIX
from bsim.text.normalize import consonantal

Log = Callable[[str], None]

SCHEMA = Path(__file__).with_name("schema.sql")
MODES = ("lexical", "semantic", "fused", "structural")
SIMILAR_EXCLUDES = (*EXCLUDES, "known")
INDEXES = (
    "CREATE INDEX units_by_type_book ON units (unit_type, book_id, start_verse_id)",
    "CREATE INDEX members_by_verse ON unit_members (verse_id, unit_id)",
    "CREATE INDEX discoveries_by_score ON discoveries (unit_type, mode, score DESC, tie DESC)",
    "CREATE INDEX phrases_by_b ON phrases (b)",
    "CREATE INDEX phrases_by_score ON phrases (score DESC)",
    "CREATE INDEX sequences_by_a ON sequences (a_start, a_end)",
    "CREATE INDEX sequences_by_b ON sequences (b_start, b_end)",
    "CREATE INDEX diff_changes_by_op ON diff_changes (op, a_key, b_key)",
    "CREATE INDEX diff_changes_by_books ON diff_changes (a_book, b_book, op)",
    "CREATE INDEX wordplay_by_score ON wordplay (score DESC)",
    "CREATE INDEX wordplay_by_vid ON wordplay (a_vid, b_vid)",
    "CREATE INDEX entity_mentions_by_verse ON entity_mentions (verse_id)",
)
TABLE_COLUMNS = {
    "books": ["book_id", "name", "he_name", "osis", "section", "n_chapters"],
    "verses": [
        "verse_id",
        "book_id",
        "chapter",
        "verse",
        "ref",
        "osis",
        "text_display",
        "text_plain",
        "ketiv_note",
        "display_tokens",
    ],
    "words": [
        "verse_id",
        "idx",
        "display_idx",
        "surface",
        "lemma",
        "content_lemmas",
        "morph",
        "in_formula",
    ],
    "units": [
        "unit_id",
        "unit_type",
        "label_en",
        "label_he",
        "book_id",
        "start_verse_id",
        "end_verse_id",
        "n_verses",
        "marker",
    ],
    "unit_members": ["unit_id", "verse_id"],
    "matches": [
        "unit_type",
        "mode",
        "src_id",
        "rank",
        "tgt_id",
        "score",
        "lex_score",
        "lex_rank",
        "sem_score",
        "sem_rank",
        "link_level",
        "link_type",
    ],
    "discoveries": [
        "unit_type",
        "mode",
        "a_id",
        "b_id",
        "score",
        "tie",
        "rank_ab",
        "rank_ba",
        "a_book",
        "b_book",
    ],
    "phrases": ["a", "b", "score", "n_tokens", "a_words", "b_words", "spread", "a_book", "b_book"],
    "sequences": [
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
        "n_gold",
    ],
    "diff_changes": [
        "seq_id",
        "a",
        "b",
        "a_book",
        "b_book",
        "op",
        "a_idx",
        "b_idx",
        "a_key",
        "b_key",
        "a_form",
        "b_form",
    ],
    "parallelism": [
        "verse_id",
        "n_cola",
        "cola",
        "pauses",
        "cos",
        "shared",
        "shape",
        "balance",
        "prob",
    ],
    "wordplay": [
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
        "book_id",
    ],
    "entities": [
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
    "entity_mentions": ["lemma", "verse_id", "n"],
    "entity_links": ["a", "b", "n_verses", "expected", "g2"],
    "seam_curve": ["book_id", "verse_id", "shift"],
    "seams": ["book_id", "verse_id", "shift", "threshold", "rank", "features"],
    "structure": ["unit_id", "unit_type", "n_verses", *SCORE_COLS],
    "map_points": ["unit_id", "unit_type", "x", "y", "cluster"],
    "map_clusters": ["unit_type", "cluster", "size", "lemmas"],
    "book_affinity": ["a_book", "b_book", "n_pairs", "expected", "lift"],
    "book_examples": ["a_book", "b_book", "rank", "a_vid", "b_vid", "score"],
    "stylo_points": ["unit_id", "x", "y", "n_words"],
    "stylo_delta": ["a_book", "b_book", "delta"],
    "stylo_features": ["book_id", "side", "rank", "feature", "label", "rate", "z"],
    "lemma_gloss": ["lemma", "he_lemma", "n_words", "n_verses", "pos"],
    "lemma_verses": ["lemma", "verse_id", "book_id"],
}

# OSHB prefix morphemes -> their letter; the article's ה is elided after ב / כ / ל (בַּשָּׁמַיִם).
PREFIX_LETTERS = {"b": "ב", "c": "ו", "d": "ה", "k": "כ", "l": "ל", "m": "מ", "s": "ש"}
ARTICLE_ELIDED_AFTER = {"b", "k", "l"}


def strip_prefixes(surface: str, lemma: str) -> str:
    """Consonantal surface without the letters of the lemma's leading prefix morphemes.

    The whole word is kept when it does not start with the expected letters.
    """
    word = consonantal(surface).replace(" ", "")
    parts = lemma.split("/")
    prefix = ""
    for i, p in enumerate(parts):
        if p not in PREFIX_LETTERS:
            break
        if p == "d" and i > 0 and parts[i - 1] in ARTICLE_ELIDED_AFTER:
            continue
        prefix += PREFIX_LETTERS[p]
    if prefix and word.startswith(prefix) and len(word) > len(prefix):
        return word[len(prefix) :]
    return word


def lemma_parts_pos(lemma: str, morph: str | None) -> dict[str, str]:
    """Content lemma -> part-of-speech letter of its morpheme. OSHB lemma parts (`c/6965 b`) line
    up with the morph's morphemes (`HC/Vqq3ms`); suffix morphemes come after and have no lemma."""
    if not morph:
        return {}
    parts, morphemes = lemma.split("/"), morph[1:].split("/")
    out = {}
    for part, m in zip(parts, morphemes, strict=False):
        lem = part.replace(" ", "")
        if lem[:1].isdigit() and m:
            out[lem] = m[0]
    return out


def lemma_display_forms(words: pd.DataFrame) -> pd.DataFrame:
    """`lemma, he_lemma, n_words, n_verses, pos`: each content lemma's most common
    prefix-stripped form (ties: first seen), its number of occurrences and of verses containing
    it, and its most common part of speech (OSHB letter; None without morphology)."""
    forms: dict[str, Counter[str]] = defaultdict(Counter)
    verses: dict[str, set[int]] = defaultdict(set)
    pos: dict[str, Counter[str]] = defaultdict(Counter)
    morphs = words.morph if "morph" in words else [None] * len(words)
    for vid, surface, lemma, content, morph in zip(
        words.verse_id, words.surface, words.lemma, words.content_lemmas, morphs, strict=True
    ):
        if len(content):
            form = strip_prefixes(surface, lemma)
            for lem in content:
                forms[lem][form] += 1
                verses[lem].add(int(vid))
            for lem, p in lemma_parts_pos(lemma, morph).items():
                pos[lem][p] += 1
    rows = [
        (
            lem,
            c.most_common(1)[0][0],
            c.total(),
            len(verses[lem]),
            pos[lem].most_common(1)[0][0] if pos[lem] else None,
        )
        for lem, c in sorted(forms.items())
    ]
    return pd.DataFrame(rows, columns=TABLE_COLUMNS["lemma_gloss"])


def lemma_verses(words: pd.DataFrame, verses: pd.DataFrame) -> pd.DataFrame:
    """`lemma, verse_id, book_id`: distinct (content lemma, verse) pairs, the concordance."""
    pairs = (
        words[["verse_id", "content_lemmas"]]
        .explode("content_lemmas")
        .dropna()
        .rename(columns={"content_lemmas": "lemma"})
        .drop_duplicates()
    )
    pairs["book_id"] = pairs.verse_id.map(verses.set_index("verse_id").book_id)
    return pairs.sort_values(["lemma", "verse_id"])[TABLE_COLUMNS["lemma_verses"]]


def formula_flags(words: pd.DataFrame, n_verses: int, formulas: dict[str, Any]) -> np.ndarray:
    """Per `words` row: True if any of its lemma tokens lies inside a formula occurrence."""
    streams = lemma_streams(words, n_verses)
    ngrams = frequent_ngrams(streams, formulas["min_n"], formulas["max_n"], formulas["min_verses"])
    weights = formula_weights(streams, ngrams, formulas["weight"])
    flagged = {
        (vid, idx)
        for vid, (s, w) in enumerate(zip(streams, weights, strict=True))
        for idx, wt in zip(s.word_idx, w, strict=True)
        if wt < 1
    }
    return np.array(
        [(v, i) in flagged for v, i in zip(words.verse_id, words.idx, strict=True)], dtype=bool
    )


def _join_types(types: Iterable[str]) -> str:
    return ",".join(sorted({t for s in types for t in s.split(",") if t}))


def gold_verse_pairs(links: pd.DataFrame) -> pd.DataFrame:
    """`src, tgt, direct, types`: every gold-linked verse pair (both directions, as in
    `links.parquet`). Unit-level rows are expanded to their Cartesian verse pairs
    (`direct` False)."""
    parts = []
    for row in links.itertuples(index=False):
        src = np.arange(row.src_vid, row.src_end_vid + 1)
        tgt = np.arange(row.tgt_vid, row.tgt_end_vid + 1)
        s, t = np.meshgrid(src, tgt, indexing="ij")
        parts.append((s.ravel(), t.ravel(), row.level == "verse", row.connection_type))
    if not parts:
        return pd.DataFrame({"src": [], "tgt": [], "direct": [], "types": []})
    df = pd.DataFrame(
        {
            "src": np.concatenate([p[0] for p in parts]),
            "tgt": np.concatenate([p[1] for p in parts]),
            "direct": np.concatenate([np.full(len(p[0]), p[2]) for p in parts]),
            "types": np.concatenate([np.full(len(p[0]), p[3], dtype=object) for p in parts]),
        }
    )
    return (
        df.groupby(["src", "tgt"], sort=False)
        .agg(direct=("direct", "any"), types=("types", _join_types))
        .reset_index()
    )


def sequence_gold(sequences: pd.DataFrame, gold: pd.DataFrame) -> pd.DataFrame:
    """`pairs` JSON `[[a, b, w], ...]` -> `[[a, b, w, is_gold], ...]` plus `n_gold`, the aligned
    pairs that are gold links (either direction)."""
    linked = set(zip(gold.src.tolist(), gold.tgt.tolist(), strict=True))
    pairs, counts = [], []
    for p in sequences.pairs:
        rows = [[a, b, w, int((a, b) in linked or (b, a) in linked)] for a, b, w in json.loads(p)]
        pairs.append(json.dumps(rows))
        counts.append(sum(r[3] for r in rows))
    return sequences.assign(pairs=pairs, n_gold=counts)


def unit_links(
    pairs: pd.DataFrame, units: pd.DataFrame, members: pd.DataFrame, unit_type: str
) -> pd.DataFrame:
    """`src_id, tgt_id, link_level, link_type` of the units of `unit_type` joined by a gold verse
    pair (a pair inside one unit is dropped)."""
    ids = set(units.unit_id[units.unit_type == unit_type])
    m = members[members.unit_id.isin(ids)]
    of_verse = pd.Series(m.unit_id.to_numpy(), index=m.verse_id.to_numpy())
    df = pd.DataFrame(
        {
            "src_id": pairs.src.map(of_verse),
            "tgt_id": pairs.tgt.map(of_verse),
            "direct": pairs.direct,
            "types": pairs.types,
        }
    ).dropna(subset=["src_id", "tgt_id"])
    df = df[df.src_id != df.tgt_id]
    out = (
        df.groupby(["src_id", "tgt_id"], sort=False)
        .agg(direct=("direct", "any"), link_type=("types", _join_types))
        .reset_index()
    )
    out["link_level"] = np.where(out.direct, "verse", "unit")
    return out[["src_id", "tgt_id", "link_level", "link_type"]]


def discoveries(
    matches: pd.DataFrame, units: pd.DataFrame, max_rank: int, window: int
) -> pd.DataFrame:
    """Unordered pairs of one (unit_type, mode) list without a gold link where either unit has
    the other in its top-`max_rank` (`TABLE_COLUMNS["discoveries"]`). Verse pairs within
    ±`window` verses of the same book are left out, as with the `neighbors` filter."""
    df = matches[(matches["rank"] <= max_rank) & matches.link_level.isna()]
    cols = TABLE_COLUMNS["discoveries"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    info = units.set_index("unit_id")
    start, book = info.start_verse_id, info.book_id
    s_start, t_start = df.src_id.map(start).to_numpy(), df.tgt_id.map(start).to_numpy()
    forward = s_start < t_start
    tie = df.sem_score if df["mode"].iloc[0] == "fused" else df.score
    pairs = pd.DataFrame(
        {
            "a_id": np.where(forward, df.src_id, df.tgt_id),
            "b_id": np.where(forward, df.tgt_id, df.src_id),
            "score": df.score.to_numpy(),
            "tie": pd.to_numeric(tie, errors="coerce").fillna(df.score).to_numpy(),
            "rank_ab": np.where(forward, df["rank"], -1),
            "rank_ba": np.where(forward, -1, df["rank"]),
        }
    )
    out = (
        pairs.groupby(["a_id", "b_id"], sort=False)
        .agg(
            score=("score", "max"),
            tie=("tie", "max"),
            rank_ab=("rank_ab", "max"),
            rank_ba=("rank_ba", "max"),
        )
        .reset_index()
    )
    for col in ("rank_ab", "rank_ba"):
        out[col] = out[col].where(out[col] > 0).astype("Int32")
    out["a_book"] = out.a_id.map(book).to_numpy()
    out["b_book"] = out.b_id.map(book).to_numpy()
    if df.unit_type.iloc[0] == "verse":
        gap = (out.b_id.map(start) - out.a_id.map(start)).abs()
        out = out[~((out.a_book == out.b_book) & (gap <= window))]
    out["unit_type"] = df.unit_type.iloc[0]
    out["mode"] = df["mode"].iloc[0]
    return out.sort_values(["score", "tie"], ascending=False, kind="stable")[cols]


def _rows(df: pd.DataFrame, cols: list[str], batch: int) -> Iterator[list[tuple[Any, ...]]]:
    """Batches of Python-typed tuples (NaN / NA -> None) for `executemany`."""
    for start in range(0, len(df), batch):
        part = df.iloc[start : start + batch]
        columns = [part[c].astype(object).where(part[c].notna(), None).tolist() for c in cols]
        yield list(zip(*columns, strict=True))


def _insert(
    conn: sqlite3.Connection,
    table: str,
    df: pd.DataFrame,
    batch: int,
    cols: list[str] | None = None,
) -> None:
    cols = cols or TABLE_COLUMNS[table]
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"
    for rows in _rows(df, cols, batch):
        conn.executemany(sql, rows)


def similar(
    conn: sqlite3.Connection,
    unit_type: str,
    mode: str,
    src_id: str,
    k: int = 10,
    exclude: Iterable[str] = (),
    window: int = 2,
) -> list[dict[str, Any]]:
    """Top-`k` stored matches of `src_id` after query-time exclusion, in stored rank order.

    `neighbors` (same book, within ±window verses) and `chapter` (same book and chapter) apply to
    verses only; `book` and `known` (gold-linked hits) apply to every unit type. Hits keep their
    stored `rank`.
    """
    exclude = set(exclude)
    unknown = exclude - set(SIMILAR_EXCLUDES)
    if unknown:
        raise ValueError(f"unknown filters {sorted(unknown)}; choose from {SIMILAR_EXCLUDES}")
    if unit_type != "verse" and exclude & {"neighbors", "chapter"}:
        raise ValueError("the neighbors / chapter filters apply to verses only")
    joins, where, params = "", [], [unit_type, mode, src_id]
    if "neighbors" in exclude:
        where.append(
            "NOT (t.book_id = s.book_id AND abs(t.start_verse_id - s.start_verse_id) <= ?)"
        )
        params.append(window)
    if "chapter" in exclude:
        joins = (
            " JOIN verses sv ON sv.verse_id = s.start_verse_id"
            " JOIN verses tv ON tv.verse_id = t.start_verse_id"
        )
        where.append("NOT (t.book_id = s.book_id AND tv.chapter = sv.chapter)")
    if "book" in exclude:
        where.append("t.book_id != s.book_id")
    if "known" in exclude:
        where.append("m.link_level IS NULL")
    sql = (
        "SELECT m.rank, m.tgt_id, m.score, m.lex_score, m.lex_rank, m.sem_score, m.sem_rank,"
        " m.link_level, m.link_type, p.score AS phrase_score, p.n_tokens AS phrase_tokens,"
        " t.label_en, t.label_he, t.book_id, t.start_verse_id, t.end_verse_id"
        " FROM matches m"
        " JOIN units s ON s.unit_id = m.src_id"
        " JOIN units t ON t.unit_id = m.tgt_id"
        " LEFT JOIN phrases p ON m.unit_type = 'verse'"
        " AND p.a = min(s.start_verse_id, t.start_verse_id)"
        " AND p.b = max(s.start_verse_id, t.start_verse_id)"
        f"{joins}"
        " WHERE m.unit_type = ? AND m.mode = ? AND m.src_id = ?"
        + "".join(f" AND {w}" for w in where)
        + " ORDER BY m.rank LIMIT ?"
    )
    cur = conn.execute(sql, [*params, k])
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r, strict=True)) for r in cur.fetchall()]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text("utf-8")) if path.exists() else {}


def _load_inputs(cfg: dict[str, Any]) -> dict[str, pd.DataFrame]:
    proc = resolve_path(cfg, "data_processed")
    out = {}
    for name in ("verses", "words", "units", "unit_members", "links"):
        path = proc / f"{name}.parquet"
        if not path.exists():
            cmd = "build-links" if name == "links" else "build-corpus"
            raise RuntimeError(f"{path} missing; run `bsim {cmd}` first")
        out[name] = pd.read_parquet(path)
    path = resolve_path(cfg, "artifacts") / "phrases" / "verse.parquet"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim phrases` first")
    out["phrases"] = pd.read_parquet(path)
    path = resolve_path(cfg, "artifacts") / "sequences" / "verse.parquet"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim sequences` first")
    out["sequences"] = pd.read_parquet(path)
    diff_dir = resolve_path(cfg, "artifacts") / "diffs"
    if not (diff_dir / "changes.parquet").exists():
        raise RuntimeError(f"{diff_dir / 'changes.parquet'} missing; run `bsim diffs` first")
    out["diff_changes"] = pd.read_parquet(diff_dir / "changes.parquet")
    out["diffs_meta"] = _read_json(diff_dir / "diffs.meta.json")
    par_dir = resolve_path(cfg, "artifacts") / "parallelism"
    if not (par_dir / "verses.parquet").exists():
        raise RuntimeError(f"{par_dir / 'verses.parquet'} missing; run `bsim parallelism` first")
    out["parallelism"] = pd.read_parquet(par_dir / "verses.parquet")
    out["parallelism_meta"] = _read_json(par_dir / "parallelism.meta.json")
    path = resolve_path(cfg, "artifacts") / "wordplay" / "pairs.parquet"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim wordplay` first")
    out["wordplay"] = pd.read_parquet(path)
    out["wordplay_meta"] = _read_json(path.with_name("wordplay.meta.json"))
    ent_dir = resolve_path(cfg, "artifacts") / "entities"
    for name in ("entities", "mentions", "links"):
        path = ent_dir / f"{name}.parquet"
        if not path.exists():
            raise RuntimeError(f"{path} missing; run `bsim entities` first")
        out[f"entity_{name}"] = pd.read_parquet(path)
    out["entities_meta"] = _read_json(ent_dir / "entities.meta.json")
    seam_dir = resolve_path(cfg, "artifacts") / "seams"
    for name in ("curve", "seams"):
        path = seam_dir / f"{name}.parquet"
        if not path.exists():
            raise RuntimeError(f"{path} missing; run `bsim seams` first")
        out[f"seam_{name}"] = pd.read_parquet(path)
    out["seams_meta"] = _read_json(seam_dir / "seams.meta.json")
    path = resolve_path(cfg, "artifacts") / "structure" / "units.parquet"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim structure` first")
    out["structure"] = pd.read_parquet(path)
    map_dir = resolve_path(cfg, "artifacts") / "map"
    for name in ("points", "clusters", "book_affinity", "book_examples"):
        path = map_dir / f"{name}.parquet"
        if not path.exists():
            raise RuntimeError(f"{path} missing; run `bsim map` first")
        out[f"map_{name}"] = pd.read_parquet(path)
    out["map_meta"] = _read_json(map_dir / "map.meta.json")
    stylo_dir = resolve_path(cfg, "artifacts") / "stylometry"
    for name in ("points", "book_delta", "book_features"):
        path = stylo_dir / f"{name}.parquet"
        if not path.exists():
            raise RuntimeError(f"{path} missing; run `bsim stylometry` first")
        out[f"stylo_{name}"] = pd.read_parquet(path)
    out["stylo_meta"] = _read_json(stylo_dir / "stylometry.meta.json")
    return out


def _match_files(cfg: dict[str, Any]) -> list[tuple[str, str, str, Path]]:
    """(unit_type, mode, system, path) of every final list; all must exist."""
    topk = resolve_path(cfg, "artifacts") / "topk"
    files = []
    for unit_type in cfg["units"]["types"]:
        for mode, system in final_systems(cfg, unit_type).items():
            path = topk / unit_type / f"{system}.parquet"
            if not path.exists():
                cmd = "fuse" if mode == "fused" else "topk" if unit_type == "verse" else "units"
                raise RuntimeError(f"{path} missing; run `bsim {cmd}` for {system!r} first")
            files.append((unit_type, mode, system, path))
    return files


def _meta(
    cfg: dict[str, Any], files: list[tuple[str, str, str, Path]], counts: dict[str, int]
) -> dict[str, Any]:
    proc = resolve_path(cfg, "data_processed")
    corpus = _read_json(proc / "corpus_meta.json")
    semantic = cfg["final_systems"]["semantic"]
    base = semantic.removesuffix(CSLS_SUFFIX)
    systems: dict[str, dict[str, Any]] = defaultdict(dict)
    for unit_type, mode, system, path in files:
        side = _read_json(path.with_suffix(".meta.json"))
        systems[unit_type][mode] = {
            "system": system,
            "config_hash": side.get("config_hash"),
            "built_at": side.get("built_at"),
        }
    return {
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "config_hash": config_hash(cfg, "retrieval", "fusion", "final_systems", "lexical"),
        "oshb_commit": cfg["sources"]["oshb"]["commit"],
        "corpus_config_hash": corpus.get("config_hash"),
        "text_version": cfg["sources"]["sefaria"]["text_version"],
        "text_license": "CC-BY-SA (Sefaria, Miqra according to the Masorah)",
        "systems": dict(systems),
        "fusion": {k: cfg["fusion"][k] for k in ("w_lex", "w_sem", "rrf_k")},
        "k": cfg["retrieval"]["k"],
        "neighbor_window": cfg["retrieval"]["neighbor_window"],
        "semantic_system": semantic,
        "semantic_csls": semantic.endswith(CSLS_SUFFIX),
        "semantic_encoder": cfg["encoders"]["systems"].get(base, {}).get("model"),
        "embeddings": f"embeddings/{base}.npy",
        "row_counts": counts,
    }


def _check_counts(conn: sqlite3.Connection, expected: dict[str, int]) -> None:
    actual = {}
    for key in expected:
        if "/" in key:  # matches/{unit_type}/{mode}
            _, unit_type, mode = key.split("/")
            sql, args = (
                "SELECT COUNT(*) FROM matches WHERE unit_type = ? AND mode = ?",
                (unit_type, mode),
            )
        else:
            sql, args = f"SELECT COUNT(*) FROM {key}", ()
        actual[key] = conn.execute(sql, args).fetchone()[0]
    wrong = {k: (actual[k], v) for k, v in expected.items() if actual[k] != v}
    if wrong:
        raise RuntimeError(f"row counts differ from the sources (db, source): {wrong}")
    dangling = conn.execute(
        "SELECT COUNT(*) FROM matches m"
        " WHERE NOT EXISTS (SELECT 1 FROM units u WHERE u.unit_id = m.src_id)"
        " OR NOT EXISTS (SELECT 1 FROM units u WHERE u.unit_id = m.tgt_id)"
    ).fetchone()[0]
    if dangling:
        raise RuntimeError(f"{dangling} matches refer to unknown unit ids")


def _write_db(
    path: Path,
    cfg: dict[str, Any],
    inputs: dict[str, pd.DataFrame],
    files: list[tuple[str, str, str, Path]],
    log: Log,
) -> dict[str, Any]:
    batch, disc = cfg["store"]["batch_rows"], cfg["store"]["discoveries"]
    window = cfg["retrieval"]["neighbor_window"]
    verses, words = inputs["verses"], inputs["words"]
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA journal_mode = OFF")
        conn.execute("PRAGMA synchronous = OFF")
        conn.executescript(SCHEMA.read_text("utf-8"))

        books = pd.DataFrame(
            [(b.book_id, b.sefaria, b.he, b.osis, b.section, b.n_chapters) for b in BOOKS],
            columns=TABLE_COLUMNS["books"],
        )
        verses = verses.assign(
            display_tokens=[json.dumps(list(t), ensure_ascii=False) for t in verses.display_tokens]
        )
        log("formula flags and lemma display forms")
        words = words.assign(
            content_lemmas=[" ".join(c) for c in words.content_lemmas],
            in_formula=formula_flags(words, len(verses), cfg["lexical"]["formulas"]).astype(int),
        )
        gloss = lemma_display_forms(inputs["words"])
        gold = gold_verse_pairs(inputs["links"])
        tables = {
            "books": books,
            "verses": verses,
            "words": words,
            "units": inputs["units"],
            "unit_members": inputs["unit_members"],
            "lemma_gloss": gloss,
            "lemma_verses": lemma_verses(inputs["words"], inputs["verses"]),
            "structure": inputs["structure"],
            "map_points": inputs["map_points"],
            "map_clusters": inputs["map_clusters"],
            "book_affinity": inputs["map_book_affinity"],
            "book_examples": inputs["map_book_examples"],
            "stylo_points": inputs["stylo_points"],
            "stylo_delta": inputs["stylo_book_delta"],
            "stylo_features": inputs["stylo_book_features"],
            "sequences": sequence_gold(inputs["sequences"], gold).assign(
                same_chapter=lambda d: d.same_chapter.astype(int)
            ),
            "diff_changes": inputs["diff_changes"],
            "parallelism": inputs["parallelism"],
            "seam_curve": inputs["seam_curve"],
            "seams": inputs["seam_seams"],
            "entities": inputs["entity_entities"],
            "entity_mentions": inputs["entity_mentions"],
            "entity_links": inputs["entity_links"],
            "wordplay": inputs["wordplay"].assign(
                book_id=lambda d: d.a_vid.map(verses.set_index("verse_id").book_id)
            ),
            "phrases": inputs["phrases"].assign(
                a_book=lambda d: d.a.map(verses.set_index("verse_id").book_id),
                b_book=lambda d: d.b.map(verses.set_index("verse_id").book_id),
            ),
        }
        expected = {}
        for table, df in tables.items():
            log(f"  {table}: {len(df)} rows")
            _insert(conn, table, df, batch)
            expected[table] = len(df)

        log("gold links")
        units, members = inputs["units"], inputs["unit_members"]
        pairs = gold
        links = {
            unit_type: unit_links(pairs, units, members, unit_type)
            for unit_type in cfg["units"]["types"]
        }
        found = []
        for unit_type, mode, system, file in files:
            df = pd.read_parquet(file).assign(mode=mode)
            if (df.unit_type != unit_type).any():
                raise RuntimeError(f"{file} holds rows of another unit type")
            for col in ("lex_score", "lex_rank", "sem_score", "sem_rank"):
                if col not in df:
                    df[col] = None
            df = df.merge(links[unit_type], on=["src_id", "tgt_id"], how="left")
            df = df.sort_values(["src_id", "rank"], kind="stable")
            _insert(conn, "matches", df, batch)
            expected[f"matches/{unit_type}/{mode}"] = len(df)
            n_known = int(df.link_level.notna().sum())
            log(f"  matches {unit_type}/{mode} ({system}): {len(df)} rows, {n_known} gold-linked")
            found.append(discoveries(df, units, disc["max_rank"], window))
        found_df = pd.concat(found, ignore_index=True)
        _insert(conn, "discoveries", found_df, batch)
        expected["discoveries"] = len(found_df)
        log(f"  discoveries: {len(found_df)} unlinked pairs")
        conn.commit()

        log("checking row counts, indexing")
        _check_counts(conn, expected)
        for sql in INDEXES:
            conn.execute(sql)
        conn.execute("ANALYZE")
        meta = _meta(cfg, files, expected)
        meta["book_order"] = inputs["map_meta"].get("book_order", [b.book_id for b in BOOKS])
        sm = inputs["stylo_meta"]
        dm = inputs["diffs_meta"]
        meta["diffs"] = {k: dm.get(k) for k in ("verse_pairs", "loose_pairs", "ops")}
        meta["seams"] = {
            "thresholds": inputs["seams_meta"].get("thresholds", {}),
            "block_words": cfg["seams"]["block_words"],
        }
        em = inputs["entities_meta"]
        meta["entities"] = {k: em.get(k) for k in ("names", "kinds", "pairs")}
        wm = inputs["wordplay_meta"]
        meta["wordplay"] = {k: wm.get(k) for k in ("pairs", "null_pairs_per_rep", "kinds")}
        pm = inputs["parallelism_meta"]
        meta["parallelism"] = {
            k: pm.get(k) for k in ("coefficients", "held_out_auc", "known_poems", "book_means")
        } | {"parallel_at": cfg["parallelism"]["parallel_at"]}
        meta["stylometry"] = {
            k: sm.get(k) for k in ("book_order", "axes", "book_words", "features")
        }
        conn.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            [(k, json.dumps(v, ensure_ascii=False)) for k, v in meta.items()],
        )
        conn.commit()
        log("VACUUM")
        conn.execute("VACUUM")
    finally:
        conn.close()
    return meta


def connect_readonly(path: Path, check_same_thread: bool = True) -> sqlite3.Connection:
    return sqlite3.connect(
        f"{path.resolve().as_uri()}?mode=ro", uri=True, check_same_thread=check_same_thread
    )


def benchmark(conn: sqlite3.Connection, cfg: dict[str, Any]) -> dict[str, Any]:
    """Time `similar()` for the spot-check verses x modes (exclude neighbours), in ms."""
    refs = cfg["eval"]["spot_checks"]
    window, runs = cfg["retrieval"]["neighbor_window"], cfg["store"]["bench_queries"]
    ids = [
        f"v:{r[0]}"
        for ref in refs
        if (r := conn.execute("SELECT verse_id FROM verses WHERE ref = ?", (ref,)).fetchone())
    ]
    times = []
    for src in ids:
        for mode in MODES:
            for _ in range(runs):
                t0 = time.perf_counter()
                similar(conn, "verse", mode, src, k=50, exclude=["neighbors"], window=window)
                times.append((time.perf_counter() - t0) * 1000)
    if not times:
        return {"queries": 0}
    return {
        "queries": len(times),
        "median_ms": round(statistics.median(times), 3),
        "max_ms": round(max(times), 3),
    }


def _spot_check(conn: sqlite3.Connection, log: Log) -> None:
    ids = dict(
        conn.execute(
            "SELECT ref, verse_id FROM verses WHERE ref IN ('Psalms 14:1', 'Psalms 53:2')"
        ).fetchall()
    )
    if len(ids) < 2:
        return
    for mode in MODES:
        hits = similar(conn, "verse", mode, f"v:{ids['Psalms 14:1']}", k=10)
        if f"v:{ids['Psalms 53:2']}" not in {h["tgt_id"] for h in hits}:
            log(f"  warning: Psalms 53:2 not in the {mode} top-10 of Psalms 14:1")


def run_build_db(cfg: dict[str, Any], log: Log = print) -> Path:
    db = resolve_path(cfg, "db")
    files = _match_files(cfg)
    inputs = _load_inputs(cfg)
    db.parent.mkdir(parents=True, exist_ok=True)
    tmp = db.with_name(db.name + ".tmp")
    tmp.unlink(missing_ok=True)
    log(f"building {db}")
    try:
        meta = _write_db(tmp, cfg, inputs, files, log)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, db)

    size_mb = db.stat().st_size / 2**20
    conn = connect_readonly(db)
    try:
        bench = benchmark(conn, cfg)
        _spot_check(conn, log)
    finally:
        conn.close()
    conn = sqlite3.connect(db)
    try:
        extra = {"size_mb": round(size_mb, 1), "similar_benchmark": bench}
        conn.executemany(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            [(k, json.dumps(v)) for k, v in extra.items()],
        )
        conn.commit()
    finally:
        conn.close()

    n_matches = sum(v for k, v in meta["row_counts"].items() if k.startswith("matches/"))
    log(f"done: {db} ({size_mb:.0f} MB, {n_matches} matches)")
    if size_mb > cfg["store"]["max_size_mb"]:
        log(f"  warning: size above store.max_size_mb = {cfg['store']['max_size_mb']}")
    if bench.get("queries"):
        log(f"  /similar query: median {bench['median_ms']:.2f} ms, max {bench['max_ms']:.2f} ms")
        if bench["median_ms"] >= 10:
            log("  warning: median /similar query is not under 10 ms")
    return db
