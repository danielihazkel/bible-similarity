"""`bsim retrieval-exp`: do contextual embeddings, late interaction or semantic domains improve
the fused verse lists? (DESIGN.md §16.21, §16.22). Dev split only.

Families of candidate verse lists, each compared with the final fused list:
    context {system}   for every `retrieval_experiments.context_systems` top-k (`bsim embed-context`
                       + `bsim topk`): the system alone, in place of the semantic list (lexical +
                       it, RRF), and as a third RRF list next to lexical + semantic at each weight
                       of `w_grid`
    lexical {system}   for every `retrieval_experiments.lexical_systems` top-k (`bsim lexical` +
                       `bsim topk`; SDBH domains, §16.22): the system alone, in place of the lexical
                       list (it + semantic, RRF), and as a third list at each weight of `w_grid`
    structural         every `retrieval_experiments.structural_systems` list (BHSA clause shapes,
                       §16.26) against the final *structural* list instead of fused: gain on both
                       golds, the share of each verse's top-10 that has its text type (narration /
                       speech / discourse, the clauses' majority), and the overlap with the
                       structural list. Adopted as the structural system if its Sefaria gain CI
                       excludes 0 and the OpenBible gain is not negative
    maxsim {encoder}   the fused top-`maxsim.depth` reordered by MaxSim (`bsim maxsim`), blended
                       with the fused rank at each weight of `maxsim_grid` (null = MaxSim alone)
    cross-encoder      the same blend with the M18 cross-encoder scores (`bsim rerank`), when its
                       list exists, for comparison
Every list is scored like the eval report (±window neighbours dropped) on two dev golds: the
Sefaria links (the gold weights are chosen on) and the OpenBible cross-references (§16.13), which
no choice here looks at. Per family:
    selected      the member best on Sefaria dev; its gain over fused, paired bootstrap over
                  queries (optimistic: chosen on the same queries, as in M18)
    cross-fitted  `folds`-fold: the member is chosen on the other folds' queries and scored on
                  the held-out fold; out-of-fold gains pooled and bootstrapped (honest)
    openbible     the selected member's gain on the OpenBible dev gold
A family is adopted only if the cross-fitted CI excludes 0 and the OpenBible gain is not negative.

Writes `artifacts/eval/retrieval_experiments.json` and `.md`.
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
from bsim.eval.metrics import paired_bootstrap, per_query
from bsim.eval.report import EvalContext, ranked_lists
from bsim.retrieve.fusion import load_lists
from bsim.retrieve.topk import read_topk

Log = Callable[[str], None]


def rrf_many(frames: list[pd.DataFrame], weights: list[float], rrf_k: int, k: int) -> pd.DataFrame:
    """Weighted RRF of any number of ranked frames (`src, tgt, rank`); `src, tgt, rank, score`
    of the best `k` per source, ties by target (as `fusion.rrf`)."""
    parts = [
        f[["src", "tgt"]].assign(score=w / (rrf_k + f["rank"].to_numpy(np.float64)))
        for f, w in zip(frames, weights, strict=True)
    ]
    m = pd.concat(parts).groupby(["src", "tgt"], as_index=False)["score"].sum()
    m = m.sort_values(["src", "score", "tgt"], ascending=[True, False, True], kind="stable")
    m["rank"] = (m.groupby("src").cumcount() + 1).astype(np.int32)
    return m[m["rank"] <= k].reset_index(drop=True)


def blend(scored: pd.DataFrame, w: float | None, rrf_k: int) -> pd.DataFrame:
    """A reranker's scores (`ce_score`) blended with the list rank, as `rerank.combine`."""
    from bsim.train.rerank import combine

    return combine(scored, w, rrf_k)[["src", "tgt", "rank"]]


class Scorer:
    """Per-query metric of verse lists on the dev golds, neighbour-filtered like the report."""

    def __init__(self, cfg: dict[str, Any], log: Log) -> None:
        self.ctx = EvalContext.load(cfg, "dev")
        self.metric = cfg["retrieval_experiments"]["metric"]
        self.golds = {"sefaria": self.ctx.gold("verse")}
        ob = resolve_path(cfg, "data_processed") / "openbible_links.parquet"
        if ob.exists():
            from bsim.eval.openbible import gold_of

            self.golds["openbible"] = gold_of(pd.read_parquet(ob), "dev")
        else:
            log(f"  {ob} missing (run `bsim eval-openbible`): Sefaria gold only")
        self.queries = {
            g: sorted(q for q, s in gold.items() if s) for g, gold in self.golds.items()
        }

    def __call__(self, df: pd.DataFrame) -> dict[str, np.ndarray]:
        ranked = ranked_lists(self.ctx.filter("verse", df))
        out = {}
        for g, gold in self.golds.items():
            pq = per_query(ranked, gold, self.metric)
            out[g] = np.array([pq[q] for q in self.queries[g]])
        return out


def families(cfg: dict[str, Any], log: Log) -> dict[str, dict[str, pd.DataFrame]]:
    """Family name -> member name -> verse list (`src, tgt, rank`)."""
    rx, fu, k = cfg["retrieval_experiments"], cfg["fusion"], cfg["retrieval"]["k"]
    art = resolve_path(cfg, "artifacts")
    lex, sem, _ = load_lists(cfg, "verse")
    out: dict[str, dict[str, pd.DataFrame]] = {}
    for system in rx["context_systems"]:
        path = art / "topk" / "verse" / f"{system}.parquet"
        if not path.exists():
            log(f"  {path} missing (`bsim embed-context` + `bsim topk --system {system}`): skipped")
            continue
        x = read_topk(path)
        members = {
            "alone": x,
            "in place of semantic": rrf_many([lex, x], [fu["w_lex"], fu["w_sem"]], fu["rrf_k"], k),
        }
        for w in rx["w_grid"]:
            members[f"third list w={w}"] = rrf_many(
                [lex, sem, x], [fu["w_lex"], fu["w_sem"], w], fu["rrf_k"], k
            )
        out[f"context {system}"] = members
    for system in rx["lexical_systems"]:
        path = art / "topk" / "verse" / f"{system}.parquet"
        if not path.exists():
            log(f"  {path} missing (`bsim lexicon` + `bsim lexical` + `bsim topk`): skipped")
            continue
        x = read_topk(path)
        members = {
            "alone": x,
            "in place of lexical": rrf_many([x, sem], [fu["w_lex"], fu["w_sem"]], fu["rrf_k"], k),
        }
        for w in rx["w_grid"]:
            members[f"third list w={w}"] = rrf_many(
                [lex, sem, x], [fu["w_lex"], fu["w_sem"], w], fu["rrf_k"], k
            )
        out[f"lexical {system}"] = members
    mc = cfg["maxsim"]
    for enc in mc["encoders"]:
        path = art / "maxsim" / f"{enc}.parquet"
        if not path.exists():
            log(f"  {path} missing (`bsim maxsim`): skipped")
            continue
        scored = pd.read_parquet(path).rename(columns={"maxsim": "ce_score"})
        out[f"maxsim {enc}"] = {
            ("alone" if w is None else f"w={w}"): blend(scored, w, mc["rrf_k"])
            for w in rx["maxsim_grid"]
        }
    rr = cfg["rerank"]
    path = art / "topk" / "verse" / f"{rr['system']}.parquet"
    if path.exists():
        ce = read_topk(path)
        scored = ce[["src", "tgt", "fused_rank", "ce_score"]].rename(columns={"fused_rank": "rank"})
        out["cross-encoder (M18)"] = {
            ("alone" if w is None else f"w={w}"): blend(scored, w, rr["rrf_k"])
            for w in rr["w_ce_grid"]
        }
    return out


def cross_fit(
    member_scores: dict[str, np.ndarray], base: np.ndarray, folds: int, seed: int
) -> tuple[np.ndarray, list[str]]:
    """Out-of-fold per-query gains: each fold scored with the member best on the other folds."""
    n = len(base)
    fold = np.random.default_rng(seed).permutation(n) % folds
    gains = np.empty(n)
    chosen = []
    for f in range(folds):
        train, held = fold != f, fold == f
        best = max(member_scores, key=lambda m: (member_scores[m][train].mean(), m))
        chosen.append(best)
        gains[held] = member_scores[best][held] - base[held]
    return gains, chosen


def run_retrieval_experiments(cfg: dict[str, Any], log: Log = print) -> dict[str, Any]:
    rx = cfg["retrieval_experiments"]
    reps, seed = rx["bootstrap_reps"], rx["seed"]
    scorer = Scorer(cfg, log)
    art = resolve_path(cfg, "artifacts")
    fused_path = art / "topk" / "verse" / f"{cfg['final_systems']['fused']}.parquet"
    base = scorer(read_topk(fused_path))
    log(
        f"fused ({rx['metric']}, dev): Sefaria {base['sefaria'].mean():.4f} over "
        f"{len(base['sefaria'])} queries"
        + (
            f", OpenBible {base['openbible'].mean():.4f} over {len(base['openbible'])}"
            if "openbible" in base
            else ""
        )
    )
    results: dict[str, Any] = {}
    for fam, members in families(cfg, log).items():
        scores = {m: scorer(df) for m, df in members.items()}
        sef = {m: s["sefaria"] for m, s in scores.items()}
        best = max(sef, key=lambda m: (sef[m].mean(), m))
        gains, chosen = cross_fit(sef, base["sefaria"], rx["folds"], seed)
        entry: dict[str, Any] = {
            "members": {m: {g: float(v.mean()) for g, v in s.items()} for m, s in scores.items()},
            "selected": best,
            "selected_gain": paired_bootstrap(sef[best] - base["sefaria"], reps, seed),
            "cross_fitted_choices": chosen,
            "cross_fitted_gain": paired_bootstrap(gains, reps, seed),
        }
        if "openbible" in base:
            entry["openbible_gain"] = paired_bootstrap(
                scores[best]["openbible"] - base["openbible"], reps, seed
            )
        cf, ob = entry["cross_fitted_gain"], entry.get("openbible_gain")
        entry["adopt"] = bool(cf["lo"] > 0 and (ob is None or ob["mean"] >= 0))
        results[fam] = entry
        log(f"\n### {fam}")
        log(
            md_table(
                ["member", "Sefaria", *(["OpenBible"] if "openbible" in base else [])],
                [[m, *(f"{v:.4f}" for v in r.values())] for m, r in entry["members"].items()],
            )
        )
        log(f"  selected {best}: {_gain(entry['selected_gain'])}")
        log(f"  cross-fitted ({' / '.join(chosen)}): {_gain(cf)}")
        if ob is not None:
            log(f"  OpenBible: {_gain(ob)}")
        log(f"  adopt: {'yes' if entry['adopt'] else 'no'}")
    out = {
        "split": "dev",
        "metric": rx["metric"],
        "baseline": cfg["final_systems"]["fused"],
        "baseline_scores": {g: float(v.mean()) for g, v in base.items()},
        "queries": {g: len(v) for g, v in base.items()},
        "results": results,
        "config_hash": config_hash(
            cfg, "retrieval_experiments", "context", "maxsim", "fusion", "eval", "retrieval"
        ),
        "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    structural = structural_experiment(cfg, scorer, log)
    if structural:
        out["structural"] = structural
    (art / "eval").mkdir(parents=True, exist_ok=True)
    (art / "eval" / "retrieval_experiments.json").write_text(
        json.dumps(out, indent=2) + "\n", "utf-8"
    )
    (art / "eval" / "retrieval_experiments.md").write_text(report(out), "utf-8")
    log(f"\nwrote {art / 'eval' / 'retrieval_experiments.md'}")
    return out


def text_types(cfg: dict[str, Any]) -> np.ndarray | None:
    """Per verse its clauses' majority text type (N / Q / D, '' without clauses), or None
    without `bsim syntax`."""
    path = resolve_path(cfg, "data_processed") / "syntax_clauses.parquet"
    if not path.exists():
        return None
    c = pd.read_parquet(path, columns=["verse_id", "txt"])
    c = c[c.txt.str.len() > 0].assign(t=lambda d: d.txt.str[-1])
    c = c[c.t.isin(["N", "Q", "D"])]
    major = c.groupby("verse_id").t.agg(lambda s: s.value_counts().index[0])
    n = int(pd.read_parquet(resolve_path(cfg, "data_processed") / "verses.parquet").shape[0])
    out = np.full(n, "", dtype=object)
    out[major.index.to_numpy()] = major.to_numpy()
    return out


def type_agreement(df: pd.DataFrame, types: np.ndarray, k: int) -> float:
    """Mean share of each verse's top-k with its own text type (verses with a type)."""
    top = df[df["rank"] <= k]
    s, t = types[top.src.to_numpy()], types[top.tgt.to_numpy()]
    ok = s != ""
    same = pd.Series((s == t)[ok]).groupby(top.src.to_numpy()[ok]).mean()
    return float(same.mean()) if len(same) else 0.0


def overlap_at(a: pd.DataFrame, b: pd.DataFrame, k: int) -> float:
    """Mean |top-k(a) ∩ top-k(b)| / k over the sources of a."""
    ta = a[a["rank"] <= k].groupby("src").tgt.apply(set)
    tb = b[b["rank"] <= k].groupby("src").tgt.apply(set)
    shared = [len(s & tb.get(q, set())) / k for q, s in ta.items()]
    return float(np.mean(shared)) if shared else 0.0


def structural_experiment(cfg: dict[str, Any], scorer: Scorer, log: Log) -> dict[str, Any]:
    rx = cfg["retrieval_experiments"]
    reps, seed, k = rx["bootstrap_reps"], rx["seed"], rx["agreement_k"]
    art = resolve_path(cfg, "artifacts") / "topk" / "verse"
    base_name = cfg["final_systems"]["structural"]
    candidates = [s for s in rx["structural_systems"] if (art / f"{s}.parquet").exists()]
    if not candidates or not (art / f"{base_name}.parquet").exists():
        return {}
    types = text_types(cfg)
    base_df = read_topk(art / f"{base_name}.parquet")
    base = scorer(base_df)

    def describe(df: pd.DataFrame, s: dict[str, np.ndarray]) -> dict[str, float]:
        out = {g: float(v.mean()) for g, v in s.items()}
        if types is not None:
            out["text_type_agreement"] = type_agreement(df, types, k)
        return out

    out: dict[str, Any] = {"baseline": base_name, base_name: describe(base_df, base), "members": {}}
    log(f"\n### structural (vs {base_name})")
    for name in candidates:
        df = read_topk(art / f"{name}.parquet")
        s = scorer(df)
        entry: dict[str, Any] = {
            **describe(df, s),
            f"overlap@{k}": overlap_at(df, base_df, k),
            "sefaria_gain": paired_bootstrap(s["sefaria"] - base["sefaria"], reps, seed),
        }
        if "openbible" in s:
            entry["openbible_gain"] = paired_bootstrap(
                s["openbible"] - base["openbible"], reps, seed
            )
        ob = entry.get("openbible_gain")
        entry["adopt"] = bool(entry["sefaria_gain"]["lo"] > 0 and (ob is None or ob["mean"] >= 0))
        out["members"][name] = entry
        log(
            f"  {name}: Sefaria {_gain(entry['sefaria_gain'])}"
            + (f"; OpenBible {_gain(ob)}" if ob else "")
            + (
                f"; text type {entry['text_type_agreement']:.3f}"
                f" ({base_name} {out[base_name]['text_type_agreement']:.3f})"
                if types is not None
                else ""
            )
            + f"; overlap@{k} {entry[f'overlap@{k}']:.3f}"
            + f"; adopt: {'yes' if entry['adopt'] else 'no'}"
        )
    return out


def _gain(g: dict[str, float]) -> str:
    return (
        f"{g['mean']:+.4f}, 95 % CI [{g['lo']:+.4f}, {g['hi']:+.4f}] "
        f"({g['better']} better, {g['worse']} worse of {g['queries']})"
    )


def report(out: dict[str, Any]) -> str:
    metric, has_ob = out["metric"], "openbible" in out["baseline_scores"]
    lines = [
        "# Retrieval experiments (dev split)",
        "",
        f"Baseline `{out['baseline']}`: {metric} Sefaria {out['baseline_scores']['sefaria']:.4f}"
        f" ({out['queries']['sefaria']} queries)"
        + (
            f", OpenBible {out['baseline_scores']['openbible']:.4f}"
            f" ({out['queries']['openbible']} queries)"
            if has_ob
            else ""
        )
        + ". Gains are paired over queries with a 95 % bootstrap CI. *Selected* = best member on"
        " Sefaria dev, scored on the same queries; *cross-fitted* = member chosen on the other"
        " folds, scored on the held-out one; *OpenBible* = the selected member on the second"
        " gold, which no choice looked at. Adopted only if the cross-fitted CI excludes 0 and"
        " the OpenBible gain is not negative.",
        "",
        md_table(
            ["family", "selected", "selected gain", "cross-fitted gain"]
            + (["OpenBible gain"] if has_ob else [])
            + ["adopt"],
            [
                [
                    fam,
                    r["selected"],
                    _gain(r["selected_gain"]),
                    _gain(r["cross_fitted_gain"]),
                    *([_gain(r["openbible_gain"])] if has_ob else []),
                    "yes" if r["adopt"] else "no",
                ]
                for fam, r in out["results"].items()
            ],
        ),
    ]
    st = out.get("structural")
    if st:
        base = st["baseline"]
        lines += [
            "",
            f"## structural (against `{base}`, not fused)",
            "",
            f"`{base}`: "
            + ", ".join(f"{key} {v:.4f}" for key, v in st[base].items())
            + ". Text type: the share of a verse's top list with its text type (narration,"
            " speech, discourse).",
            "",
            md_table(
                ["system", "Sefaria gain", "OpenBible gain", "text type", "overlap", "adopt"],
                [
                    [
                        name,
                        _gain(m["sefaria_gain"]),
                        _gain(m["openbible_gain"]) if "openbible_gain" in m else "",
                        f"{m.get('text_type_agreement', float('nan')):.3f}",
                        f"{next(v for key, v in m.items() if key.startswith('overlap@')):.3f}",
                        "yes" if m["adopt"] else "no",
                    ]
                    for name, m in st["members"].items()
                ],
            ),
        ]
    for fam, r in out["results"].items():
        lines += [
            "",
            f"## {fam}",
            "",
            md_table(
                ["member", "Sefaria", *(["OpenBible"] if has_ob else [])],
                [[m, *(f"{v:.4f}" for v in s.values())] for m, s in r["members"].items()],
            ),
        ]
    return "\n".join(lines) + "\n"
