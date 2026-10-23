"""Retold speech (DESIGN.md §16.68): what changes when something said or told is told again; the
retellings by group, each with both texts and its changes marked, and the two checks."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.retold import (
    RetoldGroup,
    RetoldOrder,
    RetoldPage,
    RetoldPair,
    RetoldResponse,
    RetoldSide,
)
from bsim.api.routes._common import Conn, State, check_page
from bsim.api.routes.dialogue import _parties

router = APIRouter()
OPS = ("same", "spelling", "form", "substitution", "omitted", "added", "moved")


def _meta(state: State) -> dict[str, Any]:
    m = state.meta.get("retold")
    if not m:
        raise HTTPException(status_code=404, detail="the retold speech was not computed")
    return m


@router.get("/retold", response_model=RetoldResponse)
def retold(state: State) -> dict[str, Any]:
    """The groups, their change rates and the two checks (404: the stage did not run)."""
    m = _meta(state)
    keep = ("pairs", "groups", "rates", "claim", "difference", "p", "shuffles", "bins", "alpha",
            "holds", "known", "known_found", "known_holds")  # fmt: skip
    return {k: m[k] for k in keep}


@router.get("/retold/items", response_model=RetoldPage)
def retold_items(
    state: State,
    conn: Conn,
    group: RetoldGroup | None = None,
    book: int | None = None,
    known: bool = False,
    order: RetoldOrder = "canon",
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """A page of retellings, each with its source and retelling verses and the changed words."""
    _meta(state)
    check_page(state, limit, offset)
    total, rows = queries.retold_page(conn, group, book, known, order, limit, offset)
    spans = {r["pair"]: (range(r["src_first"], r["src_last"] + 1),
                         range(r["later_first"], r["later_last"] + 1)) for r in rows}  # fmt: skip
    verses = queries.verses_by_id(conn, [v for a, b in spans.values() for v in (*a, *b)])
    marks: dict[tuple[int, str, int], dict[int, str]] = {}
    for mk in queries.retold_marks(conn, list(spans)):
        marks.setdefault((mk["pair"], mk["side"], mk["verse_id"]), {})[mk["display_idx"]] = mk["op"]
    parties = _parties(state, conn, [r[k] for r in rows for k in ("src_teller", "later_teller")
                                     if r[k] is not None])  # fmt: skip

    def side(r: dict[str, Any], s: str, vids: range, unit: int, teller: str | None) -> RetoldSide:
        return RetoldSide(
            kind="narration" if unit < 0 else "speech",
            teller=parties[teller] if teller is not None else None,
            verses=[verses[v] for v in vids if v in verses],
            marks=[marks.get((r["pair"], s, v), {}) for v in vids if v in verses],
        )

    items = []
    for r in rows:
        a, b = spans[r["pair"]]
        later = verses.get(r["later_first"])
        items.append(
            RetoldPair(
                pair=r["pair"],
                book_id=r["book_id"],
                group=r["grp"],
                source=side(r, "a", a, r["src_unit"], r["src_teller"]),
                retelling=side(r, "b", b, r["later_unit"], r["later_teller"]),
                unit_id=f"c:{later['book_id']}:{later['chapter']}" if later else "",
                n_ops=r["n_ops"],
                n_changed=r["n_changed"],
                rate=r["rate"],
                ops={o: r[o] for o in OPS if r[o]},
                score=r["score"],
                known=bool(r["known"]),
            )
        )
    return {"group": group, "book": book, "order": order, "known": known, "total": total,
            "offset": offset, "limit": limit, "items": items}  # fmt: skip
