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
- [x] `train/simcse.py` with sentence-transformers trainer, fp32, batch 64, lr 3e-5
- [x] Epoch selection on dev recall@10 → `models/berel-simcse/` (dev recall@10 by epoch: 0.161 raw → 0.176 / **0.181** / 0.179; epoch 2 kept)
- [x] Embed + top-k + eval `berel_simcse` (dev nDCG@10: berel_simcse_csls 0.132, berel_simcse 0.123 vs berel_mean 0.113; recall@50 0.302 vs 0.253; still below bm25_lemma 0.176)

✔ `berel_simcse` beats `berel_mean` on dev nDCG@10 (if not: record the finding in the report and continue with the better one).

## M8 — Supervised contrastive fine-tune (§7.2)
- [x] `train/negatives.py`: BM25 hard negatives (rank 5–50, unlinked, not neighbours, train books only) (9,026 train rows, 24 random fallbacks)
- [x] `train/supervised.py`: CachedMNRL (mini 32, batch 256), lr 2e-5, warmup 10 %, dev evaluator, best checkpoint → `models/berel-sup/` (peak VRAM 3.8 GB)
- [x] Ablation on dev (recall@10 / nDCG@10 at the chosen step): SimCSE init + HN 0.208 / 0.141; SimCSE init, no HN 0.205 / 0.140; **raw BEREL + HN 0.210 / 0.144** → `init_from: base`
- [x] Embed + top-k + eval `berel_sup` (+ CSLS) (dev nDCG@10: berel_sup_csls **0.150**, berel_sup 0.144; recall@50 0.346; still below bm25_lemma 0.176) → `final_systems.semantic: berel_sup_csls`

✔ Training runs within 11 GB VRAM; best semantic system chosen on dev and recorded in config.

## M9 — Fusion & unit-level results (§5.3, §6.2)
- [x] `retrieve/fusion.py`: weighted RRF; tune `w_lex` on dev (grid extended to 2.0; verse dev nDCG@10: w_lex 1.0 → **0.189** vs bm25_lemma 0.176, berel_sup_csls 0.150 → `fusion.w_lex: 1.0`, one weight for all unit types)
- [x] `retrieve/units.py`: mean and BMA aggregation (segment max on GPU) for chapter, pericope, parasha (5 systems × 3 unit types in ~22 s; dev nDCG@10 berel_sup_csls BMA vs mean: chapter 0.156 vs 0.147, pericope 0.098 vs 0.093 → `unit_aggregation: bma`)
- [x] Unit-level lexical (TF-IDF) and fused lists (dev nDCG@10 tfidf / fused: chapter 0.192 / 0.168, pericope 0.112 / 0.114; fusion does not beat TF-IDF on dev at chapter level)
- [x] Unit-level gold (≥ m shared links / unit-level links) + eval (dev: 154 chapter / 348 pericope queries; parasha has no dev/test gold, Torah = train)
- [x] **Single final test-set run** of the chosen lexical / semantic / fused systems → report section "Test" (nDCG@10 lex / sem / fused: verse 0.118 / 0.118 / **0.136**, chapter 0.153 / 0.152 / **0.157**, pericope 0.062 / 0.061 / **0.068**)

✔ Top-k Parquet for 4 unit types × 3 modes; report has dev + final test numbers; BMA vs mean comparison recorded.

## M10 — Results database (§9)
- [x] `store/schema.sql`, `store/db.py`: load books, verses, words, units, members, matches (3 modes × 4 unit types), lemma display forms, meta (4.14M matches, 9,204 lemma forms)
- [x] Indexes; `VACUUM`; size check (241 MB, ~50 s build; `/similar` median 0.53 ms)

✔ `results.sqlite` builds from scratch in one command; row counts match Parquet; a `/similar`-style query takes < 10 ms.

## M11 — API (§10)
- [x] App factory, startup loading (sqlite read-only, mmap embeddings, encoder, surface-BM25 index) (encoder on a background thread; CSLS hubness cached in `artifacts/api/`)
- [x] Endpoints: books, units, unit, similar (with exclude filters), explain, compare, search, meta
- [x] Pydantic response models; CORS for Vite dev (+ `Server-Timing` header)
- [x] TestClient tests on a small fixture DB (`tests/conftest.py`, shared with `test_store`)
- [x] Measured on the real DB: serving after ~12–14 s, encoder ready after ~32 s; CPU `/search` median lexical 8 / semantic 57 / fused 72 ms (max 87 ms); Ps 14:1 → Ps 53:2 rank 1 in all modes

✔ All endpoints covered by tests; `bsim serve` starts in < 30 s; search responds in < 300 ms on CPU.

## M12 — Frontend (§11)
- [x] Vite + React + TS scaffold in `web/`, TanStack Query, react-router, API proxy (Vite 8, React 19, react-router 8; oxlint + vitest)
- [x] Hebrew fonts (Ezra SIL / Noto Serif Hebrew), RTL layout, te'amim/niqqud toggle (Noto bundled via fontsource; Ezra SIL when installed)
- [x] Browse page (book → chapter → verses; parasha & pericope tabs)
- [x] Unit detail + results panel (mode toggle, k, filters, score breakdown bars)
- [x] Shared-lemma highlighting via `/explain`
- [x] Compare page (side-by-side, best-match pairs)
- [x] Search page
- [x] URL state for all views; MAM CC-BY-SA attribution footer
- [x] Production build served by FastAPI (`paths.web_dist`, SPA fallback; JS 318 kB / 100 kB gzip)
- [x] Walkthrough on the real DB (headless Edge): Ps 14:1 → Ps 53:2 at rank 1 in lexical / semantic / fused; II Sam 22 ↔ Ps 18 pairs all 51 verses (BMA 0.902); search "בראשית ברא אלהים" / "ויאמר אלהים יהי אור" → Gen 1:1 / 1:3 at rank 1 in every mode

✔ Manual walkthrough: open Ps 14:1 → Ps 53:2 appears under all modes; compare II Sam 22 ↔ Ps 18 shows aligned verses; free-text search for a phrase returns its verse first.

## M13 — Polish & end-to-end
- [x] `bsim all` runs the full pipeline from a clean `data/` (`bsim/pipeline.py`, 13 stages, `--from/--to/--skip`; test split only when absent; 38 min on the 1080 Ti)
- [x] README quickstart verified on a clean clone (clone → `uv sync` → `bsim all` → `npm ci && npm run build` → `bsim serve`; metrics identical to 3 decimals)
- [x] Final eval report committed as `docs/RESULTS.md` (metrics only, no raw data)
- [x] Update DESIGN decision log with any changes made during implementation (D25, §12 `pipeline` section)

✔ Fresh clone → `uv sync` → `bsim all` → `bsim serve` works end-to-end.

---

## M14 — Known vs undiscovered parallels (roadmap A1)
- [x] `build-db`: flag every stored match that is a Sefaria gold link (`matches.link_level` verse / unit, `link_type`); unit links expanded to verse pairs, mapped to chapters / pericopes / parashot
- [x] `discoveries` table: unordered strong pairs (either direction within top `store.discoveries.max_rank`) with no gold link, verse neighbours dropped (515,782 rows; DB 241 → 303 MB, `/similar` median unchanged at 0.54 ms)
- [x] API: `link` on `/similar` hits, `exclude=known`, paginated `/discoveries` (unit type, mode, book, cross-book)
- [x] Viewer: "Sefaria link" / "Sefaria passage" badge on hits, "Hide Sefaria-linked" filter, Discoveries page (filters + paging in the URL)
- [x] Tests: store (`gold_verse_pairs`, link flags, discoveries), API, vitest (badge, filter, Discoveries paging)

✔ Ps 14:1 → Ps 53:2 is badged as a Sefaria link; unlinked strong pairs such as Ps 115:8 ↔ Ps 135:18, Judg 17:6 ↔ 21:25 and I Kings 17 ↔ II Kings 4 appear on the Discoveries page.

## M15 — Word study and navigation (roadmap C + D)
- [x] `text/morph.py`: OSHB morphology code → Hebrew description per morpheme (Hebrew and Aramaic stems, verb forms, person / gender / number / state)
- [x] `build-db`: `lemma_gloss.n_words / n_verses`, `lemma_verses` concordance table (263,300 rows; DB 307 MB)
- [x] API: `/resolve` (English / OSIS / Hebrew references, prefixes, Hebrew numerals), `/words/{verse_id}`, paginated `/lemma/{lemma}` with per-book counts
- [x] Viewer: click any source word → morphology panel with concordance links; Concordance page (bars per book as a filter, highlighted occurrences, paging); Search offers the referenced verse / chapter ("Gen 1:1", "בראשית א א"); Verses tab shows the chapter's text
- [x] Tests: resolver, morph decoder, endpoints (pytest); word panel, concordance, reference banner (vitest)

✔ "שמואל א יז מט" → I Samuel 17:49; Gen 1:1 word 1 = מילת יחס + שם עצם · נקבה · יחיד · נפרד, lemma ראשית in 49 verses over 19 books.

## M16 — Shared phrases (roadmap A2)
- [x] `analysis/phrases.py` + `bsim phrases` (pipeline stage before build-db): Smith-Waterman over lemma streams of the lexical top-50 pairs, idf × formula-weight scoring, `spread` of each matched sequence (18,163 pairs, 51 s)
- [x] `phrases` table; `/similar` verse hits carry `phrase`; `/phrases/{verse_id}`; paginated `/phrases` leaderboard
- [x] Viewer: phrase badge on hits, "Shared phrases" section on verse pages, Phrases page (book, min length, cross-book, recurring-idiom filters) with matched words highlighted on both sides
- [x] Tests: alignment, candidates, spread (pytest); endpoints; badge / section / leaderboard (vitest)

✔ II Kings 18–19 ↔ Isaiah 36–37 lead the leaderboard; unlinked allusions such as Hos 13:8 ↔ Prov 17:12 appear with their shared words highlighted.

## M17 — Inner-unit structure (roadmap A3)
- [x] `analysis/structure.py`: semantic + lexical verse matrices, inclusio (frame pairs, max-null), chiasm (same-distance Monte Carlo null, pct + z), echoes, Leitworte (G², function-word POS skipped, ×7 / ×10 flags)
- [x] `bsim structure` (pipeline stage before build-db; 4,464 units in ~6 s) → `structure` table; `lemma_gloss.pos`
- [x] API: `/structure/{unit_id}` (on demand, ≤ 200 verses), `/structure` ranking
- [x] Viewer: Structure panel on chapter / pericope / parasha pages (canvas heatmap with mirror pairs, scores, echoes, Leitwort highlighting in the text; `?structure=1`), Structure ranking page
- [x] Tests: analysis functions, endpoints (pytest); panel + ranking (vitest)

✔ Ps 8 inclusio 8:2 ↔ 8:10 at the 100th percentile; Ps 29 Leitwort קול ×7 flagged as a multiple of 7.

## M18 — Cross-encoder reranker (roadmap B1)
- [x] `train/rerank.py`: `bsim train-rerank` (BEREL cross-encoder, BCE, train-book anchors with in-list fused negatives, epoch chosen on dev) and `bsim rerank [--tune]` (RRF blend of cross-encoder and fused ranks, dev grid) → `fused_rerank`
- [x] Dev: alone 0.135 / 0.128 / 0.120 nDCG@10 by epoch; best blend w_ce 0.25 → 0.194 vs fused 0.189; paired bootstrap +0.0042, 95 % CI [−0.0007, +0.0092]
- [x] Decision: not adopted (fused stays the final list); `fused_rerank` reported in the dev eval; test split untouched
- [x] Tests: blend and training-pair rules

✔ Reranker trained and evaluated on dev; the gain is recorded as not significant and the final systems are unchanged.

## M19 — Corpus map (roadmap A4)
- [x] `analysis/corpus_map.py` + `bsim map` (pipeline stage before build-db, ~30 s): t-SNE layout and KMeans clusters of chapters / pericopes / parashot with G² lemma labels; book × book lift of fused cross-book verse pairs, clustered book order, example pairs
- [x] `map_points`, `map_clusters`, `book_affinity`, `book_examples` tables + `meta.book_order`
- [x] API: `/map/{unit_type}`, `/affinity`, `/affinity/{a}/{b}`
- [x] Viewer: Map page (canvas scatter coloured by cluster or section, clickable points, cluster legend as a filter; book affinity heatmap in related / canon order with the strongest pairs of a clicked cell)
- [x] Tests: map functions, endpoints (pytest); Map page (vitest)

✔ Chapter clusters read as genres (wisdom, praise psalms, Tabernacle, sacrifices, genealogies); Ezra–Nehemiah and Haggai–Zechariah have the highest book lift.

## M20 — Structural mode (roadmap A5)
- [x] `lexical/morph.py`: word-shape tokens + n-grams; `bsim lexical` builds `bm25_morph` and `tfidf_morph_{type}`; `bsim topk` / `bsim units` handle them (pipeline lists updated)
- [x] Fourth mode `structural` through `final_systems`, the DB (`matches`, discoveries), the API (`Mode`; search keeps three modes) and the viewer (mode toggle, hint)
- [x] Dev: bm25_morph nDCG@10 0.068; 3-way fusion at best 0.192 vs 0.189 → not fused
- [x] Tests: shape tokens and n-grams, 4-mode store counts, structural `/similar`, search rejects it, search page hides it

✔ Prov 10:1 → antithetic proverbs; Gen 1:3 → the other fiats; Ex 20:13 → Deut 5:17.

## M21 — Stylometry (roadmap A6)
- [x] `analysis/stylometry.py` + `bsim stylometry` (pipeline stage before build-db): MFW + morphology rates, z-scores, Burrows' Delta and clustered book order, chapter PCA with described axes, per-book over / under features
- [x] `stylo_points`, `stylo_delta`, `stylo_features` + `meta.stylometry`; `/stylometry`, `/stylometry/book/{id}`
- [x] Viewer: Style page (chapter scatter with book highlight, axis descriptions, book profile with z bars and nearest books, Delta heatmap via a shared `BookHeatmap`)
- [x] Tests: features, Delta, PCA (pytest); endpoints; Style page (vitest)

✔ Late books (Esther–Chronicles) group together; Isaiah / Jeremiah / Ezekiel are mutual nearest neighbours.

## H1 — Serving and viewer hardening (roadmap Part B/C quick wins)
- [x] `/structure/{unit}` LRU (`serve.structure_cache`) and the corpus lemma total read once
- [x] Surface BM25 index cached under `artifacts/api/` (sidecar pins DB size/mtime and parameters)
- [x] GZip + `Cache-Control` (API max-age, `/meta` no-store, immutable `/assets`); `/compare` cap (`serve.max_compare_verses`)
- [x] Viewer: `UnitPicker` reference box (`/resolve`: `Gen 1:1`, `בראשית א`) with loading / error states
- [x] Viewer: shared DPR-aware `Scatter` (touch-sized hit radius, ←/→ + Enter) for Map and Style; Map affinity reuses `BookHeatmap` (arrow-key cursor + Enter)
- [x] Tests: caches, headers, compare cap (pytest); `UnitPicker`, `BookHeatmap` (vitest)

✔ Real DB: warm startup 1.8 s → 0.13 s (surface index cached); `/structure/c:0:1` 201 ms → 28 ms on repeat; responses gzipped.

## M22 — Parallel sequences (roadmap A7)
- [x] `analysis/sequences.py` + `bsim sequences` (pipeline stage after phrases, ~33 s): same-order chains over the fused verse top-20, within-chapter shuffle null, q-values
- [x] `sequences` table with per-pair gold flags and `n_gold`; `/sequences` (book, cross-book, same-chapter, q, unit filters; paginated) and `/sequences/{id}` (ladder rows with skipped verses, cosine, gold)
- [x] Viewer: Sequences page, side-by-side ladder page, "Runs parallel to" panel on unit pages
- [x] Tests: candidates, chaining rules, shuffle, q-values (pytest); store + endpoints; Sequences / ladder pages (vitest)

✔ Isaiah 36–38 ↔ II Kings 18–20, Ezra 2 ↔ Nehemiah 7, II Sam 22 ↔ Ps 18 and the Tabernacle command / execution chains lead; Genesis 24's retold journey is found (q 0.016).

