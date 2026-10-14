"""Read-only SQL helpers of `api/routes/corpus.py` (DESIGN.md §9)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, _marks, count

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


def map_points(conn: sqlite3.Connection, unit_type: str) -> list[dict[str, Any]]:
    """The points of one unit type, with each unit's verses inside a list (§16.45)."""
    cur = conn.execute(
        "SELECT p.unit_id, u.label_en, u.label_he, u.book_id, u.n_verses, p.x, p.y, p.cluster,"
        " (SELECT COALESCE(SUM(MIN(u.end_verse_id, l.last_vid)"
        "  - MAX(u.start_verse_id, l.first_vid) + 1), 0) FROM forms_lists l"
        "  WHERE l.first_vid <= u.end_verse_id AND l.last_vid >= u.start_verse_id) AS list_verses"
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
