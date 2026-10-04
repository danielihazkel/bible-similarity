# Task List — bible-similarity

Build plan in milestones. Each milestone lists its tasks, dependencies and **acceptance criteria (✔)**. Section numbers (§) refer to [DESIGN.md](DESIGN.md).

Dependency graph:
```
M0 → M1 → M2 → M3 ─┐
            └→ M4 ─┼→ M5 → M6 → M7 → M8 → M9 → M10 → M11 → M12 → M13
```

---

## M0 — Project setup
- [x] `git init`, `.gitignore` (data/, models/, artifacts/, .venv/, node_modules/, web/dist/)
- [x] `uv init` → `pyproject.toml` (Python 3.11, package `bsim` under `src/`)
- [x] Configure the PyTorch **cu126** index in `pyproject.toml` (`[[tool.uv.index]]` + `[tool.uv.sources]`), add torch, transformers, sentence-transformers, pandas, pyarrow, numpy, scipy, scikit-learn, lxml, typer, pyyaml, fastapi, uvicorn; dev: pytest, ruff
- [x] `scripts/check_gpu.py`: print torch version, `torch.cuda.is_available()`, device name, capability `(6, 1)`, run a small fp32 matmul on GPU
- [x] `configs/default.yaml` skeleton (§12) and `bsim/config.py` (load + section hashing)
- [x] `bsim/cli.py` Typer skeleton with all commands as stubs (ARCHITECTURE §4)
- [x] ruff config, pytest config, one trivial test

✔ `uv sync` succeeds; `uv run python scripts/check_gpu.py` reports the GTX 1080 Ti with capability 6.1 and no "no kernel image" error; `uv run bsim --help` lists all commands; `uv run pytest` passes.

## M1 — Download sources (§1)
- [x] `data/download.py`: OSHB 39 `wlc/*.xml` at a pinned commit (record SHA)
- [x] MAM JSON for all 39 books from the Sefaria-Export bucket (URL-encode spaces in paths)
- [x] Schemas for the 5 Torah books (parasha `alts`) — and all 39 for book metadata
- [x] all `linksN.csv` files, discovered by listing the bucket (17 files, ~680 MB; streamed, MD5-verified)
- [x] `manifest.json` (url, sha256, bytes, date); skip files already present with matching hash
- [x] Book table in `data/canon.py` (Sefaria name ↔ OSIS name ↔ Hebrew name, section, canon order)

✔ `bsim download` is idempotent; all 39 + 39 + 39 + 17 files present; manifest complete.

## M2 — Corpus build (§2–§4)
- [x] `text/normalize.py` + tests (points, te'amim, maqaf, finals, `/` separators)
- [x] `data/oshb.py`: parse `<w>` (surface, lemma, morph, id), ketiv/qere, `x-pe`/`x-samekh` segs → `words` rows
- [x] `data/sefaria.py`: MAM HTML cleaning → `text_display`, ketiv note, pe/samekh positions
- [x] Verse table with `verse_id` in canon order; per-chapter verse-count assertion OSHB vs MAM
- [x] `data/align.py`: OSHB ↔ MAM word alignment → `words.display_idx`
- [x] `data/units.py`: chapters, parashiyot (from schemas), pericopes (MAM markers, mid-verse breaks snapped, books always break)
- [x] Write `verses/words/units/unit_members.parquet` + `corpus_report.md` (counts, alignment coverage, pe/samekh comparison, longest verse in BEREL tokens)

✔ ~23.2k verses, 929 chapters, 54 parashiyot; every verse in exactly one chapter and one pericope; alignment coverage ≥ 99 %; longest verse ≤ max_seq_length.

## M3 — Gold links & splits (§8.1–8.2)
- [x] Ref parser for Sefaria citations (+ tests for all range forms)
- [x] Filter Tanakh↔Tanakh, expand ranges (positional / Cartesian / unit-level), drop self & ±2, symmetrize, dedupe
- [x] Book-level split 75/10/15 by pair count (seeded, balanced with a per-book share cap) → `splits.json`
- [x] `links_report.md`: totals per split, per book, per connection type
- [x] Leakage test: no train pair touches a dev/test book

✔ `links.parquet` + `splits.json` exist; report shows non-empty dev and test; leakage test passes.

## M4 — Lexical mode (§5.1)
- [x] Lemma token streams (+ bigrams) from `words`
- [x] Sparse BM25 (k1, b from config) with all-pairs via chunked sparse matmul
- [x] `lexical/formulas.py`: frequent n-gram detection (n=3..6, > T verses), down-weighting α; export `formulas.parquet`
- [x] `bm25_surface` baseline
- [x] Unit-level TF-IDF (sublinear) on lemma bags

✔ `formulas.parquet` lists the expected formulas (e.g. *וידבר ה' אל משה לאמר*); top-5 for Ps 14:1 contains Ps 53:2.

## M5 — Retrieval core & evaluation harness (§6.1, §8.3)
- [x] `retrieve/topk.py`: chunked GPU top-k (self excluded, k=50), CPU fallback; writes top-k Parquet
- [x] `retrieve/filters.py`: neighbour/chapter/book filters (shared by eval and API)
- [x] `eval/metrics.py` (recall@k, MRR@10, nDCG@10) + tests against hand-computed values
- [x] `eval/report.py`: system × unit × metric table, worst misses, sanity spot-checks
- [x] Run `bm25_lemma` and `bm25_surface` on dev (nDCG@10 0.176 vs 0.144)

✔ `artifacts/eval/report.md` shows dev metrics for both BM25 systems; `bm25_lemma` ≥ `bm25_surface`.

## M6 — Baseline encoders (§5.2)
- [x] `embed/encoders.py`: BEREL mean pooling (AutoTokenizer!), BGE-M3 dense; batched fp32 inference → `.npy`
- [x] Tokenizer sanity test: no `[UNK]` on sample verses (and none on the whole corpus; 0 truncated at 128)
- [x] `embed/csls.py` + `*_csls` variants
- [x] Top-k + eval for `berel_mean`, `bge_m3` (+ CSLS) (dev nDCG@10: bge_m3_csls 0.135, berel_mean_csls 0.124, bge_m3 0.123, berel_mean 0.113; CSLS helps both, all below bm25_lemma 0.176)

✔ Report includes 4+ new systems on dev.

## M7 — SimCSE (§7.1)
- [ ] `train/simcse.py` with sentence-transformers trainer, fp32, batch 64, lr 3e-5
- [ ] Epoch selection on dev recall@10 → `models/berel-simcse/`
- [ ] Embed + top-k + eval `berel_simcse`

✔ `berel_simcse` beats `berel_mean` on dev nDCG@10 (if not: record the finding in the report and continue with the better one).

## M8 — Supervised contrastive fine-tune (§7.2)
- [ ] `train/negatives.py`: BM25 hard negatives (rank 5–50, unlinked, not neighbours, train books only)
- [ ] `train/supervised.py`: CachedMNRL (mini 32, batch 256), lr 2e-5, warmup 10 %, dev evaluator, best checkpoint → `models/berel-sup/`
- [ ] Ablation on dev: with vs without hard negatives; start from SimCSE vs raw BEREL
- [ ] Embed + top-k + eval `berel_sup` (+ CSLS)

✔ Training runs within 11 GB VRAM; best semantic system chosen on dev and recorded in config.

## M9 — Fusion & unit-level results (§5.3, §6.2)
- [ ] `retrieve/fusion.py`: weighted RRF; tune `w_lex` on dev
- [ ] `retrieve/units.py`: mean and BMA aggregation (segment max on GPU) for chapter, pericope, parasha
- [ ] Unit-level lexical (TF-IDF) and fused lists
- [ ] Unit-level gold (≥ m shared links / unit-level links) + eval
- [ ] **Single final test-set run** of the chosen lexical / semantic / fused systems → report section "Test"

✔ Top-k Parquet for 4 unit types × 3 modes; report has dev + final test numbers; BMA vs mean comparison recorded.

## M10 — Results database (§9)
- [ ] `store/schema.sql`, `store/db.py`: load books, verses, words, units, members, matches (3 modes × 4 unit types), lemma display forms, meta
- [ ] Indexes; `VACUUM`; size check

✔ `results.sqlite` builds from scratch in one command; row counts match Parquet; a `/similar`-style query takes < 10 ms.

## M11 — API (§10)
- [ ] App factory, startup loading (sqlite read-only, mmap embeddings, encoder, surface-BM25 index)
- [ ] Endpoints: books, units, unit, similar (with exclude filters), explain, compare, search, meta
- [ ] Pydantic response models; CORS for Vite dev
- [ ] TestClient tests on a small fixture DB

✔ All endpoints covered by tests; `bsim serve` starts in < 30 s; search responds in < 300 ms on CPU.

## M12 — Frontend (§11)
- [ ] Vite + React + TS scaffold in `web/`, TanStack Query, react-router, API proxy
- [ ] Hebrew fonts (Ezra SIL / Noto Serif Hebrew), RTL layout, te'amim/niqqud toggle
- [ ] Browse page (book → chapter → verses; parasha & pericope tabs)
- [ ] Unit detail + results panel (mode toggle, k, filters, score breakdown bars)
- [ ] Shared-lemma highlighting via `/explain`
- [ ] Compare page (side-by-side, best-match pairs)
- [ ] Search page
- [ ] URL state for all views; MAM CC-BY-SA attribution footer
- [ ] Production build served by FastAPI

✔ Manual walkthrough: open Ps 14:1 → Ps 53:2 appears under all modes; compare II Sam 22 ↔ Ps 18 shows aligned verses; free-text search for a phrase returns its verse first.

## M13 — Polish & end-to-end
- [ ] `bsim all` runs the full pipeline from a clean `data/`
- [ ] README quickstart verified on a clean clone
- [ ] Final eval report committed as `docs/RESULTS.md` (metrics only, no raw data)
- [ ] Update DESIGN decision log with any changes made during implementation

✔ Fresh clone → `uv sync` → `bsim all` → `bsim serve` works end-to-end.
