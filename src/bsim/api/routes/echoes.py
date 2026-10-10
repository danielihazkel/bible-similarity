"""A direction on the cross-book echoes (DESIGN.md §16.36): the checks, the book graph, the
chapters drawn on most and every chapter pair with the layer that decided it."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models import (
    EchoBasis,
    EchoBook,
    EchoChapter,
    EchoEdge,
    EchoesResponse,
    EchoListResponse,
    UnitSummary,
)
from bsim.api.routes._common import Conn, State, check_page, unit_span, unprocessable

router = APIRouter()


@router.get("/echoes", response_model=EchoesResponse)
def echoes(state: State, conn: Conn, top: int = 20) -> dict[str, Any]:
    """The checks, directed pairs per book pair and the chapters other books draw on most."""
    if not 1 <= top <= 100:
        raise unprocessable("top must be between 1 and 100")
    rows = queries.echo_sources(conn, top)
    units = queries.units_by_id(conn, [r["unit_id"] for r in rows])
    return {
        "meta": state.meta.get("echoes") or {},
        "books": [EchoBook(**r) for r in queries.echo_books(conn)],
        "sources": [
            EchoChapter(
                unit=UnitSummary(**units[r["unit_id"]]),
                **{k: r[k] for k in ("lends", "borrows", "lends_explicit", "borrows_explicit")},
            )
            for r in rows
        ],
    }


@router.get("/echoes/list", response_model=EchoListResponse)
def echo_list(
    state: State,
    conn: Conn,
    basis: EchoBasis | None = None,
    directed: bool | None = None,
    backward: bool | None = None,
    book: int | None = None,
    unit: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Chapter pairs, cited first, then borrowed and language; `backward`: the echo comes earlier
    in the canon than its source; `unit`: either chapter overlapping it."""
    check_page(state, limit, offset)
    total, rows = queries.echoes_page(
        conn, basis, directed, backward, book, unit_span(conn, unit), limit, offset
    )
    units = queries.units_by_id(conn, [u for r in rows for u in (r["a"], r["b"])])
    items = [
        EchoEdge(
            a=UnitSummary(**units[r["a"]]),
            b=UnitSummary(**units[r["b"]]),
            **{k: r[k] for k in EchoEdge.model_fields if k not in ("a", "b")},
        )
        for r in rows
    ]
    return {
        "basis": basis,
        "directed": directed,
        "backward": backward,
        "book": book,
        "unit": unit,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
    }
