"""Letter values (DESIGN.md §16.53): a text's value in each system, and the word forms, lemmas and
verses of one value; whether equal values link related words, and Gen 1:1's numbers (§16.59)."""

from __future__ import annotations

import json
from typing import Any, Literal

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models.common import VerseLabel
from bsim.api.models.gematria import (
    GematriaForm,
    GematriaFormsResponse,
    GematriaKnown,
    GematriaLemma,
    GematriaLemmasResponse,
    GematriaLinksResponse,
    GematriaPair,
    GematriaPairsResponse,
    GematriaResponse,
    GematriaSystem,
    GematriaValueResponse,
    GematriaValues,
    GematriaVerse,
    GematriaVersesResponse,
    LinkEquivalence,
    LinkLemma,
    LinkProperty,
    LinkTest,
    LinkVerse,
)
from bsim.api.routes._common import Conn, State, check_min, check_page, unprocessable
from bsim.text.gematria import SYSTEMS, letters, values

router = APIRouter()
MAX_TEXT = 500  # characters of `/gematria/value?text=`


def _values(r: dict[str, Any]) -> GematriaValues:
    return GematriaValues(**{s: r[s] for s in SYSTEMS})


@router.get("/gematria/value", response_model=GematriaValueResponse)
def gematria_value(text: str) -> dict[str, Any]:
    """The value of any Hebrew text in each system (points, accents and other characters
    ignored)."""
    if len(text) > MAX_TEXT:
        raise unprocessable(f"text must be at most {MAX_TEXT} characters")
    if not letters(text):
        raise unprocessable("text has no Hebrew letters")
    return {"text": text, "letters": letters(text), "values": GematriaValues(**values(text))}


@router.get("/gematria", response_model=GematriaResponse)
def gematria(
    value: int, state: State, conn: Conn, system: GematriaSystem = "standard"
) -> dict[str, Any]:
    """How many word forms, lemmas and verses have this value, and the equivalences of the
    config."""
    check_min(value, "value", 0)
    meta = state.meta.get("gematria")
    known = (meta or {}).get("known") or []
    return {
        "computed": meta is not None,
        "value": value,
        "system": system,
        **queries.gematria_counts(conn, system, value),
        "known": [GematriaKnown(**k) for k in known],
    }


@router.get("/gematria/forms", response_model=GematriaFormsResponse)
def gematria_forms(
    value: int,
    state: State,
    conn: Conn,
    system: GematriaSystem = "standard",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """The written word forms of this value, the commonest first, with their first verses."""
    check_min(value, "value", 0)
    check_page(state, limit, offset)
    total, rows = queries.gematria_page(conn, "forms", system, value, limit, offset)
    where = {r["form"]: json.loads(r["verses"]) for r in rows}
    labels = queries.verse_labels(conn, {v for vs in where.values() for v in vs})
    items = [
        GematriaForm(
            form=r["form"],
            values=_values(r),
            n_words=r["n_words"],
            n_verses=r["n_verses"],
            verses=[
                VerseLabel(verse_id=v, label_en=labels[v][0], label_he=labels[v][1])
                for v in where[r["form"]]
                if v in labels
            ],
        )
        for r in rows
    ]
    return {"value": value, "system": system, "total": total, "offset": offset, "limit": limit,
            "items": items}  # fmt: skip


@router.get("/gematria/lemmas", response_model=GematriaLemmasResponse)
def gematria_lemmas(
    value: int,
    state: State,
    conn: Conn,
    system: GematriaSystem = "standard",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """The lemmas of this value (by their Strong's headword), the commonest first."""
    check_min(value, "value", 0)
    check_page(state, limit, offset)
    total, rows = queries.gematria_page(conn, "lemmas", system, value, limit, offset)
    items = [
        GematriaLemma(lemma=r["lemma"], he=r["he"], values=_values(r), n_words=r["n_words"])
        for r in rows
    ]
    return {"value": value, "system": system, "total": total, "offset": offset, "limit": limit,
            "items": items}  # fmt: skip


@router.get("/gematria/verses", response_model=GematriaVersesResponse)
def gematria_verses(
    value: int,
    state: State,
    conn: Conn,
    system: GematriaSystem = "standard",
    book: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """The verses whose words add up to this value, in canon order."""
    check_min(value, "value", 0)
    check_page(state, limit, offset)
    total, rows = queries.gematria_page(conn, "verses", system, value, limit, offset, book)
    ids = [r["verse_id"] for r in rows]
    verses = queries.verses_by_id(conn, ids)
    labels = queries.verse_labels(conn, ids)
    items = [
        GematriaVerse(
            verse=verses[r["verse_id"]],
            label_en=labels[r["verse_id"]][0],
            label_he=labels[r["verse_id"]][1],
            values=_values(r),
            n_letters=r["n_letters"],
            n_words=r["n_words"],
        )
        for r in rows
    ]
    return {"value": value, "system": system, "book": book, "total": total, "offset": offset,
            "limit": limit, "items": items}  # fmt: skip


def _link_lemma(heads: dict[str, dict[str, Any]], lemma: str) -> LinkLemma:
    h = heads.get(lemma) or {"he": lemma, "n_words": 0}
    return LinkLemma(lemma=lemma, he=h["he"], n_words=h["n_words"])


@router.get("/gematria-links", response_model=GematriaLinksResponse)
def gematria_links(state: State, conn: Conn) -> dict[str, Any]:
    """Equal-value pairs against matched pairs on three measures of relatedness, the check of the
    measures, the traditional equivalences ranked, and Gen 1:1's numbers over every verse."""
    meta = state.meta.get("gematria_links") or {}
    tests = meta.get("tests") or {}
    eqs = meta.get("equivalences") or []
    heads = queries.gematria_lemma_heads(conn, [e[k] for e in eqs for k in ("a", "b") if e.get(k)])
    equivalences = [
        LinkEquivalence(**{k: v for k, v in e.items() if k not in ("a", "b")},
                        a=_link_lemma(heads, e["a"]) if e.get("a") else None,
                        b=_link_lemma(heads, e["b"]) if e.get("b") else None)  # fmt: skip
        for e in eqs
    ]
    v = meta.get("verse")
    verse = None
    if v:
        ids = [v["verse_id"], *v.get("twins", [])]
        labels = queries.verse_labels(conn, ids)

        def label(i: int) -> VerseLabel:
            return VerseLabel(verse_id=i, label_en=labels[i][0], label_he=labels[i][1])

        verse = LinkVerse(
            **{k: v[k] for k in ("value", "words", "letters", "largest_prime", "n_verses", "all",
                                 "expected_all", "unique_here", "unique_share")},  # fmt: skip
            verse=label(v["verse_id"]),
            twins=[label(i) for i in v.get("twins", []) if i in labels],
            properties=[LinkProperty(**p) for p in meta.get("properties") or []],
        )
    return {
        "meta": {k: x for k, x in meta.items()
                 if k not in ("tests", "equivalences", "verse", "properties")},  # fmt: skip
        "equal": {m: LinkTest(**t) for m, t in (tests.get("equal") or {}).items()},
        "root_family": {m: LinkTest(**t) for m, t in (tests.get("root_family") or {}).items()},
        "equivalences": equivalences,
        "verse": verse,
    }


@router.get("/gematria-links/pairs", response_model=GematriaPairsResponse)
def gematria_link_pairs(
    state: State,
    conn: Conn,
    value: int | None = None,
    sort: Literal["vector", "domains", "value"] = "vector",
    same_letters: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Pairs of lemmas of equal value, the most related first (or by value)."""
    check_min(value, "value", 0)
    check_page(state, limit, offset)
    total, rows = queries.gematria_pairs_page(conn, value, sort, same_letters, limit, offset)
    items = [
        GematriaPair(
            a=LinkLemma(lemma=r["a"], he=r["a_he"], n_words=r["a_n"]),
            b=LinkLemma(lemma=r["b"], he=r["b_he"], n_words=r["b_n"]),
            value=r["value"], same_letters=bool(r["same_letters"]), domains=r["domains"],
            root=bool(r["root"]), vector=r["vector"],
        )  # fmt: skip
        for r in rows
    ]
    return {"value": value, "sort": sort, "same_letters": same_letters, "total": total,
            "offset": offset, "limit": limit, "items": items}  # fmt: skip
