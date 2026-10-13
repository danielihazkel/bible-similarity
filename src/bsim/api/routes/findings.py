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


def _meter(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    m = meta.get("meter") or {}
    t = m.get("test") or {}
    if t.get("p") is None:
        return None
    control = (m.get("control") or [{}])[0]
    values = {
        "mean": t["mean"],
        "pool_mean": t["pool_mean"],
        "p": t["p"],
        "poetic_p": (m.get("test_poetic") or {}).get("p"),
        "control_pct": control.get("pct"),
    }
    # the claim: Lamentations 1-4 fall (long member, then short) more than other poetry
    holds = t["mean"] > t["pool_mean"] and t["p"] <= alpha
    return Finding(key="meter", verdict="holds" if holds else "fails", values=values)


def _cognate(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    t = ((meta.get("roots") or {}).get("tests") or {}).get("cognate")
    if not t:
        return None
    values = {k: t[k] for k in ("observed", "expected", "ratio", "p")}
    # the claim: a verb takes a noun of its own root nearby more often than chance
    holds = t["ratio"] > 1 and t["p"] <= alpha
    return Finding(key="cognate", verdict="holds" if holds else "fails", values=values)


def _root_leitworte(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    r = meta.get("roots") or {}
    if not r.get("known"):
        return None
    values = {
        "n": len(r["known"]),
        "top": r.get("top"),
        "by_root": r.get("known_top_root"),
        "by_lemma": r.get("known_top_lemma"),
        "better": r.get("known_better"),
        "hidden": r.get("hidden"),
    }
    # the claim: counted by root, the Leitworte scholarship names rank higher than by lemma
    holds = (r.get("known_top_root") or 0) > (r.get("known_top_lemma") or 0)
    return Finding(key="root_leitworte", verdict="holds" if holds else "fails", values=values)


def _laments(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    n = (meta.get("meter") or {}).get("named") or {}
    if n.get("p") is None:
        return None
    values = {k: n[k] for k in ("n", "mean", "pool_mean", "p")}
    holds = n["mean"] > n["pool_mean"] and n["p"] <= alpha
    return Finding(key="laments", verdict="holds" if holds else "fails", values=values)


def _refrains(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    r = meta.get("refrains") or {}
    if not r.get("known"):
        return None
    d = r.get("detect") or {}
    values = {
        "found": r.get("known_found"),
        "n": len(r["known"]),
        "refrains": d.get("observed"),
        "expected": d.get("expected"),
        "distinct": r.get("distinct"),
    }
    # the claim: the refrains scholarship names are found, among more refrains than chance gives
    share = (r.get("known_found") or 0) / len(r["known"])
    holds = share >= r.get("known_share", 2 / 3) and (d.get("observed") or 0) > (
        d.get("expected") or 0
    )
    return Finding(key="refrains", verdict="holds" if holds else "fails", values=values)


def _refrain_regular(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    g = (meta.get("refrains") or {}).get("regular") or {}
    if not g.get("testable"):
        return None
    values = {k: g.get(k) for k in ("testable", "regular", "share", "p")}
    # the claim: refrains recur at more even intervals than the same number placed at random
    holds = g["share"] > alpha and g["p"] <= alpha
    return Finding(key="refrain_regular", verdict="holds" if holds else "fails", values=values)


def _refrain_turns(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    t = (meta.get("refrains") or {}).get("turns") or {}
    if t.get("p") is None:
        return None
    values = {k: t.get(k) for k in ("n", "observed", "expected", "p")}
    # the claim: a refrain's verse stands next to a sharper turn than other verses of its span
    holds = t["observed"] > t["expected"] and t["p"] <= alpha
    return Finding(key="refrain_turns", verdict="holds" if holds else "fails", values=values)


def _psalm_genres(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    p = meta.get("psalms") or {}
    g = p.get("genre_test")
    if not g:
        return None
    values = {"nmi": g["nmi"], "null": g["null"], "p": g["p"], "labelled": p.get("labelled"),
              "k": p.get("k")}  # fmt: skip
    # the claim: clusters of the counted form recover Gunkel's genres beyond shuffled labels
    holds = g["nmi"] > g["null"] and g["p"] <= alpha
    return Finding(key="psalm_genres", verdict="holds" if holds else "fails", values=values)


def _psalm_forms(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    checks = (meta.get("psalms") or {}).get("checks")
    if not checks:
        return None
    held = sum(c["q"] <= alpha for c in checks)
    values = {"held": held, "n": len(checks), "max_q": max(c["q"] for c in checks)}
    # the claim: each genre shows the form named in advance (persons, imperatives, mood)
    return Finding(
        key="psalm_forms", verdict="holds" if held == len(checks) else "fails", values=values
    )


def _lament_turn(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    k = (meta.get("psalms") or {}).get("known_turns")
    if not k:
        return None
    values = {key: k.get(key) for key in ("found", "n", "expected", "p")}
    # the claim: the turn found falls at the turns scholarship names more often than chance
    holds = k["found"] > k["expected"] and k["p"] <= alpha
    return Finding(key="lament_turn", verdict="holds" if holds else "fails", values=values)


def _lament_turns(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    t = (meta.get("psalms") or {}).get("laments_vs_hymns")
    if not t:
        return None
    values = {key: t.get(key) for key in ("laments", "n_laments", "hymns", "n_hymns", "p")}
    # the claim: individual laments turn to praise (above chance) more often than hymns
    return Finding(
        key="lament_turns", verdict="holds" if t["p"] <= alpha else "fails", values=values
    )


def _pentateuch(key: str, test: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """The P / non-P split's checks: agreement with the reference (all, Genesis alone) and the
    divine names it never saw, each against the split shifted within books."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        s = meta.get("pentateuch") or {}
        t = (s.get("tests") or {}).get(test)
        if not t:
            return None
        values = {"observed": t["observed"], "null": t["null"], "p": t["p"],
                  "agreement": s.get("agreement")}  # fmt: skip
        if test == "names":
            n = s.get("names") or {}
            values.update(p_like=(n.get("p_like") or {}).get("share"),
                          non_p=(n.get("non_p") or {}).get("share"))  # fmt: skip
        holds = t["observed"] > t["null"] and t["p"] <= alpha
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build


BUILDERS: list[Callable[[Meta, sqlite3.Connection, float], Finding | None]] = [
    _acrostics,
    _divisions,
    _dating,
    _borrowing,
    _citations,
    _voices,
    _clauses,
    _meter,
    _cognate,
    _echoes,
    _sevens,
    _chiasm,
    _laments,
    _root_leitworte,
    _refrains,
    _refrain_regular,
    _refrain_turns,
    _psalm_genres,
    _psalm_forms,
    _lament_turn,
    _lament_turns,
    _pentateuch("pentateuch_split", "kappa"),
    _pentateuch("pentateuch_genesis", "kappa_genesis"),
    _pentateuch("pentateuch_names", "names"),
    _allusions,
]


@router.get("/findings", response_model=FindingsResponse)
def findings(state: State, conn: Conn) -> dict[str, Any]:
    """The tested claims of the analyses with their deciding numbers and verdicts."""
    alpha = state.cfg["serve"]["findings"]["alpha"]
    items = [f for b in BUILDERS if (f := b(state.meta, conn, alpha)) is not None]
    return {"alpha": alpha, "items": items}
