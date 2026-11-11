"""`/findings` builders. Language and sources: divisions, clauses, dating, borrowing, citations,
voices, echoes, allusions, roots, the Pentateuch's split, dialogue."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

from bsim.api.models.findings import Finding
from bsim.api.routes.findings.common import Meta


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


def _clauses(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    c = (meta.get("mirrors") or {}).get("clauses")
    if not c or c.get("p") is None:
        return None
    values = {k: c[k] for k in ("poetry", "prose", "poetry_n", "prose_n", "p")}
    holds = c["poetry"] > c["prose"] and c["p"] <= alpha
    return Finding(key="clauses", verdict="holds" if holds else "fails", values=values)


def _dating(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    d = meta.get("dating") or {}
    s = d.get("synoptic")
    if not s:
        return None
    values = {"later": s["later"], "pairs": s["pairs"], "p": s["p"], "auc": d.get("held_out_auc")}
    return Finding(key="dating", verdict="holds" if s["p"] <= alpha else "fails", values=values)


def _theophoric(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    c = (meta.get("theophoric") or {}).get("claim")
    if not c:
        return None
    values = {k: c[k] for k in ("early_short", "late_short", "p", "names")}
    return Finding(key="theophoric", verdict="holds" if c["holds"] else "fails", values=values)


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


def _vocabulary(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """The vocabulary over the canon: the late books bring in more new words than their length
    and place predict (novelty: the excess over Heaps' law, averaged over random book orders);
    Job and the Song among the books richest in words found once."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        v = meta.get("vocabulary") or {}
        if not v.get("words"):
            return None
        if key == "vocabulary_late":
            values = {k: v.get(k) for k in ("late_novelty", "early_novelty", "difference",
                                            "late_p", "splits")}  # fmt: skip
            holds = bool(v.get("late_holds"))
        else:
            known = v.get("known") or []
            values = {f"rank_{i}": k.get("rank") for i, k in enumerate(known)}
            values |= {f"at_most_{i}": k.get("at_most") for i, k in enumerate(known)}
            holds = bool(v.get("known_holds"))
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build


def _reception(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """Rabbinic reception: the Mishnah cites the Torah's law more per verse than its narrative
    (against the law's blocks shifted round each book); the Bavli leans to the law less than the
    Mishnah (against the corpus of each citation shuffled); the known citations found."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        r = meta.get("reception") or {}
        if not r.get("citations"):
            return None
        ratios = r.get("ratios") or {}
        if key == "reception_law":
            values = {"ratio": ratios.get("mishnah"), "p": r.get("law_p"),
                      "shifts": r.get("shifts"), "legal": r.get("legal_verses"),
                      "narrative": r.get("narrative_verses")}  # fmt: skip
            holds = bool(r.get("law_holds"))
        elif key == "reception_bavli":
            values = {"mishnah": ratios.get("mishnah"), "bavli": ratios.get("bavli"),
                      "gap": r.get("gap"), "p": r.get("gap_p")}  # fmt: skip
            holds = bool(r.get("gap_holds"))
        else:
            known = r.get("known") or []
            values = {"found": sum(1 for k in known if k.get("found")), "of": len(known)}
            holds = bool(r.get("known_holds"))
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build


def _witnesses(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """Other witnesses: the Samaritan's pluses in the Torah's parallel verses (against the
    parallel label shifted round each book); the known readings and the Samaritan Flood."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        w = meta.get("witnesses") or {}
        if not (w.get("samaritan") or {}).get("verses"):
            return None
        if key == "witnesses_parallel":
            values = {"ratio": w.get("ratio"), "null": w.get("null_mean"), "p": w.get("p"),
                      "pluses": w.get("sp_pluses"), "parallel": w.get("parallel_verses"),
                      "shifts": w.get("shifts")}  # fmt: skip
            holds = bool(w.get("holds"))
        else:
            known = w.get("known") or []
            flood = next((c for c in w.get("chronology_known") or [] if c["event"] == "flood"), {})
            values = {"found": sum(1 for k in known if k.get("found")), "of": len(known),
                      "flood": flood.get("year")}  # fmt: skip
            holds = bool(w.get("known_holds"))
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build
