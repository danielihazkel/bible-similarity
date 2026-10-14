"""`bsim unit-exp`: does a third list from the verse-level analyses improve chapter and pericope
retrieval? (DESIGN.md §16.50). Dev split only.

Chapters and pericopes are retrieved by fusing a unit TF-IDF list with the semantic BMA list
(§6.2); pericopes are the weakest level (test nDCG@10 0.068). Three families of unit lists, each
an aggregation of verse pairs (a, b) with a weight: a unit pair (A, B) scores the sum of the
weights of the pairs with one verse in A and the other in B, either way round (pairs inside one
unit ignored), and each unit keeps its best `retrieval.k`:
    sequences   the aligned verse pairs of the parallel sequences (§16.7), weight as stored;
                every chain, or the chains with q <= each `sequences_max_q`
    phrases     the verse pairs sharing a phrase (§16.1), weight the alignment score
    hits        each verse's fused top-N verses (`hits_depth`), weight (N + 1 - rank) / N,
                neighbours (`retrieval.neighbor_window`) dropped
Each family's members are its list as a third RRF list beside the final unit lexical and
semantic lists, at each weight of `w_grid`; the list alone is reported, not chosen. The baseline
is that fusion of two lists, rebuilt in memory (the stored fused list holds any adopted third).

Scored per unit type on three dev golds (unit pairs sharing >= `eval.unit_gold_min_links` dev
verse pairs; Sefaria's also with its unit-level links), against the two-list fusion, with the
retrieval-exp protocol: the member best on Sefaria (*selected*), the member chosen on the other
fold's queries and scored on the held-out one (*cross-fitted*), the selected member on OpenBible
and ETCBC, which no choice looks at. Rule, fixed before the first run (`adoption`): a family
passes for a unit type when its cross-fitted Sefaria gain has a CI above 0 and the selected
member loses nothing significant on OpenBible or ETCBC (CIs reaching 0); of those passing, the
largest cross-fitted gain is chosen. The command never edits the config.

Writes `artifacts/eval/unit_experiments.json` and `.md`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.data.report import md_table
from bsim.eval.experiments import GOLD_FILES, cross_fit, rrf_many
from bsim.eval.metrics import paired_bootstrap, per_query
from bsim.eval.report import EvalContext, ranked_lists
from bsim.retrieve.filters import neighbor_mask
from bsim.retrieve.fusion import load_lists
from bsim.retrieve.topk import read_topk
from bsim.retrieve.unit_pairs import phrase_pairs, ranked, unit_of_verse, unit_scores

Log = Callable[[str], None]

FAMILIES = ("sequences", "phrases", "hits")


def sequence_pairs(cfg: dict[str, Any], max_q: float | None) -> pd.DataFrame:
    path = resolve_path(cfg, "artifacts") / "sequences" / "verse.parquet"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim sequences` first")
    s = pd.read_parquet(path, columns=["q", "pairs"])
    if max_q is not None:
        s = s[s.q <= max_q]
    rows = [p for chain in s.pairs for p in json.loads(chain)]
    return pd.DataFrame(rows, columns=["a", "b", "w"]).astype({"a": np.int64, "b": np.int64})


def hit_pairs(cfg: dict[str, Any], depth: int, book_id: np.ndarray) -> pd.DataFrame:
    """Directed fused verse hits within the top `depth`, neighbours dropped."""
    name = cfg["final_systems"]["fused"]
    path = resolve_path(cfg, "artifacts") / "topk" / "verse" / f"{name}.parquet"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim fuse` first")
    t = read_topk(path)
    t = t[t["rank"] <= depth]
    window = cfg["retrieval"]["neighbor_window"]
    t = t[~neighbor_mask(t.src.to_numpy(), t.tgt.to_numpy(), book_id, window)]
    w = (depth + 1 - t["rank"].to_numpy(np.float64)) / depth
    return pd.DataFrame({"a": t.src.to_numpy(np.int64), "b": t.tgt.to_numpy(np.int64), "w": w})


def candidate_lists(
    cfg: dict[str, Any], book_id: np.ndarray, log: Log
) -> dict[str, dict[str, pd.DataFrame]]:
    """Family -> variant -> verse pairs `a, b, w`."""
    ux = cfg["unit_experiments"]
    out: dict[str, dict[str, pd.DataFrame]] = {"sequences": {}, "phrases": {}, "hits": {}}
    for q in ux["sequences_max_q"]:
        out["sequences"]["all chains" if q is None else f"q<={q:g}"] = sequence_pairs(cfg, q)
    out["phrases"]["phrases"] = phrase_pairs(cfg)
    for depth in ux["hits_depth"]:
        out["hits"][f"top {depth}"] = hit_pairs(cfg, depth, book_id)
    for fam, variants in out.items():
        log(f"  {fam}: " + ", ".join(f"{v} {len(p):,} verse pairs" for v, p in variants.items()))
    return out


def unit_gold_of(
    verse_gold: dict[int, set[int]], unit_of: np.ndarray, m: int
) -> dict[int, set[int]]:
    """Unit pairs sharing >= m distinct verse pairs of a verse gold (as `eval.report.unit_gold`)."""
    rows = [(s, t) for s, ts in verse_gold.items() for t in ts]
    if not rows:
        return {}
    v = np.array(rows, np.int64)
    inside = (v < len(unit_of)).all(1)
    v = v[inside]
    a, b = unit_of[v[:, 0]], unit_of[v[:, 1]]
    d = pd.DataFrame({"a": a, "b": b, "s": v[:, 0], "t": v[:, 1]})
    d = d[(d.a >= 0) & (d.b >= 0) & (d.a != d.b)].drop_duplicates()
    counts = d.groupby(["a", "b"]).size()
    gold: dict[int, set[int]] = {}
    for x, y in counts[counts >= m].index:
        gold.setdefault(int(x), set()).add(int(y))
    return gold


def adoption(
    entries: dict[str, dict[str, Any]], others: list[str]
) -> tuple[dict[str, bool], str | None]:
    """The rule fixed in advance: cross-fitted Sefaria CI above 0, no significant loss on the
    other golds (the selected member's CIs reaching 0); the largest cross-fitted gain chosen."""
    ok = {
        fam: bool(
            e["cross_fitted_gain"]["lo"] > 0
            and all(e["gains"][g]["hi"] >= 0 for g in others if g in e["gains"])
        )
        for fam, e in entries.items()
    }
    passing = [f for f in entries if ok[f]]
    if not passing:
        return ok, None
    return ok, max(passing, key=lambda f: entries[f]["cross_fitted_gain"]["mean"])


def score_lists(
    df: pd.DataFrame, golds: dict[str, dict[int, set[int]]], metric: str
) -> dict[str, np.ndarray]:
    """Per gold, the metric of each of its queries (sorted), a missing list scoring 0."""
    r = ranked_lists(df)
    out = {}
    for g, gold in golds.items():
        pq = per_query(r, gold, metric)
        out[g] = np.array([pq[q] for q in sorted(pq)])
    return out


def run_unit_experiments(cfg: dict[str, Any], log: Log = print) -> dict[str, Any]:
    ux, fu, k = cfg["unit_experiments"], cfg["fusion"], cfg["retrieval"]["k"]
    reps, seed, metric = ux["bootstrap_reps"], ux["seed"], ux["metric"]
    m = cfg["eval"]["unit_gold_min_links"]
    ctx = EvalContext.load(cfg, "dev")
    proc = resolve_path(cfg, "data_processed")
    verse_golds: dict[str, dict[int, set[int]]] = {}
    for g in ux["golds"]:
        if g == "sefaria":
            continue
        from bsim.eval.openbible import gold_of

        name, cmd = GOLD_FILES[g]
        if not (proc / name).exists():
            raise RuntimeError(f"{proc / name} missing; run `bsim {cmd}` first")
        verse_golds[g] = gold_of(pd.read_parquet(proc / name), "dev")
    lists = candidate_lists(cfg, ctx.book_id, log)
    art = resolve_path(cfg, "artifacts")
    out_types: dict[str, Any] = {}
    for unit_type in ux["unit_types"]:
        units = ctx.units(unit_type)
        unit_of = unit_of_verse(units, len(ctx.book_id))
        golds = {"sefaria": ctx.gold(unit_type)}
        golds |= {g: unit_gold_of(vg, unit_of, m) for g, vg in verse_golds.items()}

        def score(df: pd.DataFrame, golds: dict[str, dict[int, set[int]]] = golds) -> dict:
            return score_lists(df, golds, metric)

        lex, sem, _ = load_lists(cfg, unit_type)
        # the two-list fusion, rebuilt here: the stored fused list holds the adopted third list
        base = score(rrf_many([lex, sem], [fu["w_lex"], fu["w_sem"]], fu["rrf_k"], k))
        log(
            f"\n## {unit_type}: fused {metric} "
            + ", ".join(f"{g} {v.mean():.4f} ({len(v)} queries)" for g, v in base.items())
        )
        entries: dict[str, Any] = {}
        for fam, variants in lists.items():
            alone, members = {}, {}
            for variant, pairs in variants.items():
                x = ranked(unit_scores(pairs, unit_of), k)
                alone[variant] = {
                    "scores": {g: float(v.mean()) for g, v in score(x).items()},
                    "units_with_list": int(x.src.nunique()),
                }
                for w in ux["w_grid"]:
                    df = rrf_many([lex, sem, x], [fu["w_lex"], fu["w_sem"], w], fu["rrf_k"], k)
                    members[f"{variant}, w={w:g}"] = score(df)
            sef = {mem: s["sefaria"] for mem, s in members.items()}
            best = max(sef, key=lambda mem: (sef[mem].mean(), mem))
            gains_cf, chosen = cross_fit(sef, base["sefaria"], ux["folds"], seed)
            entries[fam] = {
                "alone": alone,
                "members": {
                    mem: {g: float(v.mean()) for g, v in s.items()} for mem, s in members.items()
                },
                "selected": best,
                "gains": {
                    g: paired_bootstrap(members[best][g] - base[g], reps, seed) for g in golds
                },
                "cross_fitted_choices": chosen,
                "cross_fitted_gain": paired_bootstrap(gains_cf, reps, seed),
            }
        ok, chosen_fam = adoption(entries, [g for g in golds if g != "sefaria"])
        for fam, e in entries.items():
            e["adopt"] = ok[fam]
            log(
                f"  {fam}: selected {e['selected']}; cross-fitted {_gain(e['cross_fitted_gain'])}; "
                + "; ".join(f"{g} {_gain(e['gains'][g])}" for g in golds)
                + f"; passes: {'yes' if ok[fam] else 'no'}"
            )
        log(f"  chosen: {chosen_fam or 'none'}")
        out_types[unit_type] = {
            "baseline_scores": {g: float(v.mean()) for g, v in base.items()},
            "queries": {g: len(v) for g, v in base.items()},
            "families": entries,
            "chosen": chosen_fam,
        }
    out = {
        "split": "dev",
        "metric": metric,
        "baseline": "lexical + semantic",
        "unit_types": out_types,
        "config_hash": config_hash(cfg, "unit_experiments", "fusion", "eval", "retrieval"),
        "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (art / "eval").mkdir(parents=True, exist_ok=True)
    (art / "eval" / "unit_experiments.json").write_text(json.dumps(out, indent=2) + "\n", "utf-8")
    (art / "eval" / "unit_experiments.md").write_text(report(out), "utf-8")
    log(f"\nwrote {art / 'eval' / 'unit_experiments.md'}")
    return out


def _gain(g: dict[str, float]) -> str:
    return f"{g['mean']:+.4f} [{g['lo']:+.4f}, {g['hi']:+.4f}]"


def report(out: dict[str, Any]) -> str:
    lines = [
        "# Chapter and pericope retrieval: a third fusion list (dev split)",
        "",
        f"Baseline `{out['baseline']}` ({out['metric']}). Gains paired over queries, 95 % bootstrap"
        " CI. *Selected*: the member best on Sefaria dev; *cross-fitted*: chosen on the other fold,"
        " scored on the held-out one. A family passes when its cross-fitted CI is above 0 and the"
        " selected member loses nothing significant on the other golds.",
    ]
    for unit_type, r in out["unit_types"].items():
        golds = list(r["baseline_scores"])
        lines += [
            "",
            f"## {unit_type}",
            "",
            "fused: "
            + ", ".join(
                f"{g} {r['baseline_scores'][g]:.4f} ({r['queries'][g]} queries)" for g in golds
            )
            + ".",
            "",
            md_table(
                ["family", "selected", "cross-fitted", *golds, "passes"],
                [
                    [
                        fam,
                        e["selected"],
                        _gain(e["cross_fitted_gain"]),
                        *(_gain(e["gains"][g]) for g in golds),
                        "yes" if e["adopt"] else "no",
                    ]
                    for fam, e in r["families"].items()
                ],
            ),
            "",
            "Alone (not chosen):",
            "",
            md_table(
                ["family", "list", "units with a list", *golds],
                [
                    [fam, v, f"{a['units_with_list']:,}", *(f"{a['scores'][g]:.4f}" for g in golds)]
                    for fam, e in r["families"].items()
                    for v, a in e["alone"].items()
                ],
            ),
            "",
            f"Chosen: {r['chosen'] or 'none'}.",
        ]
    return "\n".join(lines) + "\n"
