"""Cross-encoder reranking of the fused verse lists (DESIGN.md §16.3).

`bsim train-rerank`: a BEREL cross-encoder (`[CLS] verse a [SEP] verse b`, one logit) is
fine-tuned with binary cross-entropy on train-split data only. For every train-split anchor verse,
its train links are positives and up to `negatives_per_query` negatives are drawn from the
anchor's own fused top-k (the lists it will rerank), with the hard-negative rules of
`train/negatives.py`: not linked (any split) to the anchor, in a train book, not a neighbour, not
the same text. After each epoch the dev queries' fused lists are reranked and scored like the eval
report (±window neighbours dropped); the best `select_metric` epoch is saved to
`paths.models/{output}`.

`bsim rerank`: scores every (source, candidate) pair of the fused verse lists (top
`rerank.depth`) and combines the cross-encoder rank with the fused rank by RRF,
`w_ce / (rrf_k + ce_rank) + 1 / (rrf_k + fused_rank)` (`w_ce: null` = the cross-encoder alone).
`--tune` scores `rerank.w_ce_grid` on dev and writes `artifacts/eval/rerank_tuning.json`; the list
is written as `artifacts/topk/verse/{rerank.system}.parquet` (fused breakdown columns kept, plus
`ce_score`), so `bsim evaluate` reports it next to the other systems.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.data.canon import BY_SEFARIA
from bsim.eval.metrics import evaluate_system
from bsim.eval.report import gold_pairs, ranked_lists
from bsim.retrieve.filters import apply_filters
from bsim.retrieve.topk import get_device, read_topk, verse_ids
from bsim.train.negatives import linked_sets

Log = Callable[[str], None]
TRAIN_META = "bsim_train.json"


class Corpus:
    """Verse texts, books, chapters, text keys, train-book mask, links and the fused lists."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
        fused = art / "topk" / "verse" / f"{cfg['final_systems']['fused']}.parquet"
        for path, cmd in (
            (proc / "verses.parquet", "build-corpus"),
            (proc / "links.parquet", "build-links"),
            (fused, "fuse"),
        ):
            if not path.exists():
                raise RuntimeError(f"{path} missing; run `bsim {cmd}` first")
        verses = pd.read_parquet(
            proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "text_model"]
        ).sort_values("verse_id")
        self.texts: list[str] = verses.text_model.tolist()
        self.book_id = verses.book_id.to_numpy()
        self.chapter = verses.chapter.to_numpy()
        self.text_key, _ = pd.factorize(verses.text_model)
        splits = json.loads((proc / "splits.json").read_text("utf-8"))
        self.train_book = np.zeros(int(self.book_id.max()) + 1, bool)
        for name, split in splits["books"].items():
            self.train_book[BY_SEFARIA[name].book_id] = split == "train"
        self.links = pd.read_parquet(proc / "links.parquet")
        self.window = cfg["retrieval"]["neighbor_window"]
        depth = cfg["rerank"]["depth"]
        raw = read_topk(fused)
        self.fused = raw[raw["rank"] <= depth].reset_index(drop=True)  # unfiltered, as stored
        self.candidates = apply_filters(
            self.fused, self.book_id, self.chapter, {"neighbors"}, self.window
        )


def training_pairs(corpus: Corpus, n_neg: int, seed: int) -> pd.DataFrame:
    """`a, b, label` rows: train links (label 1) + list negatives per anchor (label 0)."""
    links = corpus.links
    train = links[(links.level == "verse") & (links.split == "train")]
    linked = linked_sets(links)
    pos: dict[int, list[int]] = {}
    for s, t in zip(train.src_vid.to_numpy(), train.tgt_vid.to_numpy(), strict=True):
        pos.setdefault(int(s), []).append(int(t))
    cand = corpus.candidates
    by_src = {int(s): g.tgt.to_numpy() for s, g in cand.groupby("src", sort=False)}
    rng = np.random.default_rng(seed)
    book, key, window = corpus.book_id, corpus.text_key, corpus.window
    rows: list[tuple[int, int, float]] = []
    for a, ps in sorted(pos.items()):
        rows += [(a, p, 1.0) for p in ps]
        bad = linked.get(a, set()) | {a}
        ok = [
            int(c)
            for c in by_src.get(a, ())
            if c not in bad
            and corpus.train_book[book[c]]
            and key[c] != key[a]
            and not (book[c] == book[a] and abs(int(c) - a) <= window)
        ]
        if ok:
            take = rng.choice(len(ok), size=min(n_neg, len(ok)), replace=False)
            rows += [(a, ok[i], 0.0) for i in sorted(take)]
    return pd.DataFrame(rows, columns=["a", "b", "label"])


def score_pairs(
    model: Any, texts: list[str], a: np.ndarray, b: np.ndarray, batch: int
) -> np.ndarray:
    pairs = [(texts[i], texts[j]) for i, j in zip(a.tolist(), b.tolist(), strict=True)]
    out = model.predict(pairs, batch_size=batch, show_progress_bar=False, convert_to_numpy=True)
    return np.asarray(out, dtype=np.float32).reshape(-1)


def combine(df: pd.DataFrame, w_ce: float | None, rrf_k: int) -> pd.DataFrame:
    """Re-rank one list frame (`src, tgt, rank` = fused rank, `ce_score`) per source."""
    out = df.reset_index(drop=True)
    order = out.sort_values(
        ["src", "ce_score", "tgt"], ascending=[True, False, True], kind="stable"
    )
    out["ce_rank"] = 0
    out.loc[order.index, "ce_rank"] = order.groupby("src").cumcount().to_numpy() + 1
    if w_ce is None:
        out["new_score"] = out.ce_score.astype(np.float64)
    else:
        out["new_score"] = w_ce / (rrf_k + out.ce_rank) + 1.0 / (rrf_k + out["rank"])
    out = out.sort_values(["src", "new_score", "tgt"], ascending=[True, False, True], kind="stable")
    out["fused_rank"] = out["rank"]
    out["rank"] = (out.groupby("src").cumcount() + 1).astype(np.int32)
    return out.reset_index(drop=True)


def dev_metrics(
    scored: pd.DataFrame,
    corpus: Corpus,
    gold: dict[int, set[int]],
    cfg: dict[str, Any],
    w_ce: float | None,
) -> dict[str, float]:
    ev = cfg["eval"]
    ranked = combine(scored, w_ce, cfg["rerank"]["rrf_k"])
    ranked = apply_filters(ranked, corpus.book_id, corpus.chapter, {"neighbors"}, corpus.window)
    return evaluate_system(ranked_lists(ranked), gold, ev["ks"], ev["rank_k"])


def _dev_scored(model: Any, corpus: Corpus, gold: dict[int, set[int]], batch: int) -> pd.DataFrame:
    dev = corpus.fused[corpus.fused.src.isin(list(gold))].copy()
    dev["ce_score"] = score_pairs(
        model, corpus.texts, dev.src.to_numpy(), dev.tgt.to_numpy(), batch
    )
    return dev


def run_train_rerank(cfg: dict[str, Any], log: Log = print) -> dict[str, Any]:
    from datasets import Dataset
    from sentence_transformers.cross_encoder import (
        CrossEncoder,
        CrossEncoderTrainer,
        CrossEncoderTrainingArguments,
    )
    from sentence_transformers.cross_encoder.losses import BinaryCrossEntropyLoss
    from transformers import TrainerCallback

    rc = cfg["rerank"]
    corpus = Corpus(cfg)
    gold = gold_pairs(corpus.links, "dev")
    data = training_pairs(corpus, rc["negatives_per_query"], cfg["seed"])
    n_pos = int(data.label.sum())
    device = get_device(cfg["encoders"].get("device", "cuda"))
    out_dir = resolve_path(cfg, "models") / rc["output"]
    run_dir = resolve_path(cfg, "models") / "_runs" / rc["output"]
    log(
        f"train-rerank: {rc['base']} on {device}, {len(data)} pairs ({n_pos} positive), "
        f"batch {rc['batch_size']}, lr {rc['lr']}, {rc['epochs']} epochs -> {out_dir}"
    )
    model = CrossEncoder(rc["base"], num_labels=1, max_length=rc["max_length"], device=str(device))
    if not model.tokenizer.is_fast:
        raise RuntimeError(f"{rc['base']}: slow tokenizer loaded; a fast AutoTokenizer is required")
    model.model.float()
    history: list[dict[str, Any]] = []
    best = {"metric": -np.inf, "epoch": None}
    batch_eval = rc["eval_batch_size"]

    class DevCallback(TrainerCallback):
        def on_epoch_end(self, args: Any, state: Any, control: Any, **kwargs: Any) -> None:
            model.model.eval()
            m = dev_metrics(_dev_scored(model, corpus, gold, batch_eval), corpus, gold, cfg, None)
            model.model.train()
            history.append({"epoch": round(state.epoch, 3), "step": state.global_step, **m})
            log(
                f"  epoch {state.epoch:.2f} dev (cross-encoder alone): "
                + ", ".join(f"{k}={v:.3f}" for k, v in m.items() if k != "queries")
            )
            if m[rc["select_metric"]] > best["metric"]:
                best.update(metric=m[rc["select_metric"]], epoch=round(state.epoch, 3))
                model.save(str(out_dir))
                log(f"  saved epoch {state.epoch:.2f} to {out_dir}")

    texts = corpus.texts
    dataset = Dataset.from_dict(
        {
            "a": [texts[i] for i in data.a],
            "b": [texts[i] for i in data.b],
            "label": data.label.astype(np.float32).tolist(),
        }
    )
    args = CrossEncoderTrainingArguments(
        output_dir=str(run_dir),
        num_train_epochs=rc["epochs"],
        per_device_train_batch_size=rc["batch_size"],
        learning_rate=rc["lr"],
        warmup_steps=float(rc["warmup_ratio"]),
        fp16=False,
        bf16=False,
        seed=cfg["seed"],
        data_seed=cfg["seed"],
        save_strategy="no",
        eval_strategy="no",
        logging_steps=rc["logging_steps"],
        report_to="none",
        use_cpu=device.type == "cpu",
    )
    pos_weight = None
    if rc.get("pos_weight"):
        import torch

        pos_weight = torch.tensor(float(rc["pos_weight"]))
    trainer = CrossEncoderTrainer(
        model=model,
        args=args,
        train_dataset=dataset,
        loss=BinaryCrossEntropyLoss(model, pos_weight=pos_weight),
        callbacks=[DevCallback()],
    )
    t0 = time.perf_counter()
    trainer.train()
    if best["epoch"] is None:
        raise RuntimeError("no dev evaluation ran; nothing saved")
    meta = {
        "base": rc["base"],
        "rerank": rc,
        "n_pairs": len(data),
        "n_positive": n_pos,
        "seed": cfg["seed"],
        "best_epoch": best["epoch"],
        "best": best["metric"],
        "select_metric": rc["select_metric"],
        "history": history,
        "minutes": round((time.perf_counter() - t0) / 60, 1),
        "device": str(device),
        "config_hash": config_hash(cfg, "rerank", "seed", "retrieval"),
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (out_dir / TRAIN_META).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    log(f"done: best epoch {best['epoch']} ({rc['select_metric']} {best['metric']:.3f})")
    return meta


def load_reranker(cfg: dict[str, Any]) -> Any:
    from sentence_transformers.cross_encoder import CrossEncoder

    rc = cfg["rerank"]
    path = resolve_path(cfg, "models") / rc["output"]
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim train-rerank` first")
    device = get_device(cfg["encoders"].get("device", "cuda"))
    model = CrossEncoder(str(path), max_length=rc["max_length"], device=str(device))
    model.model.float().eval()
    return model


def run_rerank(cfg: dict[str, Any], log: Log = print, tune: bool = False) -> Path:
    rc = cfg["rerank"]
    corpus = Corpus(cfg)
    model = load_reranker(cfg)
    df = corpus.fused.copy()
    t0 = time.perf_counter()
    log(f"scoring {len(df)} pairs (fused top {rc['depth']}) with {rc['output']}")
    df["ce_score"] = score_pairs(
        model, corpus.texts, df.src.to_numpy(), df.tgt.to_numpy(), rc["eval_batch_size"]
    )
    log(f"  {time.perf_counter() - t0:.0f} s")
    art = resolve_path(cfg, "artifacts")
    if tune:
        gold = gold_pairs(corpus.links, "dev")
        key = f"ndcg@{cfg['eval']['rank_k']}"
        base = dev_metrics(df.assign(ce_score=-df["rank"].astype(float)), corpus, gold, cfg, None)
        grid = {"fused (no rerank)": base}
        for w in rc["w_ce_grid"]:
            grid["alone" if w is None else str(w)] = dev_metrics(df, corpus, gold, cfg, w)
        for name, m in grid.items():
            log(
                f"  dev w_ce={name}: "
                + ", ".join(f"{k}={v:.3f}" for k, v in m.items() if k != "queries")
            )
        best = max((n for n in grid if n != "fused (no rerank)"), key=lambda n: grid[n][key])
        (art / "eval").mkdir(parents=True, exist_ok=True)
        (art / "eval" / "rerank_tuning.json").write_text(
            json.dumps(
                {
                    "split": "dev",
                    "metric": key,
                    "best": best,
                    "grid": grid,
                    "config_hash": config_hash(cfg, "rerank", "eval", "retrieval"),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        log(f"  best on dev: w_ce={best} ({key} {grid[best][key]:.3f} vs fused {base[key]:.3f})")
    out = combine(df, rc["w_ce"], rc["rrf_k"])
    frame = pd.DataFrame(
        {
            "unit_type": "verse",
            "src_id": verse_ids(out.src.to_numpy()),
            "rank": out["rank"].astype(np.int32),
            "tgt_id": verse_ids(out.tgt.to_numpy()),
            "score": out.new_score.astype(np.float32),
            "lex_score": out.lex_score.astype(np.float32),
            "lex_rank": out.lex_rank.astype("Int32"),
            "sem_score": out.sem_score.astype(np.float32),
            "sem_rank": out.sem_rank.astype("Int32"),
            "ce_score": out.ce_score.astype(np.float32),
            "fused_rank": out.fused_rank.astype(np.int32),
        }
    ).sort_values(["src_id", "rank"], kind="stable")
    path = art / "topk" / "verse" / f"{rc['system']}.parquet"
    frame.to_parquet(path, index=False)
    meta = {
        "system": rc["system"],
        "model": rc["output"],
        "w_ce": rc["w_ce"],
        "depth": rc["depth"],
        "config_hash": config_hash(cfg, "rerank", "fusion", "retrieval"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    log(f"done: {len(frame)} rows -> {path}")
    return path
