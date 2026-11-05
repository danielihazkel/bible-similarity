"""`bsim llm-pool`: a judged dev pool, Claude's verdicts on what the systems find (DESIGN.md
§16.83, D139; series L3).

Every dev score counts a pair Sefaria does not link as wrong, though many of the systems' best
finds are real connections Sefaria never recorded. Pooling, as TREC does: the top
`llm_pool.depth` targets of each dev Sefaria query in each of `llm_pool.systems` (±window
neighbours dropped, as the report drops them), less the pairs Sefaria already links, are judged
by Claude with the triage's own prompt and schema (§16.81), in one Message Batch.

Calibration, fixed before the run: every dev Sefaria verse link (not neighbours, not the same
text) against as many random pairs of dev-book verses that no gold links; the AUC of `p_real`
must reach `calibration.min_auc` or the pool is not used. The share of the Sefaria links
Claude calls real is its recall: a ceiling on what the pool can find.

The pool is a gold of its own (`llm`): a pair is relevant when Sefaria links it or Claude calls
it real, and the lists are scored *condensed* (unjudged targets dropped before scoring, not
counted wrong; Sakai 2007), so a system outside the pool is not punished for finds no one
judged. It is reported beside Sefaria's numbers; it is not an adoption rule unless one is
decided. These are dev judgements: they never train a model (`train/pairs.py` refuses them).
"""

from __future__ import annotations

import json
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
    auc,
    ensure_columns,
    mark_collected,
    run_batch,
    undirected,
    usage,
)
from bsim.eval.llm_triage import VERDICTS, answer, calibration_pairs, request, verse_texts

OUT = "llm_pool"
COLUMNS = {"verdict": None, "p_real": np.nan, "kind": None, "rationale": None}


def system_list(cfg: dict[str, Any], name: str) -> pd.DataFrame:
    """A verse list (`src, tgt, rank`) by name: `lexical` and `semantic` are the final lists,
    any other name a top-k file under `artifacts/topk/verse/`."""
    from bsim.retrieve.fusion import load_lists
    from bsim.retrieve.topk import read_topk

    if name in ("lexical", "semantic"):
        lex, sem, _ = load_lists(cfg, "verse")
        return lex if name == "lexical" else sem
    path = resolve_path(cfg, "artifacts") / "topk" / "verse" / f"{name}.parquet"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run the stage that writes {name!r} first")
    return read_topk(path)


def pool_pairs(
    lists: dict[str, pd.DataFrame],
    queries: set[int],
    gold: dict[int, set[int]],
    depth: int,
    filt: Callable[[pd.DataFrame], pd.DataFrame],
) -> pd.DataFrame:
    """`a, b, systems`: the undirected pairs in some list's top `depth` (after `filt`, the
    neighbour filter) for a query of `queries`, Sefaria's own pairs left out; `systems` names
    the lists that pooled the pair."""
    linked = {(min(q, t), max(q, t)) for q, ts in gold.items() for t in ts}
    seen: dict[tuple[int, int], list[str]] = {}
    for name, df in lists.items():
        df = filt(df)
        df = df[df.src.isin(sorted(queries))].sort_values(["src", "rank"], kind="stable")
        top = df.groupby("src", sort=False).head(depth)
        for s, t in zip(top.src.to_numpy(), top.tgt.to_numpy(), strict=True):
            p = (min(int(s), int(t)), max(int(s), int(t)))
            if p not in linked:
                seen.setdefault(p, [])
                if name not in seen[p]:
                    seen[p].append(name)
    rows = [(a, b, ",".join(names)) for (a, b), names in sorted(seen.items())]
    return pd.DataFrame(rows, columns=["a", "b", "systems"])


def build_items(cfg: dict[str, Any], log: Log) -> pd.DataFrame:
    """`set, custom_id, a, b, gold, systems`: the calibration pairs, then the pool."""
    from bsim.data.canon import BY_SEFARIA
    from bsim.eval.report import EvalContext

    pc = cfg["llm_pool"]
    proc = resolve_path(cfg, "data_processed")
    ctx = EvalContext.load(cfg, "dev")
    gold = ctx.gold("verse")
    queries = {q for q, ts in gold.items() if ts}
    lists = {name: system_list(cfg, name) for name in pc["systems"]}
    pool = pool_pairs(lists, queries, gold, pc["depth"], lambda df: ctx.filter("verse", df))

    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "text_plain"])
    verses = verses.sort_values("verse_id").reset_index(drop=True)
    links = ctx.links
    sefaria = links[(links.level == "verse") & (links.split == "dev")]
    linked = undirected(links.src_vid.to_numpy(), links.tgt_vid.to_numpy())
    for name in ("openbible_links.parquet", "etcbc_links.parquet"):
        if (proc / name).exists():
            g = pd.read_parquet(proc / name, columns=["src_vid", "tgt_vid"])
            linked |= undirected(g.src_vid.to_numpy(), g.tgt_vid.to_numpy())
    splits = json.loads((proc / "splits.json").read_text("utf-8"))["books"]
    books = {BY_SEFARIA[b].book_id for b, s in splits.items() if s == "dev"}
    calib = calibration_pairs(
        verses, sefaria, linked, books, None, None,
        cfg["retrieval"]["neighbor_window"], pc["seed"],
    )  # fmt: skip
    log(
        f"pool: {len(pool)} pairs from the top {pc['depth']} of {', '.join(pc['systems'])}"
        f" for {len(queries)} dev queries; calibration: {int(calib.gold.sum())} Sefaria dev"
        f" links against {int((~calib.gold.astype(bool)).sum())} random pairs"
    )
    calib = calib.assign(
        set="calibration", custom_id=[f"cal-{i}" for i in range(len(calib))], systems=None
    )
    pool = pool.assign(set="pool", gold=None, custom_id=[f"pool-{i}" for i in range(len(pool))])
    cols = ["set", "custom_id", "a", "b", "gold", "systems"]
    return pd.concat([calib[cols], pool[cols]], ignore_index=True)


def run_llm_pool(
    cfg: dict[str, Any],
    log: Log = print,
    dry_run: bool = False,
    client: Any = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    lc = cfg["llm_pool"]
    out = resolve_path(cfg, "artifacts") / OUT

    def prepare() -> tuple[pd.DataFrame, list[dict]]:
        items = build_items(cfg, log)
        texts = verse_texts(cfg)
        reqs = [
            request(cid, texts[a], texts[b], lc)
            for cid, a, b in zip(items.custom_id, items.a, items.b, strict=True)
        ]
        return items, reqs

    def describe(items: pd.DataFrame) -> str:
        return (
            f"{len(items)} requests ({int((items.set == 'calibration').sum())} calibration,"
            f" {int((items.set == 'pool').sum())} pool)"
        )

    got = run_batch(
        out, lc, prepare, answer(lc["rationale_chars"]), log=log, dry_run=dry_run,
        client=client, sleep=sleep, items_file="pairs.parquet", describe=describe,
    )  # fmt: skip
    if not isinstance(got, Collected):
        return got
    df = ensure_columns(got.df, dict(COLUMNS))
    meta = summarise(df, cfg, got.state)
    cols = ["set", "custom_id", "a", "b", "gold", "systems", "status", "verdict", "p_real",
            "kind", "rationale", "input_tokens", "output_tokens"]  # fmt: skip
    df[df.set == "calibration"][cols].to_parquet(out / "calibration.parquet", index=False)
    df[df.set == "pool"][cols].to_parquet(out / "judged.parquet", index=False)
    write_meta(out / "llm_pool.meta.json", meta)
    mark_collected(out, got.state)
    c = meta["calibration"]
    log(
        f"calibration: AUC {c['auc']} (needs {c['min_auc']}: {'holds' if c['holds'] else 'fails'}),"
        f" recall of Sefaria's links {c['recall']}; pool: {meta['pool']['verdicts']};"
        f" about ${meta['usage']['usd']:.2f}"
    )
    return meta


def summarise(df: pd.DataFrame, cfg: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    lc = cfg["llm_pool"]
    c = df[(df.set == "calibration") & (df.status == "ok")]
    gold = c.gold.astype(bool).to_numpy()
    a = auc(gold, c.p_real.to_numpy(float))
    p = df[df.set == "pool"]

    def counts(x: pd.DataFrame) -> dict[str, int]:
        return {v: int((x.verdict == v).sum()) for v in VERDICTS}

    g = c[gold]
    return {
        "model": state["model"],
        "batch_id": state["batch_id"],
        "submitted_at": state["created_at"],
        "collected_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": {str(k): int(v) for k, v in df.status.value_counts().items()},
        "calibration": {
            "split": "dev",
            "gold": int(gold.sum()),
            "random": int((~gold).sum()),
            "auc": a,
            "min_auc": lc["calibration"]["min_auc"],
            "holds": a is not None and a >= lc["calibration"]["min_auc"],
            "recall": round(float((g.verdict == "real").mean()), 4) if len(g) else None,
            "gold_verdicts": counts(g),
            "random_verdicts": counts(c[~gold]),
        },
        "pool": {
            "systems": list(lc["systems"]),
            "depth": lc["depth"],
            "pairs": len(p),
            "ok": int((p.status == "ok").sum()),
            "verdicts": counts(p),
        },
        "usage": usage(df, lc),
        "config_hash": config_hash(cfg, "llm_pool"),
    }


# --- the judged gold -----------------------------------------------------------------------------


class JudgedGold:
    """The `llm` dev gold: per query, the relevant targets (Sefaria's and Claude's real ones)
    and the judged ones (those and Claude's other verdicts; `unsure` per `llm_pool.unsure`)."""

    def __init__(self, relevant: dict[int, set[int]], judged: dict[int, set[int]]) -> None:
        self.relevant, self.judged = relevant, judged

    def condensed(self, ranked: dict[int, list[int]]) -> dict[int, list[int]]:
        """Each query's list with its unjudged targets dropped (Sakai's condensed list)."""
        return {q: [t for t in ranked.get(q, []) if t in self.judged.get(q, ())] for q in ranked}

    def coverage(self, ranked: dict[int, list[int]], k: int) -> float:
        """The share of the top-k targets of the gold queries that are judged."""
        tot = hit = 0
        for q in self.relevant:
            top = ranked.get(q, [])[:k]
            tot += len(top)
            hit += sum(t in self.judged.get(q, ()) for t in top)
        return round(hit / tot, 4) if tot else 0.0


def judged_gold(
    sefaria: dict[int, set[int]], judged: pd.DataFrame, unsure: str = "drop"
) -> JudgedGold:
    """The `llm` gold from the dev Sefaria gold and the pool's answers (both directions)."""
    relevant = {q: set(ts) for q, ts in sefaria.items() if ts}
    seen = {q: set(ts) for q, ts in relevant.items()}
    ok = judged[judged.status == "ok"]
    if unsure == "drop":
        ok = ok[ok.verdict != "unsure"]
    for a, b, v in zip(ok.a.to_numpy(), ok.b.to_numpy(), ok.verdict.to_numpy(), strict=True):
        for q, t in ((int(a), int(b)), (int(b), int(a))):
            if q not in relevant:
                continue  # the queries are Sefaria's dev queries
            seen[q].add(t)
            if v == "real":
                relevant[q].add(t)
    return JudgedGold(relevant, seen)


def load_judged_gold(
    cfg: dict[str, Any], sefaria: dict[int, set[int]], log: Log
) -> JudgedGold | None:
    """The `llm` gold of the last collected run, or None (logged) when there is none or its
    calibration failed."""
    out = resolve_path(cfg, "artifacts") / OUT
    meta_path, rows = out / "llm_pool.meta.json", out / "judged.parquet"
    if not (meta_path.exists() and rows.exists()):
        log(f"  {rows} missing (run `bsim llm-pool`): no llm gold")
        return None
    meta = json.loads(meta_path.read_text("utf-8"))
    if not meta["calibration"]["holds"]:
        log(f"  the llm pool's calibration failed (AUC {meta['calibration']['auc']}): no llm gold")
        return None
    return judged_gold(sefaria, pd.read_parquet(rows), cfg["llm_pool"]["unsure"])


# --- the dev table --------------------------------------------------------------------------------


def p_at(ranked: list[int], gold: set[int], k: int) -> float:
    top = ranked[:k]
    return sum(t in gold for t in top) / k if top else 0.0


def run_pool_scores(cfg: dict[str, Any], log: Log = print) -> dict[str, Any]:
    """`bsim llm-pool --score`: each of `llm_pool.score_systems` on the dev queries, by Sefaria
    and by the judged pool (condensed), nDCG@10 and P@5, with the pool's coverage of each list's
    top 10 and the paired bootstrap of each system against fused on the pool; writes
    `artifacts/eval/llm_pool.json` and `.md`."""
    from bsim.data.report import md_table
    from bsim.eval.metrics import ndcg_at, paired_bootstrap
    from bsim.eval.report import EvalContext, ranked_lists

    pc = cfg["llm_pool"]
    ctx = EvalContext.load(cfg, "dev")
    sef = {q: ts for q, ts in ctx.gold("verse").items() if ts}
    gold = load_judged_gold(cfg, sef, log)
    if gold is None:
        raise RuntimeError("no judged pool to score with")
    qs = sorted(sef)
    per: dict[str, dict[str, np.ndarray]] = {}
    rows = []
    for name in pc["score_systems"]:
        ranked = ranked_lists(ctx.filter("verse", system_list(cfg, name)))
        cond = gold.condensed(ranked)
        per[name] = {
            "sefaria": np.array([ndcg_at(ranked.get(q, []), sef[q], 10) for q in qs]),
            "llm": np.array([ndcg_at(cond.get(q, []), gold.relevant[q], 10) for q in qs]),
        }
        rows.append(
            {
                "system": name,
                "sefaria_ndcg10": round(float(per[name]["sefaria"].mean()), 4),
                "sefaria_p5": round(
                    float(np.mean([p_at(ranked.get(q, []), sef[q], 5) for q in qs])), 4
                ),
                "llm_ndcg10": round(float(per[name]["llm"].mean()), 4),
                "llm_p5": round(
                    float(np.mean([p_at(cond.get(q, []), gold.relevant[q], 5) for q in qs])), 4
                ),
                "coverage10": gold.coverage(ranked, 10),
            }
        )
    base = pc["baseline"]
    reps, seed = pc["bootstrap_reps"], pc["seed"]
    for r in rows:
        if r["system"] == base or base not in per:
            r["llm_gain_vs_" + base] = None
            continue
        d = per[r["system"]]["llm"] - per[base]["llm"]
        r["llm_gain_vs_" + base] = paired_bootstrap(d, reps, seed)
    out = {
        "queries": len(qs),
        "baseline": base,
        "rows": rows,
        "computed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "config_hash": config_hash(cfg, "llm_pool"),
    }
    ev = resolve_path(cfg, "artifacts") / "eval"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "llm_pool.json").write_text(json.dumps(out, indent=2, default=float) + "\n", "utf-8")
    table = md_table(
        ["system", "Sefaria nDCG@10", "Sefaria P@5", "pool nDCG@10", "pool P@5",
         "judged of top 10"],
        [[r["system"], r["sefaria_ndcg10"], r["sefaria_p5"], r["llm_ndcg10"], r["llm_p5"],
          r["coverage10"]] for r in rows],
    )  # fmt: skip
    (ev / "llm_pool.md").write_text(
        f"# The judged dev pool ({len(qs)} queries)\n\n{table}\n", "utf-8"
    )
    for r in rows:
        log(
            f"  {r['system']}: Sefaria nDCG@10 {r['sefaria_ndcg10']}, pool {r['llm_ndcg10']}"
            f" (P@5 {r['sefaria_p5']} / {r['llm_p5']}; judged {r['coverage10']} of the top 10)"
        )
    return out
