"""Dependencies and parameter checks shared by the `/api` routers."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from typing import Annotated, Any

import pandas as pd
from fastapi import Depends, HTTPException, Request

from bsim.api import queries
from bsim.api.app import ServeState
from bsim.api.models.common import GoldLink
from bsim.store.analyses import SOURCES


def get_state(request: Request) -> ServeState:
    return request.app.state.serve


def get_conn(state: Annotated[ServeState, Depends(get_state)]) -> Iterator[sqlite3.Connection]:
    conn = state.acquire()
    try:
        yield conn
    finally:
        state.release(conn)


State = Annotated[ServeState, Depends(get_state)]


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]


def unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


# stage -> a table it fills (the analyses' registry, plus the stages build-db reads itself)
STAGE_TABLES: dict[str, str] = {
    **{src.stage: src.tables[0].name for src in SOURCES},
    "syntax": "clauses",
}
STAGES_RUN_LISTED = frozenset(src.stage for src in SOURCES)  # what `stages_run` can name
# table -> the stage that fills it (a missing table names its stage)
TABLE_STAGES: dict[str, str] = {t.name: src.stage for src in SOURCES for t in src.tables}


def stage_missing(stage: str) -> HTTPException:
    """503 for an analysis whose stage did not run in this build: told apart from an unknown id
    (404) by `code`, which the viewer reads to say "not computed" instead of an error."""
    return HTTPException(
        status_code=503,
        detail={
            "code": "stage_missing",
            "stage": stage,
            "message": f"not computed in this build: run `bsim {stage}`, then `bsim build-db`",
        },
    )


def stage_ran(state: ServeState, conn: sqlite3.Connection, stage: str) -> bool:
    """Listed in the DB's `stages_run` (build-db found its files); in a DB built before that
    list, its meta entry is there or its table has rows (no table at all: no)."""
    if "stages_run" in state.meta and stage in STAGES_RUN_LISTED:
        return stage in state.meta["stages_run"]
    if state.meta.get(stage.replace("-", "_")):
        return True
    try:
        return state.present(conn, STAGE_TABLES[stage])
    except sqlite3.OperationalError:
        return False


def require_stage(state: ServeState, conn: sqlite3.Connection, stage: str) -> None:
    if not stage_ran(state, conn, stage):
        raise stage_missing(stage)


def stage(name: str) -> Any:
    """A route dependency: `dependencies=[stage("ketiv")]` answers 503 `stage_missing` when
    `bsim ketiv` did not run."""
    if name not in STAGE_TABLES:
        raise KeyError(f"unknown stage {name!r}")

    def check(state: State, conn: Conn) -> None:
        require_stage(state, conn, name)

    return Depends(check)


def book_or_404(state: ServeState, book_id: int | None) -> int | None:
    """A `book=` filter: None (no filter) or a book of the canon; 404 for any other number."""
    if book_id is not None and book_id not in state.book_ids:
        raise HTTPException(status_code=404, detail=f"unknown book {book_id}")
    return book_id


def _book_filter(state: State, book: int | None = None) -> int | None:
    return book_or_404(state, book)


# the `book=` query filter of the list routes: optional, 404 for a number that is no book
BookFilter = Annotated[int | None, Depends(_book_filter)]


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


def check_cap(state: ServeState, value: int, name: str, cap: str) -> int:
    """1 ≤ value ≤ `serve.{cap}` (`max_lookup`, `max_top`), else 422."""
    high = state.cfg["serve"][cap]
    if not 1 <= value <= high:
        raise unprocessable(f"{name} must be between 1 and {high}")
    return value


def check_min(value: int | None, name: str, low: int = 1) -> None:
    if value is not None and value < low:
        raise unprocessable(f"{name} must be at least {low}")


def unit_or_404(conn: sqlite3.Connection, unit_id: str) -> dict[str, Any]:
    u = queries.unit(conn, unit_id)
    if u is None:
        raise HTTPException(status_code=404, detail=f"unknown unit {unit_id!r}")
    return u


def unit_span(conn: sqlite3.Connection, unit_id: str | None) -> tuple[int, int] | None:
    """(first, last) verse id of a `unit` filter (None: no filter; 404: unknown unit)."""
    if unit_id is None:
        return None
    u = unit_or_404(conn, unit_id)
    return u["start_verse_id"], u["end_verse_id"]


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


def span_label(labels: dict[int, tuple[str, str]], first: int, last: int, lang: int) -> str:
    """A verse range's label from its ends' labels (`queries.verse_labels`; `lang` 0 English,
    1 Hebrew): "Genesis 24:2" + "Genesis 24:16" -> "Genesis 24:2–16"."""
    a, b = labels[first][lang], labels[last][lang]
    if first == last:
        return a
    common = 0
    while common < min(len(a), len(b)) and a[common] == b[common]:
        common += 1
    cut = max(a.rfind(" ", 0, common), a.rfind(":", 0, common)) + 1
    return f"{a}–{b[cut:]}" if cut > 0 else f"{a} – {b}"
