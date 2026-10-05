"""`/export/{list}.csv`: every row of a list view under its current filters, as CSV.

The list endpoints serve pages of at most `serve.max_page` rows; an export calls the same
handler page by page (so the filters and their checks are the endpoint's own) up to
`serve.export_max_rows` rows, and flattens each item to readable columns: a unit becomes its
label, a lemma its Hebrew form, a verse its reference, and verse texts are left out.
"""

from __future__ import annotations

import csv
import inspect
import io
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from bsim.api.routes import core, parallels, phrases, poetics
from bsim.api.routes import corpus as corpus_routes
from bsim.api.routes._common import Conn, State, unprocessable

router = APIRouter()

# list name -> list handler (all take `limit` / `offset` and return `{"total", "items"}`)
EXPORTS: dict[str, Callable[..., dict[str, Any]]] = {
    "discoveries": core.discoveries,
    "concordance": core.lemma,
    "phrases": phrases.phrases,
    "sequences": parallels.sequences,
    "changes": parallels.changes,
    "rewrites": parallels.rewrites,
    "typescenes": parallels.typescenes,
    "poetry": poetics.parallelism_ranking,
    "word-pairs": poetics.word_pairs,
    "wordplay": poetics.wordplay,
    "alliteration": poetics.alliteration,
    "rhymes": poetics.rhymes,
    "structure": poetics.structure_ranking,
    "acrostics": poetics.acrostics,
    "names": corpus_routes.entities,
}
SKIPPED = {"verse", "verses", "a_verse", "b_verse", "text_display", "display_tokens", "matrix"}
INTERNAL = {"state", "conn", "limit", "offset", "response"}


def _convert(value: str, annotation: Any) -> Any:
    ann = str(annotation)
    if "bool" in ann:
        return value.lower() in ("1", "true", "yes")
    if "int" in ann and "float" not in ann:
        return int(value)
    if "float" in ann:
        return float(value)
    return value


def _label(v: dict[str, Any]) -> Any:
    """A nested object as one readable value, or None when it has no natural label."""
    for key in ("label_en", "he_lemma", "label", "ref", "letter"):
        if key in v:
            return v[key]
    return None


def flatten(item: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in item.items():
        if k in SKIPPED:
            continue
        name = f"{prefix}{k}"
        if isinstance(v, dict):
            label = _label(v)
            if label is not None:
                out[name] = label
            else:
                out.update(flatten(v, f"{name}."))
        elif isinstance(v, list):
            parts = [
                _label(x) if isinstance(x, dict) else x
                for x in v
                if not isinstance(x, (dict, list))
                or (isinstance(x, dict) and _label(x) is not None)
            ]
            if parts:
                out[name] = "; ".join(str(x) for x in parts)
        else:
            out[name] = v
    return out


@router.get("/export/{name}.csv", include_in_schema=False)
def export(name: str, request: Request, state: State, conn: Conn) -> Response:
    handler = EXPORTS.get(name)
    if handler is None:
        raise HTTPException(status_code=404, detail=f"unknown list {name!r}")
    params = inspect.signature(handler).parameters
    kwargs: dict[str, Any] = {}
    for key, value in request.query_params.items():
        if key in INTERNAL or key not in params:
            continue
        try:
            kwargs[key] = _convert(value, params[key].annotation)
        except ValueError as e:
            raise unprocessable(f"bad value for {key}: {value!r}") from e
    for key, p in params.items():  # unset parameters take the handler's defaults
        if key not in kwargs and key not in INTERNAL and p.default is not inspect.Parameter.empty:
            kwargs[key] = p.default
        elif key not in kwargs and key not in INTERNAL:
            raise unprocessable(f"{key} is required")
    if "response" in params:
        kwargs["response"] = Response()

    page, cap = state.cfg["serve"]["max_page"], state.cfg["serve"]["export_max_rows"]
    rows: list[dict[str, Any]] = []
    while len(rows) < cap:
        body = handler(state=state, conn=conn, limit=page, offset=len(rows), **kwargs)
        items = [i.model_dump() if isinstance(i, BaseModel) else i for i in body["items"]]
        rows += [flatten(i) for i in items]
        if len(items) < page or len(rows) >= body["total"]:
            break
    columns = list(dict.fromkeys(k for r in rows for k in r))
    buf = io.StringIO()
    buf.write("﻿")  # Excel reads UTF-8 (Hebrew) only with a BOM
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows[:cap])
    return Response(
        buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}.csv"'},
    )
