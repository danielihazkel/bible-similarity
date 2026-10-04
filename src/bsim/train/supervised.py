"""`bsim train-sup`: supervised contrastive fine-tune on Sefaria links (DESIGN.md §7.2).

Positives are the train-split verse links (both directions); with `hard_negatives` each row gets
one BM25 hard negative (`train/negatives.py`), giving (anchor, positive, negative) triplets.
CachedMultipleNegativesRankingLoss (`mini_batch_size`) gives the large batch within 11 GB.

The start point is `init_from`: a checkpoint under `paths.models` (default `berel-simcse`) or
`base` (raw `train.supervised.base` + mean pooling). Every `eval_steps` steps and after each epoch,
all verses are encoded and scored on dev (`DevEvaluator`, the eval report's pipeline); the best
`select_metric` checkpoint is saved to `paths.models/{output}` with `bsim_train.json`. fp32 only.
"""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
import torch

from bsim.config import config_hash, resolve_path
from bsim.embed.encoders import load_encoder, model_revision
from bsim.retrieve.topk import get_device
from bsim.train.common import TRAIN_META, BestCheckpointCallback, Log, build_model
from bsim.train.dev_eval import DevEvaluator
from bsim.train.negatives import run_hard_negatives

BASE_INIT = "base"


def with_overrides(
    cfg: dict[str, Any],
    init: str | None = None,
    hard_negatives: bool | None = None,
    output: str | None = None,
) -> dict[str, Any]:
    """A copy of `cfg` with CLI overrides applied to `train.supervised`."""
    cfg = copy.deepcopy(cfg)
    sup = cfg["train"]["supervised"]
    for key, value in (("init_from", init), ("hard_negatives", hard_negatives), ("output", output)):
        if value is not None:
            sup[key] = value
    return cfg


def init_model(cfg: dict[str, Any], device: str) -> tuple[Any, str]:
    sup, max_len = cfg["train"]["supervised"], cfg["text"]["max_seq_length"]
    if sup["init_from"] == BASE_INIT:
        return build_model(sup["base"], max_len, sup["dropout"], device), sup["base"]
    path = resolve_path(cfg, "models") / sup["init_from"]
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim train-simcse` first (or use --init base)")
    return load_encoder({"model": str(path), "pooling": "native"}, max_len, device), str(path)


def train_dataset(cfg: dict[str, Any], texts: list[str], log: Log) -> dict[str, list[str]]:
    sup = cfg["train"]["supervised"]
    if sup["hard_negatives"]:
        neg = run_hard_negatives(cfg, log)
        cols = {
            "anchor": neg.anchor_vid,
            "positive": neg.positive_vid,
            "negative": neg.negative_vid,
        }
    else:
        links = pd.read_parquet(resolve_path(cfg, "data_processed") / "links.parquet")
        train = links[(links.level == "verse") & (links.split == "train")]
        cols = {"anchor": train.src_vid, "positive": train.tgt_vid}
    return {k: [texts[v] for v in vids.to_numpy()] for k, vids in cols.items()}


def run_train_sup(
    cfg: dict[str, Any],
    log: Log = print,
    init: str | None = None,
    hard_negatives: bool | None = None,
    output: str | None = None,
) -> dict[str, Any]:
    from datasets import Dataset
    from sentence_transformers import (
        SentenceTransformerTrainer,
        SentenceTransformerTrainingArguments,
    )
    from sentence_transformers.sentence_transformer.losses import (
        CachedMultipleNegativesRankingLoss,
    )

    cfg = with_overrides(cfg, init, hard_negatives, output)
    sup = cfg["train"]["supervised"]
    evaluate = DevEvaluator(cfg, "dev")
    proc = resolve_path(cfg, "data_processed")
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "text_model"])
    verses = verses.sort_values("verse_id")
    if not (verses.verse_id.to_numpy() == np.arange(len(verses))).all():
        raise RuntimeError("verse_id is not 0..N-1; embedding rows would not match verse ids")
    all_texts = verses.text_model.tolist()
    data = train_dataset(cfg, all_texts, log)
    if not data["anchor"]:
        raise RuntimeError("no train-split verse links; run `bsim build-links` first")

    device = get_device(cfg["encoders"].get("device", "cuda"))
    models_dir = resolve_path(cfg, "models")
    out_dir, run_dir = models_dir / sup["output"], models_dir / "_runs" / sup["output"]
    log(
        f"train-sup: init {sup['init_from']} on {device}, {len(data['anchor'])} train rows "
        f"({'with' if sup['hard_negatives'] else 'without'} hard negatives), batch "
        f"{sup['batch_size']} (mini {sup['mini_batch_size']}), lr {sup['lr']}, "
        f"{sup['epochs']} epochs -> {out_dir}"
    )
    model, init_name = init_model(cfg, str(device))
    revision = model_revision(model)
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)

    callback = BestCheckpointCallback(
        model,
        all_texts,
        evaluate,
        sup["select_metric"],
        out_dir,
        cfg["encoders"]["batch_size"],
        log,
        eval_steps=sup["eval_steps"],
    )
    callback.score(0, 0.0)  # the starting model, for reference (never saved)

    args = SentenceTransformerTrainingArguments(
        output_dir=str(run_dir),
        num_train_epochs=sup["epochs"],
        per_device_train_batch_size=sup["batch_size"],
        learning_rate=sup["lr"],
        warmup_steps=float(sup["warmup_ratio"]),  # transformers v5: a float < 1 is a ratio
        fp16=False,
        bf16=False,
        seed=cfg["seed"],
        data_seed=cfg["seed"],
        batch_sampler="no_duplicates",
        save_strategy="no",
        eval_strategy="no",
        logging_steps=sup["logging_steps"],
        report_to="none",
        use_cpu=device.type == "cpu",
    )
    trainer = SentenceTransformerTrainer(
        model=model,
        args=args,
        train_dataset=Dataset.from_dict(data),
        loss=CachedMultipleNegativesRankingLoss(model, mini_batch_size=sup["mini_batch_size"]),
        callbacks=[callback],
    )
    trainer.train()
    if callback.best_step is None:
        raise RuntimeError("no dev evaluation improved on -inf; nothing saved")

    peak = torch.cuda.max_memory_allocated(device) if device.type == "cuda" else 0
    meta = {
        "init": init_name,
        "init_revision": revision,
        "supervised": sup,
        "max_seq_length": int(cfg["text"]["max_seq_length"]),
        "seed": cfg["seed"],
        "n_train_rows": len(data["anchor"]),
        "columns": list(data),
        "select_metric": sup["select_metric"],
        "start": callback.history[0],
        "best_step": callback.best_step,
        "best_epoch": callback.best_epoch,
        "best": callback.best,
        "history": callback.history,
        "peak_vram_gb": round(peak / 2**30, 2),
        "device": str(device),
        "config_hash": config_hash(cfg, "train", "text", "seed"),
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (out_dir / TRAIN_META).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    log(
        f"done: best step {callback.best_step} (epoch {callback.best_epoch}, "
        f"{sup['select_metric']} {callback.best:.3f}; start "
        f"{callback.history[0][sup['select_metric']]:.3f}), peak VRAM {meta['peak_vram_gb']} GB"
    )
    return meta
