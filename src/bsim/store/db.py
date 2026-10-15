"""`bsim build-db`: processed tables + final top-k lists -> `results.sqlite` (DESIGN.md §9).

The DB is rebuilt from scratch into `{db}.tmp` and moved into place only after every table's row
count matches its source; a failed build leaves any previous DB untouched. Only the final systems
go in (`retrieve/fusion.py:final_systems`: one per mode and unit type).

What goes in, by module:
- here: `books`, `verses`, `words`, `units`, `unit_members`; `matches` (every final list, with
  its Sefaria link) and `discoveries`; `meta` (build, systems, row counts, `similar()` timings).
- `store/lexicon.py`: `lemma_gloss`, `lemma_verses`, `words.in_formula`; `domains`,
  `domain_verses`, `words.domains` + `meta.lexicon` from `bsim lexicon` (empty without it).
- `store/links.py`: `matches.link_level / link_type`, `discoveries`, the gold flags of
  `sequences`.
- `clauses`, `syntax_phrases` + `meta.syntax`: `bsim syntax`; `speech_chapters`, `speech_books`,
  `speakers` from them (`analysis/speech.py`); `syntax_neighbors`: the top `syntax.neighbors` of
  the `syntax.system` verse list. All empty without `bsim syntax`.
- `store/analyses.py`: every analysis stage's tables and meta entries (phrases, sequences,
  diffs, ... stylometry), one `Source` each.
- column names: `store/schema.py`, read from `schema.sql`.

`similar()` is the `/api/similar` query: the stored top-k of one unit with query-time filters in
SQL, matching `retrieve/filters.py`, plus `known` (drop gold-linked hits).
"""

from __future__ import annotations

import json
import os
import sqlite3
import statistics
import time
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from bsim.analysis.speech import speech_tables
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS
from bsim.retrieve.filters import EXCLUDES
from bsim.retrieve.fusion import final_systems
from bsim.retrieve.topk import CSLS_SUFFIX
from bsim.store import analyses
from bsim.store.lexicon import domain_tables, formula_flags, lemma_display_forms, lemma_verses
from bsim.store.links import discoveries, gold_verse_pairs, unit_links
from bsim.store.schema import COLUMNS, SCHEMA

Log = Callable[[str], None]

SYNTAX_TABLES = (
    "clauses",
    "syntax_phrases",
    "syntax_neighbors",
    "speech_chapters",
    "speech_books",
    "speakers",
)
MODES = ("lexical", "semantic", "fused", "structural", "domain", "syntax")
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
    "CREATE INDEX alliteration_by_p ON alliteration (p, verse_id)",
    "CREATE INDEX alliteration_by_verse ON alliteration (verse_id)",
    "CREATE INDEX wordplay_by_vid ON wordplay (a_vid, b_vid)",
    "CREATE INDEX entity_mentions_by_verse ON entity_mentions (verse_id)",
    "CREATE INDEX network_nodes_by_community ON network_nodes (unit_type, community)",
    "CREATE INDEX network_edges_by_a ON network_edges (unit_type, a)",
    "CREATE INDEX domain_verses_by_verse ON domain_verses (verse_id, code)",
    "CREATE INDEX clauses_by_verse ON clauses (verse_id)",
    "CREATE INDEX syntax_phrases_by_verse ON syntax_phrases (verse_id)",
    # the lookups by verse / unit of /dossier and the `unit=` list filters
    "CREATE INDEX diff_changes_by_a ON diff_changes (a)",
    "CREATE INDEX diff_changes_by_b ON diff_changes (b)",
    "CREATE INDEX discoveries_by_b ON discoveries (unit_type, mode, b_id)",
    "CREATE INDEX typescenes_by_a ON typescenes (a_unit)",
    "CREATE INDEX typescenes_by_b ON typescenes (b_unit)",
    "CREATE INDEX seams_by_verse ON seams (verse_id)",
    "CREATE INDEX segment_gaps_by_kind ON segment_gaps (kind, score)",
    "CREATE INDEX segment_gaps_by_book ON segment_gaps (book_id, verse_id)",
    "CREATE INDEX kq_pairs_by_verse ON kq_pairs (verse_id)",
    "CREATE INDEX kq_pairs_by_cls ON kq_pairs (cls, verse_id)",
    "CREATE INDEX citations_by_verse ON citations (verse_id)",
    "CREATE INDEX citations_by_target ON citations (target_vid)",
    "CREATE INDEX allusions_by_a ON allusions (a_start)",
    "CREATE INDEX allusions_by_b ON allusions (b_start)",
    "CREATE INDEX echo_edges_by_a ON echo_edges (a_start)",
    "CREATE INDEX echo_edges_by_b ON echo_edges (b_start)",
    "CREATE INDEX mirror_clauses_by_verse ON mirror_clauses (verse_id)",
    "CREATE INDEX mirror_clauses_by_pair ON mirror_clauses (pair, mirrored)",
    "CREATE INDEX meter_chapters_by_net ON meter_chapters (net DESC)",
    "CREATE INDEX lemma_roots_by_root ON lemma_roots (root)",
    "CREATE INDEX root_pairs_by_verse ON root_pairs (verse_id)",
    "CREATE INDEX root_pairs_by_kind ON root_pairs (kind, verse_id)",
    "CREATE INDEX root_leitworte_by_hidden ON root_leitworte (hidden, g2 DESC)",
    "CREATE INDEX refrains_by_book ON refrains (book_id, refrain_id)",
    "CREATE INDEX refrain_verses_by_verse ON refrain_verses (verse_id)",
    "CREATE INDEX psalm_verses_by_unit ON psalm_verses (unit_id, verse_id)",
    "CREATE INDEX pentateuch_chapters_by_book ON pentateuch_chapters (book_id, chapter)",
    "CREATE INDEX dialogue_pairs_by_book ON dialogue_pairs (book_id, n_quotes DESC)",
    "CREATE INDEX dialogue_exchanges_by_book ON dialogue_exchanges (book_id, verse_id)",
    "CREATE INDEX dialogue_exchanges_by_verse ON dialogue_exchanges (verse_id, last_verse_id)",
    "CREATE INDEX forms_sayings_by_book ON forms_sayings (book_id, verse_id)",
    "CREATE INDEX forms_pairs_by_verse ON forms_pairs (verse_id)",
    "CREATE INDEX forms_lists_by_book ON forms_lists (book_id, first_vid)",
    "CREATE INDEX forms_lists_by_verse ON forms_lists (first_vid, last_vid)",
    # /gematria: what has a value, in each system
    *(
        f"CREATE INDEX gematria_{t}_by_{s} ON gematria_{t} ({s})"
        for t in ("forms", "lemmas", "verses")
        for s in ("standard", "gadol", "ordinal", "katan")
    ),
)
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
    cols = cols or COLUMNS[table]
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
        " m.phr_score, m.phr_rank,"
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


def _syntax_inputs(cfg: dict[str, Any], proc: Path, verses: pd.DataFrame) -> dict[str, Any]:
    """The `bsim syntax` tables and what is derived from them (empty frames without it)."""
    empty = {t: pd.DataFrame(columns=COLUMNS[t]) for t in SYNTAX_TABLES}
    path = proc / "syntax_clauses.parquet"
    if not path.exists():
        return {**empty, "syntax_meta": {}}
    sc = cfg["syntax"]
    clauses = pd.read_parquet(path)
    for col in ("addressee", "addressee_source"):  # from before §16.44
        if col not in clauses.columns:
            clauses[col] = None
    phrases = pd.read_parquet(proc / "syntax_phrases.parquet")
    chapters, books, speakers = speech_tables(clauses, verses, sc["divine"])
    topk = resolve_path(cfg, "artifacts") / "topk" / "verse" / f"{sc['system']}.parquet"
    if topk.exists():
        from bsim.retrieve.topk import read_topk

        nb = read_topk(topk)
        nb = nb[nb["rank"] <= sc["neighbors"]].rename(columns={"src": "verse_id"})
    else:
        nb = empty["syntax_neighbors"]
    as_json = lambda col: [json.dumps([int(i) for i in w]) for w in col]  # noqa: E731
    return {
        "clauses": clauses.assign(words=as_json(clauses.words), rela=clauses.rela.fillna(""))[
            COLUMNS["clauses"]
        ],
        "syntax_phrases": phrases.assign(words=as_json(phrases.words)),
        "syntax_neighbors": nb[COLUMNS["syntax_neighbors"]],
        "speech_chapters": chapters[COLUMNS["speech_chapters"]],
        "speech_books": books[COLUMNS["speech_books"]],
        "speakers": speakers[COLUMNS["speakers"]],
        "syntax_meta": _read_json(proc / "syntax_meta.json"),
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text("utf-8")) if path.exists() else {}


def _load_inputs(cfg: dict[str, Any]) -> dict[str, Any]:
    """The corpus, links, lexicon and syntax inputs; the analyses' frames (`frames`) and meta
    files (`metas`) from `store/analyses.py`."""
    proc = resolve_path(cfg, "data_processed")
    out: dict[str, Any] = {}
    for name in ("verses", "words", "units", "unit_members", "links"):
        path = proc / f"{name}.parquet"
        if not path.exists():
            cmd = "build-links" if name == "links" else "build-corpus"
            raise RuntimeError(f"{path} missing; run `bsim {cmd}` first")
        out[name] = pd.read_parquet(path)
    for name in ("word_senses", "lexicon_domains"):
        path = proc / f"{name}.parquet"
        out[name] = pd.read_parquet(path) if path.exists() else None
    out["lexicon_meta"] = _read_json(proc / "lexicon_meta.json")
    out.update(_syntax_inputs(cfg, proc, out["verses"]))
    out["frames"], out["metas"] = analyses.load(cfg)
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
    unit_phrases: dict[str, float] = {}  # unit type -> the phrase list's weight in its fusion
    for unit_type, mode, system, path in files:
        side = _read_json(path.with_suffix(".meta.json"))
        systems[unit_type][mode] = {
            "system": system,
            "config_hash": side.get("config_hash"),
            "built_at": side.get("built_at"),
        }
        if mode == "fused" and side.get("w_phr") is not None:
            unit_phrases[unit_type] = side["w_phr"]
    return {
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "config_hash": config_hash(cfg, "retrieval", "fusion", "final_systems", "lexical"),
        "oshb_commit": cfg["sources"]["oshb"]["commit"],
        "corpus_config_hash": corpus.get("config_hash"),
        "text_version": cfg["sources"]["sefaria"]["text_version"],
        "text_license": "CC-BY-SA (Sefaria, Miqra according to the Masorah)",
        "systems": dict(systems),
        "fusion": {k: cfg["fusion"][k] for k in ("w_lex", "w_sem", "rrf_k")}
        | {"unit_phrases": unit_phrases},
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
            columns=COLUMNS["books"],
        )
        verses = verses.assign(
            display_tokens=[json.dumps(list(t), ensure_ascii=False) for t in verses.display_tokens]
        )
        log("formula flags and lemma display forms")
        words = words.assign(
            content_lemmas=[" ".join(c) for c in words.content_lemmas],
            in_formula=formula_flags(words, len(verses), cfg["lexical"]["formulas"]).astype(int),
        )
        word_domains, domain_verses, domains = domain_tables(
            inputs["word_senses"], inputs["words"], inputs["lexicon_domains"]
        )
        words = words.assign(domains=word_domains)
        gloss = lemma_display_forms(inputs["words"])
        gold = gold_verse_pairs(inputs["links"])
        ctx = analyses.Context(cfg, inputs["verses"], gold)
        tables = {
            "books": books,
            "verses": verses,
            "words": words,
            "units": inputs["units"],
            "unit_members": inputs["unit_members"],
            "lemma_gloss": gloss,
            "lemma_verses": lemma_verses(inputs["words"], inputs["verses"]),
            "domains": domains,
            "domain_verses": domain_verses,
            **{t: inputs[t] for t in SYNTAX_TABLES},
            **analyses.tables(inputs["frames"], ctx),
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
            for col in ("lex_score", "lex_rank", "sem_score", "sem_rank", "phr_score", "phr_rank"):
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
        meta |= analyses.meta(inputs["metas"], cfg)
        meta["syntax"] = inputs["syntax_meta"]
        lm = inputs["lexicon_meta"]
        meta["lexicon"] = {
            k: lm.get(k)
            for k in ("refs", "matched", "lemma_morphemes", "tagged_sdbh", "tagged_lemma")
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
