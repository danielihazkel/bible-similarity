"""`/dossier/{unit}`: what every analysis says about one unit, in one request (DESIGN.md §10).

Each entry names an analysis (`kind`), the unit it was read on (`scope`: the unit itself, or the
chapter / book holding it, `target_unit`), whether its stage ran (`computed`: an optional stage
that did not run leaves its table empty, so "none found" and "not computed" can be told apart)
and what it found:

    phrases, sequences, changes, borrowing, wordplay, alliteration, rhymes, typescenes,
    discoveries, seams, names     count = rows touching the unit's verses
    acrostic, structure           value = the lowest q; count = 1 when it is ≤ `serve.dossier.max_q`
    dating                        value = the chapter's Late Biblical Hebrew score
    speech                        count = quotation clauses; label / key = the speaker of most
    voices                        key = that speaker's voice profile, when it has one
    network                       count = rank by PageRank, total = units ranked
    divisions                     count = flagged gaps at or inside the unit; value / key = the
                                  score / kind of the gap the unit opens with
    ketiv                         count = ketiv / qere in the unit's verses
    labels                        count = your labelled pairs with this unit (read live)

The rest is deterministic per DB, so it is cached (`serve.dossier_cache`).
"""

from __future__ import annotations

import math
import sqlite3
from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.app import ServeState
from bsim.api.models import Dossier, DossierEntry
from bsim.api.routes._common import Conn, State, unit_or_404
from bsim.config import resolve_path
from bsim.data.lexicon import strong_key

router = APIRouter()


def _count(conn: sqlite3.Connection, sql: str, args: tuple[Any, ...]) -> int:
    return int(conn.execute(sql, args).fetchone()[0])


def _min_q(values: list[float | None]) -> float | None:
    qs = [q for q in values if q is not None and not math.isnan(q)]
    return min(qs) if qs else None


def _entries(u: dict[str, Any], state: ServeState, conn: sqlite3.Connection) -> list[DossierEntry]:
    first, last, uid = u["start_verse_id"], u["end_verse_id"], u["unit_id"]
    span = (first, last)
    max_q = state.cfg["serve"]["dossier"]["max_q"]
    chapter = next(
        (p for p in queries.parents(conn, u) if p["unit_type"] == "chapter"),
        u if u["unit_type"] == "chapter" else None,
    )
    out: list[DossierEntry] = []

    def add(kind: str, computed: bool = True, **kw: Any) -> None:
        out.append(DossierEntry(kind=kind, computed=computed, **{"scope": "unit", **kw}))

    two_sides = "(a BETWEEN ? AND ? OR b BETWEEN ? AND ?)"
    add("phrases", count=_count(conn, f"SELECT COUNT(*) FROM phrases WHERE {two_sides}", span * 2))
    seqs = _count(
        conn,
        "SELECT COUNT(*) FROM sequences WHERE (a_start <= ? AND a_end >= ?)"
        " OR (b_start <= ? AND b_end >= ?)",
        (last, first, last, first),
    )
    add("sequences", count=seqs)
    add("changes", count=sum(queries.change_totals(conn, None, None, span).values()))
    add(
        "borrowing",
        computed=state.present(conn, "borrowing_sequences"),
        count=len(queries.borrowing_touching(conn, span)),
    )
    add("wordplay", count=queries.wordplay_page(conn, None, None, span, 1, 0)[0])
    add("alliteration", count=queries.alliteration_page(conn, None, span, 1, 0)[0])
    add("rhymes", count=queries.rhymes_page(conn, None, None, 1, 0, span)[0])
    add("typescenes", count=queries.typescenes_page(conn, None, max_q, True, span, 1, 0)[0])
    add(
        "discoveries",
        count=_count(
            conn,
            "SELECT COUNT(*) FROM discoveries WHERE unit_type = ? AND mode = 'semantic'"
            " AND (a_id = ? OR b_id = ?)",
            (u["unit_type"], uid, uid),
        ),
    )
    add(
        "seams",
        count=_count(conn, "SELECT COUNT(*) FROM seams WHERE verse_id BETWEEN ? AND ?", span),
    )
    add(
        "names",
        count=_count(
            conn,
            "SELECT COUNT(DISTINCT lemma) FROM entity_mentions WHERE verse_id BETWEEN ? AND ?",
            span,
        ),
    )

    if chapter is not None:
        scope = "unit" if chapter["unit_id"] == uid else "chapter"
        a = queries.acrostic(conn, chapter["unit_id"])
        q = a["q"] if a else None
        add(
            "acrostic",
            scope=scope,
            target_unit=chapter["unit_id"],
            value=q,
            count=int(q is not None and q <= max_q),
        )
        d = queries.dating_chapter_of(conn, first)
        add(
            "dating",
            computed=state.present(conn, "dating_chapters"),
            scope=scope,
            target_unit=chapter["unit_id"],
            value=d["score"] if d else None,
            count=int(d is not None and d["score"] is not None),
        )
    holder = u if u["unit_type"] != "verse" else chapter
    if holder is not None:
        row = conn.execute(
            "SELECT semantic_inclusio_q, semantic_chiasm_q, lexical_inclusio_q, lexical_chiasm_q"
            " FROM structure WHERE unit_id = ?",
            (holder["unit_id"],),
        ).fetchone()
        q = _min_q(list(row)) if row else None
        add(
            "structure",
            scope="unit" if holder["unit_id"] == uid else "chapter",
            target_unit=holder["unit_id"],
            value=q,
            count=int(q is not None and q <= max_q),
        )

    syntax = state.present(conn, "clauses")
    rows = conn.execute(
        "SELECT c.speaker, COALESCE(g.he_lemma, c.speaker), COUNT(*) FROM clauses c"
        " LEFT JOIN lemma_gloss g ON g.lemma = c.speaker"
        " WHERE c.verse_id BETWEEN ? AND ? AND c.txt LIKE '%Q'"
        " GROUP BY c.speaker ORDER BY COUNT(*) DESC, c.speaker",
        span,
    ).fetchall()
    top = next(((s, he) for s, he, _ in rows if s), (None, None))
    add("speech", computed=syntax, count=sum(n for *_, n in rows), key=top[0], label=top[1])
    voices = state.present(conn, "voice_speakers")
    voice = None
    if top[0] is not None:
        key = "divine" if strong_key(top[0]) in state.cfg["syntax"]["divine"] else top[0]
        if conn.execute("SELECT 1 FROM voice_speakers WHERE key = ?", (key,)).fetchone():
            voice = key
    add("voices", computed=voices, count=int(voice is not None), key=voice, label=top[1])

    opening = conn.execute(
        "SELECT score, kind FROM segment_gaps WHERE verse_id = ?", (first,)
    ).fetchone()
    add(
        "divisions",
        computed=state.present(conn, "segment_gaps"),
        count=_count(
            conn,
            "SELECT COUNT(*) FROM segment_gaps WHERE kind IS NOT NULL AND verse_id BETWEEN ? AND ?",
            span,
        ),
        value=opening[0] if opening else None,
        key=opening[1] if opening else None,
    )

    add(
        "ketiv",
        computed=state.present(conn, "kq_pairs"),
        count=_count(conn, "SELECT COUNT(*) FROM kq_pairs WHERE verse_id BETWEEN ? AND ?", span),
    )

    if u["unit_type"] != "verse":
        node = queries.network_node(conn, uid)
        add(
            "network",
            computed=node is not None,  # units of a type the network leaves out have no node
            count=node["rank"] if node else None,
            total=node["of"] if node else None,
        )
    return out


@router.get("/dossier/{unit_id}", response_model=Dossier)
def dossier(unit_id: str, state: State, conn: Conn) -> dict[str, Any]:
    """Every analysis's findings on one unit, with links to read them (see the module doc)."""
    u = unit_or_404(conn, unit_id)
    entries = state.dossier_cache.get(unit_id)
    if entries is None:
        entries = _entries(u, state, conn)
        state.dossier_cache.put(unit_id, entries)
    path = resolve_path(state.cfg, "labels")
    n_labels = 0
    if path.exists():  # created with its table by the first label (`store.labels.connect`)
        lconn = sqlite3.connect(path, timeout=5)
        try:
            n_labels = _count(
                lconn, "SELECT COUNT(*) FROM labels WHERE a_id = ? OR b_id = ?", (unit_id,) * 2
            )
        finally:
            lconn.close()
    labels = DossierEntry(kind="labels", scope="unit", computed=True, count=n_labels)
    return {"unit_id": unit_id, "entries": [*entries, labels]}
