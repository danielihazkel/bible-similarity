"""Do the sums add up? (DESIGN.md §16.75): each list against its stated total, a list's counts,
and the numbers of parallel verses."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.sums import (
    KnownSumsParallel,
    SumsItem,
    SumsItemsResponse,
    SumsList,
    SumsParallel,
    SumsParallelsResponse,
    SumsResponse,
)
from bsim.api.routes._common import BookFilter, Conn, State, check_page, stage, stage_missing

router = APIRouter()

KEEP = ("lists_adding_up", "lists_holds", "min_value", "pairs", "pairs_used", "numbers",
        "numbers_same", "numbers_differ", "across", "every", "step_holds", "known_holds",
        "min_shared", "min_big", "shuffles", "alpha")  # fmt: skip


@router.get("/sums", dependencies=[stage("sums")], response_model=SumsResponse)
def sums(state: State, conn: Conn) -> dict[str, Any]:
    """Every list with its sum and stated total, and the parallels' test (503: not run)."""
    m = state.meta.get("sums")
    if not m:
        raise stage_missing("sums")
    rows = queries.sums_lists(conn)
    known = m.get("known_parallels") or []
    verses = queries.verses_by_id(
        conn,
        [v for r in rows for v in (r["total_verse"], r["first_verse"], r["last_verse"])]
        + [v for k in known for v in (k["a"], k["b"])],
    )
    lists = [
        SumsList(
            **{
                k: r[k]
                for k in ("key", "total", "sum", "n_items", "total_tok_first", "total_tok_last")
            },  # fmt: skip
            adds_up=bool(r["adds_up"]),
            expected=bool(r["expected"]),
            holds=bool(r["holds"]),
            total_verse=verses[r["total_verse"]],
            first_verse=verses[r["first_verse"]],
            last_verse=verses[r["last_verse"]],
        )  # fmt: skip
        for r in rows
    ]
    kp = [
        KnownSumsParallel(**{**k, "a": verses[k["a"]], "b": verses[k["b"]]})
        for k in known
        if k["a"] in verses and k["b"] in verses
    ]
    return {**{k: m[k] for k in KEEP}, "lists": lists, "known_parallels": kp}


@router.get("/sums/items", dependencies=[stage("sums")], response_model=SumsItemsResponse)
def sums_items(key: str, state: State, conn: Conn) -> dict[str, Any]:
    """A list's counts, in text order (404: no such list)."""
    if not state.meta.get("sums"):
        raise stage_missing("sums")
    rows = queries.sums_items(conn, key)
    if not rows:
        raise HTTPException(status_code=404, detail=f"no list {key!r}")
    verses = queries.verses_by_id(conn, [r["verse_id"] for r in rows])
    items = [
        SumsItem(
            verse=verses[r["verse_id"]],
            value=r["value"],
            tok_first=r["tok_first"],
            tok_last=r["tok_last"],
        )  # fmt: skip
        for r in rows
        if r["verse_id"] in verses
    ]
    return {"key": key, "items": items}


@router.get("/sums/parallels", dependencies=[stage("sums")], response_model=SumsParallelsResponse)
def sums_parallels(
    state: State,
    conn: Conn,
    across: bool = True,
    differ: bool = True,
    one_step: bool | None = None,
    book: BookFilter = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """The aligned numbers of parallel verses, in canon order."""
    if not state.meta.get("sums"):
        raise stage_missing("sums")
    check_page(state, limit, offset)
    total, rows = queries.sums_parallels_page(conn, across, differ, one_step, book, limit,
                                              offset)  # fmt: skip
    verses = queries.verses_by_id(conn, [v for r in rows for v in (r["a"], r["b"])])
    items = [
        SumsParallel(
            a=verses[r["a"]],
            b=verses[r["b"]],
            unit=r["unit"],
            a_value=r["a_value"],
            b_value=r["b_value"],
            same=bool(r["same"]),
            one_step=None if r["one_step"] is None else bool(r["one_step"]),
            **{k: r[k] for k in ("a_tok_first", "a_tok_last", "b_tok_first", "b_tok_last")},
        )  # fmt: skip
        for r in rows
        if r["a"] in verses and r["b"] in verses
    ]
    return {"across": across, "differ": differ, "one_step": one_step, "book": book,
            "total": total, "offset": offset, "limit": limit, "items": items}  # fmt: skip
