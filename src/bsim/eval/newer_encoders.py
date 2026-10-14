"""`bsim encoder-exp`: do newer encoders beat the one in use? (DESIGN.md §16.48). Dev only.

The semantic model is BEREL 3.0 (rabbinic Hebrew) fine-tuned by `bsim train-sup` (§7.2, §16.41).
Two kinds of candidate, both named in `encoder_experiments`:
    trained     another base model through `train-sup` with the same recipe, pairs and seed
                (DictaBERT base and large, modern Hebrew), written to `paths.models/{name}-sup`;
                an existing model is reused unless `--retrain`
    zero_shot   a multilingual embedder used as it is (multilingual-E5-large, Qwen3-Embedding-0.6B),
                with its own instruction put before every verse; never trained here
Every candidate and the model in use (`baseline`) are scored the same way, in memory, as in
`bsim supervision-exp`: the semantic list (CSLS top-k) and that list fused with the final lexical
list, on the dev golds of `golds`, with each gain over the baseline paired over queries with a
bootstrap CI. The zero-shot candidates are also compared with the zero-shot system already built
(`reference`, BGE-M3), on the semantic list.

Adoption rule, fixed before any candidate was trained or encoded. A candidate may replace the
semantic model only if its fused list
- gains on Sefaria (the gold the system is built for, §8) with a CI above 0, by more than the
  largest fused gain, either way, of `noise` (supervision-exp's reseeded retrain: what a retrain
  alone moves);
- loses nothing significant on OpenBible or ETCBC (each CI reaches 0 or above).
Among the candidates that pass, the one with the largest Sefaria mean gain is chosen. This command
never edits the config: adopting is a config change by hand, followed by a pipeline retrain.

Writes `artifacts/eval/encoder_experiments.json` and `.md`.
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
from bsim.eval.supervision import LISTS, _gain, csls_list, free_gpu
from bsim.retrieve.fusion import load_lists, rrf
from bsim.retrieve.topk import get_device

Log = Callable[[str], None]
KINDS = ("trained", "zero_shot")


def candidate_config(cfg: dict[str, Any], name: str, overrides: dict[str, Any]) -> dict[str, Any]:
    """`cfg` with a trained candidate's overrides in `train.supervised`, started from its base
    (never from another checkpoint) and written to `{name}-sup`."""
    from bsim.train.supervised import BASE_INIT, with_overrides

    out = with_overrides(cfg, init=BASE_INIT, output=f"{name}-sup")
    out["train"]["supervised"].update(overrides)
    return out


def noise_bar(supervision: dict[str, Any] | None, noise: str, golds: list[str]) -> float:
    """The largest fused gain, either way, of supervision-exp's `noise` variant over `golds`."""
    gains = ((supervision or {}).get("results", {}).get(noise) or {}).get("gains")
    if not gains:
        raise RuntimeError(
            f"supervision-exp variant {noise!r} not scored; "
            f"run `bsim supervision-exp --only {noise}`"
        )
    return max(abs(gains[g]["fused"]["mean"]) for g in golds if g in gains)


def adoption(
    gains: dict[str, dict[str, dict[str, Any]]], bar: float
) -> tuple[dict[str, bool], str | None]:
    """Per candidate whether its fused list passes the rule fixed in advance, and the one chosen.
    `gains`: candidate -> gold -> list -> bootstrap dict."""
    ok = {
        name: bool(
            g["sefaria"]["fused"]["lo"] > 0
            and g["sefaria"]["fused"]["mean"] > bar
            and g["openbible"]["fused"]["hi"] >= 0
            and g["etcbc"]["fused"]["hi"] >= 0
        )
        for name, g in gains.items()
    }
    passing = [n for n, v in ok.items() if v]
    chosen = max(passing, key=lambda n: gains[n]["sefaria"]["fused"]["mean"]) if passing else None
    return ok, chosen


def encode_spec(cfg: dict[str, Any], spec: dict[str, Any], texts: list[str]) -> np.ndarray:
    from bsim.embed.encoders import encode, load_encoder

    device = get_device(cfg["encoders"].get("device", "cuda"))
    model = load_encoder(spec, cfg["text"]["max_seq_length"], str(device))
    emb = encode(model, texts, cfg["encoders"]["batch_size"], spec.get("prompt"))
    del model
    free_gpu()
    return emb


def run_encoder_experiments(
    cfg: dict[str, Any], log: Log = print, retrain: bool = False, only: list[str] | None = None
) -> dict[str, Any]:
    from bsim.train.common import TRAIN_META
    from bsim.train.supervised import run_train_sup

    ex, fu, k = cfg["encoder_experiments"], cfg["fusion"], cfg["retrieval"]["k"]
    configured = {n: (kind, spec) for kind in KINDS for n, spec in (ex.get(kind) or {}).items()}
    if only and (unknown := sorted(set(only) - set(configured))):
        raise RuntimeError(f"unknown candidate(s) {unknown}; configured: {sorted(configured)}")
    candidates = {n: v for n, v in configured.items() if not only or n in only}
    scorer = Scorer(cfg, log, tuple(ex["golds"]), ex["metric"])
    missing = [g for g in ex["golds"] if g not in scorer.golds]
    if missing:
        raise RuntimeError(f"dev gold(s) {missing} missing; run `bsim build-golds` first")
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    models = resolve_path(cfg, "models")
    sup_path = art / "eval" / "supervision_experiments.json"
    supervision = json.loads(sup_path.read_text("utf-8")) if sup_path.exists() else None
    bar = noise_bar(supervision, ex["noise"], ex["golds"])
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "text_model"])
    texts = verses.sort_values("verse_id").text_model.tolist()
    lex, _, _ = load_lists(cfg, "verse")

    def lists(emb: np.ndarray) -> dict[str, dict[str, np.ndarray]]:
        sem = csls_list(emb, cfg)
        fused = rrf(lex, sem, fu["w_lex"], fu["w_sem"], fu["rrf_k"], k)
        return {"semantic": scorer(sem), "fused": scorer(fused)}

    def built(name: str) -> dict[str, dict[str, np.ndarray]]:
        path = art / "embeddings" / f"{name}.npy"
        if not path.exists():
            raise RuntimeError(f"{path} missing; run `bsim embed` first")
        return lists(np.load(path))

    def means(scores: dict[str, dict[str, np.ndarray]]) -> dict[str, dict[str, float]]:
        return {li: {g: float(v.mean()) for g, v in scores[li].items()} for li in LISTS}

    reps, seed = ex["bootstrap_reps"], ex["seed"]
    base, ref = built(ex["baseline"]), built(ex["reference"])
    log(
        f"baseline {ex['baseline']} ({ex['metric']}, dev): "
        + "; ".join(
            f"{li} " + ", ".join(f"{g} {v:.4f}" for g, v in s.items())
            for li, s in means(base).items()
        )
        + f"; noise bar {bar:.4f}"
    )

    results: dict[str, Any] = {}
    for name, (kind, spec) in candidates.items():
        entry: dict[str, Any] = {"kind": kind}
        if kind == "trained":
            ccfg = candidate_config(cfg, name, spec)
            out_dir = models / ccfg["train"]["supervised"]["output"]
            if retrain or not (out_dir / TRAIN_META).exists():
                base_model = ccfg["train"]["supervised"]["base"]
                log(f"\n## {name}: training {out_dir.name} from {base_model}")
                run_train_sup(ccfg, log=log, negatives=f"hard_negatives_{name}")
                free_gpu()
            meta = json.loads((out_dir / TRAIN_META).read_text("utf-8"))
            entry |= {
                "model": ccfg["train"]["supervised"]["base"],
                "checkpoint": out_dir.name,
                "best_step": meta.get("best_step"),
                "best_epoch": meta.get("best_epoch"),
                "train_select": meta.get("best"),
                "train_start": (meta.get("start") or {}).get(meta.get("select_metric", "")),
                "peak_vram_gb": meta.get("peak_vram_gb"),
            }
            emb = encode_spec(cfg, {"model": str(out_dir), "pooling": "native"}, texts)
        else:
            log(f"\n## {name}: encoding with {spec['model']}")
            entry |= {"model": spec["model"], "prompt": spec.get("prompt")}
            emb = encode_spec(cfg, spec, texts)
        scores = lists(emb)
        entry["dim"] = int(emb.shape[1])
        entry["scores"] = means(scores)
        entry["gains"] = {
            g: {li: paired_bootstrap(scores[li][g] - base[li][g], reps, seed) for li in LISTS}
            for g in scorer.golds
        }
        if kind == "zero_shot":
            entry["vs_reference"] = {
                g: paired_bootstrap(scores["semantic"][g] - ref["semantic"][g], reps, seed)
                for g in scorer.golds
            }
        for li in LISTS:
            gains = entry["gains"]
            log(f"  {name} {li}: " + "; ".join(f"{g} {_gain(gains[g][li])}" for g in gains))
        results[name] = entry

    path = art / "eval" / "encoder_experiments.json"
    if only and path.exists():  # keep the candidates not rerun
        results = {**json.loads(path.read_text("utf-8")).get("results", {}), **results}
    ok, chosen = adoption({n: r["gains"] for n, r in results.items()}, bar)
    for name, r in results.items():
        r["adopt"] = ok[name]
    out = {
        "split": "dev",
        "metric": ex["metric"],
        "baseline": ex["baseline"],
        "baseline_scores": means(base),
        "reference": ex["reference"],
        "reference_scores": means(ref),
        "queries": {g: len(v) for g, v in base["fused"].items()},
        "noise": ex["noise"],
        "noise_bar": bar,
        "results": results,
        "chosen": chosen,
        "config_hash": config_hash(cfg, "encoder_experiments", "train", "fusion", "retrieval"),
        "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n", "utf-8")
    (art / "eval" / "encoder_experiments.md").write_text(report(out), "utf-8")
    log(f"\nchosen: {out['chosen'] or 'none'}; wrote {path.with_suffix('.md')}")
    return out


def report(out: dict[str, Any]) -> str:
    golds = list(out["queries"])
    zero = {n: r for n, r in out["results"].items() if r["kind"] == "zero_shot"}
    lines = [
        "# Newer encoders (dev split)",
        "",
        f"Baseline `{out['baseline']}`, {out['metric']}: "
        + "; ".join(
            f"{li} " + ", ".join(f"{g} {v:.4f}" for g, v in out["baseline_scores"][li].items())
            for li in LISTS
        )
        + f". Queries: {', '.join(f'{g} {n}' for g, n in out['queries'].items())}. Gains are"
        " paired over queries with a 95 % bootstrap CI. A candidate is adopted only if its fused"
        " Sefaria gain has a CI above 0 and is larger than"
        f" {out['noise_bar']:.4f} (the largest fused gain of `{out['noise']}`, a retrain with"
        " another seed, either way), and its OpenBible and ETCBC CIs reach 0.",
        "",
        md_table(
            ["candidate", "kind", "model", "list", *golds, "adopt"],
            [
                [
                    name,
                    r["kind"],
                    r["model"],
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
    if zero:
        lines += [
            "",
            f"## Zero-shot candidates against `{out['reference']}` (semantic list)",
            "",
            md_table(
                ["candidate", *golds],
                [[n, *(_gain(r["vs_reference"][g]) for g in golds)] for n, r in zero.items()],
            ),
        ]
    return "\n".join(lines) + "\n"
