"""`/findings`: the headline result of each analysis, from what its stage recorded (DESIGN.md §10).

Each finding names the claim an analysis tested, the numbers that decide it and a verdict computed
from them at `serve.findings.alpha`, so the page follows a rebuilt DB:

    holds   the expectation is borne out above chance (or the check passes)
    fails   it is not: no better than chance, or the data point the other way
    lead    candidates without a test that separates them from chance

The wording lives in the viewer's catalogs; an analysis whose stage did not run is left out.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter

from bsim.api.models import Finding, FindingsResponse
from bsim.api.routes._common import Conn, State

router = APIRouter()

Meta = dict[str, Any]


def _acrostics(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    a = meta.get("acrostics")
    if not a:
        return None
    found = conn.execute("SELECT COUNT(*) FROM acrostics WHERE q <= ?", (alpha,)).fetchone()[0]
    values = {"found": found, "recall": a.get("known_recall")}
    return Finding(key="acrostics", verdict="holds" if found else "fails", values=values)


def _sevens(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    n = meta.get("leitwort_numbers") or {}
    ratios = {
        int(m): v["multiples"] / v["expected"]
        for m, v in n.items()
        if m.isdigit() and v.get("expected")  # a small corpus can expect no multiples at all
    }
    if 7 not in ratios:
        return None
    values = {
        "ratio7": ratios[7],
        "ratio10": ratios.get(10),
        "smallest": min(ratios, key=ratios.__getitem__),
        "largest": max(ratios, key=ratios.__getitem__),
    }
    # the claim: multiples of 7 stand out; they do only if 7 beats every control divisor
    verdict = "holds" if values["largest"] == 7 else "fails"
    return Finding(key="sevens", verdict=verdict, values=values)


def _chiasm(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    w = ((meta.get("mirrors") or {}).get("words") or {}).get("all")
    if not w:
        return None
    values = {k: w[k] for k in ("verses_chiastic", "verses_parallel", "share", "p")}
    # the claim: repeated words favour the mirrored order
    holds = w["share"] > 0.5 and w["p"] <= alpha
    return Finding(key="chiasm", verdict="holds" if holds else "fails", values=values)


def _clauses(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    c = (meta.get("mirrors") or {}).get("clauses")
    if not c or c.get("p") is None:
        return None
    values = {k: c[k] for k in ("poetry", "prose", "poetry_n", "prose_n", "p")}
    holds = c["poetry"] > c["prose"] and c["p"] <= alpha
    return Finding(key="clauses", verdict="holds" if holds else "fails", values=values)


def _divisions(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    g = (meta.get("segments") or {}).get("groups") or {}
    if "mam_pe" not in g or "unmarked" not in g:
        return None
    values = {
        "open": g["mam_pe"]["score"],
        "closed": g["mam_samekh"]["score"],
        "unmarked": g["unmarked"]["score"],
        "null": g["mam_pe"]["null"],
        "p": max(g["mam_pe"]["p"], g["mam_samekh"]["p"]),
    }
    return Finding(
        key="divisions", verdict="holds" if values["p"] <= alpha else "fails", values=values
    )


def _dating(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    d = meta.get("dating") or {}
    s = d.get("synoptic")
    if not s:
        return None
    values = {"later": s["later"], "pairs": s["pairs"], "p": s["p"], "auc": d.get("held_out_auc")}
    return Finding(key="dating", verdict="holds" if s["p"] <= alpha else "fails", values=values)


def _borrowing(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    h = (meta.get("borrowing") or {}).get("held_out")
    if not h:
        return None
    values = {k: h[k] for k in ("agree", "n", "unclear", "p")}
    return Finding(key="borrowing", verdict="holds" if h["p"] <= alpha else "fails", values=values)


def _citations(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    fam = (meta.get("citations") or {}).get("families") or {}
    c = fam.get("command")
    if not c or c.get("p") is None:
        return None
    others = [f["p"] for k, f in fam.items() if k != "command" and f.get("p") is not None]
    values = {
        "share": c["share"],
        "null": c["null_share"],
        "p": c["p"],
        "others_held": sum(p <= alpha for p in others),
        "others": len(others),
    }
    return Finding(key="citations", verdict="holds" if c["p"] <= alpha else "fails", values=values)


def _voices(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    v = meta.get("voices") or {}
    if not v.get("speakers"):
        return None
    values = {
        "significant": v["significant"],
        "speakers": v["speakers"],
        "calibration": (v.get("calibration") or {}).get("significant"),
    }
    holds = v["significant"] > 0 and not values["calibration"]
    return Finding(key="voices", verdict="holds" if holds else "fails", values=values)


def _echoes(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    e = meta.get("echoes") or {}
    s = (e.get("checks") or {}).get("spelling")
    if not s:
        return None
    values = {
        "agree": s["agree"],
        "n": s["n"],
        "p": s["p"],
        "backward": e.get("language_backward"),
        "language": (e.get("language_backward") or 0) + (e.get("language_forward") or 0),
    }
    holds = not s["underpowered"] and s["p"] <= alpha
    return Finding(key="echoes", verdict="holds" if holds else "fails", values=values)


def _allusions(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    a = meta.get("allusions") or {}
    if not a.get("pairs"):
        return None
    values = {k: a.get(k) for k in ("pairs", "known", "strong", "strong_known", "best_new_q")}
    new_hold = a.get("best_new_q") is not None and a["best_new_q"] <= alpha
    return Finding(key="allusions", verdict="holds" if new_hold else "lead", values=values)


BUILDERS: list[Callable[[Meta, sqlite3.Connection, float], Finding | None]] = [
    _acrostics,
    _divisions,
    _dating,
    _borrowing,
    _citations,
    _voices,
    _clauses,
    _echoes,
    _sevens,
    _chiasm,
    _allusions,
]


@router.get("/findings", response_model=FindingsResponse)
def findings(state: State, conn: Conn) -> dict[str, Any]:
    """The tested claims of the analyses with their deciding numbers and verdicts."""
    alpha = state.cfg["serve"]["findings"]["alpha"]
    items = [f for b in BUILDERS if (f := b(state.meta, conn, alpha)) is not None]
    return {"alpha": alpha, "items": items}
