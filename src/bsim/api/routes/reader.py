"""The layered reader (DESIGN.md §16.39): the word-level findings of several analyses for one
unit at once, keyed by display token, so the viewer can paint them onto the text. Cola come from
`/parallelism/{unit}` and Leitworte from `/structure/{unit}`; this adds what has no unit view."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

from fastapi import APIRouter

from bsim.api import queries
from bsim.api.models import (
    ReaderGap,
    ReaderKetiv,
    ReaderRefrain,
    ReaderResponse,
    ReaderSource,
    ReaderSpeaker,
    ReaderVerse,
    ReaderWordplay,
    UnitSummary,
)
from bsim.api.routes._common import Conn, State, unit_or_404, unprocessable
from bsim.data.lexicon import strong_key

router = APIRouter()


def _speech(
    clauses: list[dict[str, Any]], display: dict[tuple[int, int], int]
) -> dict[int, dict[int, str | None]]:
    """verse_id -> display token -> speaker lemma (None: not known) of every word of a quotation;
    an embedded quotation, later in clause order, wins over the one around it."""
    out: dict[int, dict[int, str | None]] = defaultdict(dict)
    for c in clauses:
        if not c["txt"].endswith("Q"):
            continue
        v = c["verse_id"]
        for i in json.loads(c["words"]):
            if (v, i) in display:
                out[v][display[v, i]] = c["speaker"]
    return out


@router.get("/reader/{unit_id}", response_model=ReaderResponse)
def reader(unit_id: str, state: State, conn: Conn) -> dict[str, Any]:
    """Who speaks each word, the words in phrases shared with other verses, rare words, sound-alike
    pairs, ketiv / qere, refrains, words of distress and praise, each verse's side of the P /
    non-P split, and the turns and MAM breaks before each verse."""
    u = unit_or_404(conn, unit_id)
    limit = state.cfg["serve"]["max_compare_verses"]
    if u["n_verses"] > limit:
        raise unprocessable(f"{unit_id} is longer than {limit} verses")
    first, last = u["start_verse_id"], u["end_verse_id"]
    rare_max = state.cfg["serve"]["reader"]["rare_verses"]
    display = queries.display_span(conn, first, last)
    vids = range(first, last + 1)

    # speech: speakers ordered by the words they speak here, the unknown speaker last
    clauses = queries.clauses_of(conn, first, last)
    speech = _speech(clauses, display)
    said = Counter(s for toks in speech.values() for s in toks.values())
    order = sorted(said, key=lambda s: (s is None, -said[s], s or ""))
    he = queries.gloss(conn, [s for s in order if s is not None])
    # whom each speaks to here (§16.44), by words
    to: dict[str | None, Counter] = defaultdict(Counter)
    to_he: dict[str, str] = {}
    for c in clauses:
        a = c.get("addressee")
        if c["txt"].endswith("Q") and a and a != c["speaker"]:
            to[c["speaker"]][a] += len(json.loads(c["words"]))
            to_he[a] = c.get("addressee_he") or a
    divine = state.cfg["syntax"]["divine"]
    speakers = [
        ReaderSpeaker(
            lemma=s,
            he=he.get(s) if s is not None else None,
            divine=s is not None and strong_key(s) in divine,
            n_words=said[s],
            to=[to_he[a] for a, _ in to[s].most_common()],
        )
        for s in order
    ]
    index = {s: i for i, s in enumerate(order)}

    # phrases: the other verses each word shares a phrase with
    partners: dict[int, dict[int, set[int]]] = defaultdict(lambda: defaultdict(set))
    for r in queries.phrases_touching(conn, first, last):
        for v, words, other in ((r["a"], r["a_words"], r["b"]), (r["b"], r["b_words"], r["a"])):
            if first <= v <= last:
                for i in json.loads(words):
                    if (v, i) in display:
                        partners[v][display[v, i]].add(other)

    # rare words: the rarest content lemma of each token, names left out
    rows = queries.words(conn, vids)
    lemmas = {lem for w in rows for lem in w["content_lemmas"].split()}
    names = queries.entity_lemmas(conn, lemmas)
    n_verses = {k: s["n_verses"] for k, s in queries.lemma_stats(conn, lemmas - names).items()}
    rare: dict[int, dict[int, int]] = defaultdict(dict)
    for w in rows:
        if w["display_idx"] is None:
            continue
        ns = [n_verses[lem] for lem in w["content_lemmas"].split() if lem in n_verses]
        if ns and min(ns) <= rare_max:
            v, d = w["verse_id"], w["display_idx"]
            rare[v][d] = min(min(ns), rare[v].get(d, rare_max))

    # sound-alike pairs: each side in the unit gets the other as its partner
    plays = queries.wordplay_touching(conn, first, last)
    labels = queries.verse_labels(conn, {v for p in plays for v in (p["a_vid"], p["b_vid"])})
    wordplay: dict[int, list[ReaderWordplay]] = defaultdict(list)
    for p in plays:
        for s, o in (("a", "b"), ("b", "a")):
            v, d = p[f"{s}_vid"], p[f"{s}_display"]
            if first <= v <= last and d is not None:
                ov = p[f"{o}_vid"]
                wordplay[v].append(
                    ReaderWordplay(
                        display=d,
                        partner_vid=ov,
                        partner_display=p[f"{o}_display"],
                        partner_label=labels[ov][0],
                        partner_label_he=labels[ov][1],
                        form=p[f"{s}_form"],
                        partner_form=p[f"{o}_form"],
                        kind=p["kind"],
                        q=p["q"],
                    )
                )

    kq = queries.kq_in(conn, first, last)
    read = queries.display_of_words(conn, [(r["verse_id"], r["pos"], r["n_qere"]) for r in kq])
    ketiv: dict[int, list[ReaderKetiv]] = defaultdict(list)
    for r in kq:
        ketiv[r["verse_id"]].append(
            ReaderKetiv(
                display=read.get((r["verse_id"], r["pos"]), []) if r["n_qere"] else [],
                **{k: r[k] for k in ("ketiv", "qere", "cls")},
            )
        )
    # refrains: each token of a phrase that comes back nearby, the strongest refrain first
    found: dict[int, ReaderRefrain] = {}
    ref_at: dict[int, dict[int, int]] = defaultdict(dict)
    for r in queries.refrains_in(conn, first, last):
        if r["refrain_id"] not in found:
            found[r["refrain_id"]] = ReaderRefrain(
                **{k: r[k] for k in ("refrain_id", "text", "k", "known")}
            )
        i = list(found).index(r["refrain_id"])
        for t in range(r["first"], r["last"] + 1):
            ref_at[r["verse_id"]].setdefault(t, i)
    # mood: words in the distress / praise domains of `psalms` (a word in both is left unmarked)
    pc = state.cfg["psalms"]
    distress, praise = tuple(pc["distress"]), tuple(pc["praise"])
    mood: dict[int, dict[int, str]] = defaultdict(dict)
    for w in queries.word_domains(conn, vids):
        if w["display_idx"] is None:
            continue
        codes = w["domains"].split()
        d = any(c.startswith(distress) for c in codes)
        p = any(c.startswith(praise) for c in codes)
        if d != p:
            mood[w["verse_id"]][w["display_idx"]] = "distress" if d else "praise"
    sources = queries.pentateuch_verses(conn, first, last)
    gaps = {
        g["verse_id"]: ReaderGap(
            score=g["score"], kind=g["kind"], mam=g["mam"], chapter=bool(g["chapter"])
        )
        for g in queries.gaps_in(conn, first, last)
    }

    return {
        "unit": UnitSummary(**u),
        "rare_verses": rare_max,
        "computed": {
            "speech": state.present(conn, "clauses"),
            "phrases": state.present(conn, "phrases"),
            "wordplay": state.present(conn, "wordplay"),
            "ketiv": state.present(conn, "kq_pairs"),
            "gaps": state.present(conn, "segment_gaps"),
            "refrains": state.present(conn, "refrains"),
            "mood": state.present(conn, "domains"),
            "sources": state.present(conn, "pentateuch_verses"),
        },
        "speakers": speakers,
        "refrains": list(found.values()),
        "verses": [
            ReaderVerse(
                verse_id=v,
                speech={str(t): index[s] for t, s in sorted(speech.get(v, {}).items())},
                refrains={str(t): i for t, i in sorted(ref_at.get(v, {}).items())},
                mood={str(t): m for t, m in sorted(mood.get(v, {}).items())},
                source=ReaderSource(**{k: sources[v][k] for k in ("side", "prob", "reference")})
                if v in sources
                else None,
                phrases={str(t): len(o) for t, o in sorted(partners.get(v, {}).items())},
                rare={str(t): n for t, n in sorted(rare.get(v, {}).items())},
                wordplay=wordplay.get(v, []),
                ketiv=ketiv.get(v, []),
                gap=gaps.get(v),
            )
            for v in vids
        ],
    }
