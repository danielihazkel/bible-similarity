"""`/findings` builders. Letters and numbers: ciphers, the Masorah's counts, equal values, equal
skips, the chronology."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

from bsim.api.models.findings import Finding
from bsim.api.routes.findings.common import Meta


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
