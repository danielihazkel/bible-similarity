"""Dependencies and parameter checks shared by the `/api` routers."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from typing import Annotated, Any

import pandas as pd
from fastapi import Depends, HTTPException, Request

from bsim.api import queries
from bsim.api.app import ServeState
from bsim.api.models import (
    GoldLink,
)


def get_state(request: Request) -> ServeState:
    return request.app.state.serve


def get_conn(state: Annotated[ServeState, Depends(get_state)]) -> Iterator[sqlite3.Connection]:
    conn = state.connect()
    try:
        yield conn
    finally:
        conn.close()


State = Annotated[ServeState, Depends(get_state)]


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]


def unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


def check_k(state: ServeState, k: int | None) -> int:
    k = state.cfg["serve"]["default_k"] if k is None else k
    k_max = state.cfg["retrieval"]["k"]
    if not 1 <= k <= k_max:
        raise unprocessable(f"k must be between 1 and {k_max}")
    return k


def check_page(state: ServeState, limit: int, offset: int) -> None:
    max_page = state.cfg["serve"]["max_page"]
    if not 1 <= limit <= max_page:
        raise unprocessable(f"limit must be between 1 and {max_page}")
    if offset < 0:
        raise unprocessable("offset must not be negative")


def unit_or_404(conn: sqlite3.Connection, unit_id: str) -> dict[str, Any]:
    u = queries.unit(conn, unit_id)
    if u is None:
        raise HTTPException(status_code=404, detail=f"unknown unit {unit_id!r}")
    return u


def verse_or_404(state: ServeState, verse_id: int) -> int:
    if not 0 <= verse_id < state.n_verses:
        raise HTTPException(status_code=404, detail=f"unknown verse {verse_id}")
    return verse_id


def num(v: Any, cast: type) -> Any:
    """numpy / pandas scalar -> int or float; NaN / NA (missing breakdown) -> None."""
    return None if v is None or pd.isna(v) else cast(v)


def gold_link(level: str | None, types: str | None) -> GoldLink | None:
    if level is None:
        return None
    return GoldLink(level=level, types=[t for t in (types or "").split(",") if t])


def check_unit_type(unit_type: str, allowed: list[str]) -> str:
    if unit_type not in allowed:
        raise unprocessable(f"unknown unit type {unit_type!r}; choose from {list(allowed)}")
    return unit_type
