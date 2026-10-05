"""FastAPI app factory and startup loading (DESIGN.md §10, ARCHITECTURE.md §6).

`create_app(cfg)` loads everything before returning, so `bsim serve` fails fast (exit 1) on a
missing DB or embedding file:
- `results.sqlite`, opened read-only; requests borrow connections from a small pool
  (`ServeState.acquire` / `release`, at most `serve.sqlite_pool` kept idle) so each connection's
  page cache outlives the request;
- the final semantic system's verse matrix, memory-mapped (`meta.embeddings`), plus its CSLS
  hubness when the system is a `*_csls` one (cached under `paths.artifacts/serve.cache_dir`);
- the final encoder (fp32, `serve.device` with CPU fallback) for `/search`, loaded on a background
  thread (its imports dominate startup): everything else serves at once, semantic / fused search
  waits for it, and a failed load makes those searches 503;
- the surface-form BM25 index for lexical `/search` (cached next to the hubness, pinned to the DB
  file).

`/structure/{unit}` responses are kept in a bounded in-memory LRU (`serve.structure_cache`); they
are deterministic for a given DB. Query embeddings of `/search` are cached the same way
(`serve.search.query_cache`). Connections use a `serve.sqlite_cache_mb` page cache and mmap.
Responses of at least `serve.gzip_min_bytes` are gzipped, and GET `/api` responses carry
`Cache-Control: max-age=serve.api_max_age` (hashed viewer assets are cached as immutable).

The production viewer build (`paths.web_dist`) is served at `/` when present; any non-`/api` path
without a file falls back to its `index.html` (client-side routes).

Tests pass a stub `encoder` instead of loading the model.
"""

from __future__ import annotations

import queue
import sqlite3
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from bsim.api import queries
from bsim.api.search import (
    BackgroundEncoder,
    Encoder,
    StEncoder,
    SurfaceIndex,
    load_hubness,
    load_surface_index,
)
from bsim.config import resolve_path
from bsim.retrieve.topk import CSLS_SUFFIX, get_device
from bsim.store.db import connect_readonly

Log = Callable[[str], None]


class LruCache:
    """A small thread-safe LRU (sync handlers run on FastAPI's thread pool)."""

    def __init__(self, size: int):
        self.size = size
        self._items: OrderedDict[Any, Any] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Any) -> Any | None:
        with self._lock:
            if key not in self._items:
                return None
            self._items.move_to_end(key)
            return self._items[key]

    def put(self, key: Any, value: Any) -> None:
        if self.size <= 0:
            return
        with self._lock:
            self._items[key] = value
            self._items.move_to_end(key)
            while len(self._items) > self.size:
                self._items.popitem(last=False)


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
    structure_cache: LruCache = field(default_factory=lambda: LruCache(0))
    sequence_cache: LruCache = field(default_factory=lambda: LruCache(0))
    query_cache: LruCache = field(default_factory=lambda: LruCache(0))
    _lemma_total: int | None = None
    _pool: queue.SimpleQueue = field(default_factory=queue.SimpleQueue)

    def lemma_total(self, conn: sqlite3.Connection) -> int:
        """Corpus word count over lemmas (`queries.corpus_lemma_total`), read once."""
        if self._lemma_total is None:
            self._lemma_total = queries.corpus_lemma_total(conn)
        return self._lemma_total

    def connect(self) -> sqlite3.Connection:
        # FastAPI may close a sync dependency on another thread than it opened it on.
        conn = connect_readonly(self.db_path, check_same_thread=False)
        mb = self.cfg["serve"]["sqlite_cache_mb"]
        conn.execute(f"PRAGMA cache_size = -{mb * 1024}")
        conn.execute(f"PRAGMA mmap_size = {mb * 4 << 20}")
        conn.execute("PRAGMA query_only = 1")
        return conn

    def acquire(self) -> sqlite3.Connection:
        """An idle pooled connection, or a new one."""
        try:
            return self._pool.get_nowait()
        except queue.Empty:
            return self.connect()

    def release(self, conn: sqlite3.Connection) -> None:
        """Return a connection to the pool (closed instead when `serve.sqlite_pool` are idle)."""
        if self._pool.qsize() < self.cfg["serve"]["sqlite_pool"]:
            self._pool.put(conn)
        else:
            conn.close()


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

    def texts() -> list[str]:
        conn = connect_readonly(db)
        try:
            return [t for (t,) in conn.execute("SELECT text_plain FROM verses ORDER BY verse_id")]
        finally:
            conn.close()

    surface = load_surface_index(
        texts,
        db,
        art / serve["cache_dir"],
        bm["k1"],
        bm["b"],
        s["min_root_letters"],
        s["bigrams"],
    )
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
    return ServeState(
        cfg,
        db,
        meta,
        n,
        emb,
        hub,
        encoder,
        surface,
        runtime,
        structure_cache=LruCache(serve["structure_cache"]),
        sequence_cache=LruCache(serve["sequence_cache"]),
        query_cache=LruCache(serve["search"]["query_cache"]),
    )


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
        expose_headers=["Server-Timing", "X-Total-Count", "Retry-After"],
    )

    app.add_middleware(GZipMiddleware, minimum_size=cfg["serve"]["gzip_min_bytes"])
    max_age = cfg["serve"]["api_max_age"]

    @app.middleware("http")
    async def server_timing(request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        response.headers["Server-Timing"] = f"app;dur={(time.perf_counter() - t0) * 1000:.1f}"
        if request.method == "GET" and response.status_code == 200:
            path = request.url.path
            if path.startswith("/api/"):
                response.headers.setdefault("Cache-Control", f"public, max-age={max_age}")
            elif path.startswith("/assets/"):  # content-hashed file names
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    app.include_router(router)
    _mount_web(app, resolve_path(cfg, "web_dist"), log)
    return app


def _mount_web(app: FastAPI, dist: Path, log: Log) -> None:
    """Serve the production viewer build: files under `dist`, `index.html` for client routes."""
    index = dist / "index.html"
    if not index.exists():
        log(f"{dist} missing; run `npm run build` in web/ for the viewer (serving the API only)")
        return
    root = dist.resolve()
    app.mount("/assets", StaticFiles(directory=dist / "assets", check_dir=False), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        f = (root / path).resolve()
        if path and f.is_file() and f.is_relative_to(root):
            return FileResponse(f)
        return FileResponse(index)

    log(f"viewer: {dist}")
