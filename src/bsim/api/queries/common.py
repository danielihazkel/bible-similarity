"""SQL helpers shared by several routes: units, verses, words, lemmas (DESIGN.md §9)."""

from __future__ import annotations

import json
import sqlite3
import threading
from collections import OrderedDict, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
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


def gloss(conn: sqlite3.Connection, lemmas: Iterable[str]) -> dict[str, str]:
    lemmas = sorted(set(lemmas))
    if not lemmas:
        return {}
    cur = conn.execute(
        f"SELECT lemma, he_lemma FROM lemma_gloss WHERE lemma IN ({_marks(len(lemmas))})", lemmas
    )
    return dict(cur.fetchall())


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


WORDPLAY_COLS = (
    "w.a_vid, w.a_idx, w.b_vid, w.b_idx, w.a_lemma, w.b_lemma, w.a_form, w.b_form, w.kind,"
    " w.gap, w.score, w.q, wa.display_idx AS a_display, wb.display_idx AS b_display"
)


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


def corpus_lemma_total(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT SUM(n_words) FROM lemma_gloss").fetchone()[0] or 0


def clauses_of(conn: sqlite3.Connection, first: int, last: int) -> list[dict[str, Any]]:
    """The BHSA clauses of a verse range, in text order, with the speaker's Hebrew form."""
    cur = conn.execute(
        "SELECT c.*, g.he_lemma AS speaker_he, h.he_lemma AS addressee_he FROM clauses c"
        " LEFT JOIN lemma_gloss g ON g.lemma = c.speaker"
        " LEFT JOIN lemma_gloss h ON h.lemma = c.addressee"
        " WHERE c.verse_id BETWEEN ? AND ? ORDER BY c.clause",
        (first, last),
    )
    return _dicts(cur)


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


def _span_book(
    where: list[str], args: list[Any], book_id: int | None, span: tuple[int, int] | None
) -> None:
    if book_id is not None:
        where.append("verse_id IN (SELECT verse_id FROM verses WHERE book_id = ?)")
        args.append(book_id)
    if span is not None:
        where.append("verse_id BETWEEN ? AND ?")
        args += list(span)


@dataclass(frozen=True)
class RootIndex:
    """`lemma_roots` read once: lemma -> (root, root's headword), root -> its lemmas and the
    corpus count of its words (`lemma_gloss.n_words` summed)."""

    root_of: dict[str, tuple[str, str]]
    members: dict[str, list[str]]
    counts: dict[str, int]

    def family(self, lemma: str) -> tuple[str, str] | None:
        """(root, headword) of a lemma whose family has other words, else None."""
        r = self.root_of.get(lemma)
        return r if r and len(self.members.get(r[0], ())) > 1 else None


def root_index(conn: sqlite3.Connection) -> RootIndex:
    root_of: dict[str, tuple[str, str]] = {}
    members: dict[str, list[str]] = defaultdict(list)
    counts: dict[str, int] = defaultdict(int)
    cur = conn.execute(
        "SELECT r.lemma, r.root, r.root_he, COALESCE(g.n_words, 0) FROM lemma_roots r"
        " LEFT JOIN lemma_gloss g ON g.lemma = r.lemma ORDER BY r.lemma"
    )
    for lemma, root, root_he, n in cur:
        root_of[lemma] = (root, root_he)
        members[root].append(lemma)
        counts[root] += n
    return RootIndex(root_of, dict(members), dict(counts))


def display_map(conn: sqlite3.Connection, verse_id: int) -> dict[int, int]:
    """word idx -> display token of one verse (aligned words only)."""
    cur = conn.execute(
        "SELECT idx, display_idx FROM words WHERE verse_id = ? AND display_idx IS NOT NULL",
        (verse_id,),
    )
    return {int(i): int(d) for i, d in cur}


def dialogue_pairs(conn: sqlite3.Connection, book_id: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT * FROM dialogue_pairs WHERE book_id = ?"
        " ORDER BY n_quotes DESC, n_words DESC, speaker, addressee",
        (book_id,),
    )
    return _dicts(cur)
