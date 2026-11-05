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
  file), loaded on a background thread too; a lexical search waits for it (a second or two).

`/structure/{unit}` responses are kept in a bounded in-memory LRU (`serve.structure_cache`); they
are deterministic for a given DB. Query embeddings of `/search` are cached the same way
(`serve.search.query_cache`). Connections use a `serve.sqlite_cache_mb` page cache and mmap.
Responses of at least `serve.gzip_min_bytes` are gzipped, and GET `/api` responses carry
`Cache-Control: max-age=serve.api_max_age` and a weak ETag of the build (the DB's build time, the
encoder and the server's start: an answer only changes when one of them does), so a browser's
revalidation is a 304 that skips the handler; the routes whose answers change while the server
runs (`NO_STORE_PATHS`) are `no-store` instead (hashed viewer assets are cached as immutable).

The production viewer build (`paths.web_dist`) is served at `/` when present; any non-`/api` path
without a file falls back to its `index.html` (client-side routes). The build's service worker
(the offline app, DESIGN.md §11.1) and the page are `no-cache`, so a new build is found at once,
and its manifest is served as `application/manifest+json`.

Tests pass a stub `encoder` instead of loading the model.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
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
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from bsim.api import queries
from bsim.api.patterns import WordTable
from bsim.api.search import (
    BackgroundEncoder,
    Encoder,
    OffEncoder,
    StEncoder,
    SurfaceIndex,
    load_hubness,
    load_surface_index,
)
from bsim.api.workbench import DomainTable
from bsim.config import resolve_path
from bsim.retrieve.topk import CSLS_SUFFIX, get_device
from bsim.store.db import connect_readonly

Log = Callable[[str], None]

# GET routes whose answers change while the server runs (your labels and notebook, the encoder's
# state, a unit's label count): `no-store`, never an ETag
NO_STORE_PATHS = ("/api/labels", "/api/notebook", "/api/meta", "/api/dossier/")
NO_STORE = {"Cache-Control": "no-store"}
# the viewer's files a browser must ask for again each time: the page and the service worker
REVALIDATE = {"Cache-Control": "no-cache"}
mimetypes.add_type("application/manifest+json", ".webmanifest")


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


class Deferred:
    """A value built on a daemon thread; reading an attribute waits for it (and raises what the
    build raised). Stands in for the surface index, so lexical search waits a moment at startup
    instead of the whole server."""

    def __init__(self, name: str, build: Callable[[], Any], done: Callable[[Any], None]):
        self._ready = threading.Event()
        self._value: Any = None
        self._error: BaseException | None = None

        def run() -> None:
            try:
                self._value = build()
                done(self._value)
            except Exception as e:  # raised on use
                self._error = e
            finally:
                self._ready.set()

        threading.Thread(target=run, name=name, daemon=True).start()

    def get(self) -> Any:
        self._ready.wait()
        if self._error is not None:
            raise self._error
        return self._value

    def __getattr__(self, name: str) -> Any:
        return getattr(self.get(), name)


@dataclass
class ServeState:
    cfg: dict[str, Any]
    db_path: Path
    meta: dict[str, Any]
    n_verses: int
    emb: np.ndarray | None  # None: `serve.embeddings: false` (a public deploy)
    hubness: np.ndarray | None
    encoder: Encoder
    surface: SurfaceIndex | Deferred
    runtime: dict[str, Any] = field(default_factory=dict)
    structure_cache: LruCache = field(default_factory=lambda: LruCache(0))
    sequence_cache: LruCache = field(default_factory=lambda: LruCache(0))
    query_cache: LruCache = field(default_factory=lambda: LruCache(0))
    dossier_cache: LruCache = field(default_factory=lambda: LruCache(0))
    align_cache: LruCache = field(default_factory=lambda: LruCache(0))
    synopsis_cache: LruCache = field(default_factory=lambda: LruCache(0))
    pattern_cache: LruCache = field(default_factory=lambda: LruCache(0))
    workbench_cache: LruCache = field(default_factory=lambda: LruCache(0))
    _present: dict[str, bool] = field(default_factory=dict)
    _lemma_total: int | None = None
    _roots: queries.RootIndex | None = None
    _verse_books: np.ndarray | None = None
    _book_ids: frozenset[int] | None = None
    _verse_chapters: np.ndarray | None = None
    _pool: queue.SimpleQueue = field(default_factory=queue.SimpleQueue)
    _words: WordTable | None = None
    _words_lock: threading.Lock = field(default_factory=threading.Lock)
    _domains: DomainTable | None = None
    _domains_lock: threading.Lock = field(default_factory=threading.Lock)

    def word_table(self) -> WordTable:
        """Every word's features for pattern search (`api/patterns.py`), built once (a few
        seconds; `serve.patterns.preload` starts it with the server)."""
        if self._words is None:
            with self._words_lock:
                if self._words is None:
                    conn = self.connect()
                    try:
                        self._words = WordTable.load(conn)
                    finally:
                        conn.close()
        return self._words

    def domain_table(self) -> DomainTable:
        """Every word's SDBH domains for the workbench (`api/workbench.py`), in the word table's
        order, read once."""
        if self._domains is None:
            with self._domains_lock:  # not the word table's: the preload may hold that one
                if self._domains is None:
                    conn = self.connect()
                    try:
                        self._domains = DomainTable.load(conn)
                    finally:
                        conn.close()
        return self._domains

    def lemma_total(self, conn: sqlite3.Connection) -> int:
        """Corpus word count over lemmas (`queries.corpus_lemma_total`), read once."""
        if self._lemma_total is None:
            self._lemma_total = queries.corpus_lemma_total(conn)
        return self._lemma_total

    def roots(self, conn: sqlite3.Connection) -> queries.RootIndex:
        """Each lemma's root family and each root's corpus count (`queries.root_index`), read
        once; empty without `bsim roots`."""
        if self._roots is None:
            self._roots = queries.root_index(conn)
        return self._roots

    def present(self, conn: sqlite3.Connection, table: str) -> bool:
        """Whether a table has rows: an optional stage that did not run leaves it empty (read once
        per table; the DB is read-only)."""
        if table not in self._present:
            row = conn.execute(f"SELECT EXISTS (SELECT 1 FROM {table})").fetchone()
            self._present[table] = bool(row[0])
        return self._present[table]

    def connect(self) -> sqlite3.Connection:
        # FastAPI may close a sync dependency on another thread than it opened it on.
        conn = connect_readonly(self.db_path, check_same_thread=False)
        mb = self.cfg["serve"]["sqlite_cache_mb"]
        conn.execute(f"PRAGMA cache_size = -{mb * 1024}")
        conn.execute(f"PRAGMA mmap_size = {mb * 4 << 20}")
        conn.execute("PRAGMA query_only = 1")
        return conn

    @property
    def verse_books(self) -> np.ndarray:
        """book_id of every verse (by verse id), read once."""
        if self._verse_books is None:
            conn = self.connect()
            try:
                rows = conn.execute("SELECT book_id FROM verses ORDER BY verse_id").fetchall()
            finally:
                conn.close()
            self._verse_books = np.array([b for (b,) in rows], dtype=np.int64)
        return self._verse_books

    @property
    def book_ids(self) -> frozenset[int]:
        """The canon's books (a `book=` filter must name one), read once."""
        if self._book_ids is None:
            conn = self.connect()
            try:
                self._book_ids = frozenset(b for (b,) in conn.execute("SELECT book_id FROM books"))
            finally:
                conn.close()
        return self._book_ids

    @property
    def verse_chapters(self) -> np.ndarray:
        """chapter of every verse (by verse id), read once."""
        if self._verse_chapters is None:
            conn = self.connect()
            try:
                rows = conn.execute("SELECT chapter FROM verses ORDER BY verse_id").fetchall()
            finally:
                conn.close()
            self._verse_chapters = np.array([c for (c,) in rows], dtype=np.int64)
        return self._verse_chapters

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
    steps: dict[str, float] = {}

    def step(name: str, since: float) -> float:
        now = time.perf_counter()
        steps[name] = round(now - since, 2)
        return now

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
    if serve["encoder"] and not serve["embeddings"]:
        raise RuntimeError("serve.encoder needs serve.embeddings (semantic search ranks them)")
    emb = None
    if serve["embeddings"]:
        emb_path = art / meta["embeddings"]
        if not emb_path.exists():
            raise RuntimeError(f"{emb_path} missing; run `bsim embed` for the semantic system")
        emb = np.load(emb_path, mmap_mode="r")
        if emb.shape[0] != n:
            raise RuntimeError(f"{emb_path} has {emb.shape[0]} rows, the DB has {n} verses")
        log(f"embeddings {emb_path.name}: {emb.shape[0]} x {emb.shape[1]} (memory-mapped)")
    else:
        log("embeddings off (serve.embeddings): no /compare, no semantic structure")
    t = step("db_and_embeddings", t0)

    # torch is imported for the encoder and its CSLS hubness only: with `serve.encoder: false`
    # the server runs without it (the public image, DEPLOY.md)
    device: Any = "none"
    hub = None
    if encoder is None and not serve["encoder"]:
        encoder = OffEncoder()
        log("query encoder off (serve.encoder): semantic and fused search answer 503")
    if serve["encoder"]:
        device = get_device(serve["device"])
        if encoder is None:
            # Importing sentence-transformers alone takes ~15-25 s: load it while the rest starts
            # and serves; semantic search waits for it.
            base = meta["semantic_system"].removesuffix(CSLS_SUFFIX)
            log(f"loading encoder {meta.get('semantic_encoder')} on {device} in the background")
            encoder = BackgroundEncoder(_encoder_loader(cfg, base, str(device)), log)
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
    t = step("hubness", t)

    s, bm = serve["search"], cfg["lexical"]["bm25"]

    def texts() -> list[str]:
        conn = connect_readonly(db)
        try:
            return [t for (t,) in conn.execute("SELECT text_plain FROM verses ORDER BY verse_id")]
        finally:
            conn.close()

    runtime: dict[str, Any] = {
        "device": str(device),
        "semantic_system": meta["semantic_system"],
        "encoder": meta.get("semantic_encoder"),
        "embeddings_shape": None if emb is None else list(emb.shape),
        "encoder_on": bool(serve["encoder"]),
        "personal": bool(serve["personal"]),
        "csls": hub is not None,
        "surface_terms": None,  # set when the surface index has loaded
        "started_at": time.time(),
    }

    def surface_loaded(index: SurfaceIndex) -> None:
        runtime["surface_terms"] = len(index.terms)
        log(f"surface BM25: {len(index.terms)} terms ({time.perf_counter() - t:.1f} s)")

    surface = Deferred(
        "surface-index",
        lambda: load_surface_index(
            texts, db, art / serve["cache_dir"], bm["k1"], bm["b"], s["min_root_letters"],
            s["bigrams"],
        ),
        surface_loaded,
    )  # fmt: skip
    runtime["startup_s"] = round(time.perf_counter() - t0, 2)
    runtime["startup_steps"] = steps
    parts = ", ".join(f"{k} {v} s" for k, v in steps.items())
    log(f"ready in {runtime['startup_s']:.1f} s ({parts}; surface index loading)")
    state = ServeState(
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
        dossier_cache=LruCache(serve["dossier_cache"]),
        align_cache=LruCache(serve["align"]["cache"]),
        synopsis_cache=LruCache(serve["synopsis"]["cache"]),
        query_cache=LruCache(serve["search"]["query_cache"]),
        pattern_cache=LruCache(serve["patterns"]["cache"]),
        workbench_cache=LruCache(serve["workbench"]["cache"]),
    )
    if serve["patterns"]["preload"]:
        threading.Thread(target=state.word_table, name="word-table", daemon=True).start()
    if cfg["labels"]["queue"]["preload"] and serve["personal"]:
        from bsim.api.label_queue import preload

        threading.Thread(
            target=preload,
            args=(cfg, state.db_path, state.connect),
            name="label-queue",
            daemon=True,
        ).start()
    return state


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
        allow_methods=["GET", "POST", "PUT", "DELETE"],  # writes: /labels and /notebook only
        allow_headers=["*"],
        expose_headers=["Server-Timing", "X-Total-Count", "Retry-After"],
    )

    app.add_middleware(GZipMiddleware, minimum_size=cfg["serve"]["gzip_min_bytes"])
    max_age = cfg["serve"]["api_max_age"]
    serve = app.state.serve
    build = json.dumps([serve.meta.get("built_at"), serve.meta.get("semantic_encoder"),
                        serve.runtime.get("started_at")])  # fmt: skip
    etag = f'W/"{hashlib.sha256(build.encode()).hexdigest()[:16]}"'

    @app.middleware("http")
    async def server_timing(request: Request, call_next):
        t0 = time.perf_counter()
        path = request.url.path
        cacheable = (
            request.method == "GET" and path.startswith("/api/")
            and not path.startswith(NO_STORE_PATHS)
        )  # fmt: skip
        if cacheable and etag in request.headers.get("if-none-match", ""):
            response = Response(status_code=304, headers={"ETag": etag})  # the handler is skipped
        else:
            response = await call_next(request)
        response.headers["Server-Timing"] = f"app;dur={(time.perf_counter() - t0) * 1000:.1f}"
        if request.method == "GET" and response.status_code == 200:
            if path.startswith(NO_STORE_PATHS):
                response.headers.update(NO_STORE)
            elif path.startswith("/api/"):
                response.headers.setdefault("Cache-Control", f"public, max-age={max_age}")
                response.headers["ETag"] = etag
            elif path.startswith("/assets/"):  # content-hashed file names
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    @app.exception_handler(sqlite3.OperationalError)
    async def missing_table(request: Request, exc: sqlite3.OperationalError) -> JSONResponse:
        """A DB built before a stage's table existed: `stage_missing` (as a stage that did not
        run) rather than a bare 500; any other database error stays a 500."""
        msg = str(exc)
        if not msg.startswith("no such table: "):
            log(f"database error on {request.url.path}: {msg}")
            return JSONResponse({"detail": "database error"}, status_code=500)
        table = msg.removeprefix("no such table: ")
        stage = _table_stages().get(table, table)
        detail = {"code": "stage_missing", "stage": stage,
                  "message": f"not in this build (table {table}): run `bsim build-db`"}  # fmt: skip
        return JSONResponse({"detail": detail}, status_code=503)

    app.include_router(router)
    _mount_web(app, resolve_path(cfg, "web_dist"), log)
    return app


def _table_stages() -> dict[str, str]:
    from bsim.api.routes._common import TABLE_STAGES

    return TABLE_STAGES


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
            again = f.name in ("sw.js", "index.html")
            return FileResponse(f, headers=REVALIDATE if again else None)
        return FileResponse(index, headers=REVALIDATE)

    log(f"viewer: {dist}")
