"""Read-only SQL helpers of `api/routes/genealogy.py` (DESIGN.md §9, §16.63)."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from typing import Any

from bsim.api.queries.common import _dicts, _marks
from bsim.text.normalize import match_key

_LIVE = "status != 'rejected'"
_PERSON_COLS = "p.person_id, p.he, p.sex, p.kind, p.placement"


def genealogy_nodes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every drawn person (not those drawn beside a spouse) with the link it is drawn by: its
    parent (none for a root), the link's role, kind and place among the parent's children."""
    cur = conn.execute(
        "SELECT p.person_id, p.he, p.sex, p.kind, p.placement, p.book_id, p.reviewed,"
        " l.parent_id AS parent, l.role, l.kind AS link_kind, l.seq, COALESCE(l.doubt, 0) AS doubt,"
        " EXISTS (SELECT 1 FROM genealogy_conflicts c WHERE c.child_id = p.person_id) AS conflict"
        " FROM genealogy_persons p LEFT JOIN genealogy_links l"
        " ON l.child_id = p.person_id AND l.drawn = 1"
        " WHERE p.placement != 'spouse' ORDER BY p.person_id"
    )
    return _dicts(cur)


def genealogy_mothers(conn: sqlite3.Connection) -> dict[int, int]:
    """child -> its mother, for children drawn under their father (the mother headers)."""
    cur = conn.execute(
        "SELECT m.child_id, m.parent_id FROM genealogy_links m JOIN genealogy_links f"
        " ON f.child_id = m.child_id AND f.drawn = 1 AND f.role = 'father'"
        f" WHERE m.role = 'mother' AND m.{_LIVE} ORDER BY m.child_id, m.link_id"
    )
    out: dict[int, int] = {}
    for child, mother in cur.fetchall():
        out.setdefault(child, mother)
    return out


def genealogy_beside(conn: sqlite3.Connection) -> tuple[list[dict[str, Any]], dict[int, list[int]]]:
    """The people drawn beside a spouse, and node -> those beside it: a spouse who is a node, or
    the parent the other parent's children are drawn under."""
    people = _dicts(conn.execute(
        f"SELECT {_PERSON_COLS}, p.reviewed FROM genealogy_persons p"
        " WHERE p.placement = 'spouse' ORDER BY p.person_id"
    ))  # fmt: skip
    cur = conn.execute(
        "SELECT s.person_id, CASE WHEN l.parent_id = s.person_id THEN l.child_id"
        " ELSE l.parent_id END AS other, l.link_id"
        " FROM genealogy_persons s JOIN genealogy_links l"
        " ON l.role = 'spouse' AND s.person_id IN (l.parent_id, l.child_id)"
        f" WHERE s.placement = 'spouse' AND l.{_LIVE}"
        " UNION ALL"
        " SELECT s.person_id, d.parent_id, d.link_id FROM genealogy_persons s"
        " JOIN genealogy_links m ON m.parent_id = s.person_id AND m.role IN ('father', 'mother')"
        f" AND m.drawn = 0 AND m.{_LIVE}"
        " JOIN genealogy_links d ON d.child_id = m.child_id AND d.drawn = 1"
        " WHERE s.placement = 'spouse' ORDER BY 1, 3"
    )
    placed = {r[0] for r in conn.execute(
        "SELECT person_id FROM genealogy_persons WHERE placement != 'spouse'"
    )}  # fmt: skip
    beside: dict[int, list[int]] = defaultdict(list)
    for s, other, _ in cur.fetchall():
        if other in placed and s not in beside[other]:
            beside[other].append(s)
    return people, beside


def genealogy_cross(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """The parent links not drawn (another parent, another reading) between two drawn people."""
    cur = conn.execute(
        "SELECT l.parent_id AS parent, l.child_id AS child, l.role, l.kind FROM genealogy_links l"
        " JOIN genealogy_persons a ON a.person_id = l.parent_id AND a.placement != 'spouse'"
        " JOIN genealogy_persons b ON b.person_id = l.child_id AND b.placement != 'spouse'"
        f" WHERE l.role IN ('father', 'mother') AND l.drawn = 0 AND l.{_LIVE}"
        " ORDER BY l.link_id"
    )
    return _dicts(cur)


def genealogy_person(conn: sqlite3.Connection, person_id: int) -> dict[str, Any] | None:
    cur = conn.execute(
        "SELECT person_id, he, sex, kind, tribe, placement, first_vid, n_verses, reviewed,"
        " book_id, founded FROM genealogy_persons WHERE person_id = ?",
        (person_id,),
    )
    rows = _dicts(cur)
    return rows[0] | {"founded": json.loads(rows[0]["founded"] or "[]")} if rows else None


def genealogy_people(conn: sqlite3.Connection, ids: list[int]) -> dict[int, dict[str, Any]]:
    ids = list(dict.fromkeys(ids))
    if not ids:
        return {}
    cur = conn.execute(
        f"SELECT {_PERSON_COLS} FROM genealogy_persons p WHERE p.person_id IN ({_marks(len(ids))})",
        ids,
    )
    return {r["person_id"]: r for r in _dicts(cur)}


_LINK_COLS = (
    "link_id, parent_id, child_id, role, kind, drawn, doubt, marker, status, source, cue,"
    " n_candidates, conflict_id, seq"
)


def genealogy_links_of(conn: sqlite3.Connection, person_id: int) -> list[dict[str, Any]]:
    """Every link of a person but rejected ones, either side."""
    cur = conn.execute(
        f"SELECT {_LINK_COLS} FROM genealogy_links WHERE (parent_id = ? OR child_id = ?)"
        f" AND {_LIVE} ORDER BY link_id",
        (person_id, person_id),
    )
    return _dicts(cur)


def genealogy_links_by_id(conn: sqlite3.Connection, ids: list[int]) -> dict[int, dict[str, Any]]:
    if not ids:
        return {}
    cur = conn.execute(
        f"SELECT {_LINK_COLS} FROM genealogy_links WHERE link_id IN ({_marks(len(ids))})", ids
    )
    return {r["link_id"]: r for r in _dicts(cur)}


def genealogy_parent_links(conn: sqlite3.Connection, children: list[int]) -> list[dict[str, Any]]:
    """The father / mother links of these children (to group them by their other parent)."""
    if not children:
        return []
    cur = conn.execute(
        f"SELECT {_LINK_COLS} FROM genealogy_links WHERE role IN ('father', 'mother')"
        f" AND {_LIVE} AND child_id IN ({_marks(len(children))}) ORDER BY link_id",
        children,
    )
    return _dicts(cur)


def genealogy_children_of(conn: sqlite3.Connection, parents: list[int]) -> list[int]:
    """The children of these parents (for a person's siblings)."""
    if not parents:
        return []
    cur = conn.execute(
        f"SELECT DISTINCT child_id FROM genealogy_links WHERE role IN ('father', 'mother')"
        f" AND {_LIVE} AND parent_id IN ({_marks(len(parents))}) ORDER BY child_id",
        parents,
    )
    return [r[0] for r in cur.fetchall()]


def genealogy_proofs(
    conn: sqlite3.Connection, link_ids: list[int]
) -> dict[int, list[dict[str, Any]]]:
    """link -> its proof verses, best first, each with its cue and the names' display tokens."""
    if not link_ids:
        return {}
    cur = conn.execute(
        "SELECT link_id, verse_id, cue, tokens, source FROM genealogy_proofs"
        f" WHERE link_id IN ({_marks(len(link_ids))}) ORDER BY link_id, rank",
        link_ids,
    )
    out: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in _dicts(cur):
        out[r["link_id"]].append(r | {"tokens": json.loads(r["tokens"])})
    return out


def genealogy_conflicts_of(conn: sqlite3.Connection, person_id: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT conflict_id, kind, block, readings, note_en, note_he FROM genealogy_conflicts"
        " WHERE child_id = ? ORDER BY conflict_id",
        (person_id,),
    )
    return [r | {"readings": json.loads(r["readings"])} for r in _dicts(cur)]


def genealogy_identities_of(conn: sqlite3.Connection, person_id: int) -> list[dict[str, Any]]:
    """The identities a person is in: merged into it, or a possible one either side (none in a DB
    built before them)."""
    try:
        cur = conn.execute(
            "SELECT identity_id, status, person_id, other_id, keys, proofs, note_en, note_he"
            " FROM genealogy_identities WHERE person_id = ? OR other_id = ? ORDER BY identity_id",
            (person_id, person_id),
        )
    except sqlite3.OperationalError:
        return []
    return [r | {"keys": json.loads(r["keys"]), "proofs": json.loads(r["proofs"])}
            for r in _dicts(cur)]  # fmt: skip


_NAME_INDEX: dict[str, list[tuple[int, str, str, int]]] = {}


def _plain(key: str) -> str:
    """A key without its vowel letters after the first letter: דויד and דוד alike."""
    return key[:1] + key[1:].replace("ו", "").replace("י", "")


def genealogy_lookup(conn: sqlite3.Connection, q: str, limit: int) -> list[dict[str, Any]]:
    """People by a Hebrew name, as match keys (consonants, finals folded, spaces dropped); failing
    that, with ו and י ignored. The whole name first, then names starting with it; the most named
    first. Each with what tells namesakes apart: the drawn parent (or the eponym of its tribe) or
    the spouse it is drawn beside. The names are read once per DB."""
    db = conn.execute("PRAGMA database_list").fetchone()[2]
    index = _NAME_INDEX.get(db)
    if index is None:
        index = [
            (pid, match_key(he), _plain(match_key(he)), n)
            for pid, he, n in conn.execute(
                "SELECT person_id, he, n_verses FROM genealogy_persons"
                " WHERE he != '' AND kind != 'virtual' ORDER BY person_id"
            )
        ]
        _NAME_INDEX[db] = index
    key = match_key(q.strip())
    if not key:
        return []
    rank: dict[int, int] = {}
    for col, k in ((1, key), (2, _plain(key))):
        for row in index:
            if row[col] == k:
                rank[row[0]] = 0
            elif row[col].startswith(k):
                rank[row[0]] = 1
        if rank:
            break
    if not rank:
        return []
    n_verses = {pid: n for pid, _, _, n in index}
    ids = sorted(rank, key=lambda p: (rank[p], -n_verses[p], p))[:limit]
    cur = conn.execute(
        "SELECT p.person_id, p.he, p.sex, p.kind, p.placement, p.first_vid, p.n_verses,"
        " l.role, q.he AS of_he, q.kind AS of_kind"
        " FROM genealogy_persons p LEFT JOIN genealogy_links l"
        " ON l.child_id = p.person_id AND l.drawn = 1"
        " LEFT JOIN genealogy_persons q ON q.person_id = l.parent_id"
        f" WHERE p.person_id IN ({_marks(len(ids))})",
        ids,
    )
    rows = {r["person_id"]: r for r in _dicts(cur)}
    spouse = [p for p in ids if rows[p]["placement"] == "spouse"]
    _, beside = genealogy_beside(conn) if spouse else ([], {})
    partner: dict[int, int] = {}
    for node, ss in beside.items():
        for s in ss:
            partner.setdefault(s, node)
    names = genealogy_people(conn, list(partner.values()))
    out = []
    for p in ids:
        r = rows[p]
        relation, of_he = None, None
        if r["placement"] == "spouse" and p in partner:
            relation, of_he = "spouse", names[partner[p]]["he"]
        elif r["role"] in ("father", "mother") and r["of_kind"] != "virtual":
            relation, of_he = "child", r["of_he"]
        elif r["role"] == "unstated" and r["of_kind"] != "virtual":
            relation, of_he = "tribe", r["of_he"]
        out.append({k: r[k] for k in ("person_id", "he", "sex", "kind", "placement", "first_vid",
                                      "n_verses")}
                   | {"exact": rank[p] == 0, "relation": relation if of_he else None,
                      "of_he": of_he or None})  # fmt: skip
    return out
