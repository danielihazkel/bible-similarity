"""`bsim supervision-exp`: does more supervision help the encoder? (DESIGN.md §16.41). Dev only.

The semantic model (`berel-sup`, §7.2) learns from the ~4.5k Sefaria train-split links, the
connections the commentary tradition made famous (§8.4). Each variant in
`supervision_experiments.variants` retrains it with the same recipe and a few overrides: extra
training pairs from OpenBible and ETCBC between train-split books (`train/pairs.py`), or another
seed, which shows what a retrain alone moves. It is written to
`paths.models/{train.supervised.output}-{name}`; an existing variant model is reused unless
`--retrain`. Every variant and the model in use (`baseline`) are scored the same way, in memory:
    semantic   all verses encoded, CSLS top-k (`retrieval.k`), as `bsim embed` + `bsim topk`
    fused      that list fused with the final lexical list (RRF, `fusion` weights), as `bsim fuse`
on the dev golds of `golds` (Sefaria, OpenBible, ETCBC; ±window neighbours dropped as in the
report). A variant's gain over the baseline is paired over queries with a bootstrap CI.

Adoption rule, fixed before any variant was trained. A variant may replace the semantic model only
if its fused list
- gains on OpenBible with a CI above 0, by more than the `noise` variant moves it either way;
- loses nothing significant on Sefaria or ETCBC (each CI reaches 0 or above). ETCBC is a check,
  not a target: the fused list already scores 0.83 there, over 179 queries.
Among the variants that pass, the one with the largest Sefaria mean gain is chosen. This command
never edits the config: adopting is a config change by hand, followed by a pipeline retrain.

Writes `artifacts/eval/supervision_experiments.json` and `.md`.
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
from bsim.eval.experiments import Scorer
from bsim.eval.metrics import paired_bootstrap
from bsim.retrieve.fusion import load_lists, rrf
from bsim.retrieve.topk import get_device, parse_verse_ids, topk_chunks, topk_frame

Log = Callable[[str], None]
LISTS = ("semantic", "fused")


def variant_config(cfg: dict[str, Any], name: str, overrides: dict[str, Any]) -> dict[str, Any]:
    """`cfg` with a variant's overrides: `seed` at the top, the rest in `train.supervised`, and
    the output `{output}-{name}`."""
    from bsim.train.supervised import with_overrides

    out = with_overrides(cfg, seed=overrides.get("seed"))
    sup = out["train"]["supervised"]
    sup.update({k: v for k, v in overrides.items() if k != "seed"})
    sup["output"] = f"{cfg['train']['supervised']['output']}-{name}"
    return out


def csls_list(emb: np.ndarray, cfg: dict[str, Any]) -> pd.DataFrame:
    """The CSLS top-k of an embedding matrix (`src, tgt, rank, score`), as `bsim topk`."""
    from bsim.embed.csls import csls_scorer, hubness

    r = cfg["retrieval"]
    device = get_device(r["device"])
    hub = hubness(emb, r["csls_neighbors"], r["chunk_size"], device)
    scorer = csls_scorer(emb, hub, device)
    idx, score = topk_chunks(scorer, len(emb), r["k"], r["chunk_size"], device)
    df = topk_frame(idx, score)
    return pd.DataFrame(
        {
            "src": parse_verse_ids(df.src_id),
            "tgt": parse_verse_ids(df.tgt_id),
            "rank": df["rank"],
            "score": df.score,
        }
    )


def encode_model(cfg: dict[str, Any], path: str, texts: list[str]) -> np.ndarray:
    from bsim.embed.encoders import encode, load_encoder

    device = get_device(cfg["encoders"].get("device", "cuda"))
    spec = {"model": path, "pooling": "native"}
    model = load_encoder(spec, cfg["text"]["max_seq_length"], str(device))
    emb = encode(model, texts, cfg["encoders"]["batch_size"])
    del model
    free_gpu()
    return emb


def free_gpu() -> None:
    import gc

    import torch

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def adoption(
    gains: dict[str, dict[str, dict[str, Any]]], noise: str | None
) -> tuple[dict[str, bool], str | None]:
    """Per variant whether its fused list passes the rule fixed in advance, and the one chosen.
    `gains`: variant -> gold -> list -> bootstrap dict."""
    ok: dict[str, bool] = {}
    for name, g in gains.items():
        if name == noise:
            ok[name] = False
            continue
        ob = g["openbible"]["fused"]
        bar = abs(gains[noise]["openbible"]["fused"]["mean"]) if noise in gains else 0.0
        ok[name] = bool(
            ob["lo"] > 0
            and ob["mean"] > bar
            and g["sefaria"]["fused"]["hi"] >= 0
            and g["etcbc"]["fused"]["hi"] >= 0
        )
    passing = [n for n, v in ok.items() if v]
    chosen = max(passing, key=lambda n: gains[n]["sefaria"]["fused"]["mean"]) if passing else None
    return ok, chosen


def run_supervision_experiments(
    cfg: dict[str, Any], log: Log = print, retrain: bool = False, only: list[str] | None = None
) -> dict[str, Any]:
    from bsim.train.common import TRAIN_META
    from bsim.train.supervised import run_train_sup

    sx, fu, k = cfg["supervision_experiments"], cfg["fusion"], cfg["retrieval"]["k"]
    variants = {n: v for n, v in sx["variants"].items() if not only or n in only}
    if only and (unknown := sorted(set(only) - set(sx["variants"]))):
        raise RuntimeError(f"unknown variant(s) {unknown}; configured: {sorted(sx['variants'])}")
    scorer = Scorer(cfg, log, tuple(sx["golds"]), sx["metric"])
    missing = [g for g in sx["golds"] if g not in scorer.golds]
    if missing:
        raise RuntimeError(
            f"dev gold(s) {missing} missing; run `bsim build-golds` first"
        )
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    models = resolve_path(cfg, "models")
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "text_model"])
    texts = verses.sort_values("verse_id").text_model.tolist()
    lex, _, _ = load_lists(cfg, "verse")

    def lists(emb: np.ndarray) -> dict[str, dict[str, np.ndarray]]:
        sem = csls_list(emb, cfg)
        fused = rrf(lex, sem, fu["w_lex"], fu["w_sem"], fu["rrf_k"], k)
        return {"semantic": scorer(sem), "fused": scorer(fused)}

    base_name = sx["baseline"]
    base_path = art / "embeddings" / f"{base_name}.npy"
    if not base_path.exists():
        raise RuntimeError(f"{base_path} missing; run `bsim embed` first")
    base = lists(np.load(base_path))
    log(
        f"baseline {base_name} ({sx['metric']}, dev): "
        + "; ".join(
            f"{li} " + ", ".join(f"{g} {v.mean():.4f}" for g, v in base[li].items()) for li in LISTS
        )
    )

    reps, seed = sx["bootstrap_reps"], sx["seed"]
    results: dict[str, Any] = {}
    for name, overrides in variants.items():
        vcfg = variant_config(cfg, name, overrides)
        out_dir = models / vcfg["train"]["supervised"]["output"]
        if retrain or not (out_dir / TRAIN_META).exists():
            log(f"\n## {name}: training {out_dir.name} ({overrides})")
            run_train_sup(vcfg, log=log, negatives=f"hard_negatives_{name}")
            free_gpu()
        meta = json.loads((out_dir / TRAIN_META).read_text("utf-8"))
        scores = lists(encode_model(cfg, str(out_dir), texts))
        gains = {
            g: {
                li: paired_bootstrap(scores[li][g] - base[li][g], reps, seed) for li in LISTS
            }
            for g in scorer.golds
        }
        results[name] = {
            "overrides": overrides,
            "model": out_dir.name,
            "rows_by_source": meta.get("rows_by_source", {}),
            "best_step": meta.get("best_step"),
            "best_epoch": meta.get("best_epoch"),
            "train_select": meta.get("best"),
            "scores": {li: {g: float(v.mean()) for g, v in scores[li].items()} for li in LISTS},
            "gains": gains,
        }
        for li in LISTS:
            log(f"  {name} {li}: " + "; ".join(f"{g} {_gain(gains[g][li])}" for g in gains))

    path = art / "eval" / "supervision_experiments.json"
    if only and path.exists():  # keep the variants not rerun
        results = {**json.loads(path.read_text("utf-8")).get("results", {}), **results}
    ok, chosen = adoption({n: r["gains"] for n, r in results.items()}, sx["noise"])
    for name, r in results.items():
        r["adopt"] = ok[name]
    out = {
        "split": "dev",
        "metric": sx["metric"],
        "baseline": base_name,
        "baseline_scores": {li: {g: float(v.mean()) for g, v in base[li].items()} for li in LISTS},
        "queries": {g: len(v) for g, v in base["fused"].items()},
        "noise": sx["noise"],
        "results": results,
        "chosen": chosen,
        "config_hash": config_hash(cfg, "supervision_experiments", "train", "fusion", "retrieval"),
        "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n", "utf-8")
    (art / "eval" / "supervision_experiments.md").write_text(report(out), "utf-8")
    log(f"\nchosen: {out['chosen'] or 'none'}; wrote {path.with_suffix('.md')}")
    return out


def _gain(g: dict[str, Any]) -> str:
    return (
        f"{g['mean']:+.4f} [{g['lo']:+.4f}, {g['hi']:+.4f}] "
        f"({g['better']} better, {g['worse']} worse of {g['queries']})"
    )


def report(out: dict[str, Any]) -> str:
    golds = list(out["queries"])
    lines = [
        "# More supervision for the encoder (dev split)",
        "",
        f"Baseline `{out['baseline']}`, {out['metric']}: "
        + "; ".join(
            f"{li} " + ", ".join(f"{g} {v:.4f}" for g, v in out["baseline_scores"][li].items())
            for li in LISTS
        )
        + f". Queries: {', '.join(f'{g} {n}' for g, n in out['queries'].items())}. Gains are"
        " paired over queries with a 95 % bootstrap CI. A variant is adopted only if its fused"
        " OpenBible gain has a CI above 0 and is larger than the gain of"
        f" `{out['noise']}` (a retrain with another seed) either way, and its Sefaria and ETCBC"
        " CIs reach 0.",
        "",
        md_table(
            ["variant", "training rows", "list", *golds, "adopt"],
            [
                [
                    name,
                    ", ".join(f"{s} {n}" for s, n in r["rows_by_source"].items()),
                    li,
                    *(_gain(r["gains"][g][li]) for g in golds),
                    ("yes" if r["adopt"] else "no") if li == "fused" else "",
                ]
                for name, r in out["results"].items()
                for li in LISTS
            ],
        ),
        "",
        f"Chosen: {out['chosen'] or 'none'}.",
    ]
    return "\n".join(lines) + "\n"
