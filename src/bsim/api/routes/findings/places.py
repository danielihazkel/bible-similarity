"""`/findings` builders. Places: lists on the ground, the geographic arc, places named together."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

from bsim.api.models.findings import Finding
from bsim.api.routes.findings.common import Meta


def _place_lists(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """The place lists against shuffles (§16.58): every list's path shorter than random orders of
    its places (`place_lists_order`); every grouping's towns closer within a district than with
    the labels shuffled (`place_lists_districts`). Holds when all do on every located place; how
    many still do on sure sites alone is a value."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        pl = meta.get("place_lists") or {}
        if key == "place_lists_order":
            o = pl.get("order") or {}
            a, s = o.get("all") or {}, o.get("sure") or {}
            ps = [li["p"] for li in (pl.get("lists") or {}).values() if li.get("p") is not None]
        else:
            groups = list((pl.get("districts") or {}).values())
            tested = {v: [g[v]["p"] for g in groups if (g.get(v) or {}).get("p") is not None]
                      for v in ("all", "sure")}  # fmt: skip
            a = {"n": len(tested["all"]), "held": sum(p <= alpha for p in tested["all"])}
            s = {"n": len(tested["sure"]), "held": sum(p <= alpha for p in tested["sure"])}
            ps = tested["all"]
        if not a.get("n"):
            return None
        values = {"n": a["n"], "held": a.get("held"), "sure_n": s.get("n"),
                  "sure_held": s.get("held"), "max_p": max(ps) if ps else None}  # fmt: skip
        holds = a.get("held") == a["n"]
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build

def _place_arc(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """The geographic arc (§16.60): consecutive placed chapters closer than in shuffled orders,
    over all books (`place_arc_order`); every known move goes from its region towards the next
    (`place_arc_moves`); the oracles against the nations wider than the other prophetic chapters
    on spread or reach at `alpha` / 2 (`place_arc_oracles`)."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        pa = meta.get("place_arc") or {}
        if key == "place_arc_order":
            a = pa.get("arc") or {}
            if a.get("p") is None:
                return None
            values = {k: a.get(k) for k in ("placed", "chapters", "mean_step", "null_mean", "p",
                                            "books", "books_held")}  # fmt: skip
            holds = a["mean_step"] < a["null_mean"] and a["p"] <= alpha
            return Finding(key=key, verdict="holds" if holds else "fails", values=values)
        if key == "place_arc_moves":
            moves = [m for m in pa.get("moves") or [] if m.get("holds") is not None]
            if not moves:
                return None
            values = {"n": len(moves), "held": sum(m["holds"] for m in moves)}
            values |= {f"{m['key']}_km": m.get("km") for m in moves}
            holds = all(m["holds"] for m in moves)
            return Finding(key=key, verdict="holds" if holds else "fails", values=values)
        o = pa.get("oracles") or {}
        if not o.get("spread"):
            return None
        values = {"n": o["spread"]["n"], "n_other": o["spread"]["n_other"]}
        for m in ("spread", "reach"):
            r = o[m]
            values |= {f"{m}_observed": r["observed"], f"{m}_other": r["other"], f"{m}_p": r["p"]}
        holds = any(o[m]["p"] <= alpha / 2 for m in ("spread", "reach"))
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build

def _place_links(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """Do places named together lie together (§16.61)? `place_links_decay`: the linked pairs'
    G² falls with km, rho below the shuffled coordinates' at `alpha` on every located place (the
    sure-site and no-lists variants as values); `place_links_known`: every known far pair
    ("from Dan to Beersheba") among the top leads."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        pl = meta.get("place_links") or {}
        if key == "place_links_known":
            known = pl.get("known") or []
            if not known:
                return None
            values = {"n": len(known), "held": sum(bool(k["holds"]) for k in known),
                      "top": pl.get("top"), "rank": known[0].get("rank"),
                      "km": known[0].get("km")}  # fmt: skip
            holds = all(k["holds"] for k in known)
            return Finding(key=key, verdict="holds" if holds else "fails", values=values)
        tests = pl.get("tests") or {}
        a = tests.get("all") or {}
        if a.get("p") is None:
            return None
        values = {k: a.get(k) for k in ("pairs", "places", "rho", "null_mean", "p")}
        for v in ("sure", "no_lists"):
            values |= {f"{v}_rho": (tests.get(v) or {}).get("rho"),
                       f"{v}_p": (tests.get(v) or {}).get("p")}  # fmt: skip
        holds = a["rho"] < a["null_mean"] and a["p"] <= alpha
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build
