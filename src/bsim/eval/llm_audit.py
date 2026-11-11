"""`bsim llm-audit`: how often each rule-based detector is right, by Claude's reading of a
sample of its findings (DESIGN.md §16.86, D142; series L5).

The detectors (§16) are checked by their known answers, which measure recall: whether the
famous cases are found. How many of the rest are right was measured by hand only for places
(49 / 50), addressees (42 / 50) and citations. For each detector here, `llm_audit.sample`
findings are drawn (seeded, fixed before the run) from its `llm_audit.top` strongest, and each
is sent to Claude with the detector's definition, the claim the finding makes and the pointed
Hebrew of its verses; the answer is `right` | `wrong` | `unsure`, a probability that the claim is
right and a rationale in Hebrew. Nothing is translated: the claims quote the Hebrew words.

Calibration, fixed before the run: the 50 place mentions the owner judged by hand
(`artifacts/places/sample.json`, 49 right) and each detector's known answers (up to
`known_max`), which should be judged right. The precision table is published only if Claude
calls at least `min_places` of the place sample and `min_known` of the known answers right.

Precision is right / (right + wrong) with a Wilson interval; `unsure` is left out and counted.
Writes `artifacts/llm_audit/` and `artifacts/eval/llm_audit.md` (the wrong findings listed with
their references, material for later known-miss milestones).

Two populations (`llm_audit.population`, D147): `strongest` (M152) draws from each detector's
`top` strongest; `pages` (M158) draws uniformly from what each page lists by default (`shown`:
`llm_audit.pages.shown` names the pages that filter, the rest list everything) and from what a
page marks as strong (`marked`), so the precision is the chance that a finding a reader sees is
right. The `pages` run writes `artifacts/llm_audit_pages/` and `artifacts/eval/llm_audit_pages.md`.
`read_precision` gathers the calibrated runs for the API (`/detector-precision`).
"""

from __future__ import annotations

import json
import math
import sqlite3
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path, write_meta
from bsim.eval.llm_batch import (
    Collected,
    Log,
    ensure_columns,
    make_request,
    mark_collected,
    pointed,
    run_batch,
    usage,
)

OUT = "llm_audit"
POPULATIONS = ("strongest", "pages")
PAGE_SETS = ("shown", "marked")  # the `pages` run's drawn sets, in this order
VERDICTS = ("right", "wrong", "unsure")
SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "p_right": {"type": "number"},
        "rationale": {"type": "string"},
    },
    "required": ["verdict", "p_right", "rationale"],
    "additionalProperties": False,
}
SYSTEM = """You check a finding that a computer program made about the Hebrew Bible. The program \
looks for one kind of literary or linguistic feature by rules; the finding claims that the \
feature is present in the verses given. Judge, as a careful reader of the Hebrew text, whether \
the claim is right.

Verdict "right": the feature is there as the claim states it. "wrong": it is not (the words do \
not do what is claimed, or the resemblance is chance or a commonplace of the language). \
"unsure": the text alone does not decide it, or scholars are divided.

Rules:
- Never translate a verse, or any word or phrase of it, into English or any other language. \
Quote Hebrew words exactly as they are written, in Hebrew letters.
- The rationale is one or two short sentences in Hebrew, and only in Hebrew, naming the words or \
the feature that decide your verdict. Write no word of English or of any other language in it.
- p_right is your probability, from 0 to 1, that the claim is right."""

# the detector's definition, shown above each of its claims (DESIGN.md's sections)
DEFINITIONS = {
    "etiologies": "Naming etiologies (§16.66): a verse gives a person or a place a name and "
    "explains it, usually by a word that sounds like the name.",
    "brackets": "Resumptive repetition (§16.67): a narrative repeats words of an earlier verse "
    "to take up its thread again after an insertion (Wiederaufnahme).",
    "retold": "Retold speech (§16.68): words said or events narrated earlier are told again "
    "later, by a speaker or by the narrator, in largely the same wording.",
    "binomials": "Fixed word pairs (§16.72): two words joined by 'and' in a fixed order, used as "
    "a set phrase.",
    "typescenes": "Type scenes (§16.20): two passages that are not the same text (not parallel "
    "accounts) tell the same kind of scene, with the same sequence of actions in the same order.",
    "acrostics": "Acrostics (§16.15): successive verses, lines or half-lines begin with "
    "successive letters of the alphabet.",
    "wordplay": "Wordplay (§16.24): two words close together that sound alike, set side by side "
    "on purpose (paronomasia).",
    "allusions": "Allusions by rare words (§16.32): two passages share several rare words because "
    "one draws on the other, or both on a common source.",
    "refrains": "Refrains (§16.40): a phrase that comes back several times within a passage as a "
    "refrain.",
    "sayings": "Graded numerical sayings (§16.45): a number followed by the next number (three... "
    "and four) introducing a list.",
    "lists": "Lists (§16.45): a run of verses that enumerate like items (names, places, gifts, "
    "measures).",
    "mirrors": "Chiasm within a verse (§16.33): words of the verse repeat in mirror order "
    "(A B ... B A).",
    "ciphers": "Ciphers (§16.62): a word written in a letter cipher (atbash, albam) that reads as "
    "another word or name, as ששך for בבל in Jer 25:26.",
    "seams": "Seams (§16.29): at this verse the vocabulary of the text shifts, marking a join "
    "between sources or sections.",
    "mainline": "Pauses in the narrative main line (§16.91): the narrator steps off the chain of "
    "wayyiqtol clauses (ויקם … וילך) for background: setting a scene, describing, or telling what "
    "had happened before; then the chain takes up again.",
    "prophetic": "Forms of prophetic speech (§16.92), as form criticism describes them: the woe "
    "saying (הוי + a participle or noun, against those it names), the oracle against a foreign "
    "nation, the covenant lawsuit (God's ריב with his people, heaven and earth or the mountains "
    "called to hear), the call narrative (God sends someone, who objects or is reassured).",
    "places": "Place mentions (§16.56): a word in the verse is the name of a place (not a person "
    "of the same name and not a common noun).",
}


# --- the findings -------------------------------------------------------------------------------


def _q(conn: sqlite3.Connection, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn)


def _sel(
    conn: sqlite3.Connection, table: str, order: str, where: str | None, base: str | None = None
) -> pd.DataFrame:
    """A detector's table in its own order, under its own condition (`base`) and the page's."""
    conds = [c for c in (base, where) if c]
    w = " WHERE " + " AND ".join(f"({c})" for c in conds) if conds else ""
    return _q(conn, f"SELECT * FROM {table}{w} ORDER BY {order}")


def _words(tokens: list[str], idxs: list[int]) -> str:
    return " ".join(tokens[i] for i in idxs if 0 <= i < len(tokens))


def _known(x: Any) -> bool:
    """A `known` column: 1 / 0, a known answer's name, or NULL."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return False
    return x not in (0, "0", False, "")


def _span(first: int, last: int, cap: int) -> list[int]:
    vids = list(range(int(first), int(last) + 1))
    return vids if len(vids) <= cap else vids[: cap // 2] + vids[-(cap - cap // 2) :]


class Source:
    """The DB's verses (references, display tokens) for the claims."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        v = _q(conn, "SELECT verse_id, ref, display_tokens FROM verses ORDER BY verse_id")
        self.ref = v.ref.tolist()
        self.tokens = [json.loads(t) for t in v.display_tokens]

    def words(self, vid: int, idxs: list[int]) -> str:
        return pointed(_words(self.tokens[int(vid)], idxs))


def findings(
    conn: sqlite3.Connection, name: str, src: Source, cap: int, where: str | None = None
) -> pd.DataFrame:
    """`key, claim, vids, known, strength`: a detector's findings, strongest first; `where`, an
    SQL condition on its table (`llm_audit.pages`), keeps those a page lists or marks."""
    rows: list[tuple[str, str, list[int], bool]] = []
    if name == "etiologies":
        df = _sel(conn, "etiologies", "p, score DESC", where)
        for r in df.itertuples():
            name_ = src.words(r.verse_id, list(range(int(r.name_first), int(r.name_last) + 1)))
            echo = ""
            if _known(r.echo_disp):
                echo = f", playing on the word {src.words(r.verse_id, [int(r.echo_disp)])}"
            claim = f"This verse names {name_} ({r.kind}) and explains the name{echo}."
            rows.append((f"naming {r.naming}", claim, [r.verse_id], _known(r.known)))
    elif name == "brackets":
        df = _sel(conn, "brackets", "q, score DESC", where)
        for r in df.itertuples():
            a = src.words(r.a, json.loads(r.a_disp))
            b = src.words(r.b, json.loads(r.b_disp))
            claim = (
                f"{src.ref[r.b]} takes up again the words of {src.ref[r.a]} ({a} / {b}) to resume"
                f" the thread after the {r.n_between} verses between them, an insertion."
            )
            vids = [r.a, r.b] if r.n_between > 4 else _span(r.a, r.b, 8)
            rows.append((f"bracket {r.bracket}", claim, vids, _known(r.known)))
    elif name == "retold":
        df = _sel(conn, "retold_pairs", "score DESC", where)
        for r in df.itertuples():
            claim = (
                f"{src.ref[r.later_first]}–{src.ref[r.later_last]} tells again, in largely the"
                f" same words, what {src.ref[r.src_first]}–{src.ref[r.src_last]} {r.grp}."
            )
            vids = _span(r.src_first, r.src_last, 3) + _span(r.later_first, r.later_last, 3)
            rows.append((f"retold {r.pair}", claim, vids, _known(r.known)))
    elif name == "binomials":
        df = _sel(conn, "binomials", "n DESC", where)
        occ = _q(conn, "SELECT pair, verse_id FROM binomial_occurrences ORDER BY pair, verse_id")
        by = occ.groupby("pair").verse_id.apply(list).to_dict()
        for r in df.itertuples():
            claim = (
                f"{r.first_form} ו{r.second_form} is a fixed pair: the two words joined by ו in"
                f" this order {r.n} times (the order kept {r.fixed:.0%} of the time)."
            )
            vids = by.get(r.pair, [])[:3]
            rows.append((f"pair {r.pair}", claim, vids, False))
    elif name == "typescenes":
        df = _sel(conn, "typescenes", "q, score DESC", where, base="parallel_text = 0")
        units = _q(conn, "SELECT unit_id, label_en FROM units").set_index("unit_id").label_en
        for r in df.itertuples():
            al = json.loads(r.aligned)
            pairs = list(dict.fromkeys((int(a), int(b)) for a, b, _ in al))[:3]
            claim = (
                f"{units.get(r.a_unit, r.a_unit)} and {units.get(r.b_unit, r.b_unit)} tell the same"
                f" kind of scene, with {r.n_matches} verbs aligned in the same order."
            )
            vids = [a for a, _ in pairs] + [b for _, b in pairs]
            rows.append((f"{r.a_unit} {r.b_unit}", claim, vids, False))
    elif name == "acrostics":
        df = _sel(conn, "acrostics", "q, score DESC", where)
        for r in df.itertuples():
            chain = json.loads(r.chain)
            vids = list(dict.fromkeys(int(v) for v, _, _ in chain))[:8]
            claim = (
                f"{src.ref[r.start_vid]}–{src.ref[r.end_vid]} is an acrostic: successive"
                f" {r.granularity}s begin with successive letters, {r.first_letter} to"
                f" {r.last_letter} ({r.n_letters} letters, {r.missing} missing)."
            )
            rows.append((f"{r.unit_id} {r.granularity} {r.order_name}", claim, vids, False))
    elif name == "wordplay":
        df = _sel(conn, "wordplay", "q, score DESC", where)
        for r in df.itertuples():
            claim = (
                f"{pointed(r.a_form)} and {pointed(r.b_form)} are set side by side as a play on"
                f" their sound ({r.kind})."
            )
            vids = list(dict.fromkeys([r.a_vid, r.b_vid]))
            rows.append((f"{r.a_vid}:{r.a_idx} {r.b_vid}:{r.b_idx}", claim, vids, False))
    elif name == "allusions":
        df = _sel(conn, "allusions", "q, score DESC", where)
        for r in df.itertuples():
            words = " ".join(f for _, f in json.loads(r.lemmas))
            claim = (
                f"{src.ref[r.a_start]}–{src.ref[r.a_end]} and {src.ref[r.b_start]}–"
                f"{src.ref[r.b_end]} share the rare words {words}, because one draws on the other"
                " or both on a common source."
            )
            vids = _span(r.a_start, r.a_end, 3) + _span(r.b_start, r.b_end, 3)
            rows.append((f"allusion {r.allusion_id}", claim, vids, _known(r.known)))
    elif name == "refrains":
        df = _sel(conn, "refrains", "p", where, base="strongest = 1")
        for r in df.itertuples():
            claim = (
                f"{pointed(r.text)} comes back {r.k} times between {src.ref[r.first_vid]} and"
                f" {src.ref[r.last_vid]} as a refrain."
            )
            vids = [r.first_vid, r.last_vid]
            rows.append((f"refrain {r.refrain_id}", claim, vids, _known(r.known)))
    elif name == "sayings":
        df = _sel(conn, "forms_sayings", "prob", where)
        for r in df.itertuples():
            claim = f"This verse has a graded numerical saying ({r.steps})."
            rows.append((f"saying {r.verse_id}", claim, [r.verse_id], _known(r.known)))
    elif name == "lists":
        df = _sel(conn, "forms_lists", "likeness DESC", where)
        for r in df.itertuples():
            claim = (
                f"{src.ref[r.first_vid]}–{src.ref[r.last_vid]} is a list of {r.n_like} like"
                f" items ({r.kind})."
            )
            vids = _span(r.first_vid, r.last_vid, 6)
            rows.append((f"list {r.list_id}", claim, vids, _known(r.known)))
    elif name == "mirrors":
        df = _sel(conn, "mirror_verses", "q, p", where)
        for r in df.itertuples():
            claim = (
                "The words "
                f"{src.words(r.verse_id, json.loads(r.idxs))} repeat in this verse in mirror"
                " order (A B ... B A)."
            )
            rows.append((f"mirror {r.verse_id}", claim, [r.verse_id], False))
    elif name == "ciphers":
        df = _sel(conn, "cipher_hits", "known DESC, hit_id", where)
        for r in df.itertuples():
            claim = (
                f"The letters {r.span} in this verse are written in the {r.cipher} cipher and"
                f" read {r.reads}, and the text means it so."
            )
            rows.append((f"cipher {r.hit_id}", claim, [r.verse_id], _known(r.known)))
    elif name == "seams":
        df = _sel(conn, "seams", "rank, shift DESC", where)
        for r in df.itertuples():
            claim = (
                f"Between {src.ref[r.verse_id - 1]} and {src.ref[r.verse_id]} the vocabulary"
                " shifts, marking a join between sources or sections."
            )
            rows.append((f"seam {r.verse_id}", claim, [r.verse_id - 1, r.verse_id], False))
    elif name == "mainline":
        df = _sel(conn, "mainline_pauses", "pause_id", where)
        for r in df.itertuples():
            claim = (
                f"In {src.ref[r.first_vid]}–{src.ref[r.last_vid]} the narrator steps off the"
                f" chain of wayyiqtol clauses for {r.n_clauses} clauses of background (a scene set,"
                " a description, or what had happened before), and the chain takes up again after."
            )
            vids = _span(r.first_vid - 1, r.last_vid + 1, 6)  # the chain on either side
            rows.append((f"pause {r.pause_id}", claim, vids, _known(r.known)))
    elif name == "prophetic":  # the messenger formula is matched word for word: not judged
        df = _sel(conn, "prophetic_items", "item_id", where, base="form != 'messenger'")
        for r in df.itertuples():
            d, span = json.loads(r.detail), f"{src.ref[r.first_vid]}–{src.ref[r.last_vid]}"
            if r.form == "woe":
                claim = (
                    f"In {src.ref[r.first_vid]} a woe saying begins (הוי followed by the ones it is"
                    " against): an oracle of woe as the prophets speak them, not a cry of mourning"
                    " over the dead."
                )
            elif r.form == "nations":
                names = ", ".join(x["he"] for x in d["names"][:4])
                claim = (
                    f"{span} is an oracle (or a run of oracles) against a foreign nation ({names}):"
                    " spoken against that nation, not a story about it or an oracle to Israel."
                )
            elif r.form == "lawsuit":
                claim = (
                    f"In {span} God brings a covenant lawsuit (ריב): a call to hear, with the"
                    " dispute or with heaven and earth or the mountains called as witnesses"
                    " against the people."
                )
            else:
                claim = (
                    f"{span} tells of a call: God sends someone on a mission, and the one sent"
                    " objects or God reassures him (the form of Exod 3, Judg 6, Isa 6, Jer 1)."
                )
            vids = _span(r.first_vid, r.last_vid, cap)
            rows.append((f"{r.form} {r.item_id}", claim, vids, _known(r.known)))
    else:
        raise RuntimeError(f"unknown detector {name!r}")
    out = pd.DataFrame(rows, columns=["key", "claim", "vids", "known"])
    out["vids"] = [[int(v) for v in vs][:cap] for vs in out.vids]
    out["strength"] = np.arange(len(out))
    return out


def place_claims(conn: sqlite3.Connection, sample: list[dict[str, Any]]) -> pd.DataFrame:
    """The owner's hand-checked place mentions (`artifacts/places/sample.json`) as claims."""
    places = _q(conn, "SELECT place_id, he FROM places").set_index("place_id").he
    rows = [
        (f"place {s['verse_id']} {s['lemma']}",
         f"A word in this verse is the name of the place {places.get(s['place_id'], '?')}.",
         [int(s["verse_id"])], True)
        for s in sample
    ]  # fmt: skip
    return pd.DataFrame(rows, columns=["key", "claim", "vids", "known"])


def draw(df: pd.DataFrame, top: int, n: int, known_max: int, seed: int) -> pd.DataFrame:
    """`n` findings drawn from the `top` strongest (set `sample`), and up to `known_max` of the
    known answers not drawn (set `known`)."""
    pool = df.head(top)
    rng = np.random.default_rng(seed)
    take = np.sort(rng.choice(len(pool), size=min(n, len(pool)), replace=False))
    sample = pool.iloc[take].assign(set="sample")
    known = df[df.known & ~df.key.isin(sample.key)].head(known_max).assign(set="known")
    return pd.concat([sample, known], ignore_index=True).assign(population=len(pool))


def draw_pages(
    full: pd.DataFrame, lists: dict[str, pd.DataFrame], n: int, known_max: int, seed: int
) -> pd.DataFrame:
    """The `pages` run (§16.86, D147): `n` findings drawn uniformly from each list a page shows
    (set `shown`, or `marked`: what it marks as strong), all of a list shorter than `n`; and up to
    `known_max` of all the detector's known answers not drawn (set `known`). `population`: the
    size of the list each was drawn from."""
    rng = np.random.default_rng(seed)
    parts = []
    for name, df in lists.items():
        take = np.sort(rng.choice(len(df), size=min(n, len(df)), replace=False))
        parts.append(df.iloc[take].assign(set=name, population=len(df)))
    drawn = pd.concat(parts, ignore_index=True).key if parts else pd.Series([], dtype=str)
    known = full[full.known & ~full.key.isin(drawn)].head(known_max)
    parts.append(known.assign(set="known", population=int(full.known.sum())))
    return pd.concat(parts, ignore_index=True)


def out_dir(cfg: dict[str, Any]) -> str:
    """`llm_audit` for the strongest (M152's run), `llm_audit_pages` for what the pages list; a
    `tag` (a run of some detectors only, M164) gives its own folder, `llm_audit_pages_<tag>`."""
    ac = cfg["llm_audit"]
    pop = ac["population"]
    if pop not in POPULATIONS:
        raise RuntimeError(f"llm_audit.population {pop!r}: one of {', '.join(POPULATIONS)}")
    base = OUT if pop == "strongest" else f"{OUT}_{pop}"
    return f"{base}_{ac['tag']}" if ac.get("tag") else base


def build_items(cfg: dict[str, Any], log: Log) -> pd.DataFrame:
    """`set, detector, custom_id, key, claim, vids, known`: every detector's draw and the
    places calibration."""
    from bsim.store.db import connect_readonly

    ac = cfg["llm_audit"]
    db = resolve_path(cfg, "db")
    if not db.exists():
        raise RuntimeError(f"{db} missing; run `bsim build-db` first")
    sample_path = resolve_path(cfg, "artifacts") / "places" / "sample.json"
    if not sample_path.exists():
        raise RuntimeError(f"{sample_path} missing; run `bsim places` first")
    conn = connect_readonly(db)
    try:
        src = Source(conn)
        parts = []
        pages = ac["population"] == "pages"
        for i, name in enumerate(ac["detectors"]):
            df = findings(conn, name, src, ac["max_verses"])
            if pages:
                conds = {s: ac["pages"][s].get(name) for s in PAGE_SETS}
                lists = {
                    s: findings(conn, name, src, ac["max_verses"], c) if c else df
                    for s, c in conds.items()
                    if s == "shown" or c
                }
                d = draw_pages(df, lists, ac["sample"], ac["known_max"], ac["pages"]["seed"] + i)
            else:
                d = draw(df, ac["top"], ac["sample"], ac["known_max"], ac["seed"] + i)
            parts.append(d.assign(detector=name))
            drawn = ", ".join(
                f"{s} {int((d.set == s).sum())} of {int(d.population[d.set == s].iloc[0])}"
                for s in d.set.unique()
            )
            log(f"  {name}: {len(df)} findings; {drawn}")
        places = place_claims(conn, json.loads(sample_path.read_text("utf-8")))
        parts.append(places.assign(set="calibration", detector="places", population=len(places)))
        texts = {
            v: {"ref": src.ref[v], "text": pointed(" ".join(src.tokens[v]))}
            for p in parts
            for vs in p.vids
            for v in vs
        }
    finally:
        conn.close()
    items = pd.concat(parts, ignore_index=True)
    items["custom_id"] = [f"aud-{i}" for i in range(len(items))]
    items["prompt"] = [
        user_prompt(d, c, [texts[v] for v in vs])
        for d, c, vs in zip(items.detector, items.claim, items.vids, strict=True)
    ]
    cols = ["set", "detector", "custom_id", "key", "claim", "vids", "known", "population", "prompt"]
    return items[cols]


def user_prompt(detector: str, claim: str, verses: list[dict[str, str]]) -> str:
    body = "\n\n".join(f"{v['ref']}\n{v['text']}" for v in verses)
    return f"The feature: {DEFINITIONS[detector]}\n\nThe claim: {claim}\n\nThe verses:\n\n{body}"


def answer(max_chars: int) -> Callable[[dict[str, Any]], dict[str, Any] | None]:
    def check(data: dict[str, Any]) -> dict[str, Any] | None:
        if data.get("verdict") not in VERDICTS:
            return None
        try:
            p = float(np.clip(float(data["p_right"]), 0.0, 1.0))
        except (KeyError, TypeError, ValueError):
            return None
        return {
            "verdict": data["verdict"],
            "p_right": p,
            "rationale": str(data.get("rationale", ""))[:max_chars],
        }

    return check


# --- the run ----------------------------------------------------------------------------------


def run_llm_audit(
    cfg: dict[str, Any],
    log: Log = print,
    dry_run: bool = False,
    client: Any = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    lc = cfg["llm_audit"]
    out = resolve_path(cfg, "artifacts") / out_dir(cfg)

    def prepare() -> tuple[pd.DataFrame, list[dict]]:
        items = build_items(cfg, log)
        reqs = [
            make_request(cid, SYSTEM, prompt, SCHEMA, lc)
            for cid, prompt in zip(items.custom_id, items.prompt, strict=True)
        ]
        return items.drop(columns="prompt"), reqs

    def describe(items: pd.DataFrame) -> str:
        n = items.set.value_counts().to_dict()
        drawn = ", ".join(f"{n[s]} {s}" for s in ("sample", *PAGE_SETS) if n.get(s))
        return (
            f"{len(items)} requests ({drawn} findings, {n.get('known', 0)} known,"
            f" {n.get('calibration', 0)} places)"
        )

    got = run_batch(
        out, lc, prepare, answer(lc["rationale_chars"]), log=log, dry_run=dry_run,
        client=client, sleep=sleep, items_file="items.parquet", describe=describe,
    )  # fmt: skip
    if not isinstance(got, Collected):
        return got
    df = ensure_columns(got.df, {"verdict": None, "p_right": np.nan, "rationale": None})
    meta = summarise(df, cfg, got.state)
    df.to_parquet(out / "judged.parquet", index=False)
    write_meta(out / "llm_audit.meta.json", meta)
    write_report(cfg, df, meta)
    mark_collected(out, got.state)
    c = meta["calibration"]
    log(
        f"calibration: places {c['places_right']} right ({'holds' if c['holds'] else 'fails'}),"
        f" known {c['known_right']}; about ${meta['usage']['usd']:.2f}"
    )
    return meta


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(c - h, 3), round(c + h, 3)


def precision(x: pd.DataFrame) -> dict[str, Any]:
    ok = x[x.status == "ok"]
    right, wrong = int((ok.verdict == "right").sum()), int((ok.verdict == "wrong").sum())
    lo, hi = wilson(right, right + wrong)
    return {
        "judged": len(ok),
        "right": right,
        "wrong": wrong,
        "unsure": int((ok.verdict == "unsure").sum()),
        "precision": round(right / (right + wrong), 3) if right + wrong else None,
        "lo": lo,
        "hi": hi,
    }


def _size(g: pd.DataFrame) -> int | None:
    return int(g.population.iloc[0]) if "population" in g and len(g) else None


def detector_summary(g: pd.DataFrame, population: str) -> dict[str, Any]:
    """`strongest`: the sample's precision at the top level (M152's shape); `pages`: one entry per
    set drawn (`shown`, `marked`), each with the size of the list it was drawn from."""
    known = {"known": precision(g[g.known.astype(bool)].drop_duplicates("key"))}
    if population == "strongest":
        s = g[g.set == "sample"]
        return {**precision(s), "population": _size(s), **known}
    sets = {s: g[g.set == s] for s in PAGE_SETS if (g.set == s).any()}
    return {**{s: {**precision(x), "population": _size(x)} for s, x in sets.items()}, **known}


def summarise(df: pd.DataFrame, cfg: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    ac = cfg["llm_audit"]
    places = df[df.set == "calibration"]
    known = df[df.set.isin(["sample", *PAGE_SETS, "known"]) & df.known.astype(bool)]
    known = known.drop_duplicates(["detector", "key"])
    pr, kn = precision(places), precision(known)
    share = lambda p: (p["right"] / p["judged"]) if p["judged"] else 0.0  # noqa: E731
    holds = share(pr) >= ac["min_places"] and share(kn) >= ac["min_known"]
    return {
        "model": state["model"],
        "batch_id": state["batch_id"],
        "submitted_at": state["created_at"],
        "collected_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": {str(k): int(v) for k, v in df.status.value_counts().items()},
        "calibration": {
            "places_right": f"{pr['right']} / {pr['judged']}",
            "places_owner": "49 / 50",
            "known_right": f"{kn['right']} / {kn['judged']}",
            "min_places": ac["min_places"],
            "min_known": ac["min_known"],
            "holds": bool(holds),
        },
        "population": ac["population"],
        "detectors": {
            name: detector_summary(g, ac["population"])
            for name, g in df[df.set != "calibration"].groupby("detector", sort=False)
        },
        "usage": usage(df, ac),
        "config_hash": config_hash(cfg, "llm_audit"),
    }


def rows(meta: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per detector and population judged: `strongest` (M152's run) or the `pages`
    run's `shown` / `marked`, with the size of the list drawn from."""
    out = []
    for name, d in meta["detectors"].items():
        sets = (
            {"strongest": d}
            if meta.get("population", "strongest") == "strongest"
            else {s: d[s] for s in PAGE_SETS if s in d}
        )
        for s, x in sets.items():
            keep = ("judged", "right", "wrong", "unsure", "precision", "lo", "hi", "population")
            out.append({"detector": name, "set": s, **{k: x.get(k) for k in keep}})
    return out


def write_report(cfg: dict[str, Any], df: pd.DataFrame, meta: dict[str, Any]) -> None:
    from bsim.data.report import md_table

    c = meta["calibration"]
    pop = meta.get("population", "strongest")
    what = (
        "a sample of each detector's strongest findings"
        if pop == "strongest"
        else "a sample of what each page lists (shown) and marks as strong (marked)"
    )
    lines = [
        f"# How often the detectors are right (Claude's reading of {what})",
        "",
        f"Calibration: the owner's place sample {c['places_right']} right (owner 49 / 50), known"
        f" answers {c['known_right']}: {'holds' if c['holds'] else 'fails, not published'}.",
        "",
        md_table(
            [
                "detector",
                "set",
                "of",
                "judged",
                "right",
                "wrong",
                "unsure",
                "precision",
                "95 % CI",
                "known",
            ],
            [
                [
                    r["detector"],
                    r["set"],
                    r["population"],
                    r["judged"],
                    r["right"],
                    r["wrong"],
                    r["unsure"],
                    r["precision"],
                    f"[{r['lo']}, {r['hi']}]",
                    "{right} / {judged}".format(**meta["detectors"][r["detector"]]["known"]),
                ]
                for r in rows(meta)
            ],
        ),  # fmt: skip
        "",
        "## Findings judged wrong",
        "",
    ]
    wrong = df[(df.verdict == "wrong") & ~df.set.isin(["calibration", "known"])]
    wrong = wrong.drop_duplicates(["detector", "key"])
    for name, g in wrong.groupby("detector", sort=False):
        lines.append(f"### {name}")
        lines += [f"- {k}: {cl}" for k, cl in zip(g.key, g.claim, strict=True)]
        lines.append("")
    ev = resolve_path(cfg, "artifacts") / "eval"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / f"{out_dir(cfg)}.md").write_text("\n".join(lines) + "\n", "utf-8")


# --- read back, for the API -------------------------------------------------------------------


def run_files(cfg: dict[str, Any]) -> list[Path]:
    """The meta files of the runs shown (`llm_audit.shown_runs`, folders under artifacts/), in
    order: a later run's detectors replace an earlier one's; whether or not they are there."""
    art = resolve_path(cfg, "artifacts")
    return [art / f / "llm_audit.meta.json" for f in cfg["llm_audit"]["shown_runs"]]


def read_precision(cfg: dict[str, Any]) -> dict[str, Any]:
    """`runs` (each calibrated run: its population, model, date, calibration) and `detectors`
    (detector -> one row per population judged). A run whose calibration fails is left out."""
    runs, detectors = [], {}
    for f in run_files(cfg):
        if not f.exists():
            continue
        meta = json.loads(f.read_text("utf-8"))
        if not meta.get("calibration", {}).get("holds"):
            continue
        c = meta["calibration"]
        pop = meta.get("population", "strongest")
        runs.append({
            "run": f.parent.name, "population": pop, "model": meta["model"],
            "collected_at": meta["collected_at"], "places_right": c["places_right"],
            "known_right": c["known_right"],
        })  # fmt: skip
        for r in rows(meta):
            d = r.pop("detector")
            # a later run replaces an earlier one's row of the same population
            detectors[d] = [x for x in detectors.get(d, []) if x["set"] != r["set"]] + [r]
    return {"runs": runs, "detectors": detectors}
