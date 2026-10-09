"""Read-only SQL helpers over `results.sqlite` for the API routes (schema: DESIGN.md §9)."""

from __future__ import annotations

import json
import sqlite3
import threading
from collections import OrderedDict, defaultdict
from collections.abc import Iterable
from typing import Any

from bsim.data.canon import BOOKS, hebrew_numeral
from bsim.store.db import MODES

UNIT_COLS = (
    "unit_id, unit_type, label_en, label_he, book_id, start_verse_id, end_verse_id, n_verses,"
    " marker"
)
VERSE_COLS = "verse_id, book_id, chapter, verse, ref, text_display, display_tokens, ketiv_note"


def _dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r, strict=True)) for r in cur.fetchall()]


_COUNTS: OrderedDict[tuple, int] = OrderedDict()
_COUNTS_MAX = 2048
_COUNTS_LOCK = threading.Lock()


def count(conn: sqlite3.Connection, sql: str, args: Iterable[Any] = ()) -> int:
    """`SELECT COUNT(*) ...` of a list page, cached: the served DB is read-only, so a count only
    depends on the DB file, the query and its arguments (list totals repeat on every page)."""
    db = conn.execute("PRAGMA database_list").fetchone()[2]
    key = (db, sql, tuple(args))
    with _COUNTS_LOCK:
        if key in _COUNTS:
            _COUNTS.move_to_end(key)
            return _COUNTS[key]
    n = conn.execute(sql, list(key[2])).fetchone()[0]
    with _COUNTS_LOCK:
        _COUNTS[key] = n
        while len(_COUNTS) > _COUNTS_MAX:
            _COUNTS.popitem(last=False)
    return n


def _marks(n: int) -> str:
    return ", ".join("?" * n)


def books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM books ORDER BY book_id"))


def meta(conn: sqlite3.Connection) -> dict[str, Any]:
    return {k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM meta")}


def n_verses(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM verses").fetchone()[0]


def units_of_type(
    conn: sqlite3.Connection, unit_type: str, book_id: int | None = None, chapter: int | None = None
) -> list[dict[str, Any]]:
    """Units of a type, optionally of one book, and of one chapter (by their first verse)."""
    sql, args = f"SELECT {UNIT_COLS} FROM units WHERE unit_type = ?", [unit_type]
    if book_id is not None:
        sql += " AND book_id = ?"
        args.append(book_id)
    if chapter is not None:
        sql += (
            " AND start_verse_id IN (SELECT verse_id FROM verses WHERE book_id = ? AND chapter = ?)"
        )
        args += [book_id, chapter]
    return _dicts(conn.execute(sql + " ORDER BY start_verse_id", args))


def units_by_id(conn: sqlite3.Connection, ids: Iterable[str]) -> dict[str, dict[str, Any]]:
    ids = list(dict.fromkeys(ids))
    if not ids:
        return {}
    cur = conn.execute(f"SELECT {UNIT_COLS} FROM units WHERE unit_id IN ({_marks(len(ids))})", ids)
    return {u["unit_id"]: u for u in _dicts(cur)}


def unit(conn: sqlite3.Connection, unit_id: str) -> dict[str, Any] | None:
    return units_by_id(conn, [unit_id]).get(unit_id)


def ref_he(book_id: int, chapter: int, verse: int) -> str:
    """Hebrew reference of a verse, e.g. "בראשית א:א" (the stored `ref` is English)."""
    return f"{BOOKS[book_id].he} {hebrew_numeral(chapter)}:{hebrew_numeral(verse)}"


def _verse(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "ref_he": ref_he(row["book_id"], row["chapter"], row["verse"]),
        "display_tokens": json.loads(row["display_tokens"]),
    }


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
    extra = ", surface, lemma, morph, domains" if detail else ""
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
    unit_id: str | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """(total, page) of `discoveries` rows, strongest first; `unit_id`: the pairs it is in."""
    where, args = "unit_type = ? AND mode = ?", [unit_type, mode]
    if unit_id is not None:
        where += " AND (a_id = ? OR b_id = ?)"
        args += [unit_id, unit_id]
    if book_id is not None:
        where += " AND (a_book = ? OR b_book = ?)"
        args += [book_id, book_id]
    if cross_book:
        where += " AND a_book != b_book"
    total = count(conn, f"SELECT COUNT(*) FROM discoveries WHERE {where}", args)
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


def domains(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT code, level, parent, label_en, n_verses, weight FROM domains ORDER BY code"
    )
    return _dicts(cur)


def _domain_range(code: str) -> tuple[str, str]:
    """A domain and its subdomains: the codes it prefixes (codes are digits; `~` sorts after)."""
    return code, code + "~"


def domain_books(conn: sqlite3.Connection, code: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT v.book_id, COUNT(DISTINCT d.verse_id) AS n_verses FROM domain_verses d"
        " JOIN verses v ON v.verse_id = d.verse_id WHERE d.code >= ? AND d.code < ?"
        " GROUP BY v.book_id ORDER BY v.book_id",
        _domain_range(code),
    )
    return _dicts(cur)


def domain_page(
    conn: sqlite3.Connection, code: str, book_id: int | None, limit: int, offset: int
) -> list[tuple[int, float]]:
    """(verse id, summed weight) of the verses in a domain (in one book, if given), canon order."""
    sql = (
        "SELECT d.verse_id, SUM(d.weight) FROM domain_verses d"
        + (" JOIN verses v ON v.verse_id = d.verse_id" if book_id is not None else "")
        + " WHERE d.code >= ? AND d.code < ?"
    )
    args: list[Any] = list(_domain_range(code))
    if book_id is not None:
        sql += " AND v.book_id = ?"
        args.append(book_id)
    sql += " GROUP BY d.verse_id ORDER BY d.verse_id LIMIT ? OFFSET ?"
    return [(r[0], r[1]) for r in conn.execute(sql, [*args, limit, offset]).fetchall()]


def word_domains(conn: sqlite3.Connection, verse_ids: Iterable[int]) -> list[dict[str, Any]]:
    ids = list(dict.fromkeys(int(i) for i in verse_ids))
    if not ids:
        return []
    cur = conn.execute(
        f"SELECT verse_id, idx, display_idx, domains FROM words WHERE verse_id IN"
        f" ({_marks(len(ids))}) AND domains IS NOT NULL ORDER BY verse_id, idx",
        ids,
    )
    return _dicts(cur)


def unit_domain_weights(conn: sqlite3.Connection, first: int, last: int) -> list[tuple[str, float]]:
    cur = conn.execute(
        "SELECT code, SUM(weight) FROM domain_verses WHERE verse_id BETWEEN ? AND ? GROUP BY code",
        (first, last),
    )
    return [(r[0], r[1]) for r in cur.fetchall()]


def dating_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM dating_books ORDER BY book_id"))


def dating_chapters(conn: sqlite3.Connection, book_id: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT * FROM dating_chapters WHERE book_id = ? ORDER BY chapter", (book_id,)
    )
    return _dicts(cur)


def dating_chapter_of(conn: sqlite3.Connection, verse_id: int) -> dict[str, Any] | None:
    """The profile of the chapter holding a verse."""
    rows = _dicts(
        conn.execute(
            "SELECT d.* FROM dating_chapters d JOIN verses v"
            " ON v.book_id = d.book_id AND v.chapter = d.chapter WHERE v.verse_id = ?",
            (verse_id,),
        )
    )
    return rows[0] if rows else None


SHIFT_COLS = (
    "lemma, n, groups, k, silhouette, use_excess, use_q, n_senses, sense_excess, sense_q, nmi,"
    " nmi_null"
)


def shifts_page(
    conn: sqlite3.Connection, by: str, max_q: float | None, limit: int, offset: int
) -> tuple[int, list[dict[str, Any]]]:
    """Lemmas by `{by}_excess` (sense | use), strongest first, at `{by}_q` ≤ `max_q`."""
    where, args = f"{by}_excess IS NOT NULL", []
    if max_q is not None:
        where += f" AND {by}_q <= ?"
        args.append(max_q)
    total = count(conn, f"SELECT COUNT(*) FROM lemma_shifts WHERE {where}", args)
    cur = conn.execute(
        f"SELECT {SHIFT_COLS} FROM lemma_shifts WHERE {where}"
        f" ORDER BY {by}_excess DESC, lemma LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def lemma_shift(conn: sqlite3.Connection, lemma: str) -> dict[str, Any] | None:
    rows = _dicts(conn.execute(f"SELECT {SHIFT_COLS} FROM lemma_shifts WHERE lemma = ?", (lemma,)))
    return rows[0] if rows else None


def lemma_senses(conn: sqlite3.Connection, lemma: str) -> list[dict[str, Any]]:
    """A lemma's clusters (by number) then SDBH meanings (most frequent first)."""
    cur = conn.execute(
        "SELECT kind, sense, n, groups, collocates, examples, domains FROM lemma_senses"
        " WHERE lemma = ? ORDER BY kind DESC, CASE kind WHEN 'use' THEN CAST(sense AS INTEGER)"
        " ELSE -n END, sense",
        (lemma,),
    )
    return _dicts(cur)


PHRASE_COLS = "a, b, score, n_tokens, a_words, b_words, spread"
SEQUENCE_COLS = (
    "seq_id, a_start, a_end, b_start, b_end, direction, a_book, b_book, same_chapter, n_pairs,"
    " score, q, n_gold"
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
    direction: str | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """Chains, strongest first; `span` = (first, last) verse id: chains touching it."""
    where, args = "n_pairs >= ?", [min_pairs]
    if direction is not None:
        where += " AND direction = ?"
        args.append(direction)
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
    total = count(conn, f"SELECT COUNT(*) FROM sequences WHERE {where}", args)
    cur = conn.execute(
        f"SELECT {SEQUENCE_COLS} FROM sequences WHERE {where}"
        " ORDER BY score DESC, seq_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def _change_filter(
    op: str | None, a_book: int | None, b_book: int | None, span: tuple[int, int] | None = None
) -> tuple[str, list[Any]]:
    """`op` None: every op; `span`: verse pairs with a side in these verses."""
    # a moved word has a row on each side: count the A side only
    if op is None:
        where, args = "(op != 'moved' OR a_idx IS NOT NULL)", []
    else:
        where, args = "op = ?" + (" AND a_idx IS NOT NULL" if op == "moved" else ""), [op]
    if a_book is not None:
        where += " AND a_book = ?"
        args.append(a_book)
    if b_book is not None:
        where += " AND b_book = ?"
        args.append(b_book)
    if span is not None:
        where += " AND (a BETWEEN ? AND ? OR b BETWEEN ? AND ?)"
        args += [*span, *span]
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
    span: tuple[int, int] | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """(number of groups, groups) of `diff_changes` by word key (by written form for spelling /
    form changes), most frequent first; the non-grouping pair of columns is None."""
    where, args = _change_filter(op, a_book, b_book, span)
    ca, cb = _group_cols(op)
    total = count(
        conn,
        f"SELECT COUNT(*) FROM (SELECT 1 FROM diff_changes WHERE {where} GROUP BY {ca}, {cb})",
        args,
    )
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
    span: tuple[int, int] | None = None,
) -> dict[tuple[str | None, str | None], list[dict[str, Any]]]:
    """Up to `n` example verse pairs of each group (`groups`: values of its grouping columns),
    in one query."""
    out: dict[tuple[str | None, str | None], list[dict[str, Any]]] = {g: [] for g in groups}
    if not groups:
        return out
    where, args = _change_filter(op, a_book, b_book, span)
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
    conn: sqlite3.Connection,
    a_book: int | None,
    b_book: int | None,
    span: tuple[int, int] | None = None,
) -> dict[str, int]:
    """Changes per op under the book / verse filters (moved words counted once)."""
    where, args = _change_filter(None, a_book, b_book, span)
    cur = conn.execute(f"SELECT op, COUNT(*) FROM diff_changes WHERE {where} GROUP BY op", args)
    return dict(cur.fetchall())


PARALLEL_COLS = (
    "verse_id, n_cola, cola, pauses, cos, shared, shape, balance, prob, clauses, next_prob,"
    " relation, relation_pairs"
)


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
    sort: str = "prob",
    min_parallel: int = 0,
) -> tuple[int, list[dict[str, Any]]]:
    """Units ranked by the mean parallelism probability of their scored verses, or
    (`sort="antithetic"`) by the share of their parallel verses typed antithetic; units need
    `min_parallel` parallel verses."""
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
        " AS share_parallel, MIN(u.start_verse_id) AS start,"
        " SUM(CASE WHEN p.prob >= ? THEN 1 ELSE 0 END) AS n_parallel,"
        " AVG(CASE WHEN p.prob >= ? AND p.relation IS NOT NULL"
        " THEN p.relation = 'antithetic' END) AS share_antithetic"
        " FROM units u JOIN parallelism p"
        " ON p.verse_id BETWEEN u.start_verse_id AND u.end_verse_id"
        f" WHERE {where} GROUP BY u.unit_id HAVING COUNT(p.prob) >= ? AND n_parallel >= ?"
    )
    iargs = [parallel_at, parallel_at, parallel_at, *args, min_verses, min_parallel]
    total = count(conn, f"SELECT COUNT(*) FROM ({inner})", iargs)
    order = (
        "COALESCE(share_antithetic, -1) DESC, n_parallel DESC, start"
        if sort == "antithetic"
        else "mean_prob DESC, start"
    )
    cur = conn.execute(f"{inner} ORDER BY {order} LIMIT ? OFFSET ?", [*iargs, limit, offset])
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
    total = count(conn, f"SELECT COUNT(*) FROM wordplay w WHERE {where}", args)
    cur = conn.execute(
        f"SELECT {WORDPLAY_COLS} FROM wordplay w"
        " LEFT JOIN words wa ON wa.verse_id = w.a_vid AND wa.idx = w.a_idx"
        " LEFT JOIN words wb ON wb.verse_id = w.b_vid AND wb.idx = w.b_idx"
        f" WHERE {where} ORDER BY w.score DESC, w.a_vid, w.a_idx LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


ENTITY_COLS = "lemma, he, kind, n_mentions, n_verses, first_vid, last_vid, kind_source"


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
    total = count(conn, f"SELECT COUNT(*) FROM ({base})", bargs)
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
    span: tuple[int, int] | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """Shared phrases, strongest first; `span` = (first, last) verse id one side lies in."""
    where, args = "n_tokens >= ?", [min_tokens]
    if span is not None:
        where += " AND (a BETWEEN ? AND ? OR b BETWEEN ? AND ?)"
        args += [*span, *span]
    if max_spread is not None:
        where += " AND spread <= ?"
        args.append(max_spread)
    if book_id is not None:
        where += " AND (a_book = ? OR b_book = ?)"
        args += [book_id, book_id]
    if cross_book:
        where += " AND a_book != b_book"
    total = count(conn, f"SELECT COUNT(*) FROM phrases WHERE {where}", args)
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
    total = count(conn, f"SELECT COUNT(*) FROM structure WHERE {where}", args)
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
    total = count(conn, f"SELECT COUNT(*) FROM acrostics WHERE {where}", args)
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
    total = count(conn, f"SELECT COUNT(*) FROM rewrites WHERE {where}", args)
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


def network_communities(conn: sqlite3.Connection, unit_type: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT * FROM network_communities WHERE unit_type = ? ORDER BY community", (unit_type,)
    )
    return _dicts(cur)


def network_community(
    conn: sqlite3.Connection, unit_type: str, community: int
) -> dict[str, Any] | None:
    rows = _dicts(
        conn.execute(
            "SELECT * FROM network_communities WHERE unit_type = ? AND community = ?",
            (unit_type, community),
        )
    )
    return rows[0] if rows else None


def network_nodes(
    conn: sqlite3.Connection, unit_type: str, community: int | None = None, top: int | None = None
) -> list[dict[str, Any]]:
    sql, args = "SELECT * FROM network_nodes WHERE unit_type = ?", [unit_type]
    if community is not None:
        sql += " AND community = ?"
        args.append(community)
    sql += " ORDER BY pagerank DESC, unit_id"
    if top is not None:
        sql += " LIMIT ?"
        args.append(top)
    return _dicts(conn.execute(sql, args))


def network_edges_among(
    conn: sqlite3.Connection, unit_type: str, ids: list[str]
) -> list[dict[str, Any]]:
    if not ids:
        return []
    marks = _marks(len(ids))
    cur = conn.execute(
        f"SELECT a, b, weight FROM network_edges WHERE unit_type = ? AND a IN ({marks})"
        f" AND b IN ({marks}) ORDER BY a, b",
        [unit_type, *ids, *ids],
    )
    return _dicts(cur)


def network_node(conn: sqlite3.Connection, unit_id: str) -> dict[str, Any] | None:
    rows = _dicts(conn.execute("SELECT * FROM network_nodes WHERE unit_id = ?", (unit_id,)))
    if not rows:
        return None
    n = rows[0]
    n["rank"] = conn.execute(
        "SELECT COUNT(*) + 1 FROM network_nodes WHERE unit_type = ? AND pagerank > ?",
        (n["unit_type"], n["pagerank"]),
    ).fetchone()[0]
    n["of"] = conn.execute(
        "SELECT COUNT(*) FROM network_nodes WHERE unit_type = ?", (n["unit_type"],)
    ).fetchone()[0]
    return n


def word_pairs_page(
    conn: sqlite3.Connection, max_q: float | None, lemma: str | None, limit: int, offset: int
) -> tuple[int, list[dict[str, Any]]]:
    """Fixed word pairs of parallel lines, most significant first; `lemma`: pairs with it."""
    where, args = "1 = 1", []
    if max_q is not None:
        where += " AND q <= ?"
        args.append(max_q)
    if lemma is not None:
        where += " AND (a_lemma = ? OR b_lemma = ?)"
        args += [lemma, lemma]
    total = count(conn, f"SELECT COUNT(*) FROM word_pairs WHERE {where}", args)
    cur = conn.execute(
        f"SELECT * FROM word_pairs WHERE {where} ORDER BY q, g2 DESC, a_lemma, b_lemma"
        " LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def alliteration_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    unit_span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Cola by their alliteration p (lowest first)."""
    where, args = "1 = 1", []
    if book_id is not None:
        where += " AND book_id = ?"
        args.append(book_id)
    if unit_span is not None:
        where += " AND verse_id BETWEEN ? AND ?"
        args += list(unit_span)
    total = count(conn, f"SELECT COUNT(*) FROM alliteration WHERE {where}", args)
    cur = conn.execute(
        f"SELECT * FROM alliteration WHERE {where} ORDER BY p, verse_id, colon LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def rhymes_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    max_q: float | None,
    limit: int,
    offset: int,
    span: tuple[int, int] | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """Rhyme runs, most significant first; `span`: runs overlapping these verses."""
    where, args = "1 = 1", []
    if span is not None:
        where += " AND start_vid <= ? AND end_vid >= ?"
        args += [span[1], span[0]]
    if book_id is not None:
        where += " AND book_id = ?"
        args.append(book_id)
    if max_q is not None:
        where += " AND q <= ?"
        args.append(max_q)
    total = count(conn, f"SELECT COUNT(*) FROM rhymes WHERE {where}", args)
    cur = conn.execute(
        f"SELECT * FROM rhymes WHERE {where} ORDER BY q, n_cola DESC, start_vid LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def typescenes_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    max_q: float | None,
    hide_textual: bool,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Pericope pairs, most significant first; `span`: a pericope overlapping these verses."""
    where, args = "1 = 1", []
    if book_id is not None:
        where += " AND (a_book = ? OR b_book = ?)"
        args += [book_id, book_id]
    if max_q is not None:
        where += " AND q <= ?"
        args.append(max_q)
    if hide_textual:
        where += " AND parallel_text = 0"
    if span is not None:
        inside = (
            "SELECT unit_id FROM units WHERE unit_type = 'pericope'"
            " AND start_verse_id <= ? AND end_verse_id >= ?"
        )
        where += f" AND (a_unit IN ({inside}) OR b_unit IN ({inside}))"
        args += [span[1], span[0], span[1], span[0]]
    total = count(conn, f"SELECT COUNT(*) FROM typescenes WHERE {where}", args)
    cur = conn.execute(
        f"SELECT * FROM typescenes WHERE {where} ORDER BY q, score DESC, a_unit, b_unit"
        " LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def clauses_of(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    """The BHSA clauses of a verse range, in text order, with the speaker's Hebrew form."""
    cur = conn.execute(
        "SELECT c.*, g.he_lemma AS speaker_he FROM clauses c"
        " LEFT JOIN lemma_gloss g ON g.lemma = c.speaker"
        " WHERE c.verse_id BETWEEN ? AND ? ORDER BY c.clause",
        (first, last),
    )
    return _dicts(cur)


def syntax_phrases_of(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT * FROM syntax_phrases WHERE verse_id BETWEEN ? AND ? ORDER BY phrase",
        (first, last),
    )
    return _dicts(cur)


def surfaces(conn: sqlite3.Connection, first: int, last: int) -> dict[tuple[int, int], str]:
    cur = conn.execute(
        "SELECT verse_id, idx, surface FROM words WHERE verse_id BETWEEN ? AND ?", (first, last)
    )
    return {(v, i): s for v, i, s in cur}


def syntax_neighbors(conn: sqlite3.Connection, verse_id: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT tgt, score FROM syntax_neighbors WHERE verse_id = ? ORDER BY rank", (verse_id,)
    )
    return _dicts(cur)


def speech_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM speech_books ORDER BY book_id"))


def speech_chapters(conn: sqlite3.Connection, book_id: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT * FROM speech_chapters WHERE book_id = ? ORDER BY chapter", (book_id,)
    )
    return _dicts(cur)


def speakers(conn: sqlite3.Connection, book_id: int | None = None) -> list[dict[str, Any]]:
    """Speakers with their words, the most first (all books, or one)."""
    where, args = ("WHERE s.book_id = ?", (book_id,)) if book_id is not None else ("", ())
    cur = conn.execute(
        "SELECT s.book_id, s.lemma, s.n_words, s.n_explicit, COALESCE(g.he_lemma, s.lemma) AS he"
        f" FROM speakers s LEFT JOIN lemma_gloss g ON g.lemma = s.lemma {where}"
        " ORDER BY s.book_id, s.n_words DESC, s.lemma",
        args,
    )
    return _dicts(cur)


def voice_speakers(conn: sqlite3.Connection, key: str | None = None) -> list[dict[str, Any]]:
    """Profiled speakers, the most distinct first (all, or one), with their Hebrew form."""
    where, args = ("WHERE v.key = ?", (key,)) if key is not None else ("", ())
    cur = conn.execute(
        "SELECT v.*, g.he_lemma AS he FROM voice_speakers v"
        f" LEFT JOIN lemma_gloss g ON g.lemma = v.key {where} ORDER BY v.effect DESC, v.key",
        args,
    )
    return [{**r, "books": json.loads(r["books"])} for r in _dicts(cur)]


def voice_pairs(conn: sqlite3.Connection, key: str | None = None) -> list[dict[str, Any]]:
    """Delta between voices (all pairs, or those of one voice with it as `a`, nearest first)."""
    if key is None:
        return _dicts(conn.execute("SELECT a, b, delta FROM voice_pairs ORDER BY a, b"))
    cur = conn.execute(
        "SELECT a, b, delta FROM voice_pairs WHERE a = ?"
        " UNION ALL SELECT b AS a, a AS b, delta FROM voice_pairs WHERE b = ?"
        " ORDER BY delta",
        (key, key),
    )
    return _dicts(cur)


def voice_features(conn: sqlite3.Connection, key: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT side, rank, feature, label, rate, rate_ref, z FROM voice_features"
        " WHERE key = ? ORDER BY rank",
        (key,),
    )
    return _dicts(cur)


def speaker_lemmas(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT DISTINCT speaker FROM clauses WHERE speaker != ''")]


def speaker_chapters(
    conn: sqlite3.Connection, lemmas: list[str], limit: int
) -> list[dict[str, Any]]:
    """Chapters with the most speech clauses of these speaker lemmas."""
    marks = ",".join("?" * len(lemmas))
    cur = conn.execute(
        "SELECT v.book_id, v.chapter, COUNT(*) AS n_clauses FROM clauses c"
        f" JOIN verses v ON v.verse_id = c.verse_id WHERE c.speaker IN ({marks})"
        " AND c.txt LIKE '%Q' GROUP BY v.book_id, v.chapter"
        " ORDER BY n_clauses DESC, v.book_id, v.chapter LIMIT ?",
        (*lemmas, limit),
    )
    return _dicts(cur)


def borrowing_sequences(
    conn: sqlite3.Connection, seq_id: int | None = None
) -> list[dict[str, Any]]:
    where, args = ("WHERE seq_id = ?", (seq_id,)) if seq_id is not None else ("", ())
    return _dicts(conn.execute(f"SELECT * FROM borrowing_sequences {where} ORDER BY seq_id", args))


def borrowing_between(
    conn: sqlite3.Connection, a: tuple[int, int], b: tuple[int, int]
) -> list[dict[str, Any]]:
    """Sequences with one side inside verse range `a` and the other inside `b` (either way)."""
    cur = conn.execute(
        "SELECT * FROM borrowing_sequences WHERE"
        " (a_start <= ? AND a_end >= ? AND b_start <= ? AND b_end >= ?)"
        " OR (a_start <= ? AND a_end >= ? AND b_start <= ? AND b_end >= ?) ORDER BY seq_id",
        (a[1], a[0], b[1], b[0], b[1], b[0], a[1], a[0]),
    )
    return _dicts(cur)


def borrowing_touching(conn: sqlite3.Connection, span: tuple[int, int]) -> list[dict[str, Any]]:
    """Scored parallels with either side overlapping verse range `span`."""
    cur = conn.execute(
        "SELECT * FROM borrowing_sequences WHERE (a_start <= ? AND a_end >= ?)"
        " OR (b_start <= ? AND b_end >= ?) ORDER BY seq_id",
        (span[1], span[0], span[1], span[0]),
    )
    return _dicts(cur)


def borrowing_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(
        conn.execute("SELECT * FROM borrowing_books ORDER BY n_pairs DESC, a_book, b_book")
    )


def segment_books(conn: sqlite3.Connection, book_id: int | None = None) -> list[dict[str, Any]]:
    sql, args = "SELECT * FROM segment_books", []
    if book_id is not None:
        sql, args = sql + " WHERE book_id = ?", [book_id]
    return _dicts(conn.execute(sql + " ORDER BY book_id, ref", args))


def segment_gaps_page(
    conn: sqlite3.Connection,
    kind: str | None,
    book_id: int | None,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Flagged gaps (`kind`, or any kind): turns sharpest first, cuts and quiet breaks most
    cohesive first; `span`: gaps at or inside these verses (the unit's opening gap included),
    in reading order."""
    where, args = "kind IS NOT NULL", []
    if kind is not None:
        where, args = "kind = ?", [kind]
    if book_id is not None:
        where += " AND book_id = ?"
        args.append(book_id)
    if span is not None:
        where += " AND verse_id BETWEEN ? AND ?"
        args += list(span)
    order = (
        "verse_id"
        if span is not None or kind is None
        else "score DESC, verse_id"
        if kind == "turn"
        else "score, verse_id"
    )
    total = count(conn, f"SELECT COUNT(*) FROM segment_gaps WHERE {where}", args)
    cur = conn.execute(
        f"SELECT * FROM segment_gaps WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def segment_curve(conn: sqlite3.Connection, book_id: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT g.verse_id, v.chapter, v.verse, g.score, g.mam, g.oshb, g.chapter AS chapter_start,"
        " g.seam, g.kind FROM segment_gaps g JOIN verses v ON v.verse_id = g.verse_id"
        " WHERE g.book_id = ? ORDER BY g.verse_id",
        (book_id,),
    )
    return _dicts(cur)


def kq_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM kq_books ORDER BY book_id"))


def kq_letters(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute("SELECT * FROM kq_letters WHERE n > 0 ORDER BY n DESC, pair")
    return [{**r, "lookalike": bool(r["lookalike"])} for r in _dicts(cur)]


def kq_pairs_page(
    conn: sqlite3.Connection,
    f: dict[str, Any],
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Ketiv / qere in reading order, filtered by `cls`, `grammar`, `parallel`, `euphemism`,
    `book_id` (keys of `f`, None = any) and a verse span."""
    where, args = ["1 = 1"], []
    for col in ("cls", "grammar", "parallel", "book_id"):
        if f.get(col) is not None:
            where.append(f"{col} = ?")
            args.append(f[col])
    if f.get("euphemism") is not None:
        where.append("euphemism = ?")
        args.append(int(f["euphemism"]))
    if span is not None:
        where.append("verse_id BETWEEN ? AND ?")
        args += list(span)
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM kq_pairs WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM kq_pairs WHERE {w} ORDER BY verse_id, pos LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def display_of_words(
    conn: sqlite3.Connection, spans: list[tuple[int, int, int]]
) -> dict[tuple[int, int], list[int]]:
    """(verse_id, first idx) -> display tokens of the words first .. first + n - 1."""
    out: dict[tuple[int, int], list[int]] = {}
    for v, first, n in spans:
        cur = conn.execute(
            "SELECT display_idx FROM words WHERE verse_id = ? AND idx BETWEEN ? AND ?"
            " AND display_idx IS NOT NULL ORDER BY idx",
            (v, first, first + n - 1),
        )
        out[(v, first)] = sorted({r[0] for r in cur})
    return out


def citation_books(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _dicts(conn.execute("SELECT * FROM citation_books ORDER BY n DESC, book_id"))


def citations_page(
    conn: sqlite3.Connection,
    family: str | None,
    resolved: bool | None,
    book_id: int | None,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Citations in reading order; `span`: citing from it, or resolved and pointing into it."""
    where, args = ["1 = 1"], []
    if family is not None:
        where.append("family = ?")
        args.append(family)
    if resolved is not None:
        where.append("resolved = ?")
        args.append(int(resolved))
    if book_id is not None:
        where.append("book_id = ?")
        args.append(book_id)
    if span is not None:
        where.append(
            "(verse_id BETWEEN ? AND ? OR (resolved = 1 AND target_vid BETWEEN ? AND ?))"
        )
        args += [*span, *span]
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM citations WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM citations WHERE {w} ORDER BY verse_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def allusions_page(
    conn: sqlite3.Connection,
    known: bool | None,
    book_id: int | None,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Allusion leads, strongest first; `span`: either side overlapping these verses."""
    where, args = ["1 = 1"], []
    if known is not None:
        where.append("known = ?")
        args.append(int(known))
    if book_id is not None:
        where.append("(a_book = ? OR b_book = ?)")
        args += [book_id, book_id]
    if span is not None:
        where.append("((a_start <= ? AND a_end >= ?) OR (b_start <= ? AND b_end >= ?))")
        args += [span[1], span[0], span[1], span[0]]
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM allusions WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM allusions WHERE {w} ORDER BY score DESC, allusion_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def lemma_marks(
    conn: sqlite3.Connection, vids: list[int], lemmas: set[str]
) -> dict[int, list[int]]:
    """verse_id -> display tokens of its words carrying one of `lemmas` (Strong's numbers, any
    sense letter)."""
    out: dict[int, list[int]] = {v: [] for v in vids}
    if not vids or not lemmas:
        return out
    cur = conn.execute(
        f"SELECT verse_id, display_idx, content_lemmas FROM words WHERE verse_id IN"
        f" ({_marks(len(vids))}) AND display_idx IS NOT NULL",
        vids,
    )
    for v, d, cl in cur:
        if any(c.rstrip("abcdefghijklmnopqrstuvwxyz") in lemmas for c in (cl or "").split()):
            out[v].append(d)
    return {v: sorted(set(ds)) for v, ds in out.items()}


def _span_book(
    where: list[str], args: list[Any], book_id: int | None, span: tuple[int, int] | None
) -> None:
    if book_id is not None:
        where.append("verse_id IN (SELECT verse_id FROM verses WHERE book_id = ?)")
        args.append(book_id)
    if span is not None:
        where.append("verse_id BETWEEN ? AND ?")
        args += list(span)


def mirror_verses_page(
    conn: sqlite3.Connection,
    book_id: int | None,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Full mirrors, lowest p first."""
    where: list[str] = ["1 = 1"]
    args: list[Any] = []
    _span_book(where, args, book_id, span)
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM mirror_verses WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM mirror_verses WHERE {w} ORDER BY p, n_pairs DESC, verse_id"
        " LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def mirror_clauses_page(
    conn: sqlite3.Connection,
    pair: str | None,
    mirrored: bool | None,
    poetic: bool | None,
    book_id: int | None,
    span: tuple[int, int] | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Clause pairs in reading order."""
    where: list[str] = ["1 = 1"]
    args: list[Any] = []
    for col, val in (("pair", pair), ("mirrored", mirrored), ("poetic", poetic)):
        if val is not None:
            where.append(f"{col} = ?")
            args.append(int(val) if isinstance(val, bool) else val)
    _span_book(where, args, book_id, span)
    w = " AND ".join(where)
    total = count(conn, f"SELECT COUNT(*) FROM mirror_clauses WHERE {w}", args)
    cur = conn.execute(
        f"SELECT * FROM mirror_clauses WHERE {w} ORDER BY verse_id, pair_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)


def display_map(conn: sqlite3.Connection, verse_id: int) -> dict[int, int]:
    """word idx -> display token of one verse (aligned words only)."""
    cur = conn.execute(
        "SELECT idx, display_idx FROM words WHERE verse_id = ? AND display_idx IS NOT NULL",
        (verse_id,),
    )
    return {int(i): int(d) for i, d in cur}
