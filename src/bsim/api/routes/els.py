"""Equidistant letter sequences against controls (DESIGN.md §16.62): per scope (the Torah,
Genesis) the names' hits at equal skips against their exact expectation, and the same statistic
over shuffled letters, shuffled verses and blocks of the rest of the Bible; the tradition's
sequences at the start of each book."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models.common import VerseLabel
from bsim.api.models.els import ElsBlock, ElsControl, ElsKnown, ElsResponse, ElsScope, ElsTerm
from bsim.api.routes._common import Conn, State, span_label

router = APIRouter()


@router.get("/els", response_model=ElsResponse)
def els(state: State, conn: Conn) -> dict[str, Any]:
    """Every scope's hits against its controls, its terms, and the known sequences."""
    meta = state.meta.get("els") or {}
    t = queries.els_tables(conn)
    scopes_meta = meta.get("scopes") or {}
    vids = [v for s in scopes_meta.values() for v in (s["first_vid"], s["last_vid"])]
    vids += [v for s in scopes_meta.values() for b in s.get("blocks") or []
             for v in (b["first_vid"], b["last_vid"])]  # fmt: skip
    vids += [k["verse_id"] for k in meta.get("known") or []]
    labels = queries.verse_labels(conn, vids)
    scopes = []
    for key, s in scopes_meta.items():
        values: dict[str, list[float]] = {}
        for r in t["draws"]:
            if r["scope"] == key:
                values.setdefault(r["control"], []).append(r["r"])
        scopes.append(ElsScope(
            key=key,
            label_en=span_label(labels, s["first_vid"], s["last_vid"], 0),
            label_he=span_label(labels, s["first_vid"], s["last_vid"], 1),
            **{k: s[k] for k in ("letters", "verses", "hits", "expected", "r", "holds")},
            controls={c: ElsControl(**v, values=values.get(c, []))
                      for c, v in (s.get("controls") or {}).items()},
            blocks=[ElsBlock(block=b["block"], first_vid=b["first_vid"], r=b["r"],
                             label_en=span_label(labels, b["first_vid"], b["last_vid"], 0),
                             label_he=span_label(labels, b["first_vid"], b["last_vid"], 1))
                    for b in s.get("blocks") or []],
            terms=[ElsTerm(**{k: v for k, v in r.items() if k != "scope"})
                   for r in t["terms"] if r["scope"] == key],
        ))  # fmt: skip
    known = [
        ElsKnown(
            verse=VerseLabel(verse_id=k["verse_id"], label_en=labels[k["verse_id"]][0],
                             label_he=labels[k["verse_id"]][1]),
            **{x: k[x] for x in ("term", "skip", "found", "offset", "in_torah", "expected")},
        )  # fmt: skip
        for k in meta.get("known") or []
        if k["verse_id"] in labels
    ]
    return {
        "meta": {k: v for k, v in meta.items() if k not in ("scopes", "known")},
        "scopes": scopes,
        "known": known,
    }
