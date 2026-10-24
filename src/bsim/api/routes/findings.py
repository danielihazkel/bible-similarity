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

from bsim.api.models.findings import Finding, FindingsResponse
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


def _dialogue(key: str, test: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """Who speaks to whom: "your servant" and נא in speech addressed up (to God or a king), each
    against the "up" label permuted within books; the last word in exchanges between unequal
    parties, against the higher one's share of the turns."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        t = ((meta.get("dialogue") or {}).get("tests") or {}).get(test)
        if not t or t.get("p") is None:
            return None
        if test == "last_word":
            values = {k: t[k] for k in ("observed", "expected", "exchanges", "p")}
            holds = t["observed"] > t["expected"] and t["p"] <= alpha
        else:
            values = {"up": t["up"]["rate"], "rest": t["rest"]["rate"], "p": t["p"],
                      "up_count": t["up"]["count"], "up_of": t["up"]["of"]}  # fmt: skip
            holds = t["observed"] > 0 and t["p"] <= alpha
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build


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


def _ciphers(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """Atbash and albam against random pairings of the letters: the cases named in advance found;
    atbash in the chapters named, atbash elsewhere and albam anywhere reading more names than the
    random pairings do."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        c = meta.get("ciphers") or {}
        if key == "ciphers_known":
            if not c.get("known"):
                return None
            n = len(c["known"])
            values = {"found": c.get("known_found"), "n": n}
            holds = c.get("known_found") == n
        else:
            t = (c.get("tests") or {}).get(key.removeprefix("ciphers_")) or {}
            if t.get("p") is None:
                return None
            values = {k: t.get(k) for k in ("observed", "expected", "p")}
            values["random_hits"] = c.get("random_hits")
            holds = t["observed"] > t["expected"] and t["p"] <= alpha
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build


def _divine(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """The divine names: Psalms' best three-part split by the mix of יהוה and אלהים finds the
    Elohistic Psalter named in advance and beats its shuffles; in the doubled psalms the side
    inside it has אלהים for the other's יהוה more often than the reverse (sign test)."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        d = meta.get("divine") or {}
        if key == "divine_elohistic":
            e = d.get("elohistic") or {}
            if e.get("p") is None:
                return None
            values = {k: e.get(k) for k in ("first", "last", "p", "gain")}
            values |= {"named_first": e["named"][0], "named_last": e["named"][1]}
            values |= {f"share{i + 1}": s for i, s in enumerate(e.get("shares") or [])}
            holds = bool(e.get("found")) and e["p"] <= alpha
        else:
            c = d.get("doubled") or {}
            if not c.get("pairs"):
                return None
            values = {k: c.get(k) for k in ("e_ward", "y_ward", "p")}
            values["pairs"] = len(c["pairs"])
            holds = c["e_ward"] > c["y_ward"] and c["p"] <= alpha
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build


def _etiologies(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """Naming etiologies: a name echoes its own explanation more than the explanations shuffled
    among the names; the etiologies named in advance are found, and most of them echo."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        e = meta.get("etiologies") or {}
        if not e.get("namings"):
            return None
        if key == "etiology_echo":
            values = {k: e.get(k) for k in ("namings", "mean_own", "mean_null", "p", "leads")}
            holds = e["mean_own"] > e["mean_null"] and e["p"] <= alpha
        else:
            values = {k: e.get(k) for k in ("known_found", "known_echo", "known_rank")}
            values["known"] = len(e.get("known") or [])
            holds = bool(e.get("known_holds"))
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build


def _brackets(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """Resumptive repetition: the blocks inside repeated clauses interrupt their surroundings
    more than random brackets of the same span; the editors' brackets named in advance are found
    and each beats its random brackets."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        b = meta.get("brackets") or {}
        if not b.get("brackets"):
            return None
        if key == "brackets_insertion":
            values = {k: b.get(k) for k in ("brackets", "mean", "mean_null", "p", "leads")}
            holds = b["mean"] > b["mean_null"] and b["p"] <= alpha
        else:
            values = {k: b.get(k) for k in ("known_found", "known_beat")}
            values["known"] = len(b.get("known") or [])
            holds = bool(b.get("known_holds"))
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build


def _retold(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """Retold speech: a speech retold by another speaker changes more than one carried out in
    narration (labels shuffled within length strata); the retellings named in advance are
    found."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        r = meta.get("retold") or {}
        if not r.get("pairs"):
            return None
        if key == "retold_claim":
            a, b = r["claim"]
            values = {"pairs": r["pairs"], "difference": r.get("difference"), "p": r["p"],
                      "a_rate": r["rates"].get(a), "b_rate": r["rates"].get(b),
                      "a_n": r["groups"].get(a), "b_n": r["groups"].get(b)}  # fmt: skip
            holds = bool(r.get("holds"))
        else:
            values = {"known_found": r.get("known_found"), "known": len(r.get("known") or [])}
            holds = bool(r.get("known_holds"))
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build


def _haftarot(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """Haftarot: a parasha's haftarah ranks higher among the Prophets' chapters than haftarot
    shuffled among the parashot; higher than the haftarot the calendar fixes; the known ones in
    the first chapters."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        h = meta.get("haftarot") or {}
        if not h.get("parashot"):
            return None
        if key == "haftarot_claim":
            values = {k: h.get(k) for k in ("thematic", "thematic_pct", "shuffled_pct", "p",
                                             "candidates")}  # fmt: skip
            modes = h.get("modes") or {}
            values |= {f"{m}_mrr": e["mrr"] for m, e in modes.items()}
            values |= {f"{m}_hits": e["hits"] for m, e in modes.items()}
            values["list"] = h.get("list")
            holds = bool(h.get("holds"))
        elif key == "haftarot_calendar":
            values = {k: h.get(k) for k in ("thematic_pct", "calendar_pct", "calendar_p")}
            holds = bool(h.get("calendar_holds"))
        else:
            known = h.get("known") or []
            values = {"known": len(known), "known_rank": h.get("known_rank"),
                      "found": sum(bool(k["holds"]) for k in known)}  # fmt: skip
            values |= {f"rank_{i}": k["rank"] for i, k in enumerate(known)}
            holds = bool(h.get("known_holds"))
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build


def _chronology(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """The text's own chronology: the Flood, Abram and the Exodus at Seder Olam's years; the
    years between the kings' synchronisms agree in both kingdoms' counts more often than with the
    reigns shuffled; Gen 5's year numbers end in 0 / 2 / 5 / 7 more often than the others."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        c = meta.get("chronology") or {}
        if not c.get("events"):
            return None
        if key == "chronology_known":
            known = c.get("known") or []
            values = {f"{k['event']}": k["year"] for k in known}
            values |= {f"{k['event']}_expected": k["expected"] for k in known}
            values["conflicts"] = c.get("conflicts")
            holds = bool(c.get("known_holds"))
        elif key == "chronology_syncs":
            values = {k: c.get(k) for k in ("agree", "intervals", "expected", "p", "tolerance")}
            rules = c.get("rules") or {}
            values |= {f"{k}_accession": float(v == "accession") for k, v in rules.items()}
            holds = bool(c.get("holds"))
        else:
            d = c.get("digits") or {}
            values = {k: d.get(k) for k in ("hits", "n", "share", "rest_share", "p")}
            holds = bool(d.get("holds"))
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build


def _frameworks(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """The narrative frameworks: the judges' cycle grows less complete through the book;
    Othniel's is whole and Samson's broken; the kings' verdicts are worded alike within a kingdom;
    the known verdicts are read."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        f = meta.get("frameworks") or {}
        if not f.get("episodes"):
            return None
        if key == "frameworks_cycle":
            values = {"rho": f.get("rho"), "p": f.get("cycle_p"), "episodes": f.get("episodes"),
                      "slots": len(f.get("slots") or [])}  # fmt: skip
            holds = bool(f.get("cycle_holds"))
        elif key == "frameworks_cycle_known":
            known = f.get("known_cycle") or []
            values = {f"{k['episode']}_missing": len(k["missing"]) for k in known}
            values["slots"] = len(f.get("slots") or [])
            holds = bool(f.get("known_cycle_holds"))
        elif key == "frameworks_verdicts":
            values = {k: f.get(k) for k in ("verdicts", "within_all", "between", "difference",
                                             "expected")}  # fmt: skip
            values["p"] = f.get("verdict_p")
            values |= {f"within_{k}": v for k, v in (f.get("within") or {}).items()}
            holds = bool(f.get("verdict_holds"))
        else:
            known = f.get("known_verdicts") or []
            values = {"known": len(known), "found": sum(bool(k["holds"]) for k in known)}
            holds = bool(f.get("known_verdicts_holds"))
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build


def _masorah(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """The Masorah's counts on our text: the middle letter, words and verse of the Torah land
    within `masorah.tolerance` units of ours; our books have the Masorah's verse totals. A check
    of the text, not a test against chance."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        c = ((meta.get("masorah") or {}).get("checks") or {}).get(
            {"masorah_words": "word"}.get(key, key.removeprefix("masorah_"))
        )
        if not c:
            return None
        if key == "masorah_books":
            values = {k: c.get(k) for k in ("n", "agree", "max_diff", "reasoned")}
            holds = c["agree"] == c["n"]
        else:
            values = {k: c.get(k) for k in ("n", "distance", "verses_apart")}
            holds = bool(c["holds"])
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build


def _gematria_links(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """Do equal letter values link related words (§16.59)? `gematria_links`: equal-value pairs
    more related than matched pairs on any of the three measures at `alpha` / 3 (Bonferroni);
    `gematria_measures`: the check, pairs of one root family closer on domains and vectors;
    `gematria_genesis`: Gen 1:1 singular by its own numbers where few verses are (the share of
    verses that are the only one with their own word count, letter count and largest prime
    factor at most `alpha`)."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        g = meta.get("gematria_links") or {}
        tests = g.get("tests") or {}
        if key == "gematria_genesis":
            v = g.get("verse")
            if not v:
                return None
            values = {k: v.get(k) for k in ("value", "all", "expected_all", "unique_share")}
            values["unique_here"] = float(bool(v.get("unique_here")))
            values["twins"] = len(v.get("twins") or [])
            holds = bool(v.get("unique_here")) and v["unique_share"] <= alpha
            return Finding(key=key, verdict="holds" if holds else "fails", values=values)
        t = tests.get("equal" if key == "gematria_links" else "root_family") or {}
        if not t:
            return None
        values = {"pairs": next(iter(t.values()))["n"]}
        for m, r in t.items():
            values |= {f"{m}_observed": r["observed"], f"{m}_null": r["null_mean"],
                       f"{m}_p": r["p"]}  # fmt: skip
        if key == "gematria_links":
            holds = any(r["observed"] > r["null_mean"] and r["p"] <= alpha / len(t)
                        for r in t.values())  # fmt: skip
        else:
            holds = all(r["observed"] > r["null_mean"] and r["p"] <= alpha for r in t.values())
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build


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


def _els(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """Equidistant letter sequences (§16.62). `els_counts`: the names' hits in the Torah are no
    more than the controls' (letters shuffled, verses shuffled, blocks of the rest of the Bible)
    in every scope, none at p <= `alpha`; `els_known`: the tradition's sequences at the start of
    the books of the Torah are in our letters."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        e = meta.get("els") or {}
        if key == "els_known":
            known = e.get("known") or []
            if not known:
                return None
            values = {"n": len(known), "found": sum(bool(k["found"]) for k in known)}
            holds = all(k["found"] for k in known)
            return Finding(key=key, verdict="holds" if holds else "fails", values=values)
        scopes = e.get("scopes") or {}
        if "torah" not in scopes:
            return None
        values: dict[str, float | None] = {"terms": e.get("terms")}
        for name, s in scopes.items():
            values[f"{name}_r"] = s["r"]
            for c, v in (s.get("controls") or {}).items():
                values[f"{name}_{c}_p"] = v["p"]
        holds = all(c["p"] > alpha for s in scopes.values()
                    for c in (s.get("controls") or {}).values())  # fmt: skip
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
    _dialogue("dialogue_deference", "deference"),
    _dialogue("dialogue_particle", "particle"),
    _dialogue("dialogue_last_word", "last_word"),
    _forms("forms_known"),
    _forms("forms_chance"),
    _forms("forms_parallel"),
    _forms("forms_lists"),
    _ciphers("ciphers_known"),
    _ciphers("ciphers_jeremiah"),
    _ciphers("ciphers_elsewhere"),
    _ciphers("ciphers_albam"),
    _divine("divine_elohistic"),
    _divine("divine_doubled"),
    _etiologies("etiology_echo"),
    _etiologies("etiology_known"),
    _brackets("brackets_insertion"),
    _brackets("brackets_known"),
    _retold("retold_claim"),
    _retold("retold_known"),
    _haftarot("haftarot_claim"),
    _haftarot("haftarot_calendar"),
    _haftarot("haftarot_known"),
    _chronology("chronology_known"),
    _chronology("chronology_syncs"),
    _chronology("chronology_digits"),
    _frameworks("frameworks_cycle"),
    _frameworks("frameworks_cycle_known"),
    _frameworks("frameworks_verdicts"),
    _frameworks("frameworks_verdicts_known"),
    _masorah("masorah_letter"),
    _masorah("masorah_words"),
    _masorah("masorah_verse"),
    _masorah("masorah_books"),
    _gematria_links("gematria_links"),
    _gematria_links("gematria_measures"),
    _gematria_links("gematria_genesis"),
    _place_lists("place_lists_order"),
    _place_lists("place_lists_districts"),
    _place_arc("place_arc_order"),
    _place_arc("place_arc_moves"),
    _place_arc("place_arc_oracles"),
    _place_links("place_links_decay"),
    _place_links("place_links_known"),
    _els("els_counts"),
    _els("els_known"),
    _allusions,
]


@router.get("/findings", response_model=FindingsResponse)
def findings(state: State, conn: Conn) -> dict[str, Any]:
    """The tested claims of the analyses with their deciding numbers and verdicts."""
    alpha = state.cfg["serve"]["findings"]["alpha"]
    items = [f for b in BUILDERS if (f := b(state.meta, conn, alpha)) is not None]
    return {"alpha": alpha, "items": items}
