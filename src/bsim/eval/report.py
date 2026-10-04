"""`bsim evaluate`: score every system in `artifacts/topk/` against the gold links (§8.3).

Writes to `paths.artifacts`/eval:
    metrics.json   {"splits": {split: {evaluated_at, config_hash, results: {unit: {system: m}}}}};
                   a run replaces its own split and keeps the others (dev + the final test run)
    report.md      system x metric tables per split and unit type; missed gold pairs and
                   spot checks for the split just evaluated
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.data.report import md_table
from bsim.eval.metrics import evaluate_system, metric_names
from bsim.retrieve.filters import apply_filters
from bsim.retrieve.topk import read_topk

Log = Callable[[str], None]

SPLIT_ORDER = ("dev", "test")
# Acceptance check (TASKS.md M5)
EXPECTED_ORDER = ("bm25_lemma", "bm25_surface")


@dataclass
class SystemRun:
    name: str
    filtered: pd.DataFrame  # neighbour-filtered verse top-k with integer src / tgt
    ranked: dict[int, list[int]]
    metrics: dict[str, float]


def gold_pairs(links: pd.DataFrame, split: str) -> dict[int, set[int]]:
    """Verse-level gold of a split: query verse -> linked verses."""
    v = links[(links.level == "verse") & (links.split == split)]
    gold: dict[int, set[int]] = {}
    for s, t in zip(v.src_vid.to_numpy(), v.tgt_vid.to_numpy(), strict=True):
        gold.setdefault(int(s), set()).add(int(t))
    return gold


def ranked_lists(df: pd.DataFrame) -> dict[int, list[int]]:
    df = df.sort_values(["src", "rank"], kind="stable")
    return {int(s): g.tolist() for s, g in df.groupby("src", sort=False).tgt}


def missed_pairs(
    run: SystemRun,
    others: list[SystemRun],
    gold: dict[int, set[int]],
    rank_k: int,
    limit: int,
) -> list[tuple[int, int, int, int | None]]:
    """Gold pairs outside the system's list: (src, tgt, #other systems with it in their top
    `rank_k`, best other rank), the ones other systems find most often first."""
    rows = []
    for s in sorted(gold):
        found = set(run.ranked.get(s, []))
        for t in sorted(gold[s] - found):
            ranks = [o.ranked.get(s, []).index(t) + 1 for o in others if t in o.ranked.get(s, [])]
            n_top = sum(r <= rank_k for r in ranks)
            rows.append((s, t, n_top, min(ranks) if ranks else None))
    rows.sort(key=lambda r: (-r[2], r[3] if r[3] is not None else np.inf, r[0], r[1]))
    return rows[:limit]


def load_metrics(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"splits": {}}


def _fmt(v: float) -> str:
    return f"{v:.3f}"


def write_report(
    path: Path,
    metrics: dict[str, Any],
    split: str,
    runs: list[SystemRun],
    gold: dict[int, set[int]],
    refs: list[str],
    ctype: dict[tuple[int, int], str],
    cfg: dict[str, Any],
) -> None:
    ev = cfg["eval"]
    names = metric_names(ev["ks"], ev["rank_k"])
    sort_key = f"ndcg@{ev['rank_k']}"
    parts = [
        "# Evaluation report",
        "",
        "Gold = Sefaria Tanakh↔Tanakh verse links of the split (§8). Predictions: stored top-"
        f"{cfg['retrieval']['k']} with ±{cfg['retrieval']['neighbor_window']} same-book "
        "neighbours removed. Macro-averaged over query verses with ≥ 1 gold link.",
    ]
    for s in sorted(metrics["splits"], key=lambda x: SPLIT_ORDER.index(x)):
        entry = metrics["splits"][s]
        parts += [
            "",
            f"## {s.capitalize()}",
            "",
            f"Evaluated {entry['evaluated_at']}, config hash `{entry['config_hash']}`.",
        ]
        for unit_type, systems in entry["results"].items():
            ordered = sorted(systems.items(), key=lambda kv: -kv[1][sort_key])
            parts += [
                "",
                f"### {unit_type}",
                md_table(
                    ["system", *names, "queries"],
                    [
                        [name, *(_fmt(m[n]) for n in names), int(m["queries"])]
                        for name, m in ordered
                    ],
                ),
            ]

    n_pairs = sum(len(g) for g in gold.values())
    parts += [
        "",
        f"## Missed gold pairs ({split}, verse)",
        "",
        f"{len(gold)} queries, {n_pairs} directed gold pairs. Gold pairs a system does not "
        f"return, the ones other systems have in their top-{ev['rank_k']} first.",
    ]
    for run in runs:
        others = [o for o in runs if o is not run]
        misses = missed_pairs(run, others, gold, ev["rank_k"], ev["worst_misses"])
        rows = []
        for s, t, n_top, best in misses:
            top1 = run.ranked.get(s, [])
            rows.append(
                [
                    refs[s],
                    refs[t],
                    ctype.get((s, t), "") or "—",
                    n_top,
                    best if best is not None else "—",
                    refs[top1[0]] if top1 else "—",
                ]
            )
        parts += [
            "",
            f"### {run.name}",
            md_table(["query", "gold", "type", "others top-k", "best other rank", "top-1"], rows)
            if rows
            else "(none missed)",
        ]

    vid = {r: i for i, r in enumerate(refs)}
    parts += ["", "## Spot checks (top-5, neighbours removed)"]
    for q in ev["spot_checks"]:
        if q not in vid:
            continue
        parts += ["", f"**{q}**"]
        rows = []
        for run in runs:
            hits = run.filtered[(run.filtered.src == vid[q]) & (run.filtered["rank"] <= 5)]
            pairs = zip(hits.tgt, hits.score, strict=True)
            rows.append([run.name, "<br>".join(f"{refs[t]} ({sc:.2f})" for t, sc in pairs)])
        parts.append(md_table(["system", "top-5"], rows))
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def run_evaluate(cfg: dict[str, Any], split: str = "dev", log: Log = print) -> dict[str, Any]:
    proc = resolve_path(cfg, "data_processed")
    art = resolve_path(cfg, "artifacts")
    topk_dir, out = art / "topk", art / "eval"
    ev, window = cfg["eval"], cfg["retrieval"]["neighbor_window"]

    if not (proc / "links.parquet").exists():
        raise RuntimeError(f"{proc / 'links.parquet'} missing; run `bsim build-links` first")
    files = sorted(topk_dir.glob("*/*.parquet"))
    if not files:
        raise RuntimeError(f"no top-k files under {topk_dir}; run `bsim topk` first")

    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "ref"]
    ).sort_values("verse_id")
    book_id, chapter = verses.book_id.to_numpy(), verses.chapter.to_numpy()
    refs = verses.ref.tolist()
    links = pd.read_parquet(proc / "links.parquet")
    gold = gold_pairs(links, split)
    if not gold:
        raise RuntimeError(f"no verse-level gold links in split {split!r}")
    vl = links[links.level == "verse"]
    ctype = {
        (int(s), int(t)): c
        for s, t, c in zip(vl.src_vid, vl.tgt_vid, vl.connection_type, strict=True)
    }

    runs: list[SystemRun] = []
    results: dict[str, dict[str, dict[str, float]]] = {}
    for f in files:
        unit_type, system = f.parent.name, f.stem
        if unit_type != "verse":
            log(f"skip {unit_type}/{system}: unit-level gold comes in M9")
            continue
        filtered = apply_filters(read_topk(f), book_id, chapter, {"neighbors"}, window)
        ranked = ranked_lists(filtered)
        m = evaluate_system(ranked, gold, ev["ks"], ev["rank_k"])
        runs.append(SystemRun(system, filtered, ranked, m))
        results.setdefault(unit_type, {})[system] = m
        log(
            f"{unit_type}/{system}: "
            + ", ".join(f"{k}={v:.3f}" for k, v in m.items() if k != "queries")
        )

    out.mkdir(parents=True, exist_ok=True)
    metrics = load_metrics(out / "metrics.json")
    metrics["splits"][split] = {
        "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "config_hash": config_hash(cfg, "retrieval", "eval", "splits"),
        "results": results,
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    write_report(out / "report.md", metrics, split, runs, gold, refs, ctype, cfg)

    verse = results.get("verse", {})
    hi, lo = EXPECTED_ORDER
    key = f"ndcg@{ev['rank_k']}"
    if hi in verse and lo in verse and verse[hi][key] < verse[lo][key]:
        log(f"  warning: {hi} {key} {verse[hi][key]:.3f} < {lo} {verse[lo][key]:.3f}")
    log(f"done: {len(runs)} systems on {split} ({len(gold)} queries); wrote {out}")
    return metrics
