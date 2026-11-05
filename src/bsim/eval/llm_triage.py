"""`bsim llm-triage`: Claude's judgement of the label queue's pairs, as suggestions (DESIGN.md
§16.81, D134).

The queue (§16.79) orders the unlabelled train-book pairs by where the lexical and semantic lists
disagree; judging them takes a reader's time. A language model reads both verses and suggests a
verdict, which the queue shows beside the label buttons: you confirm it or not. Its suggestions
are never labels: they live in `artifacts/llm/` and never in `paths.labels`.

One Message Batches request per pair (`llm_triage.model`, half price, results within the day),
each with the two verses' references and pointed text (cantillation removed) and a structured
answer (`output_config.format`): `verdict` real | not | unsure, `p_real` (the probability that
the connection is real), `kind`, and a short `rationale` that names Hebrew words and is told never
to translate. The batch holds
- **calibration** (fixed before the first run): `calibration.gold` Sefaria verse links of the
  dev split against `calibration.random` random pairs of dev-book verses that no gold links (not
  neighbours, not the same text); the AUC of `p_real`, gold against random. Suggestions are shown
  only when it reaches `calibration.min_auc`;
- **triage**: the first `max_pairs` pairs of the label queue, labelled pairs left out.

The batch id is written first (`artifacts/llm/batch.json`), so a run that is stopped picks the
same batch up again instead of paying twice. `--dry-run` writes the requests and an estimate of
the cost without calling the API. The key comes from `ANTHROPIC_API_KEY` (the SDK's own lookup).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path, write_meta

# pointed, clean_rationale, auc, make_client and estimate were this module's own until L1
from bsim.eval.llm_batch import (  # noqa: F401
    Collected,
    Log,
    auc,
    clean_rationale,
    ensure_columns,
    estimate,
    make_client,
    make_request,
    mark_collected,
    parse_message,
    pointed,
    run_batch,
    undirected,
    usage,
)

VERDICTS = ("real", "not", "unsure")
KINDS = (
    "quotation",
    "allusion",
    "parallel_account",
    "shared_formula",
    "shared_phrase",
    "thematic",
    "none",
)
SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "p_real": {"type": "number"},
        "kind": {"type": "string", "enum": list(KINDS)},
        "rationale": {"type": "string"},
    },
    "required": ["verdict", "p_real", "kind", "rationale"],
    "additionalProperties": False,
}
SYSTEM = """You judge whether two verses of the Hebrew Bible are connected in a way a careful \
reader of the Hebrew text would record.

Connected (verdict "real"): one verse quotes the other; one alludes to the other through a \
distinctive phrase or a rare word; the two tell the same event (parallel accounts, as Kings and \
Chronicles); they share a formula that ties these two passages together; or one evidently plays \
on the other's theme with shared language.

Not connected (verdict "not"): the verses only share common words (the divine name, ויאמר, הארץ, \
בני ישראל) or a common topic, or the resemblance is the kind any two verses of the same genre have.

Use "unsure" when the text alone does not decide it.

Rules:
- Never translate a verse, or any word or phrase of it, into English or any other language. \
Quote Hebrew words exactly as they are written, in Hebrew letters.
- {rationale}
- p_real is your probability, from 0 to 1, that the connection is real.
- kind is the kind of connection, "none" when there is none."""

RATIONALE = {
    "english": "The rationale is one or two short sentences in English naming the Hebrew words or "
    "the feature that decide your verdict.",
    "hebrew": "The rationale is one or two short sentences in Hebrew, and only in Hebrew, naming "
    "the words or the feature that decide your verdict. Write no word of English or of any other "
    "language in it.",
}


def system_prompt(language: str) -> str:
    """The instructions, with the rationale asked in `language` (`llm_triage.rationale`)."""
    if language not in RATIONALE:
        raise RuntimeError(f"llm_triage.rationale must be one of {sorted(RATIONALE)}")
    return SYSTEM.replace("{rationale}", RATIONALE[language])


def user_prompt(a: dict[str, str], b: dict[str, str]) -> str:
    return f"Verse A: {a['ref']}\n{a['text']}\n\nVerse B: {b['ref']}\n{b['text']}"


def request(custom_id: str, a: dict[str, str], b: dict[str, str], lc: dict[str, Any]) -> dict:
    """One Message Batches request (plain dicts, as the SDK takes them)."""
    return make_request(custom_id, system_prompt(lc["rationale"]), user_prompt(a, b), SCHEMA, lc)


def answer(max_chars: int) -> Callable[[dict[str, Any]], dict[str, Any] | None]:
    """The fields of a verdict answer, None when it is not one."""

    def check(data: dict[str, Any]) -> dict[str, Any] | None:
        if data.get("verdict") not in VERDICTS or data.get("kind") not in KINDS:
            return None
        try:
            p = float(np.clip(float(data["p_real"]), 0.0, 1.0))
        except (KeyError, TypeError, ValueError):
            return None
        return {
            "verdict": data["verdict"],
            "p_real": p,
            "kind": data["kind"],
            "rationale": str(data.get("rationale", ""))[:max_chars],
        }

    return check


def parse(message: Any, max_chars: int) -> dict[str, Any]:
    """A succeeded batch result's message as a row (`status` says when it could not be read)."""
    return parse_message(message, answer(max_chars))


# --- the pairs ---------------------------------------------------------------------------------


def calibration_pairs(
    verses: pd.DataFrame,
    sefaria: pd.DataFrame,
    linked: set[tuple[int, int]],
    split_books: set[int],
    n_gold: int | None,
    n_random: int | None,
    window: int,
    seed: int,
) -> pd.DataFrame:
    """`a, b, gold`: Sefaria's verse links of the split and random pairs of its books that no
    gold links; neither kind a pair of neighbours (±window, one book) or of the same text.
    `n_gold` None takes every fair link, `n_random` None as many random pairs as links taken."""
    book = verses.book_id.to_numpy()
    text = verses.text_plain.to_numpy()

    def fair(a: int, b: int) -> bool:
        return a != b and not (book[a] == book[b] and abs(a - b) <= window) and text[a] != text[b]

    rng = np.random.default_rng(seed)
    gold = sorted(
        p for p in undirected(sefaria.src_vid.to_numpy(), sefaria.tgt_vid.to_numpy()) if fair(*p)
    )
    n_gold = len(gold) if n_gold is None else n_gold
    n_random = n_gold if n_random is None else n_random
    if len(gold) < n_gold:
        raise RuntimeError(f"only {len(gold)} gold pairs for calibration, {n_gold} asked")
    take = [gold[i] for i in sorted(rng.choice(len(gold), n_gold, replace=False))]
    pool = np.flatnonzero(np.isin(book, sorted(split_books)))
    rand: set[tuple[int, int]] = set()
    while len(rand) < n_random:
        a, b = (int(x) for x in rng.choice(pool, 2, replace=False))
        p = (min(a, b), max(a, b))
        if fair(*p) and p not in linked:
            rand.add(p)
    rows = [(a, b, True) for a, b in take] + [(a, b, False) for a, b in sorted(rand)]
    return pd.DataFrame(rows, columns=["a", "b", "gold"])


def queue_pairs(cfg: dict[str, Any], n: int) -> pd.DataFrame:
    """`a, b`: the first `n` unlabelled pairs of the label queue (verse ids)."""
    from bsim.api.label_queue import queue_for, train_books, unlabelled
    from bsim.store.db import connect_readonly
    from bsim.store.labels import read_labels

    db = resolve_path(cfg, "db")
    if not db.exists():
        raise RuntimeError(f"{db} missing; run `bsim build-db` first")
    books = train_books(cfg, cfg["labels"]["queue"]["split"])
    if books is None:
        raise RuntimeError("splits.json missing; run `bsim build-links` first")
    conn = connect_readonly(db)
    try:
        pool = queue_for(conn, db, books, cfg["retrieval"]["k"] + 1)
    finally:
        conn.close()
    done = {(r["a_id"], r["b_id"]) for r in read_labels(resolve_path(cfg, "labels"))}
    done |= {(b, a) for a, b in done}
    top = unlabelled(pool, done, "all")[:n]
    v = lambda i: int(i.removeprefix("v:"))  # noqa: E731
    return pd.DataFrame({"a": [v(p.a_id) for p in top], "b": [v(p.b_id) for p in top]})


# --- the run -----------------------------------------------------------------------------------


def run_llm_triage(
    cfg: dict[str, Any],
    log: Log = print,
    dry_run: bool = False,
    client: Any = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    lc = cfg["llm_triage"]
    out = resolve_path(cfg, "artifacts") / "llm"

    def prepare() -> tuple[pd.DataFrame, list[dict]]:
        pairs = build_pairs(cfg, log)
        texts = verse_texts(cfg)
        requests = [
            request(cid, texts[a], texts[b], lc)
            for cid, a, b in zip(pairs.custom_id, pairs.a, pairs.b, strict=True)
        ]
        return pairs, requests

    def describe(pairs: pd.DataFrame) -> str:
        return (
            f"{len(pairs)} requests ({int((pairs.set == 'calibration').sum())} calibration,"
            f" {int((pairs.set == 'triage').sum())} triage)"
        )

    got = run_batch(
        out, lc, prepare, answer(lc["rationale_chars"]), log=log, dry_run=dry_run,
        client=client, sleep=sleep, items_file="pairs.parquet", describe=describe,
    )  # fmt: skip
    if not isinstance(got, Collected):
        return got
    df = ensure_columns(
        got.df, {"verdict": None, "p_real": np.nan, "kind": None, "rationale": None}
    )
    meta = summarise(df, cfg, got.state)
    df["a_id"] = "v:" + df.a.astype(str)
    df["b_id"] = "v:" + df.b.astype(str)
    cols = ["set", "custom_id", "a_id", "b_id", "gold", "status", "verdict", "p_real", "kind",
            "rationale", "input_tokens", "output_tokens"]  # fmt: skip
    df[df.set == "calibration"][cols].to_parquet(out / "calibration.parquet", index=False)
    df[df.set == "triage"][cols].to_parquet(out / "triage.parquet", index=False)
    write_meta(out / "llm_triage.meta.json", meta)
    mark_collected(out, got.state)
    c = meta["calibration"]
    log(
        f"calibration: AUC {c['auc']} (needs {c['min_auc']}: {'holds' if c['holds'] else 'fails'});"
        f" triage: {meta['triage']['verdicts']}; {meta['usage']['input_tokens']} input,"
        f" {meta['usage']['output_tokens']} output tokens, about ${meta['usage']['usd']:.2f}"
    )
    return meta


def build_pairs(cfg: dict[str, Any], log: Log) -> pd.DataFrame:
    """`set, custom_id, a, b, gold`: the calibration pairs, then the triage pairs."""
    from bsim.data.canon import BY_SEFARIA

    lc, cal = cfg["llm_triage"], cfg["llm_triage"]["calibration"]
    proc = resolve_path(cfg, "data_processed")
    for file, cmd in (
        ("verses.parquet", "build-corpus"),
        ("links.parquet", "build-links"),
        ("splits.json", "build-links"),
    ):
        if not (proc / file).exists():
            raise RuntimeError(f"{proc / file} missing; run `bsim {cmd}` first")
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "text_plain"])
    verses = verses.sort_values("verse_id").reset_index(drop=True)
    links = pd.read_parquet(proc / "links.parquet")
    sefaria = links[(links.level == "verse") & (links.split == cal["split"])]
    linked = undirected(links.src_vid.to_numpy(), links.tgt_vid.to_numpy())
    for name in ("openbible_links.parquet", "etcbc_links.parquet"):
        if (proc / name).exists():
            g = pd.read_parquet(proc / name, columns=["src_vid", "tgt_vid"])
            linked |= undirected(g.src_vid.to_numpy(), g.tgt_vid.to_numpy())
    splits = json.loads((proc / "splits.json").read_text("utf-8"))["books"]
    books = {BY_SEFARIA[b].book_id for b, s in splits.items() if s == cal["split"]}
    calib = calibration_pairs(
        verses, sefaria, linked, books, cal["gold"], cal["random"],
        cfg["retrieval"]["neighbor_window"], lc["seed"],
    )  # fmt: skip
    triage = queue_pairs(cfg, lc["max_pairs"]).assign(gold=None)
    log(f"calibration: {len(calib)} pairs; triage: {len(triage)} pairs of the label queue")
    calib = calib.assign(set="calibration", custom_id=[f"cal-{i}" for i in range(len(calib))])
    triage = triage.assign(set="triage", custom_id=[f"tri-{i}" for i in range(len(triage))])
    return pd.concat([calib, triage], ignore_index=True)[["set", "custom_id", "a", "b", "gold"]]


def verse_texts(cfg: dict[str, Any]) -> dict[int, dict[str, str]]:
    proc = resolve_path(cfg, "data_processed")
    v = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "ref", "text_display"])
    return {
        int(i): {"ref": r, "text": pointed(t)}
        for i, r, t in zip(v.verse_id, v.ref, v.text_display, strict=True)
    }


def summarise(df: pd.DataFrame, cfg: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    lc, cal = cfg["llm_triage"], cfg["llm_triage"]["calibration"]
    c = df[(df.set == "calibration") & (df.status == "ok")]
    gold = c.gold.astype(bool).to_numpy()
    a = auc(gold, c.p_real.to_numpy(float))
    t = df[df.set == "triage"]

    def counts(x: pd.DataFrame) -> dict[str, int]:
        return {v: int((x.verdict == v).sum()) for v in VERDICTS}

    return {
        "model": state["model"],
        "rationale": lc["rationale"],
        "batch_id": state["batch_id"],
        "submitted_at": state["created_at"],
        "collected_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": {str(k): int(v) for k, v in df.status.value_counts().items()},
        "calibration": {
            "split": cal["split"],
            "gold": int(gold.sum()),
            "random": int((~gold).sum()),
            "auc": a,
            "min_auc": cal["min_auc"],
            "holds": a is not None and a >= cal["min_auc"],
            "gold_verdicts": counts(c[gold]),
            "random_verdicts": counts(c[~gold]),
        },
        "triage": {"pairs": len(t), "ok": int((t.status == "ok").sum()), "verdicts": counts(t)},
        "usage": usage(df, lc),
        "config_hash": config_hash(cfg, "llm_triage"),
    }


def read_triage(cfg: dict[str, Any]) -> tuple[dict[str, Any] | None, pd.DataFrame | None]:
    """The last collected run's meta and triage rows (None when there is none)."""
    out = resolve_path(cfg, "artifacts") / "llm"
    meta_path, rows_path = out / "llm_triage.meta.json", out / "triage.parquet"
    if not (meta_path.exists() and rows_path.exists()):
        return None, None
    return json.loads(Path(meta_path).read_text("utf-8")), pd.read_parquet(rows_path)
