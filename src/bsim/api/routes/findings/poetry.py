"""`/findings` builders. Poetry and form: acrostics, sevens, chiasm, meter, laments, refrains,
psalms, forms, prophetic forms."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

from bsim.api.models.findings import Finding
from bsim.api.routes.findings.common import Meta


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


def _forms(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """Graded numerical sayings and lists: the sayings named in advance found; graded pairs
    against the book's numbers placed at random; sayings in parallel lines against other verses
    with two numbers; the lists named in advance found among more lists than chance gives."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        f = meta.get("forms") or {}
        if key == "forms_known":
            if not f.get("known"):
                return None
            n = len(f["known"])
            values = {"found": f.get("known_found"), "n": n, "sayings": f.get("sayings")}
            holds = (f.get("known_found") or 0) / n >= f.get("known_share", 2 / 3)
        elif key == "forms_chance":
            c = f.get("chance") or {}
            if c.get("p") is None:
                return None
            values = {k: c.get(k) for k in ("observed", "expected", "p", "without_observed",
                                            "without_expected", "without_p")}  # fmt: skip
            holds = c["observed"] > c["expected"] and c["p"] <= alpha
        elif key == "forms_parallel":
            c = f.get("parallel") or {}
            if c.get("p") is None:
                return None
            values = {k: c.get(k) for k in ("sayings", "others", "saying_parallel",
                                            "other_parallel", "p")}  # fmt: skip
            holds = c["saying_prob"] > c["other_prob"] and c["p"] <= alpha
        else:
            li = f.get("lists") or {}
            if not li.get("known"):
                return None
            n = len(li["known"])
            values = {"found": li.get("known_found"), "n": n, "lists": li.get("observed"),
                      "expected": li.get("expected")}  # fmt: skip
            holds = (li.get("known_found") or 0) / n >= li.get("known_share", 2 / 3) and (
                li.get("observed") or 0
            ) > (li.get("expected") or 0)
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build


def _prophetic(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    """The prophetic forms: the passages named in advance found, each form's findings counted."""
    m = meta.get("prophetic") or {}
    if not m.get("known"):
        return None
    values = {"known": m["known_found"], "of": m["known_total"], **(m.get("counts") or {})}
    return Finding(key="prophetic", verdict="holds" if m["known_holds"] else "fails", values=values)
