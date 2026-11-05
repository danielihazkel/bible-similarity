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
"""

from __future__ import annotations

import json
import math
import sqlite3
import time
from collections.abc import Callable
from datetime import UTC, datetime
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
    "places": "Place mentions (§16.56): a word in the verse is the name of a place (not a person "
    "of the same name and not a common noun).",
}


# --- the findings -------------------------------------------------------------------------------


def _q(conn: sqlite3.Connection, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn)


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


def findings(conn: sqlite3.Connection, name: str, src: Source, cap: int) -> pd.DataFrame:
    """`key, claim, vids, known, strength`: a detector's findings, strongest first."""
    rows: list[tuple[str, str, list[int], bool]] = []
    if name == "etiologies":
        df = _q(conn, "SELECT * FROM etiologies ORDER BY p, score DESC")
        for r in df.itertuples():
            name_ = src.words(r.verse_id, list(range(int(r.name_first), int(r.name_last) + 1)))
            echo = ""
            if _known(r.echo_disp):
                echo = f", playing on the word {src.words(r.verse_id, [int(r.echo_disp)])}"
            claim = f"This verse names {name_} ({r.kind}) and explains the name{echo}."
            rows.append((f"naming {r.naming}", claim, [r.verse_id], _known(r.known)))
    elif name == "brackets":
        df = _q(conn, "SELECT * FROM brackets ORDER BY q, score DESC")
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
        df = _q(conn, "SELECT * FROM retold_pairs ORDER BY score DESC")
        for r in df.itertuples():
            claim = (
                f"{src.ref[r.later_first]}–{src.ref[r.later_last]} tells again, in largely the"
                f" same words, what {src.ref[r.src_first]}–{src.ref[r.src_last]} {r.grp}."
            )
            vids = _span(r.src_first, r.src_last, 3) + _span(r.later_first, r.later_last, 3)
            rows.append((f"retold {r.pair}", claim, vids, _known(r.known)))
    elif name == "binomials":
        df = _q(conn, "SELECT * FROM binomials ORDER BY n DESC")
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
        df = _q(conn, "SELECT * FROM typescenes WHERE parallel_text = 0 ORDER BY q, score DESC")
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
        df = _q(conn, "SELECT * FROM acrostics ORDER BY q, score DESC")
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
        df = _q(conn, "SELECT * FROM wordplay ORDER BY q, score DESC")
        for r in df.itertuples():
            claim = (
                f"{pointed(r.a_form)} and {pointed(r.b_form)} are set side by side as a play on"
                f" their sound ({r.kind})."
            )
            vids = list(dict.fromkeys([r.a_vid, r.b_vid]))
            rows.append((f"{r.a_vid}:{r.a_idx} {r.b_vid}:{r.b_idx}", claim, vids, False))
    elif name == "allusions":
        df = _q(conn, "SELECT * FROM allusions ORDER BY q, score DESC")
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
        df = _q(conn, "SELECT * FROM refrains WHERE strongest = 1 ORDER BY p")
        for r in df.itertuples():
            claim = (
                f"{pointed(r.text)} comes back {r.k} times between {src.ref[r.first_vid]} and"
                f" {src.ref[r.last_vid]} as a refrain."
            )
            vids = [r.first_vid, r.last_vid]
            rows.append((f"refrain {r.refrain_id}", claim, vids, _known(r.known)))
    elif name == "sayings":
        df = _q(conn, "SELECT * FROM forms_sayings ORDER BY prob")
        for r in df.itertuples():
            claim = f"This verse has a graded numerical saying ({r.steps})."
            rows.append((f"saying {r.verse_id}", claim, [r.verse_id], _known(r.known)))
    elif name == "lists":
        df = _q(conn, "SELECT * FROM forms_lists ORDER BY likeness DESC")
        for r in df.itertuples():
            claim = (
                f"{src.ref[r.first_vid]}–{src.ref[r.last_vid]} is a list of {r.n_like} like"
                f" items ({r.kind})."
            )
            vids = _span(r.first_vid, r.last_vid, 6)
            rows.append((f"list {r.list_id}", claim, vids, _known(r.known)))
    elif name == "mirrors":
        df = _q(conn, "SELECT * FROM mirror_verses ORDER BY q, p")
        for r in df.itertuples():
            claim = (
                "The words "
                f"{src.words(r.verse_id, json.loads(r.idxs))} repeat in this verse in mirror"
                " order (A B ... B A)."
            )
            rows.append((f"mirror {r.verse_id}", claim, [r.verse_id], False))
    elif name == "ciphers":
        df = _q(conn, "SELECT * FROM cipher_hits ORDER BY known DESC, hit_id")
        for r in df.itertuples():
            claim = (
                f"The letters {r.span} in this verse are written in the {r.cipher} cipher and"
                f" read {r.reads}, and the text means it so."
            )
            rows.append((f"cipher {r.hit_id}", claim, [r.verse_id], _known(r.known)))
    elif name == "seams":
        df = _q(conn, "SELECT * FROM seams ORDER BY rank, shift DESC")
        for r in df.itertuples():
            claim = (
                f"Between {src.ref[r.verse_id - 1]} and {src.ref[r.verse_id]} the vocabulary"
                " shifts, marking a join between sources or sections."
            )
            rows.append((f"seam {r.verse_id}", claim, [r.verse_id - 1, r.verse_id], False))
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
    return pd.concat([sample, known], ignore_index=True)


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
        for i, name in enumerate(ac["detectors"]):
            df = findings(conn, name, src, ac["max_verses"])
            d = draw(df, ac["top"], ac["sample"], ac["known_max"], ac["seed"] + i)
            parts.append(d.assign(detector=name))
            log(f"  {name}: {len(df)} findings, {int((d.set == 'sample').sum())} drawn,"
                f" {int((d.set == 'known').sum())} known")  # fmt: skip
        places = place_claims(conn, json.loads(sample_path.read_text("utf-8")))
        parts.append(places.assign(set="calibration", detector="places"))
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
    cols = ["set", "detector", "custom_id", "key", "claim", "vids", "known", "prompt"]
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
    out = resolve_path(cfg, "artifacts") / OUT

    def prepare() -> tuple[pd.DataFrame, list[dict]]:
        items = build_items(cfg, log)
        reqs = [
            make_request(cid, SYSTEM, prompt, SCHEMA, lc)
            for cid, prompt in zip(items.custom_id, items.prompt, strict=True)
        ]
        return items.drop(columns="prompt"), reqs

    def describe(items: pd.DataFrame) -> str:
        n = items.set.value_counts().to_dict()
        return (
            f"{len(items)} requests ({n.get('sample', 0)} findings, {n.get('known', 0)} known,"
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


def summarise(df: pd.DataFrame, cfg: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    ac = cfg["llm_audit"]
    places = df[df.set == "calibration"]
    known = df[df.set.isin(["sample", "known"]) & df.known.astype(bool)]
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
        "detectors": {
            name: {
                **precision(g[g.set == "sample"]),
                "known": precision(g[g.known.astype(bool)]),
            }
            for name, g in df[df.set != "calibration"].groupby("detector", sort=False)
        },
        "usage": usage(df, ac),
        "config_hash": config_hash(cfg, "llm_audit"),
    }


def write_report(cfg: dict[str, Any], df: pd.DataFrame, meta: dict[str, Any]) -> None:
    from bsim.data.report import md_table

    c = meta["calibration"]
    lines = [
        "# How often the detectors are right (Claude's reading of a sample)",
        "",
        f"Calibration: the owner's place sample {c['places_right']} right (owner 49 / 50), known"
        f" answers {c['known_right']}: {'holds' if c['holds'] else 'fails, not published'}.",
        "",
        md_table(
            ["detector", "judged", "right", "wrong", "unsure", "precision", "95 % CI", "known"],
            [
                [
                    name,
                    d["judged"],
                    d["right"],
                    d["wrong"],
                    d["unsure"],
                    d["precision"],
                    f"[{d['lo']}, {d['hi']}]",
                    f"{d['known']['right']} / {d['known']['judged']}",
                ]
                for name, d in meta["detectors"].items()
            ],
        ),  # fmt: skip
        "",
        "## Findings judged wrong",
        "",
    ]
    wrong = df[(df.verdict == "wrong") & (df.set != "calibration")]
    for name, g in wrong.groupby("detector", sort=False):
        lines.append(f"### {name}")
        lines += [f"- {k}: {cl}" for k, cl in zip(g.key, g.claim, strict=True)]
        lines.append("")
    ev = resolve_path(cfg, "artifacts") / "eval"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "llm_audit.md").write_text("\n".join(lines) + "\n", "utf-8")
