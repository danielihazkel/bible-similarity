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
