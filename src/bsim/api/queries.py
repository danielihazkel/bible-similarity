"""Read-only SQL helpers over `results.sqlite` for the API routes (schema: DESIGN.md §9)."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

UNIT_COLS = (
    "unit_id, unit_type, label_en, label_he, book_id, start_verse_id, end_verse_id, n_verses,"
    " marker"
)
VERSE_COLS = "verse_id, book_id, chapter, verse, ref, text_display, display_tokens, ketiv_note"


def _dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r, strict=True)) for r in cur.fetchall()]


def _marks(n: int) -> str:
    return ", ".join("?" * n)


def books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM books ORDER BY book_id"))


def meta(conn: sqlite3.Connection) -> dict[str, Any]:
    return {k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM meta")}


def n_verses(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM verses").fetchone()[0]


def units_of_type(
    conn: sqlite3.Connection, unit_type: str, book_id: int | None = None
) -> list[dict[str, Any]]:
    sql, args = f"SELECT {UNIT_COLS} FROM units WHERE unit_type = ?", [unit_type]
    if book_id is not None:
        sql += " AND book_id = ?"
        args.append(book_id)
    return _dicts(conn.execute(sql + " ORDER BY start_verse_id", args))


def units_by_id(conn: sqlite3.Connection, ids: Iterable[str]) -> dict[str, dict[str, Any]]:
    ids = list(dict.fromkeys(ids))
    if not ids:
        return {}
    cur = conn.execute(f"SELECT {UNIT_COLS} FROM units WHERE unit_id IN ({_marks(len(ids))})", ids)
    return {u["unit_id"]: u for u in _dicts(cur)}


def unit(conn: sqlite3.Connection, unit_id: str) -> dict[str, Any] | None:
    return units_by_id(conn, [unit_id]).get(unit_id)


def _verse(row: dict[str, Any]) -> dict[str, Any]:
    return {**row, "display_tokens": json.loads(row["display_tokens"])}


def verse_range(conn: sqlite3.Connection, start: int, end: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        f"SELECT {VERSE_COLS} FROM verses WHERE verse_id BETWEEN ? AND ? ORDER BY verse_id",
        (start, end),
    )
    return [_verse(r) for r in _dicts(cur)]


def verses_by_id(conn: sqlite3.Connection, ids: Iterable[int]) -> dict[int, dict[str, Any]]:
    ids = list(dict.fromkeys(int(i) for i in ids))
    if not ids:
        return {}
    cur = conn.execute(
        f"SELECT {VERSE_COLS} FROM verses WHERE verse_id IN ({_marks(len(ids))})", ids
    )
    return {r["verse_id"]: _verse(r) for r in _dicts(cur)}


def verse_labels(conn: sqlite3.Connection, ids: Iterable[int]) -> dict[int, tuple[str, str]]:
    """verse_id -> (label_en, label_he) of its verse unit."""
    keys = [f"v:{int(i)}" for i in ids]
    return {
        int(u["unit_id"][2:]): (u["label_en"], u["label_he"])
        for u in units_by_id(conn, keys).values()
    }


def parents(conn: sqlite3.Connection, u: dict[str, Any]) -> list[dict[str, Any]]:
    """Units of the other types containing the unit's first verse (canon order of types)."""
    cur = conn.execute(
        f"SELECT {', '.join('u.' + c.strip() for c in UNIT_COLS.split(','))}"
        " FROM unit_members m JOIN units u ON u.unit_id = m.unit_id"
        " WHERE m.verse_id = ? AND u.unit_type != ?"
        " ORDER BY u.n_verses",
        (u["start_verse_id"], u["unit_type"]),
    )
    return _dicts(cur)


def neighbours(conn: sqlite3.Connection, u: dict[str, Any]) -> tuple[str | None, str | None]:
    """(previous, next) unit id of the same type, in canon order."""
    prev = conn.execute(
        "SELECT unit_id FROM units WHERE unit_type = ? AND start_verse_id < ?"
        " ORDER BY start_verse_id DESC LIMIT 1",
        (u["unit_type"], u["start_verse_id"]),
    ).fetchone()
    nxt = conn.execute(
        "SELECT unit_id FROM units WHERE unit_type = ? AND start_verse_id > ?"
        " ORDER BY start_verse_id LIMIT 1",
        (u["unit_type"], u["start_verse_id"]),
    ).fetchone()
    return (prev[0] if prev else None), (nxt[0] if nxt else None)


def previews(conn: sqlite3.Connection, start_ids: Iterable[int], chars: int) -> dict[int, str]:
    """First verse's display text (cut at a word boundary near `chars`) by verse_id."""
    out = {}
    for vid, v in verses_by_id(conn, start_ids).items():
        text = v["text_display"]
        if len(text) > chars:
            cut = text.rfind(" ", 0, chars)
            text = text[: cut if cut > 0 else chars] + " …"
        out[vid] = text
    return out


def words(
    conn: sqlite3.Connection, verse_ids: Iterable[int], detail: bool = False
) -> list[dict[str, Any]]:
    """`words` rows in order; `detail` adds surface, raw lemma and morph."""
    ids = list(dict.fromkeys(int(i) for i in verse_ids))
    if not ids:
        return []
    extra = ", surface, lemma, morph" if detail else ""
    cur = conn.execute(
        f"SELECT verse_id, idx, display_idx, content_lemmas, in_formula{extra} FROM words"
        f" WHERE verse_id IN ({_marks(len(ids))}) ORDER BY verse_id, idx",
        ids,
    )
    return _dicts(cur)


def verse_lemmas(rows: list[dict[str, Any]]) -> dict[int, list[str]]:
    """verse_id -> distinct content lemmas in word order, from `words()` rows."""
    out: dict[int, dict[str, None]] = defaultdict(dict)
    for w in rows:
        out[w["verse_id"]].update(dict.fromkeys(w["content_lemmas"].split()))
    return {v: list(lems) for v, lems in out.items()}


def gloss(conn: sqlite3.Connection, lemmas: Iterable[str]) -> dict[str, str]:
    lemmas = sorted(set(lemmas))
    if not lemmas:
        return {}
    cur = conn.execute(
        f"SELECT lemma, he_lemma FROM lemma_gloss WHERE lemma IN ({_marks(len(lemmas))})", lemmas
    )
    return dict(cur.fetchall())


def discoveries(
    conn: sqlite3.Connection,
    unit_type: str,
    mode: str,
    book_id: int | None,
    cross_book: bool,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """(total, page) of `discoveries` rows, strongest first."""
    where, args = "unit_type = ? AND mode = ?", [unit_type, mode]
    if book_id is not None:
        where += " AND (a_book = ? OR b_book = ?)"
        args += [book_id, book_id]
    if cross_book:
        where += " AND a_book != b_book"
    total = conn.execute(f"SELECT COUNT(*) FROM discoveries WHERE {where}", args).fetchone()[0]
    cur = conn.execute(
        "SELECT a_id, b_id, score, tie, rank_ab, rank_ba FROM discoveries"
        f" WHERE {where} ORDER BY score DESC, tie DESC, a_id, b_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def lemma_stats(conn: sqlite3.Connection, lemmas: Iterable[str]) -> dict[str, dict[str, Any]]:
    lemmas = sorted(set(lemmas))
    if not lemmas:
        return {}
    cur = conn.execute(
        "SELECT lemma, he_lemma, n_words, n_verses, pos FROM lemma_gloss"
        f" WHERE lemma IN ({_marks(len(lemmas))})",
        lemmas,
    )
    return {r["lemma"]: r for r in _dicts(cur)}


def verse_at(conn: sqlite3.Connection, book_id: int, chapter: int, verse: int) -> int | None:
    row = conn.execute(
        "SELECT verse_id FROM verses WHERE book_id = ? AND chapter = ? AND verse = ?",
        (book_id, chapter, verse),
    ).fetchone()
    return row[0] if row else None


def lemma_books(conn: sqlite3.Connection, lemma: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT book_id, COUNT(*) AS n_verses FROM lemma_verses WHERE lemma = ?"
        " GROUP BY book_id ORDER BY book_id",
        (lemma,),
    )
    return _dicts(cur)


def lemma_page(
    conn: sqlite3.Connection, lemma: str, book_id: int | None, limit: int, offset: int
) -> list[int]:
    """Verse ids containing `lemma` (in one book, if given), canon order."""
    sql, args = "SELECT verse_id FROM lemma_verses WHERE lemma = ?", [lemma]
    if book_id is not None:
        sql += " AND book_id = ?"
        args.append(book_id)
    cur = conn.execute(sql + " ORDER BY verse_id LIMIT ? OFFSET ?", [*args, limit, offset])
    return [r[0] for r in cur.fetchall()]


PHRASE_COLS = "a, b, score, n_tokens, a_words, b_words, spread"
SEQUENCE_COLS = (
    "seq_id, a_start, a_end, b_start, b_end, a_book, b_book, same_chapter, n_pairs, score, q,"
    " n_gold"
)


def sequences_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    cross_book: bool,
    hide_same_chapter: bool,
    max_q: float | None,
    min_pairs: int,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Chains, strongest first; `span` = (first, last) verse id: chains touching it."""
    where, args = "n_pairs >= ?", [min_pairs]
    if max_q is not None:
        where += " AND q <= ?"
        args.append(max_q)
    if book_id is not None:
        where += " AND (a_book = ? OR b_book = ?)"
        args += [book_id, book_id]
    if cross_book:
        where += " AND a_book != b_book"
    if hide_same_chapter:
        where += " AND same_chapter = 0"
    if span is not None:
        where += " AND ((a_start <= ? AND a_end >= ?) OR (b_start <= ? AND b_end >= ?))"
        args += [span[1], span[0], span[1], span[0]]
    total = conn.execute(f"SELECT COUNT(*) FROM sequences WHERE {where}", args).fetchone()[0]
    cur = conn.execute(
        f"SELECT {SEQUENCE_COLS} FROM sequences WHERE {where}"
        " ORDER BY score DESC, seq_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def _change_filter(op: str, a_book: int | None, b_book: int | None) -> tuple[str, list[Any]]:
    # a moved word has a row on each side: count the A side only
    where, args = "op = ?" + (" AND a_idx IS NOT NULL" if op == "moved" else ""), [op]
    if a_book is not None:
        where += " AND a_book = ?"
        args.append(a_book)
    if b_book is not None:
        where += " AND b_book = ?"
        args.append(b_book)
    return where, args


# spelling / form changes keep the lemma: they are grouped by the written forms instead
FORM_OPS = ("spelling", "form")


def _group_cols(op: str) -> tuple[str, str]:
    return ("a_form", "b_form") if op in FORM_OPS else ("a_key", "b_key")


def change_groups(
    conn: sqlite3.Connection,
    op: str,
    a_book: int | None,
    b_book: int | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """(number of groups, groups) of `diff_changes` by word key (by written form for spelling /
    form changes), most frequent first; the non-grouping pair of columns is None."""
    where, args = _change_filter(op, a_book, b_book)
    ca, cb = _group_cols(op)
    total = conn.execute(
        f"SELECT COUNT(*) FROM (SELECT 1 FROM diff_changes WHERE {where} GROUP BY {ca}, {cb})",
        args,
    ).fetchone()[0]
    other = "NULL AS a_key, NULL AS b_key" if op in FORM_OPS else "NULL AS a_form, NULL AS b_form"
    cur = conn.execute(
        f"SELECT {ca}, {cb}, {other}, COUNT(*) AS count, COUNT(DISTINCT seq_id) AS n_sequences"
        f" FROM diff_changes WHERE {where} GROUP BY {ca}, {cb}"
        f" ORDER BY count DESC, n_sequences DESC, {ca}, {cb} LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def change_examples(
    conn: sqlite3.Connection,
    op: str,
    a_book: int | None,
    b_book: int | None,
    a_value: str | None,
    b_value: str | None,
    n: int,
) -> list[dict[str, Any]]:
    """Example verse pairs of one group (`a_value, b_value` = its grouping columns)."""
    where, args = _change_filter(op, a_book, b_book)
    ca, cb = _group_cols(op)
    cur = conn.execute(
        f"SELECT DISTINCT seq_id, a, b FROM diff_changes WHERE {where}"
        f" AND {ca} IS ? AND {cb} IS ? ORDER BY seq_id, a LIMIT ?",
        [*args, a_value, b_value, n],
    )
    return _dicts(cur)


def change_totals(
    conn: sqlite3.Connection, a_book: int | None, b_book: int | None
) -> dict[str, int]:
    """Changes per op under the book filters (moved words counted once)."""
    where, args = "(op != 'moved' OR a_idx IS NOT NULL)", []
    if a_book is not None:
        where += " AND a_book = ?"
        args.append(a_book)
    if b_book is not None:
        where += " AND b_book = ?"
        args.append(b_book)
    cur = conn.execute(f"SELECT op, COUNT(*) FROM diff_changes WHERE {where} GROUP BY op", args)
    return dict(cur.fetchall())


PARALLEL_COLS = "verse_id, n_cola, cola, pauses, cos, shared, shape, balance, prob"


def parallelism_verses(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        f"SELECT {PARALLEL_COLS} FROM parallelism WHERE verse_id BETWEEN ? AND ? ORDER BY verse_id",
        (first, last),
    )
    return _dicts(cur)


def parallelism_units(
    conn: sqlite3.Connection,
    unit_type: str,
    book_id: int | None,
    skip_books: list[int],
    parallel_at: float,
    min_verses: int,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Units ranked by the mean parallelism probability of their scored verses."""
    where, args = "u.unit_type = ?", [unit_type]
    if book_id is not None:
        where += " AND u.book_id = ?"
        args.append(book_id)
    if skip_books:
        where += f" AND u.book_id NOT IN ({_marks(len(skip_books))})"
        args += skip_books
    inner = (
        "SELECT u.unit_id, AVG(p.prob) AS mean_prob, COUNT(p.prob) AS n_scored,"
        " AVG(CASE WHEN p.prob IS NULL THEN NULL WHEN p.prob >= ? THEN 1.0 ELSE 0.0 END)"
        " AS share_parallel, MIN(u.start_verse_id) AS start"
        " FROM units u JOIN parallelism p"
        " ON p.verse_id BETWEEN u.start_verse_id AND u.end_verse_id"
        f" WHERE {where} GROUP BY u.unit_id HAVING COUNT(p.prob) >= ?"
    )
    iargs = [parallel_at, *args, min_verses]
    total = conn.execute(f"SELECT COUNT(*) FROM ({inner})", iargs).fetchone()[0]
    cur = conn.execute(
        f"{inner} ORDER BY mean_prob DESC, start LIMIT ? OFFSET ?", [*iargs, limit, offset]
    )
    return total, _dicts(cur)


def parallelism_books(conn: sqlite3.Connection, parallel_at: float) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT v.book_id, AVG(p.prob) AS mean_prob, COUNT(p.prob) AS n_scored,"
        " AVG(CASE WHEN p.prob IS NULL THEN NULL WHEN p.prob >= ? THEN 1.0 ELSE 0.0 END)"
        " AS share_parallel"
        " FROM parallelism p JOIN verses v ON v.verse_id = p.verse_id"
        " GROUP BY v.book_id ORDER BY v.book_id",
        (parallel_at,),
    )
    return _dicts(cur)


WORDPLAY_COLS = (
    "w.a_vid, w.a_idx, w.b_vid, w.b_idx, w.a_lemma, w.b_lemma, w.a_form, w.b_form, w.kind,"
    " w.gap, w.score, w.q, wa.display_idx AS a_display, wb.display_idx AS b_display"
)


def wordplay_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    kind: str | None,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Sound-alike pairs, strongest first; `span` = (first, last) verse id the pair touches."""
    where, args = "1 = 1", []
    if book_id is not None:
        where += " AND w.book_id = ?"
        args.append(book_id)
    if kind is not None:
        where += " AND w.kind = ?"
        args.append(kind)
    if span is not None:
        where += " AND w.b_vid >= ? AND w.a_vid <= ?"
        args += [span[0], span[1]]
    total = conn.execute(f"SELECT COUNT(*) FROM wordplay w WHERE {where}", args).fetchone()[0]
    cur = conn.execute(
        f"SELECT {WORDPLAY_COLS} FROM wordplay w"
        " LEFT JOIN words wa ON wa.verse_id = w.a_vid AND wa.idx = w.a_idx"
        " LEFT JOIN words wb ON wb.verse_id = w.b_vid AND wb.idx = w.b_idx"
        f" WHERE {where} ORDER BY w.score DESC, w.a_vid, w.a_idx LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def sequence(conn: sqlite3.Connection, seq_id: int) -> dict[str, Any] | None:
    cur = conn.execute(f"SELECT {SEQUENCE_COLS}, pairs FROM sequences WHERE seq_id = ?", (seq_id,))
    rows = _dicts(cur)
    return rows[0] if rows else None


def phrases_of(conn: sqlite3.Connection, verse_id: int) -> list[dict[str, Any]]:
    """Phrase rows involving `verse_id`, strongest first."""
    cur = conn.execute(
        f"SELECT {PHRASE_COLS} FROM phrases WHERE a = ? OR b = ? ORDER BY score DESC, a, b",
        (verse_id, verse_id),
    )
    return _dicts(cur)


def phrases_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    cross_book: bool,
    min_tokens: int,
    max_spread: int | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    where, args = "n_tokens >= ?", [min_tokens]
    if max_spread is not None:
        where += " AND spread <= ?"
        args.append(max_spread)
    if book_id is not None:
        where += " AND (a_book = ? OR b_book = ?)"
        args += [book_id, book_id]
    if cross_book:
        where += " AND a_book != b_book"
    total = conn.execute(f"SELECT COUNT(*) FROM phrases WHERE {where}", args).fetchone()[0]
    cur = conn.execute(
        f"SELECT {PHRASE_COLS} FROM phrases WHERE {where}"
        " ORDER BY score DESC, a, b LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def verse_links(conn: sqlite3.Connection, pairs: Iterable[tuple[int, int]]) -> dict:
    """(src, tgt) verse pair -> (link_level, link_type) from any stored verse match row."""
    out = {}
    for a, b in pairs:
        row = conn.execute(
            "SELECT link_level, link_type FROM matches WHERE unit_type = 'verse'"
            " AND src_id = ? AND tgt_id = ? AND link_level IS NOT NULL LIMIT 1",
            (f"v:{a}", f"v:{b}"),
        ).fetchone()
        if row:
            out[(a, b)] = row
    return out


STRUCTURE_SORT = {
    "semantic_chiasm": "semantic_chiasm_pct DESC, semantic_chiasm_z DESC",
    "lexical_chiasm": "lexical_chiasm_pct DESC, lexical_chiasm_z DESC",
    "semantic_inclusio": "semantic_inclusio_pct DESC, semantic_inclusio DESC",
    "lexical_inclusio": "lexical_inclusio_pct DESC, lexical_inclusio DESC",
}


def structure_page(
    conn: sqlite3.Connection, unit_type: str, by: str, min_verses: int, limit: int, offset: int
) -> tuple[int, list[dict[str, Any]]]:
    """Units ranked by one structure score (units without that score left out)."""
    score = by + "_pct"
    where = f"unit_type = ? AND n_verses >= ? AND {score} IS NOT NULL"
    args: list[Any] = [unit_type, min_verses]
    total = conn.execute(f"SELECT COUNT(*) FROM structure WHERE {where}", args).fetchone()[0]
    cur = conn.execute(
        f"SELECT * FROM structure WHERE {where} ORDER BY {STRUCTURE_SORT[by]}, unit_id"
        " LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def corpus_lemma_total(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT SUM(n_words) FROM lemma_gloss").fetchone()[0] or 0


def map_points(conn: sqlite3.Connection, unit_type: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT p.unit_id, u.label_en, u.label_he, u.book_id, u.n_verses, p.x, p.y, p.cluster"
        " FROM map_points p JOIN units u ON u.unit_id = p.unit_id"
        " WHERE p.unit_type = ? ORDER BY u.start_verse_id",
        (unit_type,),
    )
    return _dicts(cur)


def map_clusters(conn: sqlite3.Connection, unit_type: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT cluster, size, lemmas FROM map_clusters WHERE unit_type = ? ORDER BY cluster",
        (unit_type,),
    )
    return [{**r, "lemmas": json.loads(r["lemmas"])} for r in _dicts(cur)]


def book_affinity(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM book_affinity ORDER BY a_book, b_book"))


def book_examples(conn: sqlite3.Connection, a: int, b: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT a_vid, b_vid, score FROM book_examples WHERE a_book = ? AND b_book = ?"
        " ORDER BY rank",
        (min(a, b), max(a, b)),
    )
    return _dicts(cur)


def stylo_points(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT p.unit_id, u.label_en, u.label_he, u.book_id, p.n_words, p.x, p.y"
        " FROM stylo_points p JOIN units u ON u.unit_id = p.unit_id ORDER BY u.start_verse_id"
    )
    return _dicts(cur)


def stylo_delta(conn: sqlite3.Connection, book: int | None = None) -> list[dict[str, Any]]:
    sql, args = "SELECT a_book, b_book, delta FROM stylo_delta", []
    if book is not None:
        sql += " WHERE a_book = ? OR b_book = ?"
        args = [book, book]
    return _dicts(conn.execute(sql + " ORDER BY delta", args))


def stylo_features(conn: sqlite3.Connection, book: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT side, feature, label, rate, z FROM stylo_features WHERE book_id = ? ORDER BY rank",
        (book,),
    )
    return _dicts(cur)
