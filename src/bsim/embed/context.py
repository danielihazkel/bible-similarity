"""`bsim embed-context`: verse embeddings that see their neighbours (DESIGN.md §16.21, roadmap A9).

Each verse is encoded together with the `context.window` verses on each side (never crossing
`context.scope`: chapter or book), with the encoder of `context.encoder` (an `encoders.systems`
entry). One forward pass gives two systems:
    {encoder}_ctx    mean of every token of the window (the passage around the verse)
    {encoder}_late   mean of the centre verse's tokens only, contextualised by the window
                     ("late chunking": the verse's own words, read in context)
Both are written like `bsim embed` output (`artifacts/embeddings/{system}.npy`, L2-normalized fp32,
row = verse_id), so `bsim topk --system {system}_csls` and the experiments stage use them as they
are. fp32 only.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.embed.encoders import load_encoder
from bsim.retrieve.topk import get_device

Log = Callable[[str], None]

SCOPES = ("chapter", "book")
VARIANTS = ("ctx", "late")


def load_verses(cfg: dict[str, Any]) -> pd.DataFrame:
    proc = resolve_path(cfg, "data_processed")
    if not (proc / "verses.parquet").exists():
        raise RuntimeError(f"{proc / 'verses.parquet'} missing; run `bsim build-corpus` first")
    v = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "text_model"]
    ).sort_values("verse_id")
    if not (v.verse_id.to_numpy() == np.arange(len(v))).all():
        raise RuntimeError("verse_id is not 0..N-1; embedding rows would not match verse ids")
    return v.reset_index(drop=True)


def windows(texts: list[str], group: np.ndarray, window: int) -> list[tuple[str, int, int]]:
    """Per verse: (window text, centre start char, centre end char). Neighbours come from the
    same `group` (chapter or book key) only."""
    out = []
    n = len(texts)
    for i in range(n):
        lo, hi = i, i
        while lo > 0 and i - lo < window and group[lo - 1] == group[i]:
            lo -= 1
        while hi < n - 1 and hi - i < window and group[hi + 1] == group[i]:
            hi += 1
        before = " ".join(texts[lo:i])
        start = len(before) + (1 if before else 0)
        text = " ".join(texts[lo : hi + 1])
        out.append((text, start, start + len(texts[i])))
    return out


def centre_mask(offsets: np.ndarray, special: np.ndarray, start: int, end: int) -> np.ndarray:
    """Tokens whose characters lie in [start, end) (special tokens excluded)."""
    return (
        ~special
        & (offsets[:, 0] >= start)
        & (offsets[:, 1] <= end)
        & (offsets[:, 1] > offsets[:, 0])
    )


def pooled(hidden: np.ndarray, masks: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Masked mean of `hidden` (batch x tokens x dim) per named mask (batch x tokens), L2-normed."""
    out = {}
    for name, m in masks.items():
        w = m.astype(np.float32)[:, :, None]
        v = (hidden * w).sum(1) / np.maximum(w.sum(1), 1.0)
        out[name] = v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)
    return out


def token_batches(
    model: Any, texts: list[str], max_len: int, batch_size: int
) -> Iterator[tuple[int, np.ndarray, dict[str, np.ndarray]]]:
    """(first row, last hidden state, tokenizer output as numpy) per batch, fp32, no grad."""
    import torch

    tok, tf = model.tokenizer, model[0].auto_model
    device = next(tf.parameters()).device
    for b in range(0, len(texts), batch_size):
        enc = tok(
            texts[b : b + batch_size],
            padding=True,
            truncation=True,
            max_length=max_len,
            return_offsets_mapping=True,
            return_special_tokens_mask=True,
            return_tensors="pt",
        )
        offsets = enc.pop("offset_mapping")
        special = enc.pop("special_tokens_mask")
        with torch.no_grad():
            hidden = tf(**{k: v.to(device) for k, v in enc.items()}).last_hidden_state
        yield (
            b,
            hidden.float().cpu().numpy(),
            {
                "attention_mask": enc["attention_mask"].numpy().astype(bool),
                "offsets": offsets.numpy(),
                "special": special.numpy().astype(bool),
            },
        )


def run_embed_context(cfg: dict[str, Any], log: Log = print) -> dict[str, np.ndarray]:
    cc = cfg["context"]
    systems = cfg["encoders"]["systems"]
    if cc["encoder"] not in systems:
        raise RuntimeError(f"context.encoder {cc['encoder']!r} is not in encoders.systems")
    if cc["scope"] not in SCOPES:
        raise RuntimeError(f"context.scope must be one of {SCOPES}")
    v = load_verses(cfg)
    group = v.book_id.to_numpy() * 1000 + (v.chapter.to_numpy() if cc["scope"] == "chapter" else 0)
    wins = windows(v.text_model.tolist(), group, cc["window"])
    device = get_device(cfg["encoders"].get("device", "cuda"))
    model = load_encoder(systems[cc["encoder"]], cc["max_seq_length"], str(device))
    model.eval()
    lengths = [len(x) for x in model.tokenizer([w[0] for w in wins])["input_ids"]]
    n_trunc = int(sum(n > cc["max_seq_length"] for n in lengths))
    log(
        f"{cc['encoder']}: ±{cc['window']} verses (within the {cc['scope']}) on {device}; "
        f"window tokens max {max(lengths)}, {n_trunc} truncated at {cc['max_seq_length']}"
    )
    order = np.argsort(lengths, kind="stable")  # length-sorted batches pad less
    texts = [wins[i][0] for i in order]
    out: dict[str, np.ndarray] = {}
    parts: dict[str, list[np.ndarray]] = {name: [] for name in VARIANTS}
    empty = 0
    for b, hidden, enc in token_batches(model, texts, cc["max_seq_length"], cc["batch_size"]):
        rows = order[b : b + len(hidden)]
        centre = np.stack(
            [
                centre_mask(enc["offsets"][j], enc["special"][j], wins[r][1], wins[r][2])
                for j, r in enumerate(rows)
            ]
        )
        no_centre = ~centre.any(1)  # the centre was truncated away: fall back to the window
        empty += int(no_centre.sum())
        centre[no_centre] = enc["attention_mask"][no_centre]
        p = pooled(hidden, {"ctx": enc["attention_mask"], "late": centre})
        for name in VARIANTS:
            parts[name].append(p[name])
    art = resolve_path(cfg, "artifacts") / "embeddings"
    art.mkdir(parents=True, exist_ok=True)
    inverse = np.empty_like(order)
    inverse[order] = np.arange(len(order))
    for name in VARIANTS:
        emb = np.concatenate(parts[name])[inverse].astype(np.float32)
        if not np.isfinite(emb).all():
            raise RuntimeError("encoder produced non-finite values")
        system = f"{cc['encoder']}_{name}"
        np.save(art / f"{system}.npy", emb)
        meta = {
            "system": system,
            "model": systems[cc["encoder"]]["model"],
            "pooling": "window mean" if name == "ctx" else "centre-verse mean (late chunking)",
            "window": cc["window"],
            "scope": cc["scope"],
            "n": int(emb.shape[0]),
            "dim": int(emb.shape[1]),
            "max_seq_length": int(cc["max_seq_length"]),
            "n_truncated": n_trunc,
            "n_centre_truncated": empty,
            "device": str(device),
            "config_hash": config_hash(cfg, "context", "encoders"),
            "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        (art / f"{system}.meta.json").write_text(json.dumps(meta, indent=2) + "\n", "utf-8")
        out[name] = emb
        log(f"  wrote {art / (system + '.npy')}: {emb.shape[0]} x {emb.shape[1]}")
    return out
