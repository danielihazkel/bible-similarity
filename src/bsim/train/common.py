"""Shared training pieces (DESIGN.md §7): model construction and best-checkpoint selection on dev.

`BestCheckpointCallback` scores the model with a `DevEvaluator` (the same top-k + neighbour filter +
metrics as the eval report) after every epoch and, when `eval_steps` is set, every `eval_steps`
optimizer steps; the model is saved to `out_dir` whenever the selection metric improves.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from transformers import TrainerCallback

from bsim.embed.encoders import encode, mean_pooling_model, model_path

Log = Callable[[str], None]
Evaluator = Callable[[np.ndarray], dict[str, float]]

TRAIN_META = "bsim_train.json"


def build_model(name: str, max_seq_length: int, dropout: float, device: str) -> Any:
    """Raw HF encoder + mean pooling, with hidden + attention dropout set to `dropout`."""
    model = mean_pooling_model(
        model_path(name),
        max_seq_length,
        device,
        config_kwargs={"hidden_dropout_prob": dropout, "attention_probs_dropout_prob": dropout},
    )
    if not model.tokenizer.is_fast:
        raise RuntimeError(f"{name}: slow tokenizer loaded; a fast AutoTokenizer is required")
    return model.float()


class BestCheckpointCallback(TrainerCallback):
    """Score the model on dev after each epoch (and every `eval_steps` steps, if set); save it to
    `out_dir` when `metric` improves."""

    def __init__(
        self,
        model: Any,
        texts: list[str],
        evaluate: Evaluator,
        metric: str,
        out_dir: Path,
        batch_size: int,
        log: Log = print,
        eval_steps: int | None = None,
    ) -> None:
        self.model, self.texts, self.evaluate = model, texts, evaluate
        self.metric, self.out_dir, self.batch_size, self.log = metric, out_dir, batch_size, log
        self.eval_steps = eval_steps
        self.history: list[dict[str, Any]] = []
        self.best_step: int | None = None
        self.best_epoch: float | None = None
        self.best: float = -np.inf
        self._last_step: int | None = None

    def score(self, step: int, epoch: float) -> dict[str, float]:
        m = self.evaluate(encode(self.model, self.texts, self.batch_size))
        if self.metric not in m:
            raise RuntimeError(f"select_metric {self.metric!r} not in {sorted(m)}")
        self._last_step = step
        self.history.append({"step": step, "epoch": round(epoch, 3), **m})
        self.log(
            f"  step {step} (epoch {epoch:.2f}) dev: "
            + ", ".join(f"{k}={v:.3f}" for k, v in m.items() if k != "queries")
        )
        return m

    def _check(self, step: int, epoch: float) -> None:
        if step == self._last_step:
            return
        m = self.score(step, epoch)
        if m[self.metric] > self.best:
            self.best, self.best_step, self.best_epoch = m[self.metric], step, round(epoch, 3)
            self.model.save(str(self.out_dir))
            self.log(f"  saved step {step} ({self.metric} {self.best:.3f}) to {self.out_dir}")

    def on_step_end(self, args: Any, state: Any, control: Any, **kwargs: Any) -> None:
        if self.eval_steps and state.global_step % self.eval_steps == 0:
            self._check(state.global_step, state.epoch)

    def on_epoch_end(self, args: Any, state: Any, control: Any, **kwargs: Any) -> None:
        self._check(state.global_step, state.epoch)
