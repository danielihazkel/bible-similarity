"""`bsim train-simcse`: unsupervised SimCSE adaptation of BEREL (DESIGN.md §7.1).

MultipleNegativesRankingLoss over `(verse, verse)` pairs: both sides pass through the encoder in
train mode, so dropout (`train.simcse.dropout`) is the only noise and the other verses of the batch
are the negatives. Texts are the distinct `text_model` strings (repeated formula verses would be
false negatives of each other); no labels are used, so all verses are trained on.

After each epoch every verse is encoded and scored on dev (`DevEvaluator`, same pipeline as the
eval report); the epoch with the best `train.simcse.select_metric` is saved to
`paths.models/{train.simcse.output}` as a native ST model (Transformer + mean pooling), with
`bsim_train.json` (config, per-epoch dev metrics, chosen epoch). fp32 only.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from transformers import TrainerCallback

from bsim.config import config_hash, resolve_path
from bsim.embed.encoders import encode, mean_pooling_model, model_path, model_revision
from bsim.retrieve.topk import get_device
from bsim.train.dev_eval import DevEvaluator

Log = Callable[[str], None]
Evaluator = Callable[[np.ndarray], dict[str, float]]

TRAIN_META = "bsim_train.json"


def simcse_texts(texts: list[str]) -> list[str]:
    """Distinct texts in order of first appearance."""
    return list(dict.fromkeys(texts))


def build_model(name: str, max_seq_length: int, dropout: float, device: str) -> Any:
    model = mean_pooling_model(
        model_path(name),
        max_seq_length,
        device,
        config_kwargs={"hidden_dropout_prob": dropout, "attention_probs_dropout_prob": dropout},
    )
    if not model.tokenizer.is_fast:
        raise RuntimeError(f"{name}: slow tokenizer loaded; a fast AutoTokenizer is required")
    return model.float()


class EpochSelectCallback(TrainerCallback):
    """Score the model on dev after each epoch; save it to `out_dir` when `metric` improves."""

    def __init__(
        self,
        model: Any,
        texts: list[str],
        evaluate: Evaluator,
        metric: str,
        out_dir: Path,
        batch_size: int,
        log: Log = print,
    ) -> None:
        self.model, self.texts, self.evaluate = model, texts, evaluate
        self.metric, self.out_dir, self.batch_size, self.log = metric, out_dir, batch_size, log
        self.history: list[dict[str, Any]] = []
        self.best_epoch: int | None = None
        self.best: float = -np.inf

    def score(self, epoch: int) -> dict[str, float]:
        m = self.evaluate(encode(self.model, self.texts, self.batch_size))
        if self.metric not in m:
            raise RuntimeError(f"select_metric {self.metric!r} not in {sorted(m)}")
        self.history.append({"epoch": epoch, **m})
        self.log(
            f"  epoch {epoch} dev: "
            + ", ".join(f"{k}={v:.3f}" for k, v in m.items() if k != "queries")
        )
        return m

    def on_epoch_end(self, args: Any, state: Any, control: Any, **kwargs: Any) -> None:
        epoch = round(state.epoch)
        m = self.score(epoch)
        if m[self.metric] > self.best:
            self.best, self.best_epoch = m[self.metric], epoch
            self.model.save(str(self.out_dir))
            self.log(f"  saved epoch {epoch} ({self.metric} {self.best:.3f}) to {self.out_dir}")


def run_train_simcse(cfg: dict[str, Any], log: Log = print) -> dict[str, Any]:
    from datasets import Dataset
    from sentence_transformers import (
        SentenceTransformerTrainer,
        SentenceTransformerTrainingArguments,
    )
    from sentence_transformers.sentence_transformer.losses import MultipleNegativesRankingLoss

    sc, max_len = cfg["train"]["simcse"], cfg["text"]["max_seq_length"]
    evaluate = DevEvaluator(cfg, "dev")
    proc = resolve_path(cfg, "data_processed")
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "text_model"])
    verses = verses.sort_values("verse_id")
    if not (verses.verse_id.to_numpy() == np.arange(len(verses))).all():
        raise RuntimeError("verse_id is not 0..N-1; embedding rows would not match verse ids")
    all_texts = verses.text_model.tolist()
    train_texts = simcse_texts(all_texts)

    device = get_device(cfg["encoders"].get("device", "cuda"))
    models_dir = resolve_path(cfg, "models")
    out_dir, run_dir = models_dir / sc["output"], models_dir / "_runs" / sc["output"]
    log(
        f"simcse: {sc['base']} on {device}, {len(train_texts)} distinct verse texts "
        f"(of {len(all_texts)}), batch {sc['batch_size']}, lr {sc['lr']}, {sc['epochs']} epochs"
    )
    model = build_model(sc["base"], max_len, sc["dropout"], str(device))
    revision = model_revision(model)

    callback = EpochSelectCallback(
        model,
        all_texts,
        evaluate,
        sc["select_metric"],
        out_dir,
        cfg["encoders"]["batch_size"],
        log,
    )
    callback.score(0)  # untrained BEREL mean pooling, for reference (never saved)

    args = SentenceTransformerTrainingArguments(
        output_dir=str(run_dir),
        num_train_epochs=sc["epochs"],
        per_device_train_batch_size=sc["batch_size"],
        learning_rate=sc["lr"],
        warmup_steps=float(sc["warmup_ratio"]),  # transformers v5: a float < 1 is a ratio
        fp16=False,
        bf16=False,
        seed=cfg["seed"],
        data_seed=cfg["seed"],
        batch_sampler="no_duplicates",
        save_strategy="no",
        eval_strategy="no",
        logging_steps=sc["logging_steps"],
        report_to="none",
        use_cpu=device.type == "cpu",
    )
    trainer = SentenceTransformerTrainer(
        model=model,
        args=args,
        train_dataset=Dataset.from_dict({"anchor": train_texts, "positive": train_texts}),
        loss=MultipleNegativesRankingLoss(model),
        callbacks=[callback],
    )
    trainer.train()
    if callback.best_epoch is None:
        raise RuntimeError("no epoch finished; nothing saved")

    meta = {
        "base": sc["base"],
        "base_revision": revision,
        "simcse": sc,
        "max_seq_length": int(max_len),
        "seed": cfg["seed"],
        "n_train_texts": len(train_texts),
        "select_metric": sc["select_metric"],
        "best_epoch": callback.best_epoch,
        "history": callback.history,
        "device": str(device),
        "config_hash": config_hash(cfg, "train", "text", "seed"),
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (out_dir / TRAIN_META).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    log(f"done: best epoch {callback.best_epoch} ({sc['select_metric']} {callback.best:.3f})")
    return meta
