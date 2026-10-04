"""`bsim evaluate`: score every system in `artifacts/topk/` against the gold links (§8.3).

Verse gold = the split's verse links (±window neighbours filtered from predictions). Unit gold
(chapter / pericope / parasha) = unit pairs sharing >= `eval.unit_gold_min_links` distinct verse
links of the split, plus unit-level links (every unit overlapping one range x every unit
overlapping the other); no neighbour filter at unit level. Unit types without gold in the split
(parasha: the Torah is all train) are skipped.

`--split test` is the single final run: only the final systems of each unit type
(`retrieve/fusion.py:final_systems`); it refuses to replace an existing test entry unless forced.

Writes to `paths.artifacts`/eval:
    metrics.json   {"splits": {split: {evaluated_at, config_hash, gold, results:
                   {unit: {system: m}}}}}; a run replaces its own split and keeps the others
    report.md      system x metric tables per split and unit type, BMA vs mean; missed verse
                   gold pairs and spot checks for the split just evaluated
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
from bsim.retrieve.fusion import final_systems
from bsim.retrieve.topk import Units, load_units, read_topk
from bsim.retrieve.units import member_index

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


def unit_gold(links: pd.DataFrame, units: Units, split: str, m: int) -> dict[int, set[int]]:
    """Unit-level gold of a split over unit positions (see module docstring)."""
    sel = links[links.split == split]
    verses, unit_of_member = member_index(units)
    size = int(max(verses.max(), sel[["src_end_vid", "tgt_end_vid"]].to_numpy().max(initial=0))) + 1
    unit_of = np.full(size, -1, np.int64)
    unit_of[verses] = unit_of_member

    gold: dict[int, set[int]] = {}
    v = sel[sel.level == "verse"]
    pairs = pd.DataFrame(
        {
            "a": unit_of[v.src_vid.to_numpy()],
            "b": unit_of[v.tgt_vid.to_numpy()],
            "s": v.src_vid.to_numpy(),
            "t": v.tgt_vid.to_numpy(),
        }
    )
    pairs = pairs[(pairs.a >= 0) & (pairs.b >= 0) & (pairs.a != pairs.b)].drop_duplicates()
    counts = pairs.groupby(["a", "b"]).size()
    for a, b in counts[counts >= m].index:
        gold.setdefault(int(a), set()).add(int(b))

    u = sel[sel.level == "unit"]
    for s, se, t, te in zip(u.src_vid, u.src_end_vid, u.tgt_vid, u.tgt_end_vid, strict=True):
        src_units = np.flatnonzero((units.start <= se) & (units.end >= s))
        tgt_units = np.flatnonzero((units.start <= te) & (units.end >= t))
        for a in src_units:
            for b in tgt_units:
                if a != b:
                    gold.setdefault(int(a), set()).add(int(b))
    return gold


@dataclass
class EvalContext:
    """Verse table, links and per-unit-type gold of one split, shared by evaluate and fuse."""

    cfg: dict[str, Any]
    split: str
    links: pd.DataFrame
    book_id: np.ndarray
    chapter: np.ndarray
    refs: list[str]
    _gold: dict[str, dict[int, set[int]]]
    _units: dict[str, Units]

    @classmethod
    def load(cls, cfg: dict[str, Any], split: str) -> EvalContext:
        proc = resolve_path(cfg, "data_processed")
        if not (proc / "links.parquet").exists():
            raise RuntimeError(f"{proc / 'links.parquet'} missing; run `bsim build-links` first")
        verses = pd.read_parquet(
            proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "ref"]
        ).sort_values("verse_id")
        return cls(
            cfg,
            split,
            pd.read_parquet(proc / "links.parquet"),
            verses.book_id.to_numpy(),
            verses.chapter.to_numpy(),
            verses.ref.tolist(),
            {},
            {},
        )

    def units(self, unit_type: str) -> Units:
        if unit_type not in self._units:
            self._units[unit_type] = load_units(self.cfg, unit_type)
        return self._units[unit_type]

    def gold(self, unit_type: str) -> dict[int, set[int]]:
        if unit_type not in self._gold:
            if unit_type == "verse":
                g = gold_pairs(self.links, self.split)
            else:
                m = self.cfg["eval"]["unit_gold_min_links"]
                g = unit_gold(self.links, self.units(unit_type), self.split, m)
            self._gold[unit_type] = g
        return self._gold[unit_type]

    def read(self, path: Path, unit_type: str) -> pd.DataFrame:
        positions = None if unit_type == "verse" else self.units(unit_type).position()
        return read_topk(path, positions)

    def filter(self, unit_type: str, df: pd.DataFrame) -> pd.DataFrame:
        """Verse lists lose the ±window neighbours; unit lists are evaluated as stored."""
        if unit_type != "verse":
            return df
        window = self.cfg["retrieval"]["neighbor_window"]
        return apply_filters(df, self.book_id, self.chapter, {"neighbors"}, window)

    def score(self, unit_type: str, df: pd.DataFrame) -> dict[str, float]:
        ev = self.cfg["eval"]
        ranked = ranked_lists(self.filter(unit_type, df))
        return evaluate_system(ranked, self.gold(unit_type), ev["ks"], ev["rank_k"])


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


def bma_vs_mean(systems: dict[str, dict[str, float]], keys: list[str]) -> list[list[Any]]:
    """Rows `[base, k1 bma, k1 mean, k2 bma, ...]` for systems stored with both aggregations."""
    rows = []
    for name in sorted(systems):
        base = name.removesuffix("_bma")
        if name.endswith("_bma") and f"{base}_mean" in systems:
            bma, mean = systems[name], systems[f"{base}_mean"]
            rows.append([base, *(_fmt(x[k]) for k in keys for x in (bma, mean))])
    return rows


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
        "",
        "Unit gold (chapter / pericope / parasha): unit pairs sharing ≥ "
        f"{ev['unit_gold_min_links']} verse links of the split, or overlapping the two ranges of "
        "a unit-level link; stored lists evaluated as they are (self excluded, no neighbour "
        "filter). Semantic unit systems are `{verse system}_{bma|mean}`. The test split holds "
        "only the final systems (`final_systems`), evaluated once.",
    ]
    for s in sorted(metrics["splits"], key=lambda x: SPLIT_ORDER.index(x)):
        entry = metrics["splits"][s]
        parts += [
            "",
            f"## {s.capitalize()}",
            "",
            f"Evaluated {entry['evaluated_at']}, config hash `{entry['config_hash']}`.",
        ]
        if entry.get("gold"):
            parts += [
                "",
                md_table(
                    ["unit type", "gold queries", "directed gold pairs"],
                    [[u, g["queries"], g["pairs"]] for u, g in entry["gold"].items()],
                ),
            ]
        keys = [sort_key, "recall@10", "recall@50"]
        comparison = []
        for unit_type, systems in entry["results"].items():
            rows = bma_vs_mean(systems, keys)
            if rows:
                header = ["system", *(f"{k} {a}" for k in keys for a in ("bma", "mean"))]
                comparison += ["", f"**{unit_type}**", md_table(header, rows)]
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
        if comparison:
            parts += ["", "### BMA vs mean", *comparison]

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


def run_evaluate(
    cfg: dict[str, Any], split: str = "dev", log: Log = print, force: bool = False
) -> dict[str, Any]:
    art = resolve_path(cfg, "artifacts")
    topk_dir, out = art / "topk", art / "eval"
    ev = cfg["eval"]

    metrics = load_metrics(out / "metrics.json")
    if split == "test" and "test" in metrics["splits"] and not force:
        done = metrics["splits"]["test"]["evaluated_at"]
        raise RuntimeError(
            f"the test split was already evaluated ({done}); it is run once at the end "
            "(pass --force to replace it)"
        )
    ctx = EvalContext.load(cfg, split)
    files = sorted(topk_dir.glob("*/*.parquet"))
    if not files:
        raise RuntimeError(f"no top-k files under {topk_dir}; run `bsim topk` first")
    if split == "test":
        files = [f for f in files if f.stem in final_systems(cfg, f.parent.name).values()]
        log(
            "test split, final systems only: "
            + ", ".join(f"{f.parent.name}/{f.stem}" for f in files)
        )
    order = {u: i for i, u in enumerate(cfg["units"]["types"])}
    files.sort(key=lambda f: (order.get(f.parent.name, len(order)), f.stem))

    gold = ctx.gold("verse")
    if not gold:
        raise RuntimeError(f"no verse-level gold links in split {split!r}")
    vl = ctx.links[ctx.links.level == "verse"]
    ctype = {
        (int(s), int(t)): c
        for s, t, c in zip(vl.src_vid, vl.tgt_vid, vl.connection_type, strict=True)
    }

    runs: list[SystemRun] = []
    results: dict[str, dict[str, dict[str, float]]] = {}
    gold_sizes: dict[str, dict[str, int]] = {}
    for f in files:
        unit_type, system = f.parent.name, f.stem
        unit_gold_ = ctx.gold(unit_type)
        if not unit_gold_:
            log(f"skip {unit_type}/{system}: no {unit_type} gold in split {split!r}")
            continue
        gold_sizes[unit_type] = {
            "queries": len(unit_gold_),
            "pairs": sum(len(g) for g in unit_gold_.values()),
        }
        filtered = ctx.filter(unit_type, ctx.read(f, unit_type))
        ranked = ranked_lists(filtered)
        m = evaluate_system(ranked, unit_gold_, ev["ks"], ev["rank_k"])
        if unit_type == "verse":
            runs.append(SystemRun(system, filtered, ranked, m))
        results.setdefault(unit_type, {})[system] = m
        log(
            f"{unit_type}/{system}: "
            + ", ".join(f"{k}={v:.3f}" for k, v in m.items() if k != "queries")
        )

    out.mkdir(parents=True, exist_ok=True)
    metrics["splits"][split] = {
        "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "config_hash": config_hash(cfg, "retrieval", "eval", "splits", "fusion", "final_systems"),
        "gold": gold_sizes,
        "results": results,
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    write_report(out / "report.md", metrics, split, runs, gold, ctx.refs, ctype, cfg)

    verse = results.get("verse", {})
    hi, lo = EXPECTED_ORDER
    key = f"ndcg@{ev['rank_k']}"
    if hi in verse and lo in verse and verse[hi][key] < verse[lo][key]:
        log(f"  warning: {hi} {key} {verse[hi][key]:.3f} < {lo} {verse[lo][key]:.3f}")
    n_runs = sum(len(v) for v in results.values())
    log(f"done: {n_runs} system x unit runs on {split} ({len(gold)} verse queries); wrote {out}")
    return metrics
