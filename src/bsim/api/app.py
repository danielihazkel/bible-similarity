"""FastAPI app factory and startup loading (DESIGN.md §10, ARCHITECTURE.md §6).

`create_app(cfg)` loads everything before returning, so `bsim serve` fails fast (exit 1) on a
missing DB or embedding file:
- `results.sqlite`, opened read-only per request (`ServeState.connect`);
- the final semantic system's verse matrix, memory-mapped (`meta.embeddings`), plus its CSLS
  hubness when the system is a `*_csls` one (cached under `paths.artifacts/serve.cache_dir`);
- the final encoder (fp32, `serve.device` with CPU fallback) for `/search`, loaded on a background
  thread (its imports dominate startup): everything else serves at once, semantic / fused search
  waits for it, and a failed load makes those searches 503;
- the surface-form BM25 index for lexical `/search`.

Tests pass a stub `encoder` instead of loading the model.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from bsim.api import queries
from bsim.api.search import (
    BackgroundEncoder,
    Encoder,
    StEncoder,
    SurfaceIndex,
    build_surface_index,
    load_hubness,
)
from bsim.config import resolve_path
from bsim.retrieve.topk import CSLS_SUFFIX, get_device
from bsim.store.db import connect_readonly

Log = Callable[[str], None]


@dataclass
class ServeState:
    cfg: dict[str, Any]
    db_path: Path
    meta: dict[str, Any]
    n_verses: int
    emb: np.ndarray
    hubness: np.ndarray | None
    encoder: Encoder
    surface: SurfaceIndex
    runtime: dict[str, Any] = field(default_factory=dict)

    def connect(self) -> sqlite3.Connection:
        # FastAPI may close a sync dependency on another thread than it opened it on.
        return connect_readonly(self.db_path, check_same_thread=False)


def _encoder_loader(cfg: dict[str, Any], base: str, device: str) -> Callable[[], Encoder]:
    spec = cfg["encoders"]["systems"].get(base)
    if spec is None:
        raise RuntimeError(f"semantic system {base!r} is not in encoders.systems")

    def load() -> Encoder:
        from bsim.embed.encoders import load_encoder

        return StEncoder(load_encoder(spec, cfg["text"]["max_seq_length"], device))

    return load


def load_state(cfg: dict[str, Any], encoder: Encoder | None = None, log: Log = print) -> ServeState:
    t0 = time.perf_counter()
    serve, retrieval = cfg["serve"], cfg["retrieval"]
    db = resolve_path(cfg, "db")
    if not db.exists():
        raise RuntimeError(f"{db} missing; run `bsim build-db` first")
    conn = connect_readonly(db)
    try:
        meta = queries.meta(conn)
        n = queries.n_verses(conn)
        texts = [t for (t,) in conn.execute("SELECT text_plain FROM verses ORDER BY verse_id")]
    finally:
        conn.close()

    art = resolve_path(cfg, "artifacts")
    emb_path = art / meta["embeddings"]
    if not emb_path.exists():
        raise RuntimeError(f"{emb_path} missing; run `bsim embed` for the semantic system first")
    emb = np.load(emb_path, mmap_mode="r")
    if emb.shape[0] != n:
        raise RuntimeError(f"{emb_path} has {emb.shape[0]} rows, the DB has {n} verses")
    device = get_device(serve["device"])
    log(f"embeddings {emb_path.name}: {emb.shape[0]} x {emb.shape[1]} (memory-mapped)")

    if encoder is None:
        # Importing sentence-transformers alone takes ~15-25 s: load it while the rest starts and
        # serves; semantic search waits for it.
        base = meta["semantic_system"].removesuffix(CSLS_SUFFIX)
        log(f"loading encoder {meta.get('semantic_encoder')} on {device} in the background")
        encoder = BackgroundEncoder(_encoder_loader(cfg, base, str(device)), log)

    hub = None
    if meta.get("semantic_csls"):
        hub = load_hubness(
            emb,
            emb_path,
            art / serve["cache_dir"],
            retrieval["csls_neighbors"],
            retrieval["chunk_size"],
            device,
        )
        log(f"CSLS hubness for {len(hub)} verses")

    s, bm = serve["search"], cfg["lexical"]["bm25"]
    surface = build_surface_index(texts, bm["k1"], bm["b"], s["min_root_letters"], s["bigrams"])
    log(f"surface BM25: {len(surface.terms)} terms")

    runtime = {
        "device": str(device),
        "semantic_system": meta["semantic_system"],
        "encoder": meta.get("semantic_encoder"),
        "embeddings_shape": list(emb.shape),
        "csls": hub is not None,
        "surface_terms": len(surface.terms),
        "startup_s": round(time.perf_counter() - t0, 2),
    }
    log(f"ready in {runtime['startup_s']:.1f} s")
    return ServeState(cfg, db, meta, n, emb, hub, encoder, surface, runtime)


def create_app(
    cfg: dict[str, Any],
    *,
    state: ServeState | None = None,
    encoder: Encoder | None = None,
    log: Log = print,
) -> FastAPI:
    from bsim.api.routes import router

    app = FastAPI(title="bible-similarity", version="0.1.0")
    app.state.serve = state or load_state(cfg, encoder=encoder, log=log)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg["serve"]["cors_origins"],
        allow_methods=["GET"],
        allow_headers=["*"],
        expose_headers=["Server-Timing"],
    )

    @app.middleware("http")
    async def server_timing(request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        response.headers["Server-Timing"] = f"app;dur={(time.perf_counter() - t0) * 1000:.1f}"
        return response

    app.include_router(router)
    return app
