"""Read-only SQL helpers over `results.sqlite` for the API routes (schema: DESIGN.md §9)."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from bsim.store.db import MODES

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
    groups: list[tuple[str | None, str | None]],
    n: int,
) -> dict[tuple[str | None, str | None], list[dict[str, Any]]]:
    """Up to `n` example verse pairs of each group (`groups`: values of its grouping columns),
    in one query."""
    out: dict[tuple[str | None, str | None], list[dict[str, Any]]] = {g: [] for g in groups}
    if not groups:
        return out
    where, args = _change_filter(op, a_book, b_book)
    ca, cb = _group_cols(op)
    values = ", ".join("(?, ?)" for _ in groups)
    cur = conn.execute(
        f"WITH g(ga, gb) AS (VALUES {values}),"
        f" d AS (SELECT DISTINCT g.ga, g.gb, c.seq_id, c.a, c.b FROM diff_changes c"
        f" JOIN g ON c.{ca} IS g.ga AND c.{cb} IS g.gb WHERE {where}),"
        " r AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY ga, gb ORDER BY seq_id, a, b) AS rn"
        " FROM d)"
        " SELECT ga, gb, seq_id, a, b FROM r WHERE rn <= ? ORDER BY ga, gb, rn",
        [*(v for g in groups for v in g), *args, n],
    )
    for ga, gb, seq_id, a, b in cur:
        out[(ga, gb)].append({"seq_id": seq_id, "a": a, "b": b})
    return out


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


ENTITY_COLS = "lemma, he, kind, n_mentions, n_verses, first_vid, last_vid"


def entities_page(
    conn: sqlite3.Connection,
    kind: str | None,
    book_id: int | None,
    text: str | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Names, most mentioned first (in `book_id` when given: mentions there)."""
    where, args = "1 = 1", []
    if kind is not None:
        where += " AND e.kind = ?"
        args.append(kind)
    if text:
        where += " AND e.he LIKE ?"
        args.append(f"%{text}%")
    if book_id is None:
        base = f"SELECT e.*, e.n_mentions AS n_here FROM entities e WHERE {where}"
        bargs: list[Any] = args
    else:
        base = (
            "SELECT e.*, SUM(m.n) AS n_here FROM entities e"
            " JOIN entity_mentions m ON m.lemma = e.lemma"
            " JOIN verses v ON v.verse_id = m.verse_id"
            f" WHERE {where} AND v.book_id = ? GROUP BY e.lemma"
        )
        bargs = [*args, book_id]
    total = conn.execute(f"SELECT COUNT(*) FROM ({base})", bargs).fetchone()[0]
    cur = conn.execute(
        f"SELECT {ENTITY_COLS}, n_here FROM ({base}) ORDER BY n_here DESC, lemma LIMIT ? OFFSET ?",
        [*bargs, limit, offset],
    )
    return total, _dicts(cur)


def entity(conn: sqlite3.Connection, lemma: str) -> dict[str, Any] | None:
    rows = _dicts(conn.execute(f"SELECT {ENTITY_COLS} FROM entities WHERE lemma = ?", (lemma,)))
    return rows[0] if rows else None


def entity_books(conn: sqlite3.Connection, lemma: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT v.book_id, COUNT(*) AS n FROM entity_mentions m"
        " JOIN verses v ON v.verse_id = m.verse_id WHERE m.lemma = ?"
        " GROUP BY v.book_id ORDER BY v.book_id",
        (lemma,),
    )
    return _dicts(cur)


def entity_partners(conn: sqlite3.Connection, lemma: str, limit: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT l.b AS lemma, e.he, e.kind, l.n_verses, l.expected, l.g2 FROM entity_links l"
        " JOIN entities e ON e.lemma = l.b WHERE l.a = ? ORDER BY l.g2 DESC, l.b LIMIT ?",
        (lemma, limit),
    )
    return _dicts(cur)


def entity_links_among(conn: sqlite3.Connection, lemmas: list[str]) -> list[dict[str, Any]]:
    """Stored links whose two ends are both in `lemmas` (a < b)."""
    if not lemmas:
        return []
    marks = _marks(len(lemmas))
    cur = conn.execute(
        f"SELECT a, b, n_verses, g2 FROM entity_links WHERE a IN ({marks}) AND b IN ({marks})"
        " AND a < b",
        [*lemmas, *lemmas],
    )
    return _dicts(cur)


def unit_entities(
    conn: sqlite3.Connection, first: int, last: int, limit: int
) -> list[dict[str, Any]]:
    cur = conn.execute(
        f"SELECT {', '.join('e.' + c.strip() for c in ENTITY_COLS.split(','))}, SUM(m.n) AS n_here"
        " FROM entity_mentions m JOIN entities e ON e.lemma = m.lemma"
        " WHERE m.verse_id BETWEEN ? AND ? GROUP BY e.lemma ORDER BY n_here DESC, e.lemma LIMIT ?",
        (first, last, limit),
    )
    return _dicts(cur)


def seam_curve(conn: sqlite3.Connection, book_id: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT c.verse_id, c.shift, v.chapter, v.verse FROM seam_curve c"
        " JOIN verses v ON v.verse_id = c.verse_id WHERE c.book_id = ? ORDER BY c.verse_id",
        (book_id,),
    )
    return _dicts(cur)


def seams_of(
    conn: sqlite3.Connection, book_id: int | None, limit: int, offset: int = 0
) -> list[dict[str, Any]]:
    """A book's seams by rank, or the strongest seams of all books (by shift / threshold)."""
    if book_id is not None:
        sql, args = "SELECT * FROM seams WHERE book_id = ? ORDER BY rank", [book_id]
    else:
        sql, args = "SELECT * FROM seams ORDER BY shift / threshold DESC, book_id, rank", []
    return _dicts(conn.execute(sql + " LIMIT ? OFFSET ?", [*args, limit, offset]))


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
    pairs = set(pairs)
    if not pairs:
        return {}
    srcs = sorted({f"v:{a}" for a, _ in pairs})
    cur = conn.execute(
        "SELECT src_id, tgt_id, link_level, link_type FROM matches WHERE unit_type = 'verse'"
        f" AND mode IN ({_marks(len(MODES))}) AND src_id IN ({_marks(len(srcs))})"
        " AND link_level IS NOT NULL",
        [*MODES, *srcs],
    )
    out = {}
    for src, tgt, level, types in cur:
        key = (int(src[2:]), int(tgt[2:]))
        if key in pairs and key not in out:
            out[key] = (level, types)
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


def acrostics_page(
    conn: sqlite3.Connection, max_q: float | None, book_id: int | None, limit: int, offset: int
) -> tuple[int, list[dict[str, Any]]]:
    """Chapters by their best alphabetic chain: lowest q, then highest score."""
    where, args = "1 = 1", []
    if max_q is not None:
        where += " AND q <= ?"
        args.append(max_q)
    if book_id is not None:
        where += " AND book_id = ?"
        args.append(book_id)
    total = conn.execute(f"SELECT COUNT(*) FROM acrostics WHERE {where}", args).fetchone()[0]
    cur = conn.execute(
        f"SELECT * FROM acrostics WHERE {where} ORDER BY q, score DESC, unit_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def acrostic(conn: sqlite3.Connection, unit_id: str) -> dict[str, Any] | None:
    rows = _dicts(conn.execute("SELECT * FROM acrostics WHERE unit_id = ?", (unit_id,)))
    return rows[0] if rows else None


def rewrites_page(
    conn: sqlite3.Connection,
    a_book: int | None,
    b_book: int | None,
    op: str | None,
    max_q: float | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Systematic changes between book pairs, strongest (lowest q, highest G²) first."""
    where, args = "1 = 1", []
    for col, cmp, val in (
        ("a_book", "=", a_book),
        ("b_book", "=", b_book),
        ("op", "=", op),
        ("q", "<=", max_q),
    ):
        if val is not None:
            where += f" AND {col} {cmp} ?"
            args.append(val)
    total = conn.execute(f"SELECT COUNT(*) FROM rewrites WHERE {where}", args).fetchone()[0]
    cur = conn.execute(
        f"SELECT * FROM rewrites WHERE {where} ORDER BY q, g2 DESC, a_book, b_book, a_key, b_key"
        " LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def rewrite_profiles(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(
        conn.execute("SELECT * FROM rewrite_profiles ORDER BY verse_pairs DESC, a_book, b_book")
    )
