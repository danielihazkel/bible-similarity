"""`bsim embed`: encode every verse's `text_model` with a configured encoder (DESIGN.md §5.2).

Encoders are sentence-transformers models named in `encoders.systems`:
    pooling: mean     a plain HF encoder (BEREL) + mean pooling over the last hidden state
    pooling: native   the model's own ST config (BGE-M3: CLS + normalize = its dense vector;
                      later the fine-tuned checkpoints under `models/`)
The tokenizer is always loaded through `AutoTokenizer` (fast); inference is fp32 only.

Writes `artifacts/embeddings/{system}.npy` (float32, L2-normalized, row = verse_id) and
`{system}.meta.json` (model, dim, token stats: verses with [UNK] / truncated, config hash).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import PROJECT_ROOT, config_hash, resolve_path
from bsim.retrieve.topk import get_device

Log = Callable[[str], None]

POOLINGS = ("mean", "native")


def model_path(name: str) -> str:
    """A local checkpoint (relative to the project root) if it exists, else the HF hub id."""
    p = Path(name)
    local = p if p.is_absolute() else PROJECT_ROOT / p
    return str(local) if local.exists() else name


def load_encoder(spec: dict[str, Any], max_seq_length: int, device: str) -> Any:
    """A fp32 SentenceTransformer for an `encoders.systems` entry."""
    from sentence_transformers import SentenceTransformer
    from sentence_transformers.sentence_transformer.modules import Pooling, Transformer

    pooling, name = spec.get("pooling", "native"), model_path(spec["model"])
    if pooling == "mean":
        tf = Transformer(name, max_seq_length=max_seq_length)
        pool = Pooling(tf.get_embedding_dimension(), "mean")
        model = SentenceTransformer(modules=[tf, pool], device=device)
    elif pooling == "native":
        model = SentenceTransformer(name, device=device)
        model.max_seq_length = max_seq_length
    else:
        raise RuntimeError(f"unknown pooling {pooling!r}; choose from {POOLINGS}")
    if not model.tokenizer.is_fast:
        raise RuntimeError(f"{name}: slow tokenizer loaded; a fast AutoTokenizer is required")
    return model.float()


def token_stats(tokenizer: Any, texts: list[str], max_len: int) -> dict[str, int]:
    """[UNK] and truncation counts over untruncated tokenizations (special tokens included)."""
    ids = tokenizer(texts, add_special_tokens=True, truncation=False)["input_ids"]
    unk = tokenizer.unk_token_id
    n_unk = [sum(t == unk for t in row) for row in ids] if unk is not None else [0] * len(ids)
    lengths = [len(row) for row in ids]
    return {
        "n_unk_verses": int(sum(n > 0 for n in n_unk)),
        "n_unk_tokens": int(sum(n_unk)),
        "n_truncated": int(sum(n > max_len for n in lengths)),
        "max_tokens": int(max(lengths, default=0)),
    }


def encode(model: Any, texts: list[str], batch_size: int) -> np.ndarray:
    emb = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    )
    emb = np.asarray(emb, dtype=np.float32)
    if not np.isfinite(emb).all():
        raise RuntimeError("encoder produced non-finite values")
    norms = np.linalg.norm(emb, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-4):
        raise RuntimeError(f"embeddings not L2-normalized (norms {norms.min()}..{norms.max()})")
    return emb


def model_revision(model: Any) -> str | None:
    """HF commit hash of the underlying transformer, when it came from the hub."""
    try:
        first = model[0]
        auto = getattr(first, "auto_model", None) or getattr(first, "model", None)
        return getattr(auto.config, "_commit_hash", None)
    except Exception:
        return None


def run_embed(cfg: dict[str, Any], system: str, log: Log = print) -> np.ndarray:
    enc = cfg["encoders"]
    systems = enc.get("systems", {})
    if system not in systems:
        raise RuntimeError(f"unknown encoder system {system!r}; configured: {sorted(systems)}")
    spec, max_len = systems[system], cfg["text"]["max_seq_length"]

    proc = resolve_path(cfg, "data_processed")
    if not (proc / "verses.parquet").exists():
        raise RuntimeError(f"{proc / 'verses.parquet'} missing; run `bsim build-corpus` first")
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "text_model"])
    verses = verses.sort_values("verse_id")
    if not (verses.verse_id.to_numpy() == np.arange(len(verses))).all():
        raise RuntimeError("verse_id is not 0..N-1; embedding rows would not match verse ids")
    texts = verses.text_model.tolist()

    device = get_device(enc.get("device", "cuda"))
    log(f"{system}: {spec['model']} ({spec.get('pooling', 'native')} pooling) on {device}")
    model = load_encoder(spec, max_len, str(device))
    stats = token_stats(model.tokenizer, texts, max_len)
    log(
        f"  tokens: max {stats['max_tokens']}, {stats['n_unk_verses']} verses with "
        f"{model.tokenizer.unk_token}, {stats['n_truncated']} truncated at {max_len}"
    )
    if stats["n_unk_verses"] or stats["n_truncated"]:
        log("  warning: unknown tokens or truncation; check the tokenizer / max_seq_length")

    emb = encode(model, texts, enc["batch_size"])
    out = resolve_path(cfg, "artifacts") / "embeddings"
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / f"{system}.npy", emb)
    meta = {
        "system": system,
        "model": spec["model"],
        "pooling": spec.get("pooling", "native"),
        "revision": model_revision(model),
        "n": int(emb.shape[0]),
        "dim": int(emb.shape[1]),
        "max_seq_length": int(max_len),
        "device": str(device),
        **stats,
        "config_hash": config_hash(cfg, "encoders", "text"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (out / f"{system}.meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    log(f"  wrote {out / (system + '.npy')}: {emb.shape[0]} x {emb.shape[1]}")
    return emb
