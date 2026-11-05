"""`bsim llm-genealogy`: Claude checks the family tree's links nobody reviewed, as suggestions
for the owner's review (DESIGN.md §16.87, D143; series L6).

The review (§16.63, `curation/genealogy/`) checked every parent and spouse link against the
Hebrew; the links TIPNR gives otherwise were left as they came: 2,585 siblings and 1,265
attachments to a people or tribe with the generations unstated. Most siblings follow from two
reviewed parents they share and need no reading. What is left is judged here:
- **siblings** no shared reviewed parent implies, with the verses that name both (or each);
- **attachments** to a named people or tribe (not to the tree's virtual root), with the verses
  that name the person.

Calibration, fixed before the run: `calibration.confirmed` reviewed parent links the review
confirmed against every parent link it rejected, each with its proof verses; the AUC of
`p_right` must reach `min_auc`, or the sheet says the suggestions are not to be used.

The answers are suggestions: they go to `artifacts/llm_genealogy/review.md`, by person key, for
the owner to act on in the curation files. Nothing here writes `curation/`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path, write_meta
from bsim.eval.llm_audit import SCHEMA, answer
from bsim.eval.llm_batch import (
    Collected,
    Log,
    auc,
    ensure_columns,
    make_request,
    mark_collected,
    run_batch,
    usage,
)

OUT = "llm_genealogy"
REVIEWED = ("confirmed", "fixed", "added")
SYSTEM = """You check a family relation that a database of biblical persons gives, against the \
Hebrew text. You are given the claim and the verses that name the persons. Judge, as a careful \
reader of the Hebrew Bible, whether the claim is right: verdict "right" when the text states or \
clearly implies it, "wrong" when the text contradicts it or the persons are confused with others \
of the same name, "unsure" when the text alone does not decide it.

Rules:
- Never translate a verse, or any word or phrase of it, into English or any other language. \
Quote Hebrew words exactly as they are written, in Hebrew letters.
- The rationale is one or two short sentences in Hebrew, and only in Hebrew.
- p_right is your probability, from 0 to 1, that the claim is right."""


def load(cfg: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    art = resolve_path(cfg, "artifacts") / "genealogy"
    files = ("links", "persons", "mentions", "proofs")
    for f in files:
        if not (art / f"{f}.parquet").exists():
            raise RuntimeError(f"{art / f'{f}.parquet'} missing; run `bsim genealogy` first")
    return tuple(pd.read_parquet(art / f"{f}.parquet") for f in files)  # type: ignore[return-value]


def candidates(
    links: pd.DataFrame, persons: pd.DataFrame, mentions: pd.DataFrame, cap: int
) -> pd.DataFrame:
    """`kind, link_id, a, b, claim, vids`: the siblings no shared reviewed parent implies and the
    attachments to a named people or tribe."""
    he = persons.set_index("person_id").he.to_dict()
    named = mentions.groupby("person_id").verse_id.apply(sorted).to_dict()
    par = links[links.role.isin(["father", "mother"]) & links.status.isin(REVIEWED)]
    parents = par.groupby("child_id").parent_id.apply(set).to_dict()
    rows = []
    for r in links[(links.role == "sibling") & (links.status == "tipnr")].itertuples():
        a, b = int(r.parent_id), int(r.child_id)
        if parents.get(a, set()) & parents.get(b, set()):
            continue
        both = sorted(set(named.get(a, [])) & set(named.get(b, [])))
        vids = both[:cap] or (named.get(a, [])[: cap // 2] + named.get(b, [])[: cap // 2])
        claim = f"{he.get(a, '?')} and {he.get(b, '?')} are siblings (children of one parent)."
        rows.append(("sibling", int(r.link_id), a, b, claim, vids))
    for r in links[(links.role == "unstated") & (links.status == "tipnr")].itertuples():
        a, b = int(r.parent_id), int(r.child_id)
        if not he.get(a):
            continue  # attached to the tree's virtual root: no claim to check
        claim = (
            f"{he.get(b, '?')} belongs to {he[a]}: one of its people or a descendant of {he[a]},"
            " the generations between not stated."
        )
        rows.append(("attachment", int(r.link_id), a, b, claim, named.get(b, [])[:cap]))
    return pd.DataFrame(rows, columns=["kind", "link_id", "a", "b", "claim", "vids"])


def calibration(
    links: pd.DataFrame,
    persons: pd.DataFrame,
    proofs: pd.DataFrame,
    n_confirmed: int,
    seed: int,
    cap: int,
) -> pd.DataFrame:
    """Reviewed parent links with proof verses: `n_confirmed` confirmed ones drawn with `seed`
    (gold True) and every rejected one (gold False)."""
    he = persons.set_index("person_id").he.to_dict()
    pv = proofs.sort_values(["link_id", "rank"]).groupby("link_id").verse_id.apply(list).to_dict()
    par = links[links.role.isin(["father", "mother"]) & links.link_id.isin(list(pv))]
    conf = par[par.status == "confirmed"]
    rng = np.random.default_rng(seed)
    conf = conf.iloc[
        np.sort(rng.choice(len(conf), size=min(n_confirmed, len(conf)), replace=False))
    ]
    rej = par[par.status == "rejected"]
    rows = []
    for gold, df in ((True, conf), (False, rej)):
        for r in df.itertuples():
            a, b = int(r.parent_id), int(r.child_id)
            claim = f"{he.get(a, '?')} is the {r.role} of {he.get(b, '?')}."
            rows.append(("calibration", int(r.link_id), a, b, claim, pv[r.link_id][:cap], gold))
    return pd.DataFrame(rows, columns=["kind", "link_id", "a", "b", "claim", "vids", "gold"])


def build_items(cfg: dict[str, Any], log: Log) -> tuple[pd.DataFrame, dict[str, str]]:
    from bsim.eval.llm_triage import verse_texts

    gc = cfg["llm_genealogy"]
    links, persons, mentions, proofs = load(cfg)
    cand = candidates(links, persons, mentions, gc["max_verses"]).assign(gold=None)
    cal = calibration(links, persons, proofs, gc["calibration"]["confirmed"], gc["seed"],
                      gc["max_verses"])  # fmt: skip
    items = pd.concat([cal, cand], ignore_index=True)
    items = items[items.vids.map(len) > 0].reset_index(drop=True)
    items["custom_id"] = [f"gen-{i}" for i in range(len(items))]
    texts = verse_texts(cfg)
    prompts = {
        cid: f"The claim: {claim}\n\nThe verses:\n\n"
        + "\n\n".join(f"{texts[v]['ref']}\n{texts[v]['text']}" for v in vids)
        for cid, claim, vids in zip(items.custom_id, items.claim, items.vids, strict=True)
    }
    log(f"{items.kind.value_counts().to_dict()} (calibration: {int(cal.gold.sum())} confirmed,"
        f" {int((~cal.gold.astype(bool)).sum())} rejected)")  # fmt: skip
    return items, prompts


def run_llm_genealogy(
    cfg: dict[str, Any],
    log: Log = print,
    dry_run: bool = False,
    client: Any = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    lc = cfg["llm_genealogy"]
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
    df = ensure_columns(got.df, {"verdict": None, "p_right": np.nan, "rationale": None})
    cal = df[(df.kind == "calibration") & (df.status == "ok")]
    gold = cal.gold.astype(bool).to_numpy()
    a = auc(gold, cal.p_right.to_numpy(float))
    holds = a is not None and a >= lc["calibration"]["min_auc"]
    checked = df[df.kind != "calibration"]
    meta = {
        "model": got.state["model"],
        "batch_id": got.state["batch_id"],
        "submitted_at": got.state["created_at"],
        "collected_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": {str(k): int(v) for k, v in df.status.value_counts().items()},
        "calibration": {
            "confirmed": int(gold.sum()),
            "rejected": int((~gold).sum()),
            "auc": a,
            "min_auc": lc["calibration"]["min_auc"],
            "holds": bool(holds),
        },
        "checked": {
            k: {v: int((g.verdict == v).sum()) for v in ("right", "wrong", "unsure")}
            for k, g in checked.groupby("kind")
        },
        "usage": usage(df, lc),
        "config_hash": config_hash(cfg, "llm_genealogy"),
    }
    df.to_parquet(out / "judged.parquet", index=False)
    write_meta(out / "llm_genealogy.meta.json", meta)
    write_sheet(cfg, checked, meta)
    mark_collected(out, got.state)
    log(f"calibration AUC {a} ({'holds' if holds else 'fails'}); {meta['checked']};"
        f" about ${meta['usage']['usd']:.2f}")  # fmt: skip
    return meta


def write_sheet(cfg: dict[str, Any], checked: pd.DataFrame, meta: dict[str, Any]) -> None:
    """The owner's sheet: the links Claude calls wrong, then unsure, by person key."""
    persons = pd.read_parquet(resolve_path(cfg, "artifacts") / "genealogy" / "persons.parquet")
    key = persons.set_index("person_id").key.to_dict()
    c = meta["calibration"]
    lines = [
        "# Family-tree links nobody reviewed: Claude's suggestions",
        "",
        f"Calibration (reviewed parent links, {c['confirmed']} confirmed against {c['rejected']}"
        f" rejected): AUC {c['auc']}, {'holds' if c['holds'] else 'FAILS: do not use these'}.",
        "Suggestions only: decide in `curation/genealogy/`; nothing here was changed.",
        "",
    ]
    for verdict in ("wrong", "unsure"):
        g = checked[checked.verdict == verdict]
        lines += [f"## {verdict} ({len(g)})", ""]
        for r in g.sort_values(["kind", "link_id"]).itertuples():
            lines.append(
                f"- link {r.link_id} ({r.kind}; {key.get(r.a, r.a)} / {key.get(r.b, r.b)}):"
                f" {r.claim} — {r.rationale}"
            )
        lines.append("")
    path = resolve_path(cfg, "artifacts") / OUT / "review.md"
    path.write_text("\n".join(lines) + "\n", "utf-8")
