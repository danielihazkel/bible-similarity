"""`/findings` builders. Narrative: names of God, etiologies, brackets, retold speech, haftarot,
frameworks, word pairs."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

from bsim.api.models.findings import Finding
from bsim.api.routes.findings.common import Meta


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


def _mainline(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    m = meta.get("mainline") or {}
    c = m.get("claim")
    if not c:
        return None
    values = {"excess": c["excess"], "null": c["null_mean"], "p": c["p"],
              "known": m.get("known_found"), "of": len(m.get("known") or [])}  # fmt: skip
    return Finding(key="mainline", verdict="holds" if c["holds"] else "fails", values=values)


def _laws(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
    """The law codes: the laws the commentaries set side by side found among the matched pairs."""
    m = meta.get("laws") or {}
    if not m.get("known"):
        return None
    values = {"known": m["known_found"], "of": m["known_total"], "pairs": m["pairs"],
              "laws": m["laws"]}  # fmt: skip
    return Finding(key="laws", verdict="holds" if m["known_holds"] else "fails", values=values)


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


def _binomials(key: str) -> Callable[[Meta, sqlite3.Connection, float], Finding | None]:
    """Fixed word pairs: the shorter word first (letters and syllables); the rarer order commoner
    in the late books; שמים וארץ and איש ואשה fixed, זהב וכסף turning late."""

    def build(meta: Meta, conn: sqlite3.Connection, alpha: float) -> Finding | None:
        b = meta.get("binomials") or {}
        if not b.get("binomials"):
            return None
        if key == "binomials_short":
            le, sy = b.get("letters") or {}, b.get("syllables") or {}
            values = {"binomials": b.get("binomials"), "letters_k": le.get("shorter_first"),
                      "letters_m": le.get("differ"), "letters_p": le.get("p"),
                      "syll_k": sy.get("shorter_first"), "syll_m": sy.get("differ"),
                      "syll_p": sy.get("p")}  # fmt: skip
            holds = bool(b.get("short_holds"))
        elif key == "binomials_late":
            w = b.get("without_known") or {}
            values = {k: b.get(k) for k in ("rate_early", "rate_late", "n_early", "n_late")}
            values |= {"p": b.get("late_p"), "without_p": w.get("p")}
            holds = bool(b.get("late_holds"))
        else:
            known = b.get("known") or []
            kl = b.get("known_late") or {}
            values = {f"share_{i}": k["share"] for i, k in enumerate(known)}
            values |= {f"n_{i}": k["n"] for i, k in enumerate(known)}
            values |= {"gold_early": kl.get("share_early"), "gold_late": kl.get("share_late")}
            holds = bool(b.get("known_holds"))
        return Finding(key=key, verdict="holds" if holds else "fails", values=values)

    return build
