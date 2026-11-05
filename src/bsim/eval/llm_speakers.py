"""`bsim llm-speakers` / `bsim speaker-eval`: who speaks each quotation, by Claude's reading, as a
gold for the speaker rules (DESIGN.md §16.87, D143; series L6).

The speaker rules (§16.26: explicit, carried, enclosing, formula, framed) were measured by hand
tallies only (42 / 50, 37 / 45), and the judged items were not kept. Here `llm_speakers.per_source`
quotations of each source (and of those with no speaker) are drawn, seeded and fixed before the
run, and each is sent to Claude with the passage it stands in (up to `context` verses before its
first verse, pointed) and its opening words. Claude names the speaker as a word of the passage,
exactly as written, with the reference of the verse it is in, or nothing when the passage does
not name one. The word is mapped back to its lemma through the passage's words, and
`speaker-eval` scores each source's agreement with Claude, per book split.

Calibration: none can be fixed in advance (no item-level gold exists), so `speaker-eval` writes
`review.csv`, `llm_speakers.owner_check` of Claude's answers for the owner to mark right or
wrong; the agreement is published with the owner's count beside it, and is not used to change a
rule until that count is in. Rules changed later are tuned on the dev books only.
"""

from __future__ import annotations

import json
import re
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

OUT = "llm_speakers"
NONE = "none"  # the stratum of quotations the rules gave no speaker
SCHEMA = {
    "type": "object",
    "properties": {
        "speaker": {"type": "string"},
        "ref": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": ["speaker", "ref", "rationale"],
    "additionalProperties": False,
}
SYSTEM = """You read a passage of the Hebrew Bible in which a speech begins, and say who speaks it.

Answer with the speaker's name or title exactly as it is written in the passage, in Hebrew \
letters, as one word without the letters joined before it (ו, ה, ל, ב, כ, מ, ש): for example \
משה, יהוה, המלך → מלך. Give the reference of the verse of the passage where you found that word \
(as written above the verse). If the passage does not name the speaker anywhere, answer an empty \
speaker and an empty reference.

Rules:
- Never translate a verse, or any word or phrase of it, into English or any other language.
- The rationale is one short sentence in Hebrew, and only in Hebrew."""

_MARKS = re.compile("[֑-ׇ־׀׃׳״|׀ ]")
_FINAL = str.maketrans("ךםןףץ", "כמנפצ")


def consonants(text: str) -> str:
    """Letters only (points, accents, maqaf, paseq and spaces dropped), final forms folded."""
    return _MARKS.sub("", text or "").translate(_FINAL)


def match_lemma(answer: str, ref: str, words: pd.DataFrame, refs: dict[int, str]) -> str | None:
    """The lemma of the passage word Claude named: a word of its verse (any verse of the passage
    when the reference does not match) whose letters are the answer's, or end with them after at
    most two prefixed letters. None when no word matches."""
    want = consonants(answer)
    if not want:
        return None
    by_ref = words[words.verse_id.map(refs) == ref]
    for pool in (by_ref, words):
        for surf, lem in zip(pool.surface, pool.content_lemmas, strict=True):
            have = consonants(surf)
            if lem and (have == want or (have.endswith(want) and len(have) - len(want) <= 2)):
                return str(lem).split()[0]
    return None


def lemma_key(x: Any) -> str | None:
    """A lemma id as text (`430`, `1121a`), whether stored as a number or a string."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    t = str(x)
    return t[:-2] if t.endswith(".0") else t


def draw(quotes: pd.DataFrame, per_source: int, seed: int) -> pd.DataFrame:
    """`per_source` quotations of each speaker source (`none`: no speaker), seeded."""
    q = quotes.assign(source=quotes.speaker_source.fillna(NONE))
    rng = np.random.default_rng(seed)
    parts = []
    for src in sorted(q.source.unique()):
        g = q[q.source == src]
        take = np.sort(rng.choice(len(g), size=min(per_source, len(g)), replace=False))
        parts.append(g.iloc[take])
    return pd.concat(parts, ignore_index=True)


def build_items(cfg: dict[str, Any], log: Log) -> tuple[pd.DataFrame, dict[str, str]]:
    """The drawn quotations (`custom_id, quote, verse_id, source, speaker, book_id`) and each
    one's prompt."""
    from bsim.store.db import connect_readonly

    sc = cfg["llm_speakers"]
    path = resolve_path(cfg, "artifacts") / "dialogue" / "quotations.parquet"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim dialogue` first")
    quotes = pd.read_parquet(path)
    items = draw(quotes, sc["per_source"], sc["seed"])
    conn = connect_readonly(resolve_path(cfg, "db"))
    try:
        v = pd.read_sql_query(
            "SELECT verse_id, book_id, chapter, ref, display_tokens FROM verses", conn
        ).set_index("verse_id")
        clauses = pd.read_sql_query(
            "SELECT clause, verse_id, words FROM clauses WHERE clause IN ("
            + ",".join(str(int(x)) for x in items.quote)
            + ")",
            conn,
        ).set_index("clause")
    finally:
        conn.close()
    prompts: dict[str, str] = {}
    cids = []
    for i, r in enumerate(items.itertuples()):
        cid = f"spk-{i}"
        cids.append(cid)
        vids = passage(v, int(r.verse_id), int(r.last_verse_id), sc["context"], sc["max_verses"])
        tokens = json.loads(v.display_tokens[int(r.verse_id)])
        opening = ""
        if int(r.quote) in clauses.index:
            idxs = json.loads(clauses.words[int(r.quote)])
            opening = pointed(" ".join(tokens[j] for j in idxs if j < len(tokens)))
        body = "\n\n".join(
            f"{v.ref[x]}\n{pointed(' '.join(json.loads(v.display_tokens[x])))}" for x in vids
        )
        prompts[cid] = (
            f"{body}\n\nA speech begins in {v.ref[int(r.verse_id)]} with the words: {opening}\n"
            "Who speaks it?"
        )
    items = items.assign(custom_id=cids)
    items["context"] = [
        passage(v, int(a), int(b), sc["context"], sc["max_verses"])
        for a, b in zip(items.verse_id, items.last_verse_id, strict=True)
    ]
    log(f"{len(items)} quotations: {items.source.value_counts().to_dict()}")
    keep = ["custom_id", "quote", "verse_id", "last_verse_id", "book_id", "source", "speaker",
            "context"]  # fmt: skip
    return items[keep], prompts


def passage(v: pd.DataFrame, first: int, last: int, before: int, cap: int) -> list[int]:
    """The verses of the passage: up to `before` verses of the same chapter before `first`,
    through `last`, at most `cap` (the end cut first)."""
    book, chapter = v.book_id[first], v.chapter[first]
    start = first
    while start > first - before and start - 1 in v.index:
        if v.book_id[start - 1] != book or v.chapter[start - 1] != chapter:
            break
        start -= 1
    return list(range(start, min(last, start + cap - 1) + 1))


def answer(max_chars: int) -> Callable[[dict[str, Any]], dict[str, Any] | None]:
    def check(data: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(data.get("speaker"), str) or not isinstance(data.get("ref"), str):
            return None
        return {
            "answer": data["speaker"].strip(),
            "answer_ref": data["ref"].strip(),
            "rationale": str(data.get("rationale", ""))[:max_chars],
        }

    return check


def run_llm_speakers(
    cfg: dict[str, Any],
    log: Log = print,
    dry_run: bool = False,
    client: Any = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    lc = cfg["llm_speakers"]
    out = resolve_path(cfg, "artifacts") / OUT

    def prepare() -> tuple[pd.DataFrame, list[dict]]:
        items, prompts = build_items(cfg, log)
        reqs = [make_request(c, SYSTEM, prompts[c], SCHEMA, lc) for c in items.custom_id]
        return items, reqs

    got = run_batch(
        out, lc, prepare, answer(lc["rationale_chars"]), log=log, dry_run=dry_run,
        client=client, sleep=sleep, items_file="items.parquet",
    )  # fmt: skip
    if not isinstance(got, Collected):
        return got
    df = ensure_columns(got.df, {"answer": None, "answer_ref": None, "rationale": None})
    df["answer_lemma"] = lemmas_of(cfg, df)
    df.to_parquet(out / "judged.parquet", index=False)
    meta = {
        "model": got.state["model"],
        "batch_id": got.state["batch_id"],
        "submitted_at": got.state["created_at"],
        "collected_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": {str(k): int(v) for k, v in df.status.value_counts().items()},
        "usage": usage(df, lc),
        "config_hash": config_hash(cfg, "llm_speakers"),
    }
    write_meta(out / "llm_speakers.meta.json", meta)
    mark_collected(out, got.state)
    log(f"{meta['status']}; about ${meta['usage']['usd']:.2f}; now `bsim speaker-eval`")
    return meta


def lemmas_of(cfg: dict[str, Any], df: pd.DataFrame) -> list[str | None]:
    """Each answer's lemma, through the words of its passage."""
    from bsim.store.db import connect_readonly

    conn = connect_readonly(resolve_path(cfg, "db"))
    try:
        vids = sorted({int(x) for c in df.context for x in c})
        words = pd.read_sql_query(
            "SELECT verse_id, surface, content_lemmas FROM words WHERE verse_id IN ("
            + ",".join(map(str, vids or [-1]))
            + ")",
            conn,
        )
        refs = dict(conn.execute("SELECT verse_id, ref FROM verses").fetchall())
    finally:
        conn.close()
    out: list[str | None] = []
    for a, ref, ctx, st in zip(df.answer, df.answer_ref, df.context, df.status, strict=True):
        if st != "ok" or not a:
            out.append(None)
            continue
        out.append(match_lemma(a, ref, words[words.verse_id.isin(list(ctx))], refs))
    return out


# --- the scores ----------------------------------------------------------------------------------


def agreement(df: pd.DataFrame, dev_books: set[int]) -> dict[str, dict[str, Any]]:
    """Per rule source: answered, Claude named a speaker it could place, the rule agrees; on the
    dev books as well (where a rule may later be tuned)."""
    out: dict[str, dict[str, Any]] = {}
    ok = df[df.status == "ok"]
    for src, g in ok.groupby("source", sort=True):
        named = g[g.answer_lemma.notna()]
        same = named.answer_lemma.map(lemma_key) == named.speaker.map(lemma_key)
        dev = named.book_id.isin(sorted(dev_books))
        out[str(src)] = {
            "answered": len(g),
            "named": len(named),
            "agree": int(same.sum()) if src != NONE else None,
            "share": round(float(same.mean()), 3) if len(named) and src != NONE else None,
            "dev_named": int(dev.sum()),
            "dev_agree": int((same & dev).sum()) if src != NONE else None,
        }
    return out


def run_speaker_eval(cfg: dict[str, Any], log: Log = print) -> dict[str, Any]:
    """`bsim speaker-eval`: each source's agreement with Claude; the owner's review sheet written
    on the first run and read once it is marked."""
    from bsim.data.canon import BY_SEFARIA

    sc = cfg["llm_speakers"]
    art = resolve_path(cfg, "artifacts") / OUT
    if not (art / "judged.parquet").exists():
        raise RuntimeError(f"{art / 'judged.parquet'} missing; run `bsim llm-speakers` first")
    df = pd.read_parquet(art / "judged.parquet")
    splits = json.loads((resolve_path(cfg, "data_processed") / "splits.json").read_text("utf-8"))
    dev = {BY_SEFARIA[b].book_id for b, s in splits["books"].items() if s == "dev"}
    sheet = art / "review.csv"
    if not sheet.exists():
        pick = df[(df.status == "ok") & (df.answer != "")].sample(
            n=min(sc["owner_check"], int(((df.status == "ok") & (df.answer != "")).sum())),
            random_state=sc["seed"],
        )
        pick[["custom_id", "verse_id", "answer", "answer_ref"]].assign(owner="").to_csv(
            sheet, index=False, encoding="utf-8-sig"  # the BOM keeps Excel from losing the Hebrew
        )
        log(f"wrote {sheet}: mark `owner` right or wrong for each of {len(pick)} answers")
    marks = pd.read_csv(sheet, dtype=str).fillna("")
    marked = marks[marks.owner.str.strip().isin(["right", "wrong"])]
    owner = {
        "marked": len(marked),
        "right": int((marked.owner.str.strip() == "right").sum()),
        "of": len(marks),
    }
    out = {
        "sources": agreement(df, dev),
        "owner_check": owner,
        "usable": owner["marked"] == owner["of"] and owner["of"] > 0,
        "computed_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    ev = resolve_path(cfg, "artifacts") / "eval"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "speaker_eval.json").write_text(json.dumps(out, indent=2) + "\n", "utf-8")
    for src, s in out["sources"].items():
        log(f"  {src}: {s['named']} of {s['answered']} named, the rule agrees {s['agree']}")
    log(f"  owner check: {owner['right']} right of {owner['marked']} marked ({owner['of']})")
    return out
