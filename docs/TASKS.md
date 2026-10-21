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

## M23 — How parallels differ (roadmap A8)
- [x] `analysis/diffs.py` + `bsim diffs` (pipeline stage after sequences, seconds): word-level Needleman-Wunsch over lemma keys for strong sequences; spelling / form / substitution / added / omitted / moved; loose pairs left out
- [x] `diff_changes` table + `meta.diffs`; `/changes` (grouped, counted, examples; book filters), `/diff` (any two verses); ladder rows carry word marks
- [x] Viewer: Changes page; change marks + legend in the side-by-side sequence view
- [x] Tests: alignment labels, moved, loose filter (pytest); endpoints; Changes page and ladder marks (vitest)

✔ יהוה → אלהים, אל → על, דוד → דויד, אנכי → אני, ממלכות → מלכות and the Chronicler's name forms rise to the top unprompted.

## M24 — Te'amim verse halves and poetic parallelism (roadmap A9)
- [x] `text/accents.py`: cola from etnahta (+ oleh-ve-yored in Psalms / Proverbs / Job, Job's prose frame excepted)
- [x] `analysis/parallelism.py` + `bsim parallelism` (pipeline stage, ~50 s on GPU): cola embeddings, cos / shared / shape / balance, logistic regression on poetic-accent vs narrative / law books; held-out-book AUC and known-poem ranks in the meta
- [x] `parallelism` table + `meta.parallelism`; `/parallelism/{unit}`, `/parallelism` (ranked units + book shares)
- [x] Viewer: verse-halves toggle on unit pages (‖ pauses, ∥ parallel badge); Poetry page
- [x] Tests: accent pauses, features, model checks (pytest); endpoints; unit page halves and Poetry page (vitest)

✔ Held-out AUC 0.85–0.90; Deut 33, Deut 32, Gen 49, 2 Sam 22 and Ex 15 are the top five poems among 435 narrative / law chapters; Hannah's song (1 Sam 2:1–10) and Habakkuk 3 surface unprompted.

## M25 — Wordplay (roadmap A10)
- [x] `analysis/wordplay.py` + `bsim wordplay` (pipeline stage, ~18 s): heard forms (prefix-stripped skeleton + vowel pattern), one-edit sound-alike pairs within 8 words, rarity score, within-chapter shuffle baseline
- [x] `wordplay` table + `meta.wordplay`; `/wordplay` (book, kind, unit filters; paginated)
- [x] Viewer: Wordplay page (both words highlighted, chance baseline), unit-page panel
- [x] Tests: skeleton / relation / vowels / heard forms, neighbour index, window and chapter rules (pytest); endpoint; Wordplay page (vitest)

✔ Shibboleth / sibboleth, mevusah / mevukhah, gopher / kopher, shetsef / qetsef and naneḥim / naneqim lead; requiring the same vowels turned 10k pairs with no excess over chance into 400 with ~120 excess.

## M26 — People and places (roadmap A11)
- [x] `analysis/entities.py` + `bsim entities` (pipeline stage, ~5 s): name lemmas, person / place from context cues, verse co-occurrence links by G²
- [x] `entities`, `entity_mentions`, `entity_links` + `meta.entities`; `/entities`, `/entities/{lemma}`, `/unit-entities/{unit}`
- [x] Viewer: Names page (chips, book strip, ego network, partner list); name chips on unit pages
- [x] Tests: cues, classification, G² and links (pytest); endpoints; Names page (vitest)

✔ 909 people and 333 places told apart without a lexicon; David's, Moses' and Abraham's strongest partners are the expected ones.

## M27 — Where the style changes (roadmap A12)
- [x] `analysis/seams.py` + `bsim seams` (pipeline stage, ~25 s): per-verse stylometry counts, Delta curve at every verse boundary (600 words each side), per-book shuffled-maxima threshold, peaks with their changing features
- [x] `seam_curve`, `seams` + `meta.seams`; `/seams` (a book's curve and seams, or the corpus' strongest)
- [x] Viewer: Style page shift chart and seam list
- [x] Tests: curve, peaks, features (pytest); endpoint; Style page seams (vitest)

✔ Daniel's and Ezra's language switches, Proverbs 22:17, Isaiah 36 / 40, Zechariah 9, Job's frame and Elihu, Ezekiel 40 found without being told where to look.

## M28 — A second gold set (roadmap A13)
- [x] `eval/openbible.py` + `bsim eval-openbible` (pipeline stage after evaluate): OpenBible cross-references (≥ 5 votes), KJV-versification-unsafe chapters dropped, Sefaria split rule, dev only
- [x] Final verse systems scored on OpenBible and Sefaria dev gold side by side; gold overlap reported (`artifacts/eval/openbible.md`)
- [x] Tests: reference parsing / ranges / unsafe chapters, gold construction, file reading (pytest)

✔ 6,318 dev pairs, only 3 % shared with Sefaria; fused > lexical > semantic > structural on both, and the Sefaria-trained encoder drops no more than BM25.

## H2 — Serving and viewer hardening, part 2
- [x] `/search` query-embedding LRU; SQLite page cache, mmap, `query_only` per connection
- [x] `/phrases/{verse}` `limit`; limit / offset edge tests for the newer list endpoints
- [x] `api/routes.py` (1,250 lines) split into `api/routes/` feature routers; shared parameter checks (`check_unit_type` replaces five copies)
- [x] Viewer: lazy page chunks (entry bundle 358 → 235 kB); Search shows the real encoder status from `/api/meta` (polled until ready)
- [x] Viewer: "Export page (CSV)" on the list pages (UTF-8 + BOM)
- [x] Tests: Books / Search / Compare pages, CSV, navigation (vitest)
- [x] End-to-end: `npm run e2e` — Playwright in the installed Edge against `bsim serve` + the real DB: 16 pages load with no console errors at desktop and phone width, both navigation modes, no sideways scroll at 390 px, axe (WCAG 2 A/AA) with no serious violations in light and dark themes
- [x] Accessibility fixes found by axe: links in running text underlined; contrast of the "known" green, the person tag, selected name chips and the pager buttons

✔ Every page verified in a real browser for the first time.

## H3 — Serving and viewer hardening, part 3
- [x] Pooled read-only SQLite connections (`serve.sqlite_pool`), so the page cache outlives a request
- [x] One query instead of one per row: `verse_links` (phrases, affinity examples), `/changes` examples; `/sequences/{id}` cached (`serve.sequence_cache`)
- [x] Encoder state: semantic `/search` answers 503 + `Retry-After` at once while the encoder loads; `/meta` `encoder_error`; Search waits for the encoder and says when it failed
- [x] Parameter checks: `/units/verse` needs `book`; `offset` for `/seams` and `/phrases/{verse}` (`X-Total-Count`); `min_pairs` / `min_tokens` / `min_verses` >= 1; `/affinity/{a}/{b}` 404 for unknown books; 422 messages without config key names
- [x] Viewer: error boundary around every page (a stale lazy chunk reloads once); Unit-page panels show their errors and the real phrase count
- [x] Viewer: Compare marks word changes A → B (`/api/diff`); Sequences / Wordplay honour `unit=` (linked from the Unit page); Evaluation page (`/api/eval`)
- [x] README / DESIGN §10–11 brought up to date
- [x] Tests: pool, fail-fast encoder, parameter checks, paging, caches, `/eval` (pytest); error boundary, panel errors, encoder failure, Compare changes, unit filter, Evaluation page (vitest)

## M29 — Significance across many tests (roadmap A8)
- [x] `analysis/stats.py`: Monte Carlo p, percentile → p, Benjamini–Hochberg q
- [x] `bsim structure`: inclusio / chiasm q per unit type (`structure.*_q`); `/structure` ranking shows q
- [x] Leitworte in sevens: multiples of m vs a count-matched baseline, m = 6…13 as controls (`meta.leitwort_numbers`, note on the Structure page)
- [x] Tests: BH / p helpers, q columns, the sevens check (pytest); Structure page q and note (vitest)

✔ 284 / 300 inclusio frames survive BH, no chiasm does; 7 shows the smallest excess of all divisors 6–13.

## M30 — Acrostics (roadmap A1)
- [x] `analysis/acrostic.py` + `bsim acrostics` (pipeline stage after parallelism): verse and colon first letters, best alphabetic chain per chapter (both פ/ע orders), line-shuffle null with an adaptive number of shuffles, BH q
- [x] `acrostics` table, `/acrostics`, `/acrostics/{unit}`; Acrostics page; acrostic bar with letter marks on chapters
- [x] Validation against the known acrostics (`acrostics.known`)
- [x] Tests: chain DP (vectorised = traceback), blocks / gaps / skipped letters, significance, lines from cola (pytest); page and bar (vitest)

✔ 13 significant chapters, all known acrostics (13 / 14; Nahum 1 missed), nothing else.

## M31 — Systematic rewrites (roadmap A3)
- [x] `bsim diffs` also writes `rewrites.parquet` (recurring substitutions / omissions / additions per book pair, G², BH q) and `profiles.parquet` (change counts, spelling direction)
- [x] `rewrites`, `rewrite_profiles` tables, `/rewrites`, `/rewrite-profiles`; Changes page "Systematic rewrites" view
- [x] Tests: rewrite statistics and profile on a constructed book pair (pytest); rewrites view (vitest)

✔ II Sam → I Chr יהוה → אלהים tops 151 significant rewrites; Chronicles spells fuller than Samuel–Kings.

## M32 — Mirrored and reordered parallels (roadmap A2)
- [x] `find_chains(direction=forward|reverse|mixed)`; `all_chains`: kinds in order, overlap dedup, monotone mixed chains dropped; q per kind against the same kind's shuffle chains; spans stored as min / max, `direction` column
- [x] `/sequences?direction=`; the ladder runs the b side backwards for reverse chains; Sequences page "Order" filter, card and detail wording; the Unit page keeps same-order runs
- [x] Tests: reverse / nested / crossing chains, dedup, frame (pytest); order filter (vitest)

✔ No mirrored or reordered chain beats the shuffle (best q 0.33 / 0.08); the wife–sister stories are found as weak chains only.

## M33 — Network of echoes (roadmap A5)
- [x] `analysis/network.py` + `bsim network` (pipeline stage after map): unit edges from the fused top-10, PageRank, Louvain communities with G² labels, per-community layout
- [x] `network_*` tables, `/network/{type}`, `/network/{type}/{community}`, `/unit-network/{unit}`; Network page; "most echoed" line on unit pages
- [x] Tests: edges, communities, centrality, layout bounds (pytest); API (pytest); Network page (vitest)

✔ 28 chapter / 49 pericope communities, many across books; the Abraham-cycle community holds the wife–sister triad.

## M34 — Finer accents and word pairs (roadmap A7)
- [x] `text/accents.py`: disjunctive hierarchy for prose and poetry, `token_levels`, `clauses`; `parallelism.clauses`; "Finer clauses" on the Unit page
- [x] Bicola across two verses (`next_prob`, ∥↓ badge)
- [x] Word pairs across parallel members (G², BH, ≥ 3 chapters): `word_pairs` table, `/word-pairs`, Poetry page → Word pairs
- [x] Parallelism typing by negation tried and dropped (Prov 10–15 lowest), documented
- [x] Tests: accent levels / clauses, word pairs (pytest); API; clause toggle and word pairs view (vitest)

✔ 683 significant word pairs (צדיק // רשע, יום // שנה, חכמה // בינה, ציון // ירושלם …).

## M35 — Alliteration and rhyme (roadmap A6)
- [x] `analysis/sound.py` + `bsim sound`: phoneme sounds, shape-conditioned alliteration per colon, rhyme runs; `alliteration`, `rhymes` tables, `/alliteration`, `/rhymes`; Wordplay page tabs
- [x] Tests: sounds, prefixes, endings, tails, content words (pytest); API; views (vitest)

✔ 4 significant rhymes (Job 10:8–11 ‑נִי); no alliteration beyond chance, shown as candidates.

## M36 — Action sequences (roadmap A4)
- [x] `analysis/typescenes.py` + `bsim typescenes`: verb-lemma Smith–Waterman between pericopes, verb-order shuffle null, textual parallels flagged; `typescenes` table, `/typescenes`, Action sequences page
- [x] Tests: alignment, candidates, verb sequences (pytest); API; page (vitest)

✔ Dan 3 ↔ 6, Dan 2 ↔ 7, Lev 8 ↔ 9, purity procedures; classic type-scenes not recovered (documented).

## M37 — Retrieval experiments (roadmap A9)
- [x] `embed/context.py` + `bsim embed-context`: ±1-verse window and late-chunked BEREL-sup embeddings (`berel_sup_ctx`, `berel_sup_late`), CSLS top-k
- [x] `retrieve/maxsim.py` + `bsim maxsim`: symmetric token MaxSim over the fused top-50 (BEREL-sup, BEREL), `fused_maxsim`
- [x] `eval/experiments.py` + `bsim retrieval-exp`: dev families vs fused, paired bootstrap (`eval/metrics.py`), 2-fold cross-fitting, OpenBible check; `artifacts/eval/retrieval_experiments.{json,md}`
- [x] Tests: windows, centre tokens, pooling, MaxSim vs brute force, n-way RRF, bootstrap, cross-fitting (pytest)

✔ Not adopted: best cross-fitted gain +0.0032 nDCG@10 (late chunking, CI [−0.0050, +0.0114]); MaxSim lowers the fused list; final systems unchanged (§16.21, D53).

## H4 — Serving and viewer hardening, part 4
- [x] List totals cached per DB file and query (`api.queries.count`); book-column indexes tried and rejected (slower counts)
- [x] `/api/export/{list}.csv`: every row under the list's filters (15 lists, `serve.export_max_rows`); "Export all (CSV)" in the viewer, CSV for Concordance and Structure
- [x] Search: `book` filter and `k` up to 200 (`serve.search.max_k`); `/units/verse?chapter=` and a chapter step in the verse picker
- [x] Pager: page box, `aria-current`, past-the-end recovery on every list
- [x] Accessibility: page titles, focus / scroll reset, skip link, roving tabindex for words, keyboard Names graph and Structure heatmap, reduced motion, cosine as text on the ladder, focus-highlight and new-control contrast
- [x] Usability: j / k between hits, copy link, word changes on verse hits (`marks=changes`)
- [x] Canvas: scatter points drawn once per change with the hover ring on an overlay and a bucket grid for hover; DPR-aware Structure heatmap
- [x] Tests: export, search filters, units per chapter (pytest); pager, empty list, export link, word roving, layout, unit changes / j (vitest); e2e and axe on the new pages

## M38 — Hebrew interface (§11, D54)
Phase 1 (M38a): infrastructure, chrome and core flow
- [x] `web/src/i18n/` catalogs (`en.ts` source, `he.ts` typed against it), `LocaleProvider` / `useT()`, `bsim.locale` in localStorage, `<html lang dir>` set before first paint
- [x] EN / עב toggle in the header; Hebrew is fully RTL (physical CSS properties made logical or RTL-aware)
- [x] Layout, nav, footer, page titles; shared components (pager, status, error boundary, hit / phrase / sequence / wordplay cards, score bars, unit picker, unit filter, CSV export, keypad, lemma chips, word panel, link badge, diff legend)
- [x] Pages: Browse, Book, Unit, Search, Compare, Concordance, 404
- [x] `Verse.ref_he` from the API; unit labels and book names per language (`UnitName`, `lib/names.ts`); `hebrewNumeral` for chapter:verse
- [x] Text no longer parsed from English labels (unit picker chapter, compare partner reference); CSS classes and menu ids no longer derived from display text
- [x] Tests: `ref_he` (pytest); catalog parity, Hebrew plurals and numerals, language toggle and persistence, Browse / Search / Unit in Hebrew (vitest)

Phase 2 (M38b): analysis pages
- [x] Parallels (`i18n/pages/parallels.ts`): Discoveries, Phrases, Sequences / Sequence, Changes + rewrites, Action sequences
- [x] Patterns (`i18n/pages/patterns.ts`): Structure + StructurePanel, Acrostics, Poetry + word pairs, Wordplay + alliteration / rhyme
- [x] Overview (`i18n/pages/overview.ts`): Map, Network, Style + SeamsPanel, Evaluation, Names; Scatter and BookHeatmap
- [x] API `*_label_he` next to the English-only labels: change examples, wordplay pairs, names first / last, seams, alliteration, rhyme
- [x] Charts in the interface language with left-to-right geometry (`dir="ltr"`); seam peaks from chapter / verse, not the English label; About as `AboutEn` / `AboutHe`
- [x] English-only label tables removed from `lib/format.ts` and `lib/diff.ts`; Structure CSV columns keyed separately from their display labels
- [x] Tests: the new label fields (pytest); every page group in Hebrew (vitest); e2e: switch, reload, every page in Hebrew without errors or overflow, axe in Hebrew

✔ Phase 1: the core flow (browse → unit → compare / search / concordance) reads fully in Hebrew and RTL; English is unchanged.
✔ Phase 2: every page reads in Hebrew; 68 / 68 e2e (desktop and phone) including the Hebrew run and its accessibility check.

## H5: CI and generated API types (§13, D55)
- [x] `bsim.fixture`: the pytest fixture DB moved from `tests/conftest.py` into the package, plus a stub query encoder
- [x] `bsim fixture-serve` (API + viewer over the fixture DB, no data, model or GPU) and `bsim openapi` (the API schema)
- [x] `ApiModel` base for the response models: fields with defaults are required in the schema (they are always sent)
- [x] `npm run gen:api` / `check:api`: `src/api/schema.gen.ts` (openapi-typescript) and `drift.gen.ts`, a `tsc` check of every hand-written type against the schema of the same name
- [x] Drift fixed: `SearchResponse.book`, `SequencesResponse.direction`, and always-sent fields typed optional (`SequenceSummary.direction`, `StructureRank.*_q`, `VerseHalves.clauses` / `next_prob`, `leitwort_numbers`)
- [x] `e2e/fixture.spec.ts` (`npm run e2e:fixture`): 28 pages load without errors, overflow or error boxes in English and Hebrew, axe in both, desktop and phone
- [x] Accessibility fixes found by it: underlined links in Compare headings and the seam list, `--sem-ink` for small `--sem` text, a themed unit-picker "Go" button (dark-mode contrast); Compare and Style added to the real-data axe pass
- [x] `.github/workflows/ci.yml`: ruff, pytest, oxlint + tsc, vitest, `check:api`, build, fixture e2e in Chromium
- [x] Tests: `openapi` / `fixture-serve` in the CLI tests

✔ The full check runs without the 1.1 GB of artifacts; the fixture e2e suite passes 64 / 64 locally.

## M39: Word senses and semantic domains (§16.22, D56; roadmap A1)
Phase 1 (M39a): data, tagging, retrieval experiment
- [x] `bsim download --only lexicon`: SDBH (UBS, CC BY-SA 4.0) and OpenScriptures HebrewStrong.xml (CC BY 4.0) at pinned commits
- [x] `bsim lexicon` (`data/lexicon.py`): SDBH word references matched to OSHB morphemes (92.2 % of 288k; positions over lemma parts + the article in `Rd`, ±2 window); 262,588 of 299,516 lemma morphemes tagged with a meaning and its domains; synonym / antonym lemma pairs; Strong's name types. Glosses never stored
- [x] `lexical/domains.py`: `bm25_domain`, `tfidf_domain_{unit}`, `bm25_lemma_domain` (expansion) in `bsim lexical`; `bm25_domain` in `pipeline.lexical_systems`
- [x] `bsim retrieval-exp`: `lexical {system}` families (alone, in place of lexical, third list); results on dev: not adopted (lemma + domain beats lemma, not fused)
- [x] Tests: Strong keys, references, morpheme counting, matching and fallback, relations, readers, domain tokens; download, CLI, pipeline order

Phase 2 (M39b): analyses
- [x] Antithetic / synonymous parallelism from SDBH antonym / synonym pairs and shared domains across the members of parallel verses (`relation`, `relation_pairs`); Prov 10–15 check (69.1 % vs 6.8 %, p 4e-77) and a shuffle null in the meta
- [x] People and places typed from Strong's parts of speech first (2,253 of 2,548 names), context cues for the rest; agreement where both decide 94.8 %
- [x] Tests: line typing (antonyms first, synonyms, domains of different lemmas), the typing check, Strong's name kinds and agreement

Phase 3 (M39c): API and viewer
- [x] DB: `domains`, `domain_verses`, `words.domains`, `parallelism.relation*`, `entities.kind_*` (empty without the lexicon); the `domain` mode (`bm25_domain`, `tfidf_domain`) in `matches`
- [x] API: `/domains`, `/domain/{code}`, `/unit-domains/{unit_id}`; `/words` domains; typed `/parallelism/{unit}`; `/parallelism?sort=antithetic` (`typing_min_parallel`); `Entity.kind_source`
- [x] Viewer: Patterns → Domains (tree, domain concordance), themes on units, domain chips in the word panel, Domains mode, `∥≠` antithetic halves with their pairs, Poetry sorted by antithetic share with the typing check, Names kind source; domain names in English and (top two levels) Hebrew
- [x] SDBH / HebrewLexicon credits in the footer and About
- [x] Tests: domains / themes / words / typed halves / ranking (pytest, fixture with word senses); Domains page, themes, Hebrew names, antithetic badge (vitest); e2e: new pages in both languages, axe (a chip contrast and an About link fixed)

✔ Phase 1: every word carries its attested sense and domains; domains help the lemma list but not the fused one, so the final systems are unchanged.
✔ Phase 2: antithetic parallelism is recovered where D49 failed; names are typed by the lexicon, confirming the cue heuristic.
✔ Phase 3: domains, themes and antithetic lines are browsable in both languages; 72 / 72 fixture and 76 / 76 real-data e2e.

## M40: Senses and uses across the canon (§16.23, D57; roadmap A3)
- [x] `bsim senses` (`analysis/senses.py`): 611 frequent lemmas over six corpus groups; SDBH meanings and k-means clusters of pretrained-BEREL word vectors (subwords mapped to OSHB words by character offsets); MI against a shuffled-group null, BH q; Hebrew collocates and nearest examples per cluster; clusters vs SDBH NMI 0.20 (shuffled 0.03)
- [x] Results: senses shift for 296 of 384 lemmas, uses for 539 of 611; גאל, פקד, עדות, קנה lead; תורה and נפש split into readable uses
- [x] DB `lemma_shifts`, `lemma_senses` (+ `meta.senses`, empty without the stage); API `/shifts`, `/lemma/{lemma}/senses`
- [x] Viewer: Overview → Shifts; *Senses across the canon* on the concordance (share per group, domains, collocates, highlighted examples); English and Hebrew (group names in the catalogs)
- [x] Tests: spans and subword mapping, MI and the shuffle test, collocates, the run on the fixture (pytest); the API on the fixture DB; Shifts page and senses panel (vitest); e2e: new pages, axe

✔ A word's senses and uses can be compared across the canon; the dictionary and the contextual reading agree well above chance; 76 / 76 fixture and 80 / 80 real-data e2e.

## M41: A Late Biblical Hebrew profile (§16.24, D58; roadmap A4)
- [x] `bsim dating` (`analysis/dating.py`): seven features (late words, אנכי, infinitive absolute, את + suffix, directional ה, ואשלחה forms, דויד) per chapter over Hebrew words, shrunk rates; logistic regression of the late books against Genesis–Kings, training chapters scored held out by book; poetic books and poem chapters flagged out of domain; drivers per chapter
- [x] Checks: leave-one-book-out AUC 0.948 (grammar / spelling only 0.895); synoptic test, trained without Samuel, Kings and Chronicles: Chronicles later in 26 / 26 parallels (p 3e-8)
- [x] DB `dating_chapters`, `dating_books` (+ `meta.dating`, empty without the stage); API `/dating`, `/dating/book/{id}`, `/unit-dating/{unit}`; `span_label` shared with the sequences
- [x] Viewer: Overview → Language (book ranges, checks, synoptic gaps, chapters with drivers), profile line on chapter pages; English and Hebrew
- [x] Tests: word flags, shrunk rates, held-out AUC, drivers, the sign test, a run without late books (pytest); the API on the fixture DB; the Language page in both languages (vitest); e2e: new pages, axe

✔ Every chapter has a language profile whose evidence can be read back; the method passes the synoptic test it was not trained on, and its blind spots (post-exilic prophets, poetry, single spellings) are shown, not hidden; 80 / 80 fixture and 82 / 82 real-data e2e (a contrast issue on the selected book fixed).

## M42: Your labels, a third gold set (§16.25, D59; roadmap B4)
- [x] `store/labels.py`: real / not / unsure (+ note, the proposing list) per undirected pair in `paths.labels`, apart from the read-only results DB
- [x] API: `GET` / `PUT /labels`, `DELETE /labels/{a}/{b}` (`no-store`; 403 with `serve.labels_writable: false`), `GET /labels/eval` (per mode: found real / not within `labels.k`, precision, AUC)
- [x] `bsim eval-labels` (`eval/labels.py`): dev-split real verse pairs as gold for the final systems, separation over the same split, overlap with Sefaria and OpenBible
- [x] Viewer: label buttons on Discoveries and on similar-passage hits; Parallels → Your labels (counts, separation per mode, the pairs with notes, CSV); English and Hebrew
- [x] Tests: store, separation, ranks, splits, the API (order, validation, read-only), the CLI run (pytest); the Labels page and the buttons (vitest); e2e: the page in both languages and axe, labelling a hit and clearing it on the fixture server

✔ Pairs the systems propose can be judged where they are shown, and the judgements score every mode, including on pairs neither gold set has; 81 / 81 fixture and 84 / 84 real-data e2e.

## M43: Syntax — clauses, phrases and who speaks (§16.26, D60; roadmap A2)
- [x] `bsim download --only syntax`: 18 BHSA Text-Fabric feature files (ETCBC, CC BY-NC 4.0) at a pinned commit, no glosses
- [x] `bsim syntax` (`data/bhsa.py`): a Text-Fabric reader; BHSA words aligned to OSHB words by consonants (23,206 verses, 22,108 identical); 88,131 clauses and 253,203 phrases with types, functions and text types
- [x] Speakers from the clause-atom link to the introducing clause: explicit subjects (beings by SDBH sense), carried subjects (third person, gender agreement), enclosing quotations; hand check 42 / 50 (explicit 29 / 31, carried 13 / 19)
- [x] `bm25_syntax` (`lexical/syntax.py`) and `bm25_morph_syntax`; `bsim retrieval-exp` structural family (gain vs `bm25_morph`, text-type agreement, overlap): not adopted as fused or structural; top 10 per verse kept as *built the same way*
- [x] DB `clauses`, `syntax_phrases`, `syntax_neighbors`, `speech_{chapters,books}`, `speakers` (+ `meta.syntax`); API `/syntax/{unit}`, `/speech`, `/speech/book/{id}`
- [x] Viewer: Overview → Who speaks (stacked shares, speakers, chapters); *Clauses and speakers* on every passage with *built the same way* on verses; clause types and phrase functions named in English and Hebrew; BHSA credits in the footer and About
- [x] Tests: Text-Fabric reading, alignment, a synthetic BHSA run (speech, explicit speaker, gender check), clause tokens, speech shares, segments, the API on the fixture DB (pytest); Speech page and clause panel (vitest); e2e: new pages in both languages, axe (a link style fixed)

✔ Every clause of the Bible can be read with its structure and, in speech, its speaker; the speech map shows where God, Moses or the narrator speak, with the reliability of each attribution stated; clause shapes add a "built the same way" list but do not beat the existing modes; 91 / 91 fixture and 88 / 88 real-data e2e.

## M44: Who borrowed — the direction of cross-book parallels (§16.27, D61; roadmap A7)
- [x] `bsim borrowing` (`analysis/borrowing.py`): four signs fixed in advance (language features with literature signs, fuller spelling, rare → common substitutions, expansion) over the 43 word-aligned cross-book parallels
- [x] Check on 35 parallels of accepted direction: language 30 / 35, spelling 29 / 31, smoothing 15 / 28, expansion 15 / 33; voting signs chosen by the check and validated leaving each book pair out (30 / 32 right, 3 undecided); the canon-order confound stated
- [x] Results: Nehemiah 7 → Ezra 2, 2 Kgs 20 → Isa 38–39, Exod 29 → Lev 8, Lev 11 → Deut 14; 2 Sam 22 ↔ Ps 18 unclear; Ps 105 ↔ 1 Chr 16 and 2 Kgs 25 ↔ Jer 39 wrong
- [x] DB `borrowing_sequences`, `borrowing_books` (+ `meta.borrowing`); API `/borrowing`, `/borrowing/sequence/{id}`, `/borrowing/between`
- [x] Viewer: Parallels → Who borrowed (check, voting signs, book pairs with each parallel's signs); "Which borrowed?" on parallel sequences and Compare; English and Hebrew
- [x] Tests: each sign, agreement, sign selection and the held-out check (pytest); the API on the fixture DB; the page and the line (vitest); e2e: new pages, axe

✔ Every cross-book parallel carries a direction estimate with the evidence behind it, validated where the answer is known and honest about what that check cannot tell; 97 / 97 fixture and 90 / 90 real-data e2e.

## M43b: Clause shapes as a mode (D62)
- [x] `final_systems.syntax: bm25_syntax`, `unit_syntax: tfidf_syntax` (unit TF-IDF over the clause tokens, `bsim units`); `syntax` in the DB modes, API and viewer ("Clauses" / "פסוקיות"); `store.max_size_mb` 4096 (DB 616 MB)
- [x] Tests: six modes in the fixture DB (matches, discoveries); e2e: the mode on a unit page in both languages

## M45: Speaker voices (§16.28, D63)
- [x] `stylometry.feature_counts` (features per word-level unit; `feature_matrix` is now a wrapper)
- [x] `bsim voices` (`analysis/voices.py`, pipeline stage after stylometry, ~31 s): proper-name speakers (OSHB `Np` in most occurrences, `voices.exclude` peoples) and the divine names as one voice; Delta to the other attributed speech of the same books; within-book clause-label shuffle null (999), BH q; calibration shuffle; explicit-only sensitivity; Delta between voices, the narrator and unattributed speech; feature profiles
- [x] Checks fixed in advance (`voices.checks`): author vs character (David in Samuel / Chronicles, God in Kings / Chronicles, Solomon in Kings / Chronicles), the most distinct speaker of Job (Elihu)
- [x] DB `voice_speakers`, `voice_features`, `voice_pairs` (+ `meta.voices`, empty without the stage); API `/voices`, `/voices/{key}`
- [x] Viewer: Who speaks → Voices (speakers with distinctiveness and q, the checks, Delta heatmap via the generalised `Heatmap`, a speaker's profile with `FeatureBars`, chapters where they speak); English and Hebrew
- [x] Tests: feature counts, clause mapping, keys and proper names, within-group shuffle, a planted speaker found and an unplanted one not, the author check and its verdicts (pytest); the API on the fixture DB; the Voices tab and its empty state (vitest); e2e: the tab in both languages, axe

✔ 23 speakers profiled, 18 distinct at q ≤ 0.05 (calibration shuffle 0 / 23, explicit-only ρ 0.88); David and God sound like the book that narrates them (p 0.001 / 0.045), Solomon does not differ between Kings and Chronicles; Elihu ranks second in Job, after Job (the named expectation fails, reported).

## M46: The unit dossier (§10, D64)
- [x] `/dossier/{unit}` (`api/routes/dossier.py`): one entry per analysis with `computed` (optional stages read from table presence, `ServeState.present`), counts / q / score / speaker, chapter scope for verses; cached (`serve.dossier_cache`) except your labels, read live
- [x] `unit=` on `/phrases`, `/changes`, `/rhymes`, `/discoveries`, `/borrowing`; `/typescenes?unit=` matches any pericope overlapping the unit (was: the pericope itself); CSV export carries the filter
- [x] Indexes for the lookups: `diff_changes (a)`, `(b)`, `discoveries (unit_type, mode, b_id)`, `typescenes (a_unit)`, `(b_unit)`, `seams (verse_id)`
- [x] Viewer: `DossierBar` under the unit heading (findings as links to the filtered lists or panels; "nothing found"; "not computed in this build"); the phrases / wordplay / sequences panels are not fetched when the dossier found none; `?unit=` with `UnitFilter` on Phrases (recurring idioms included), Changes, Discoveries, Who borrowed, Action sequences, alliteration and rhyme
- [x] Tests: dossier of a verse and a chapter (counts equal the filtered lists), live labels, not-computed stages, the new filters and 404s, the export (pytest); the bar in both languages, skipped panels, a dossier failure, the Phrases filter (vitest); e2e: filtered pages, a dossier chip to a filtered list

✔ Every analysis that touches a passage is one click from it, and "nothing here" is told apart from "not run"; a dossier is computed in ~12 ms in-process on the real DB (cached after); 117 / 117 fixture and 100 / 100 real-data e2e.

## M47: Where the text divides (§16.29, D65; proposed A2)
- [x] `bsim segments` (`analysis/segments.py`, pipeline stage after voices, ~25 s): every verse boundary scored by TextTiling depth of lemma (idf) and embedding cohesion across a window, combined as a within-book percentile; window chosen on the dev books (`segments.window_grid`: 4)
- [x] Divisions on the boundaries: MAM and Leningrad (OSHB) open / closed paragraphs, chapter starts, parashot, style seams; within-book shuffle tests per kind (999), contrasts (open vs closed, both traditions vs one, chapters with vs without a paragraph break), a calibration shuffle, seams near divisions, Pk / WindowDiff per book against random segmentations
- [x] Lists: unmarked turns, chapters in running text, quiet paragraph breaks (`turn_min`, `turn_peak`, `cut_max`, `quiet_max`)
- [x] `stats.permute_within` (moved from voices)
- [x] DB `segment_gaps`, `segment_books` (+ `meta.segments`, empty without the stage); API `/segments`, `/segments/gaps?kind&book&unit`, `/segments/book/{id}`; dossier entry `divisions`
- [x] Viewer: Patterns → Divisions (tests table and contrasts, a book's boundary scores by paragraph type with chapter lines and a chapter zoom, the three lists with the verses on either side, `?unit=` from the dossier); English and Hebrew
- [x] Tests: window cosines, depth, scores and ties, Pk / WindowDiff, agreement, group tests and contrasts on planted data, gap labels across book ends, peaks, kinds, lemma weights (pytest); the API and dossier on the fixture DB; the page, its chart, chapter zoom, a unit's list in Hebrew, the empty state, the dossier chip (vitest); e2e: the page in both languages with axe, dossier chip → list

✔ Every kind of division falls at turns of the text more than chance (MAM open 0.650, closed 0.554, parashot 0.771, chapters 0.708; calibration 0.507); open over closed and agreed over single-tradition breaks hold (p 0.001); chapters without a paragraph break are weaker turns (0.616 vs 0.728); 20 chapters in running text led by known disputed divisions (Gen 47:1, Isa 64:1, Hag 2:1, Hos 6:1); `results.sqlite` 654 MB; 125 / 125 fixture (1 skipped by design) and 104 / 104 real-data e2e.

## M48: Written and read — ketiv and qere (§16.30, D66; proposed A3)
- [x] `data.oshb.kq_pairs`: both sides of every ketiv / qere from the raw OSHB, with the read words' position in the verse
- [x] `bsim ketiv` (`analysis/ketiv.py`, pipeline stage after segments, ~8 s): letter classes, grammar from both sides' lemmas and morphology with the differing features, euphemisms (`ketiv.euphemisms`), the written form of an aligned parallel (sequences + diffs alignment)
- [x] Findings: look-alike letters against letter frequencies (with and without ו / י), every letter pair (BH q), fuller written spelling in the late books (books permuted), parallels siding with qere or ketiv, written ־ו read ־יו, spread over the books
- [x] DB `kq_pairs`, `kq_letters`, `kq_books` (+ `meta.ketiv`, empty without the stage); API `/ketiv`, `/ketiv/pairs?cls&grammar&parallel&euphemism&book&unit`; dossier entry `ketiv`
- [x] Viewer: Patterns → Written and read (findings, kinds, books, letters, grammar in words, every pair with its verse and parallel); English and Hebrew
- [x] Tests: the parser (both readings, positions), letter classes, morphology features and grammar, letter pairs and look-alikes, the late-book permutation, parallel readings, position checks (pytest); the API and dossier on the fixture DB; the page, its filters, Hebrew, the empty state, the dossier chip (vitest); e2e: the page in both languages with axe, dossier chip → pair → parallel

✔ 1,260 pairs described; look-alike letters 71 % of one-letter swaps (3.9 % expected), the late books' written spelling fuller (82 % vs 40 %, p 0.006), aligned parallels write the qere 57 : 11; `results.sqlite` 655 MB.

## M49: Explicit citations (§16.31, D67; proposed A4)
- [x] `bsim citations` (`analysis/citations.py`, pipeline stage after ketiv, ~3 s): formula families (`citations.families`: as it is written, the word fulfilled, as commanded) with their allowed sources; BM25 + cosine z-score; resolved when the two signals agree; each family against random verses of the same books (binomial); percentiles of the scores
- [x] Gold check (`citations.gold`, 20 sources named by scholarship): rank-1, top-5 and the precision of "resolved"
- [x] DB `citations`, `citation_books` (+ `meta.citations`, empty without the stage); API `/citations`, `/citations/list?family&resolved&book&unit`; dossier entry `citations` (citing from the unit or resolved into it)
- [x] Viewer: Parallels → Citations (families against random verses, gold, who cites whom, every citation with its source and candidates, Compare); English and Hebrew
- [x] Tests: formula families, allowed sources, ranking and agreement, gold parsing and ranks (pytest); the API (unit as source or target) and the dossier on the fixture DB; the page, its filters, Hebrew, the empty state, the dossier chip (vitest); e2e: the page in both languages with axe, dossier chip → citation → Compare

✔ 116 citations, 41 resolved; only "as commanded" resolves above chance as a family (55 % vs 32 %, p 0.0008), "as it is written" and the fulfilment notices do not; gold 15 / 20 at rank 1, every resolved gold citation right (10 / 10); 141 / 141 fixture and 112 / 112 real-data e2e.

## M50: Rare words over a few verses (§16.32, D68; proposed A5)
- [x] `bsim allusions` (`analysis/allusions.py`, pipeline stage after citations, ~5 s): rare lemmas (Strong's numbers, 2–15 verses, no names, gentilics or Aramaic), three-verse windows of different chapters sharing ≥ 3, idf score, overlap suppression; within-chapter verse-shuffle null (null-ratio q, as §16.7); known = fused top 10 or a sequence
- [x] DB `allusions` (+ `meta.allusions`, empty without the stage); API `/allusions?known&book&unit` with both passages and the shared words marked; dossier entry `allusions`
- [x] Viewer: Phrases → Spread over verses (new pairs by default, the rare words, both passages marked, q, Compare); English and Hebrew
- [x] Tests: rare lemmas (senses merged, names and Aramaic out), windows within a chapter, pairs and suppression (pytest); the API and dossier on the fixture DB; the view, its default, the toggle back to phrases, the dossier chip (vitest); e2e: the view in both languages with axe

✔ 176 pairs, 171 known parallels; nothing new beats the within-chapter shuffle (the 3 at q ≤ 0.05 are known, the best new q 0.82): the five new echoes (Urim and Thummim, wormwood and gall, …) are shown as leads; 145 / 145 fixture and 114 / 114 real-data e2e.

## M51: Chiasm at the small scale (§16.33, D69; proposed A6)
- [x] `bsim mirrors` (`analysis/mirrors.py`, pipeline stage after allusions, ~16 s): mirrored against repeated order of lemmas used twice in a verse (bigrams apart; sign test, chapter-resampled interval, poetry / prose); constituent order of consecutive BHSA clause pairs (genre permuted over chapters, per constituent pair); full mirrors with a per-verse shuffle p and BH q
- [x] DB `mirror_verses`, `mirror_clauses` (+ `meta.mirrors`, empty without the stage); API `/mirrors`, `/mirrors/verses`, `/mirrors/clauses`; dossier entry `mirrors`
- [x] Viewer: Structure → Small scale (both tests, the constituent table, clause pairs with their two parts marked, full mirrors by depth); English and Hebrew
- [x] Tests: order counts (mirrored, spread, bigram, no overlap, thrice), sign test and interval, clause pairs, the chapter permutation (pytest); the API and dossier on the fixture DB; the view, its lists, Hebrew, back to whole passages, the empty state, the dossier chip (vitest); e2e: the view in both languages with axe

✔ Repeated words keep their order more often than they mirror it (2,790 vs 2,099 verses, p 5e-23, poetry too); poetry mirrors its clause constituents more than prose (23.5 % vs 16.7 %, p 0.0003); the 94 full mirrors are leads; 151 / 151 fixture and 118 / 118 real-data e2e.

## M52: ETCBC's parallel passages as a third gold (§16.34, D70; proposed A7)
- [x] `sources.etcbc_parallels` (pinned commit) and the `parallels` download group; `bsim eval-etcbc` (`eval/etcbc.py`, pipeline stage before build-db, ~7 s): Text-Fabric edges with values, BHSA verse nodes to verse ids, undirected pairs without neighbours, formula and list cliques set apart (`etcbc.max_partners`), the Sefaria split rule
- [x] Dev retrieval of the final verse systems against ETCBC and Sefaria, fused recall@10 by similarity band; coverage of all parallels by sequences, phrases and the fused list; strong-sequence pairs ETCBC lists; overlap with Sefaria and OpenBible
- [x] `/eval` → `etcbc`; Evaluation page section (both tables, bands, coverage); English and Hebrew
- [x] Tests: edges with values (implicit sources), gold links (neighbours, split rule, best value), formula cliques, coverage (pytest); `/eval` with and without the file; the Evaluation section (vitest)

✔ 1,973 near-verbatim parallels (13,645 formula pairs apart): lexical nDCG@10 0.853, fused 0.832 on dev; 94 % of all parallels in the fused top 10; 56 % of strong-sequence pairs are ETCBC parallels; only 11 % are Sefaria links; 151 / 151 fixture and 118 / 118 real-data e2e.

## M53: Incremental `bsim all` (§16.35, D71; proposed C2)
- [x] Fix first: `config_hash` takes dotted keys; `sound`, `parallelism`, `senses`, `map`, `network` hash `structure.leitwort_skip_pos`
- [x] `bsim/incremental.py`: `TrackedConfig` (keys read, two levels), code hash over the import closure, an audit hook for files opened, outputs from folder snapshots, content hashes cached by size and mtime; `paths.pipeline_state`, `pipeline.roots`, `pipeline.ignore`
- [x] `pipeline.DEPS` (each stage's upstream stages) with a note for any read it misses; `bsim all --force / --rerun / --dry-run / --adopt`
- [x] `bsim` writes UTF-8 when its output is redirected (a log line with ≤ stopped `senses` under cp1252)
- [x] Tests: tracked keys (dotted, missing, dumped, deep-copied), the import closure, DEPS order, skip / rerun / early cut-off / deleted and hand-edited outputs / dry run / adopt / undeclared reads on toy stages, the CLI flags (pytest)

✔ A second `bsim all` with nothing changed takes 2.3 s; `--rerun mirrors` ran mirrors (27 s) and build-db (3:09; `mirrors.meta.json` carries a build time, so build-db follows) and skipped the other 38 stages: 3 min 42 s, against 38 min for the whole pipeline.

## M54: Shared statistics (§16.14; proposed C3)
- [x] `stats.g2_table` replaces the four copies of the 2 × 2 G² (diffs, parallelism, entities, senses); keyness (structure) and domain over-representation (API) are different two-cell statistics and stay
- [x] `stats.shuffle_within` replaces the copies in sequences and wordplay (allusions imports it from there)
- [x] Found by comparing the rerun with the run before: senses (example draws) and network (layout) depended on set order, so two runs of the same code differed; senses breaks count ties by sense id, network lays out each community from a copy in a fixed node order, and network now gives the same bytes under any `PYTHONHASHSEED`; senses differs only in one list of examples (the uses of דבר nearest their centre, near-identical formula verses whose order is GPU arithmetic)
- [x] Incremental runs hash syntax trees (line endings, comments, layout do not rerun anything); `--adopt` on a stage with a record keeps it
- [x] Tests: `g2_table` against SciPy's log-likelihood test, `shuffle_within` with split groups (pytest); the moved helpers' callers

✔ `bsim all` reran those 24 stages in 13 min 30 s (the other 16 skipped). 65 of the 69 outputs were identical; entities' name links and parallelism's word pairs held the same rows with ties re-sorted (G² equal to the last digit, summed in another order); senses' examples and network's layout also differ between two runs of unchanged code, which led to two fixes (set order fed a seeded draw and a seeded layout).

## M55: Who echoes whom (§16.36, D72; proposed A4b)
- [x] `bsim echoes` (`analysis/echoes.py`, pipeline stage after allusions, ~5 s): the chapter network's cross-book edges plus the chapter pairs of resolved citations and decided borrowing sequences; directed by the first deciding layer (cited, borrowed, then the late-language profile at `echoes.language_gap`); conflicts kept apart
- [x] Checks fixed in advance: language against citations, against the spelling sign, against borrowing (stated as not independent); directions against the canon order; book cycles of the explicit layers
- [x] DB `echo_edges`, `echo_books`, `echo_chapters` (+ `meta.echoes`, empty without the stage); API `/echoes`, `/echoes/list?basis&directed&backward&book&unit`; dossier entry `echoes`
- [x] Viewer: Network → Directions (checks, book to book, chapters drawn on most, every pair with its evidence, against-the-canon filter, Compare); English and Hebrew
- [x] Tests: layer order, language vote, chapter pairs against the canon, cycles, a toy run (pytest); the API and the dossier on the fixture DB; the view, its filters, Hebrew, the empty state, the dossier chip (vitest); e2e: the view in both languages with axe, dossier chip → directions → Compare

✔ 459 of 2,422 pairs directed; language agrees with spelling 23 / 23 (p 2e-7); 50 language directions against the canon (1 Kgs 20, Ezek 44 → Lev 21, the late Writings); the two contradictions are §16.27's known misses; 157 / 157 fixture and 122 / 122 real-data e2e.

## M56: Jump box (§11.1; proposed B2)
- [x] `GET /api/lemmas?q=`: lemmas by Strong's number or Hebrew form (pointing ignored, finals folded, prefix letters dropped when nothing matches), exact first, commonest first
- [x] `components/JumpBox.tsx`: Ctrl+K / ⌘K anywhere or *Jump to…* in the top bar; a passage by reference, a word by form or number, a page by name (the nav list moved to `lib/nav.ts`, shared with the menus), a text search last; a modal combobox with arrows, Enter, Escape and focus return; Enter before the lookups settle looks up at once
- [x] English and Hebrew; phone width without the key hints
- [x] Tests: the lookup by number, pointed form, prefixed form and prefix (pytest); reference, word, page, arrows and wrap, Escape and focus, an Enter that beats the pause, Hebrew (vitest); e2e: Ctrl+K to a verse, a lemma and a page in both languages with axe on the open box (fixture), a chapter and a pointed word on the real DB

✔ 131 / 131 vitest; 161 / 161 fixture and 124 / 124 real-data e2e.

## M57: Findings (§10, §11.1; proposed B3)
- [x] `GET /api/findings`: per analysis the tested claim's deciding numbers (from `meta`) and a verdict at `serve.findings.alpha` (holds / fails / lead); stages not run are left out
- [x] Viewer: `/findings` (top bar, and a link on the home page): claims grouped borne out / not borne out / leads, each a sentence with its numbers and a link to the evidence; sentences branch on the direction of the numbers; English and Hebrew
- [x] Tests: each verdict rule both ways, missing stages, a zero expected count (pytest); grouping, numbers, links, direction-dependent wording in Hebrew, the empty state (vitest); e2e: home → findings → evidence, the page in both languages with axe

✔ Real DB: 8 claims hold (acrostics, divisions, the synoptic test, borrowing held out, "as commanded", voices, mirrored clauses, language against spelling), 2 fail (sevens, chiasm in repeated words), 1 lead (rare-word allusions); 165 / 165 fixture (the accessibility loops' time limit raised for the longer page list) and 126 / 126 real-data e2e; 134 / 134 vitest.

## M58: Parallel sequences across the canon (§11.1; proposed B4)
- [x] `GET /api/sequences/arcs?max_q&direction`: every matching chain at once, strongest first, up to `serve.max_arcs`, with the books' verse spans
- [x] Viewer: Sequences → *Across the canon*: an arc per chain over the books in canon order (right to left in Hebrew), width by verse pairs, colour between / within books; the list's filters; a chosen book brings out its arcs; every arc a link to its chain; English and Hebrew
- [x] Tests: the endpoint, its filters, the cap and bad parameters (pytest); arcs, links, drawing order, labels, filters, highlight, the view switch, right to left in Hebrew (vitest); e2e: keyboard from an arc to its chain, the view in both languages with axe

✔ Real DB: 78 strong chains (43 between books), 1,228 in the same order, all 3,615 capped at the 2,000 strongest; 137 / 137 vitest, 171 / 171 fixture and 130 / 130 real-data e2e (the jump-box tests now find the box's field inside its dialog: the unit page has a combobox of its own).

## M59: One paged list (§11.1; proposed B6)
- [x] `PagedList` (`components/Pager.tsx`): the loading / error / empty / past-the-end states, summary line, stale marker and pager of a list page in one place
- [x] 21 lists in 19 files moved to it (20 by a one-off script that rewrote only blocks matching the old skeleton exactly, Sequences by hand); concordance, domain verses and rare-word pairs keep their own states (their header comes from the same response)
- [x] Tests: each state, past the end, stale, paging, a single page (vitest); every list page's existing tests unchanged

✔ 141 / 141 vitest; 171 / 171 fixture and 130 / 130 real-data e2e.

## M60: Meter — stresses per line and the falling lament line (§16.37, D73; proposed A1)
- [x] `bsim meter` (`analysis/meter.py`, pipeline stage after mirrors, ~5 s): stresses from the accents (a word not ending in maqaf), lines = the largest spans of the accent dichotomy (strongest pause, the first of equals) of at most `max_stresses` stresses, split at their own main pause into `a:b`; net fall per chapter (falling − rising share of lines of 4–7 stresses)
- [x] Test fixed in advance: Lam 1–4 against poetry under the same prose accents (top quarter of prose-accented chapters by parallel-halves probability) by drawing chapters; against Psalms / Proverbs / Job; a grid of line lengths; Lam 5 as control; chapters naming קינה (H7015) tested the same way
- [x] DB `meter_lines`, `meter_chapters` (+ `meta.meter`, empty without the stage); API `/meter?group&book`, `/meter/{unit}`; dossier entry `meter` (`serve.dossier.meter_pct`); findings `meter` and `laments`; CSV export `meter`
- [x] Viewer: Poetry → Meter (the test, control, line lengths, commonest lines, chapters naming a lament, ranking by group and book); *Stresses* next to the verse halves on unit pages (`a:b` per line, line ends marked, the chapter's net fall); English and Hebrew
- [x] Tests: stresses, the dichotomy and its ties, lines and maqaf, chapter rates, the group test, the API, dossier, findings and DB on the fixture (pytest); the view, its filter, Hebrew, the empty state, the unit-page toggle, the dossier chip, the findings (vitest); e2e: the view and the unit toggle in both languages with axe, dossier chip → stresses

✔ Lamentations 1–4 fall: net fall 0.39 against 0.17 for poetry under the same accents (p 0.008) and 0.14 for Psalms, Proverbs and Job (p 0.001), at every line length tried (p ≤ 0.011); 3:2 is Lamentations' commonest line; Lam 5 at the 74th percentile; chapters naming קינה not borne out (p 0.26), though Ezek 19 and 27 fall like Lamentations; 496 pytest, 146 / 146 vitest, 179 / 179 fixture (1 skipped by design) and 134 / 134 real-data e2e.

## M61: Root families (§16.38, D74; proposed A2)
- [x] `bsim roots` (`analysis/roots.py`, pipeline stage after meter, ~35 s): Strong's derivations followed at most `max_depth` links, kept where the word is the root's strong radicals in a Hebrew shape; names, Aramaic, patronymics, the divine names and `exclude` out
- [x] Words of one root side by side (cognate verb + noun, other, infinitive absolute) against content words permuted within chapters; per book counts
- [x] Leitworte by root per chapter; check fixed in advance on eight named Leitworte; hidden key roots (two or more words, none a Leitwort alone)
- [x] DB `lemma_roots`, `root_pairs`, `root_books`, `root_leitworte` (+ `meta.roots`); API `/roots`, `/roots/pairs`, `/roots/hidden`, `/root/{root}`, `root_leitworte` on `/structure`, `roots` on `/words`; dossier `roots`; findings `cognate`, `root_leitworte`; CSV `root-pairs`, `hidden-roots`
- [x] Viewer: Patterns → Roots (side by side, key roots), the root page, a root chip in the word panel, "By root" chips in the structure panel; English and Hebrew
- [x] Tests: radicals and shapes, derivations, families (depth, names, exclude), tokens and pairs, the vectorised count against the pair list, the API, dossier, findings, export and DB on the fixture (pytest); the page, its views and filters, Hebrew, the empty state, the family page, both panels' chips, the dossier chip, the findings (vitest); e2e: the pages, dossier chip → pairs → root

✔ A verb takes a noun of its own root nearby 4.1 times as often as chance (1,677 vs 406, p 0.005); counted by root, the eight named Leitworte do not rank higher (6 / 8 in the top 12 either way: 3 up, 3 down); 896 hidden key roots as leads; the infinitive absolute is rare in Chronicles (0.15 per 1,000 words vs ~1 in Kings); 506 pytest, 152 / 152 vitest, 189 / 189 fixture (1 skipped by design) and 140 / 140 real-data e2e (a word-chip contrast on the root page fixed).

## M62: Layered reader (§16.39, D75; proposed B1)
- [x] `GET /api/reader/{unit}`: speech per display token, phrase partners, rare words (`serve.reader.rare_verses`, names out), sound-alike pairs with their partner, ketiv / qere, the gap before each verse; `computed` per layer
- [x] Viewer: the Reader page (`/read/:unit`), eight layers in `?layers=` (speakers, verse halves, Leitworte by word or root, shared phrases, rare words, wordplay, ketiv / qere, turns), a legend per layer, tooltips with every layer's word, the word panel, prev / next keeping the layers; "Read with layers" on the unit page; `HebrewText` takes a per-word `decorate`; colours ≥ 5:1 on every tint in both themes; English and Hebrew
- [x] Tests: the endpoint on the fixture, across units, too long, without the stages (pytest); the layers in the URL, defaults, toggling, every layer's marks, wordplay partners, by root, not computed, Hebrew, a verse read in its chapter (vitest); e2e: the pages, unit page → reader → a layer → partner → next; axe on Genesis 3 with every layer

## M63: Refrains (§16.40, D76; proposed A3)
- [x] `bsim refrains` (`analysis/refrains.py`, pipeline stage after roots, ~6 s): 3-lemma seeds (prefixes dropped, two content words that are not names) in 3+ verses of a book within 20 verses of each other, scored by burst against the book rate; false discovery rate against verse orders shuffled within books; each refrain extended to its longest shared phrase
- [x] Checks fixed in advance: nine refrains scholarship names; even spacing against random placements (untestable ones left out); the turns of §16.29 next to refrain verses; the strongest refrain of each group as the sample; a robustness grid (seed, gap, names)
- [x] DB `refrains`, `refrain_verses` (+ `meta.refrains`); API `/refrains`, `/refrains/list`; dossier `refrains`; findings `refrains`, `refrain_regular`, `refrain_turns`; CSV `refrains`; the reader's Refrains layer
- [x] Viewer: Patterns → Refrains (the three tests, the known table, the list with each refrain's verses marked, filters for book, the strongest of each group, named in advance, a unit); English and Hebrew
- [x] Tests: tokens, seeds, runs and the burst, the false discovery rate, extension, spacing, the stage on a toy corpus (a refrain found, a name phrase not, the known check, spacing, turns), the API, dossier, findings, export, reader and DB on the fixture (pytest); the page, its tests, the list, filters, Hebrew, the empty state, the reader layer (vitest); e2e: the pages, dossier chip → refrains → reader

✔ 925 refrains against 46 by chance (551 distinct); 8 of 9 named refrains found (the Song of Songs' adjuration is too far apart); even spacing 27 / 179 (15 % vs 5 %, p 3 × 10⁻⁷), mostly lists; refrain verses stand next to sharper turns, 0.679 vs 0.650 (p 0.001). Three choices changed after the first run are reported with a robustness grid.

## M64: More supervision for the encoder (§16.41, D77; proposed C1)
- [x] `train/pairs.py`: training pairs = Sefaria's train rows, then the train-split pairs of `train.supervised.extra_pairs` (OpenBible ≥ `extra_min_votes` votes, ETCBC parallels) that no earlier source links; hard negatives exclude every source's pairs; `bsim train-sup --extra`
- [x] `bsim build-golds` (`data/golds.py`, pipeline stage after build-links): OpenBible and ETCBC pairs built before training; `eval-openbible` / `eval-etcbc` read them
- [x] `bsim supervision-exp` (`eval/supervision.py`): variants `seed14`, `etcbc`, `openbible`, `both` trained with the same recipe; semantic and fused lists scored in memory on the Sefaria, OpenBible and ETCBC dev golds with paired bootstrap CIs; adoption rule fixed before training (fused OpenBible gain above 0 and beyond the reseeded retrain, no significant Sefaria / ETCBC loss)
- [x] Adopted `both` (`extra_pairs: [openbible, etcbc]`): the experiment's model in place, the Sefaria-only one kept; `--adopt` now adds a newly declared dependency's outputs to a stage's inputs; embed and everything after rerun; test split not rerun
- [x] API `/eval` → `supervision`; Evaluation page: *More supervision* (fused and semantic tables, the rule, the verdict); English and Hebrew
- [x] Tests: merging and the gold files, variant configs, the adoption rule, negatives written under their name, adopt with a new dependency, the stage order (pytest); the section, its cells and verdict (vitest)

✔ `both` passes the rule fixed in advance (fused OpenBible dev +0.0056, CI [+0.0017, +0.0096], against ±0.001 for a reseeded retrain; Sefaria +0.0051 and ETCBC +0.0006, CIs include 0); `openbible` alone fails it on ETCBC (−0.030), `etcbc` alone on OpenBible. Adopted: dev fused 0.1895 → 0.1946 (Sefaria), 0.1460 → 0.1516 (OpenBible); all 18 findings keep their verdict. 525 pytest, 167 / 167 vitest, 205 / 205 fixture (1 skipped by design) and 150 / 150 real-data e2e (a chapter link beside "out of domain" on the Language page is now underlined: with the new lists a chapter of Ecclesiastes became out of domain, and axe flagged the link).

## M65: Psalm genres and the lament's turn (§16.42, D78; proposed A4)
- [x] `bsim psalms` (`analysis/psalms.py`, pipeline stage after refrains, ~9 s): per psalm without its superscription (a leading run of title lemmas), persons, imperatives, plural imperatives, questions (OSHB morphology) and the shares of SDBH distress / praise words, per word
- [x] Fixed before the first run: Gunkel's genres for 119 psalms (core cases, entered by hand) against 7 Ward clusters of the standardized counts (NMI, labels permuted); six genre profiles (BH); the turn as the split where praise − distress per word rises most (verse orders shuffled), twelve named turns within a verse (Poisson binomial), individual laments against hymns (Fisher); robustness: titles kept, form only, domains only, tolerance 0–2
- [x] DB `psalms`, `psalm_verses` (+ `meta.psalms`); API `/psalms`, `/psalms/list`; dossier `psalms`; findings `psalm_genres`, `psalm_forms`, `lament_turn`, `lament_turns`; CSV `psalms`; the reader's *Distress and praise* layer (`mood`, any chapter)
- [x] Viewer: Patterns → Psalms (the four tests, genres by cluster, what each cluster counts, the named turns, the list with each psalm's form, turn and a strip of its verses' mood); English and Hebrew
- [x] Tests: morphology counts, superscriptions, the split statistic and its shuffles, Poisson binomial, profiles, the stage on a toy psalter, the API, findings, dossier, export, the reader layer and DB on the fixture (pytest); the page, its tests, filters, Hebrew, the empty state, the reader layer (vitest); e2e: dossier chip → psalms → reader with the mood layer; the pages with axe

✔ The counted form recovers Gunkel's genres: NMI 0.262 against 0.082 with the genres shuffled (p 0.001; the form alone 0.294, the domains alone 0.142); 6 / 6 genre profiles hold; 7 of 12 named turns found within a verse against 3.4 by chance (p 0.016, but p 0.24 within 2 verses); individual laments do not turn above chance more often than hymns (7 / 37 against 2 / 30, p 0.13). 533 pytest, 173 / 173 vitest, 213 / 213 fixture (1 skipped by design) and 156 / 156 real-data e2e.

## M66: The Pentateuch's sources (§16.43, D79; proposed A5)
- [x] `bsim pentateuch` (`analysis/pentateuch.py`, pipeline stage after psalms, ~6 s): Genesis–Numbers split in two after Koppel–Dershowitz — chunks of 10 verses by their choices within 18 synonym sets (first principal component), the furthest 30 % of each side training a logistic regression on the synonym members and 60 function words, smoothed over ±2 verses; the side holding most of Leviticus P-like; the divine names never features
- [x] Fixed before the first run: Noth's P entered by hand (2,787 verses, 88 unassigned); kappa over Genesis–Numbers and within Genesis, and יהוה's share before Exodus 6 on each side, each against the split shifted circularly within books; a grid of chunk size × smoothing
- [x] DB `pentateuch_verses`, `pentateuch_chapters` (+ `meta.pentateuch`); API `/pentateuch`, `/pentateuch/chapters`, `source` on the reader's verses; dossier `pentateuch`; findings `pentateuch_split`, `pentateuch_genesis`, `pentateuch_names`; CSV `pentateuch`; the reader's *P / non-P* layer
- [x] Viewer: Overview → The Pentateuch's sources (the checks, confusion, books, grid, the words that decide it, the synonym table, chapter by chapter against the reference); English and Hebrew
- [x] The new config section was first named `sources`, which overwrote the download sources of the same name (a YAML duplicate key): found by the tests before any pipeline run, renamed `pentateuch` throughout
- [x] A shadowed variable in `store/db.py` (the new meta block reused stylometry's `sm`) emptied the stylometry axes in one build: caught by the full test run, fixed, DB rebuilt
- [x] Tests: tokens and the held-out names, chunks, choices, the first component, kappa, the names gap, circular shifts, smoothing, the stage on a toy Pentateuch, the API, reader, findings, dossier, export and DB on the fixture (pytest); the page, its tables, words and stems, chapters, the book switch, Hebrew, the empty state, the reader tag (vitest); e2e: dossier chip → reader with the split → the page

✔ The split finds P: agreement 78 %, kappa 0.559 against 0.161 for the split shifted within books (p 0.001); within Genesis kappa 0.301 against 0.002 (p 0.004) — modest; the divine names, never seen, do not follow it (יהוה 37 % of divine names on the P-like side against 43 %, p 0.28; 1 % against 49 % in the reference). Leviticus, all P, only 69 % P-like. 540 pytest, 179 / 179 vitest, 221 / 221 fixture (1 skipped by design) and 162 / 162 real-data e2e.

## M67: Who speaks to whom (§16.44, D80; proposed A6)
- [x] Addressees in `bsim syntax` (`data/bhsa.py`; five more BHSA features, `nu`, `prs`, `prs_ps`, `prs_gn`, `prs_nu`): the introduction's אל / ל complement or the object of צוה, a vocative, a pronoun resolved to the other party, a bare ויאמר as an answer to the previous speaker; `quote` on every clause; speakers unchanged
- [x] Rules tuned on two samples (40, 30), then frozen; hand check of 50 drawn after: 42 right — explicit 21 / 21, vocative 11 / 11, turn 6 / 9, pronoun 4 / 9; the checks rest on explicit and vocative addressees, every addressee as the sensitivity
- [x] `bsim dialogue` (`analysis/dialogue.py`, pipeline stage after pentateuch, ~4 s): quotations with "your servant" forms, imperatives and נא; per-book pairs (the divine names one party); exchanges between two parties; checks fixed in advance: deference and נא toward God or a king (the "up" label permuted within books), the last word in unequal exchanges (the last turn drawn within each exchange); opener and turn lengths described
- [x] The exchange definition changed after the first run (God's names one party, narrated turns only, a turn to someone else ends a run): stated with the first run's numbers (last word 142 / 250 against 130.5, p 0.075; same verdict)
- [x] DB `clauses.addressee*`, `dialogue_pairs`, `dialogue_exchanges` (+ `meta.dialogue`); API `/dialogue`, `/dialogue/book/{id}`, `/dialogue/exchanges`; `addressee` on clauses, `to` on a book's speakers and the reader's; dossier `dialogue`; findings `dialogue_deference`, `dialogue_particle`, `dialogue_last_word`; CSV `exchanges`
- [x] Viewer: Who speaks → To whom (counts, hand check, the three checks, a book's conversations as a network and a pairs table, exchanges linking to the reader); "to X" on the clause panel, a book's speakers and the reader's speaker legend; English and Hebrew
- [x] Changing the `syntax` config section marked `train-simcse` / `train-sup` as changed (they read the whole section): adopted with `bsim all --adopt` rather than retrained, as D71 intends — the new keys cannot touch the encoders. Adopted before the upstream stages had rerun, the adoption did not hold: their reruns recorded more outputs, `train-simcse` started retraining on "new input corpus_meta.json" and was stopped before writing anything (the models are unchanged). After the upstream reruns the encoders were adopted again, and so were the stages whose only reason was a new, never-read input (their recorded inputs all matched)
- [x] Tests: addressees on two synthetic BHSA texts (explicit, pronoun to the other party, pronoun to the being named before), word marks, quotation extents, ranks and parties, exchanges (third speaker, addressed elsewhere, unknown speaker, not narrated), the permutation test on a planted rate, turn checks, pairs, the stage on a toy text, the API, findings, dossier, export, without the stage (pytest); the view, its checks, network, pairs, party filter, unequal filter, Hebrew, the empty state; the clause panel, speakers and reader legend (vitest); e2e: the tab in both languages with axe

✔ Speech to God or a king calls the speaker "your servant" 13.1 times per 1,000 words against 1.5 (p 0.001; 11.7 without Solomon's temple prayer); commands to them take נא 14 % of the time against 4 % (p 0.003), siding with the politeness reading; the higher party does not have the last word more than its share of the turns gives (96 of 170 against 89.4, p 0.17), nor open more, nor speak longer. All 25 earlier findings unchanged. 552 pytest, 183 / 183 vitest, 227 fixture e2e (1 skipped by design; axe first flagged the exchange links as colour-only, underlined like the other running-text links) and 168 / 168 real-data e2e.

## M68: Graded numerical sayings and lists (§16.45, D81; proposed A7)
- [x] `bsim forms` (`analysis/forms.py`, stage after dialogue, ~6 s): number words from the lemma table `forms.numbers` (cardinals, Hebrew and Aramaic); compound numbers left out; graded pairs within 8 words of one verse (`steps`); lists as runs of verses whose word-shape n-grams match a neighbour up to 3 verses away above the shuffled 0.99 quantile; kinds described
- [x] Checks fixed in advance (`forms.checks`): the 19 sayings named in advance; graded pairs against the book's number values permuted; sayings against other number pairs by parallelism; the 10 lists named in advance among more lists than shuffled orders give
- [x] Changed after the first run, stated: a NaN bug in the parallelism check fixed; the `names` kind; the sensitivity without 1 / 2 (described); the lists on their own random stream. No verdict changed
- [x] DB `forms_sayings`, `forms_pairs`, `forms_lists`, `forms_books` (+ `meta.forms`); API `/forms`, `/forms/sayings`, `/forms/lists`; `list_verses` on map points; dossier `forms`; findings `forms_known`, `forms_chance`, `forms_parallel`, `forms_lists`; CSV `sayings`, `lists`
- [x] Viewer: Patterns → Numbers and lists (the sayings with both numbers marked, the lists with their first verses, the checks and what was named in advance); the Map coloured by lists; English and Hebrew
- [x] Tests: number words, compound numbers, candidate pairs and steps, likeness and runs, the stage on a toy text, the API, map, findings, dossier, without the stage (pytest); the page, its checks, filters, Hebrew, the empty state; the map's colour option (vitest); e2e: the page in both languages with axe, from a chapter's dossier, Amos 1 and Genesis 5 on the real build

✔ 18 of the 19 sayings named in advance are found (Deut 32:30's אחד אלף ושנים reads as one number), and a verse with a graded pair is a parallel line more often than one with another pair of numbers (12 % against 5 %, p 0.026); but graded pairs are no more common than the books' numbers placed at random (105 against 96.2, p 0.20): "one … two" in the measurements of the Tabernacle and Temple swamps the sayings (without 1 / 2: 48 against 37.0, p 0.037, described). 69 lists against 0.7 by chance, 8 of the 10 named in advance (Num 7 and Neh 3 missed).

## M69: Pattern search (§16.46, D82; proposed B2)
- [x] `api/patterns.py`: the query language (bracketed word patterns, `key=value` / `!=` / `|`, `..N` and `..` gaps, `@` variables on lemma, root and word), a parser that reports errors as codes with a position, the word table from the results DB (OSHB morphology decoded per main morpheme, prefixes and suffix apart; BHSA functions, clause types, speech and speaker), matching by masks and word offsets
- [x] `/patterns` (paged verses, matches per book, `error`), CSV `patterns`; the word table built in the background at server start (`serve.patterns`), queries cached
- [x] Check: the infinitive absolute with a finite verb of the same lemma within three words, both orders, 432 + 41 = 473, the count of `bsim roots`
- [x] Viewer: Patterns → Pattern search (`/query`): query box, examples, syntax guide with every key, errors worded and marked in place, counts per book as filters, matched words marked; English and Hebrew
- [x] Tests: the morphology decoding, every parse error, matching on a small DB (variables, gaps, functions, speech, prefixes, suffixes, Hebrew lemmas, too broad), the endpoint, paging, filters and CSV, the table built once (pytest); the page, examples, book filter, errors, Hebrew (vitest); e2e: the page in both languages with axe, a query and an error on the fixture, the 432 pairs on the real build

✔ A construction can be searched from the viewer: `[form=infabs root=@r] [root=@r form=finite]` lists the 377 verses of מות יומת and its kind, and the query language reproduces the roots stage's count of infinitive-absolute pairs exactly (473).

## M70: Your notebook (§16.47, D83; proposed B3)
- [x] `store/notebook.py`: entries (a unit with a note), collections, members, in the labels file; adding to a collection keeps the unit, removing an entry takes it out of its collections, deleting a collection keeps its entries
- [x] API `/notebook` (entries in canon order with a verse's text, collections with counts, `hidden` for units an older build had), entries, collections and members (PUT / POST / DELETE; 403 read-only, 404, 409 for a name taken, 422 for limits `serve.notebook`); CORS allows POST
- [x] Viewer: a Notebook panel on every unit page (keep, note, collections, create one in place, remove with an in-page confirmation); the Notebook page (collections as filters with create / rename / describe / delete, search over notes, Markdown and CSV export written in the browser); English and Hebrew
- [x] Tests: the store, the API (order, limits, conflicts, read-only, units of an older build, the file shared with the labels) (pytest); the panel, the page, the Markdown file, against an in-memory server (vitest); e2e: keep a verse with a note and a new collection, see it in the notebook, axe, clean up (fixture, desktop only: one shared file); the page loads on the real build

## M71: Newer encoders (§16.48, D84; proposed C2)
- [x] Availability checked first: DictaBERT base / large, multilingual-E5-large, Qwen3-Embedding-0.6B on the hub, ungated, fast tokenizers, every verse within 128 tokens; NeoDictaBERT left out (`trust_remote_code`)
- [x] `bsim encoder-exp [--retrain] [--only NAME]` (`eval/newer_encoders.py`): trained candidates through `train-sup` with BEREL's recipe, pairs and seed from their base model (`models/{name}-sup`); zero-shot candidates encoded with their own instruction (`encoders` `prompt`); semantic and fused lists on the Sefaria, OpenBible and ETCBC dev golds with paired bootstrap CIs; zero-shot ones also against BGE-M3; never edits the config
- [x] Rule fixed before any candidate ran: Sefaria fused gain with CI above 0 and above the reseeded retrain's 0.0009, no significant loss on OpenBible or ETCBC
- [x] API `/eval` → `encoders`; Evaluation page: *Newer encoders* (fused and semantic tables, the rule, the zero-shot comparison); English and Hebrew
- [x] Tests: candidate configs, the noise bar, the adoption rule, the report (pytest); the section and its cells (vitest)

✔ None passes, so BEREL stays. Fused Sefaria dev against `berel_sup` (0.1946): DictaBERT base −0.0164, CI [−0.0264, −0.0068], large −0.0213, CI [−0.0320, −0.0110], multilingual-E5 −0.0271, CI [−0.0395, −0.0151], Qwen3 −0.0476, CI [−0.0606, −0.0351]. Every candidate scores higher on ETCBC's near-verbatim parallels, significantly only DictaBERT base (+0.0275, CI [+0.0024, +0.0532]) and E5 (+0.0376, CI [+0.0105, +0.0659]). DictaBERT large trained 3 h 53 min and peaked at step 100 of 755. Zero-shot, multilingual-E5 is level with BGE-M3 and Qwen3 below it.

## M72: Comparing two builds (§16.49, D85; proposed C4)
- [x] `store/compare.py`: both DBs attached read-only; per table schema, row counts, keyed tables joined on the primary key (only old / only new / changed, exactly and beyond `compare_builds.float_tol`, example keys and columns), unkeyed tables as multisets plus their order; `meta` by flattened JSON paths, `volatile_meta` apart
- [x] `bsim compare-builds OLD NEW [--json PATH] [--fail-on-diff]`; config `compare_builds`
- [x] Tests: identical builds, tables and columns added and removed, keys, the tolerance, reordered and duplicate rows, `meta` paths, a missing file, the command's report, JSON and exit codes (pytest)
- [x] Real check: the build before M71 against the one after, and against a copy edited by hand

✔ The builds before and after M71 are identical in all 85 tables (about 75 s), so rewriting `surface_bm25.json` changed nothing served; only the build time and the `/similar` timings differ, now volatile. A copy with one row deleted, one score moved within the tolerance and one beyond it, and one `meta` count changed is reported as exactly that.

## M73: A third fusion list for chapters and pericopes (§16.50, D86; proposed C3)
- [x] `retrieve/unit_pairs.py`: unit lists summed from weighted verse pairs; `bsim unit-exp` (`eval/unit_experiments.py`): parallel sequences (every chain / q ≤ 0.2), shared phrases, fused verse hits (top 10 / 50) as a third RRF list at w 0.25 / 0.5 / 1, per unit type on the Sefaria, OpenBible and ETCBC dev unit golds, selected and cross-fitted, paired bootstrap; the two-list baseline rebuilt in memory
- [x] Rule fixed before the first run: cross-fitted Sefaria CI above 0, no significant loss on OpenBible or ETCBC; the largest passing gain adopted
- [x] Adopted phrases for chapters (`fusion.unit_phrases: {chapter: 1.0}`): `bsim fuse` writes `topk/chapter/phrases.parquet` and fuses three lists; the phrases stage moved before fuse; `matches.phr_score`, `phr_rank`; training stages adopted, the rest rerun (33 stages, 16 min)
- [x] API `/similar` → `phrases` and `phr_*`; `/eval` → `units`; viewer: a third rank bar (*Phr*) on chapter pages, the Evaluation page's *A third list for chapters and pericopes* (per unit type: the verdict, gains, the lists alone); English and Hebrew
- [x] Tests: aggregation, ranking, unit gold from verse pairs, scoring, the rule, the report, fusion with the phrase list, the API fields (pytest); the rank bar, the Evaluation section (vitest)
- [x] Checked with `bsim compare-builds`: only chapter fused matches and what is built on them changed; all 32 findings keep their verdict
- [x] Fixed: the server's `/search` caches are never stage files (`incremental.Scope` ignores `serve.cache_dir`, the state forgets recorded files it ignores); a viewer session after a rebuild no longer marks `phrases` and everything after it stale (§16.35)

✔ Shared phrases pass for chapters: cross-fitted +0.0266 on Sefaria dev (CI [+0.0066, +0.0461]), OpenBible +0.0123 and ETCBC +0.0677 (CIs above 0); chapter fused 0.1710 → 0.1976, now above TF-IDF (0.1916). Nothing passes for pericopes: fused verse hits come nearest (cross-fitted +0.0095, CI [−0.0002, +0.0190]). Parallel sequences help little at either level.

## M74: Code health (§16.51, D87; proposed C5)
- [x] `api/models/` and `api/queries/`: one module per route module + `common` (routes import their own models; `queries` re-exported); `queries.domains` → `domain_tree`; the OpenAPI schema unchanged
- [x] `store/analyses.py`: one `Source` per analysis stage (files, tables, fixes, meta keys) in place of the per-analysis read / adapt / insert code; columns from `schema.sql` (`store/schema.py`); `store/lexicon.py`, `store/links.py`; the analysis modules import the lemma helpers at the top; the DB built identical
- [x] `Literal` fields in pydantic where the viewer narrows a string; `types.ts`: 214 aliases of the schema, 19 responses with open JSON fields written over it; the drift check only for those
- [x] `components/UnitPanels.tsx`: the unit page's data panels with their unit types, place and dossier gate
- [x] Checks: ruff, pytest, lint, vitest, fixture and real e2e; `bsim compare-builds` (identical after `bsim build-db`; after `bsim all`, `senses` differs between two runs of unchanged code: fixed in M75)

✔ Same API, same DB: `models.py` 2,425 / `queries.py` 2,145 / `db.py` 2,031 lines became feature modules (the largest 303 lines), a 526-line `db.py` and the 689-line analyses registry, `types.ts` 3,130 → 1,263, the unit page 557 → 445. Found on the way: `bsim senses` is not deterministic across runs (one example or one clustering of a frequent lemma).

## M75: Deterministic k-means (§16.52, D88)
- [x] Found the cause of the senses run-to-run differences. The GPU word vectors are bitwise the same across runs and processes; sklearn's multi-threaded `KMeans` is not (centres in the last bits, and at times the optimum: כֹּל 3605)
- [x] `stats.kmeans`: one thread via `threadpoolctl`, with sklearn imported first; used by `senses.cluster_uses` and `corpus_map.clusters`
- [x] Test: four fits of 6,000 random points give one answer, where plain `KMeans` gives one per fit
- [x] Two runs of `bsim senses` and of `bsim map`: byte-identical files, at the same speed. `bsim all` (31 stages, 12 min 30 s) gave the same senses files a third time; `bsim compare-builds` against the DB before: 82 of 85 tables the same, `lemma_senses` and `lemma_shifts` differ in those lemmas only, `word_pairs` holds the same rows in another order (as in M54)

✔ `bsim senses` gives one answer per seed. Against the last run, the use clusters of בֵּן 1121a, כֹּל 3605 and מֶלֶךְ 4428 and one example list of דָּבַר 1696 changed; the counts in the meta and the map did not.

## M76: Gematria (§16.53, D89; proposed G1)
- [x] `text/gematria.py`: standard, gadol (finals 500–900), ordinal, katan over the consonants; `bsim gematria` (`analysis/gematria.py`, pipeline stage after forms, ~15 s): every written form (MAM display tokens, qere), lemma (Strong's headword, else its commonest form) and verse valued; the equivalences of `gematria.known` checked (the stage stops when one fails)
- [x] DB `gematria_forms`, `gematria_lemmas`, `gematria_verses` (indexed by each system's value; + `meta.gematria`); API `/gematria/value?text=`, `/gematria?value&system`, `/gematria/{forms,lemmas,verses}`; `gematria` per token on `/reader/{unit}`
- [x] Viewer: Patterns → Gematria (a word or a number, its four values, forms / lemmas / verses of that value, the equivalences), the word panel's value chip, a Gematria layer in the reader (word values, verse totals linked to their verses), `= 318` in the jump box; English and Hebrew
- [x] Tests: tables, points and maqaf ignored, Genesis 1:1 = 2701, the known values, the stage, DB and API on the fixture, the reader layer (pytest); the page, its systems, views and equivalences, Hebrew, the empty state, the reader layer, the jump box (vitest); e2e on the fixture and the real build

✔ 39,555 written forms, 9,204 lemmas and 23,206 verses valued; the eight equivalences hold. Seven verses add up to 2701 as Genesis 1:1 does, a reminder of how common equal values are before G2 tests them. 607 pytest, 209 vitest, 249 / 251 fixture e2e (2 skipped by design; one page load failed once under load and passed 12 / 12 on rerun) and 188 / 188 real-data e2e.

## M77: Atbash and albam (§16.54, D90; proposed G3)
- [x] `text/ciphers.py`: atbash, albam and random pairings of the 22 letters; `bsim ciphers` (`analysis/ciphers.py`, ~170 s): rare words and adjacent word pairs a swap turns into a name of the text (`Np`), against 999 random pairings; checks fixed in advance in `ciphers.checks` (known, Jeremiah 25 + 51, elsewhere, albam); per chapter p and BH q
- [x] DB `cipher_hits`, `cipher_chapters` (+ `meta.ciphers`); API `/ciphers`, `/ciphers/hits`, `/ciphers/value`; findings `ciphers_known`, `ciphers_jeremiah`, `ciphers_elsewhere`, `ciphers_albam`
- [x] Viewer: Patterns → Atbash and albam (the checks, the cases named in advance, the hits with their words marked, the chapters against random pairings), the word panel's "Swapped" line; English and Hebrew
- [x] Tests: the swaps (pairs, no fixed letter), the known readings, names and spans, the stage on a small corpus (hits, known, checks, the same file twice, a bad reference), the API, findings (pytest); the page, its filters and chapters, Hebrew, the empty state (vitest); e2e on the fixture and the real build

✔ The three places of Jeremiah are found and stand out there: 3 names against 0.64 for a random pairing (p 0.036). Elsewhere atbash reads 78 names against 104 (p 0.76) and albam 94 against 105 (p 0.53): neither hides names beyond chance; no chapter passes after correction. 615 pytest, 214 vitest, 256 / 258 fixture e2e (2 skipped by design) and 194 / 194 real-data e2e (the word-panel step first looked for the word with its te'amim, which the page does not show by default: fixed and rerun).

## M78: The Masorah's counts (§16.55, D91; proposed G4)
- [x] `bsim masorah` (`analysis/masorah.py`, ~4 s): the written and the read text from the MAM tokens and OSHB's ketiv / qere; the middles of `masorah.middles` (the Torah's letter, words and verse from Kiddushin 30a, the Masorah and Soferim; each Torah book's middle verse; Psalms) against ours; the Masorah's verse totals per book (Ginsburg's collation, other manuscripts' figures listed) and the sections against ours, each differing book with its reason
- [x] DB `masorah_middles`, `masorah_totals`, `masorah_books` (+ `meta.masorah`); API `/masorah`; findings `masorah_letter`, `masorah_words`, `masorah_verse`, `masorah_books`
- [x] Viewer: Patterns → The Masorah's counts (the middles, as written or as read, with both verses marked; the verse totals with their reasons; the sections; every book counted); English and Hebrew
- [x] Tests: the two texts (a word shown as written, as read, written not read, read not written), the middles in letters, words and verses, the totals and their sum, bad claims, the same file twice, the API, findings (pytest); the page, the text switch, the totals, Hebrew, the empty state (vitest); e2e on the fixture and the real build

✔ Written, the Torah has 304,801 letters (the printed count is 304,805) and 79,978 words in 5,846 verses. The ו of גחון is 4,829 letters past our middle letter (the ל of ליהוה, Lev 8:28), and דרש דרש are 932 words past our middle words. The Masorah's middle verse, Lev 8:8, lands (our middle is between 8:8 and 8:9), as do the middle verses of the five books and of Psalms. 18 of the Masorah's 24 books have its verse total. The other six differ by 1–2 verses: the Ten Commandments divided otherwise (Exodus, Deuteronomy), Gen 35:22 counted as two, Josh 21:36–37 left out, Kings untraced, and Jeremiah, where the manuscripts disagree. 621 pytest, 219 vitest, 258 / 260 fixture e2e (2 skipped by design; the page first failed axe's link-in-text-block: its in-text links are now underlined, and the accessibility runs pass) and 200 / 200 real-data e2e.

## M79: The gazetteer (§16.56, D92; proposed P1)
- [x] `bsim download --only geo`: STEPBible TIPNR and OpenBible.info's `ancient.jsonl`, both CC BY 4.0, at pinned commits (DESIGN §1); `data/geo.py` reads them
- [x] `bsim places` (`analysis/places.py`, ~3 s): each name mention to a TIPNR place by Strong's number and the nearest reference (exact, shifted by English numbering, or a number's only place); the site located by OpenBible's best-voted identification (joined by name and TIPNR id, decided by shared verses); kinds from SDBH's name subdomains and OpenBible's types; every name's SDBH kind; hand check 49 / 50
- [x] DB `places`, `place_mentions`, `name_kinds` (+ `meta.places`); API `/places`, `name_kind` and `sites` on `/entities/{lemma}`; the Names page shows a name's kind and sites (English and Hebrew)
- [x] Tests: both readers (a psalm title's verse 0, the Septuagint skipped, spellings, votes sorted), matching mentions (exact, shifted, only, person, none), the OpenBible join, the stage on a small corpus, the API (pytest); the Names page's sites (vitest); e2e on the fixture and the real build

✔ 6,463 name mentions are 820 sites, 818 located (802 by OpenBible); 574 towns, 97 regions, 94 landforms, 41 waters; 92 Strong's numbers name several sites (Abel: a stone, Abel-beth-maacah). Hand check: the site is the place meant in 49 of 50. Votes are often low (363 sites under 300 of 1,000), stated with every point. 630 pytest, 220 vitest, 264 / 266 fixture e2e (2 skipped by design) and 202 / 202 real-data e2e; adding the `geo` download group was adopted for every stage it does not feed (no corpus input changed), and the real DB only gained the three tables.

## M80: A real map (§16.57, D93; proposed P2)
- [x] Natural Earth's 1:10m land, lakes and rivers (public domain) in the `geo` download group; `data/basemap.py` clips (Sutherland–Hodgman, Liang–Barsky) and thins (Douglas–Peucker) them in plain Python; `bsim places` writes the base map (17,689 points, 280 KB); TIPNR's `@0,14z` no longer read as a point
- [x] DB `map_shapes`; API `/places/basemap`, `/places/{id}` (names, verses per book, places named with it), `/places/{id}/verses`; `places` on `/reader/{unit}`
- [x] Viewer: Overview → Places on the map (an SVG projected by hand: points sized on a fixed log scale and coloured by kind, labels kept apart, drag and zoom, keyboard; filters by book, chapter, unit and kind; three views; the place panel); "Where this happens" on chapter and pericope pages; a places layer in the reader; English and Hebrew, light and dark
- [x] Tests: clipping, lines and simplification (pytest); the base map from a small corpus, the place panel, verses, the reader layer (pytest); the page, the panel, filters, keyboard and zoom, Hebrew, the empty state, the reader layer (vitest); e2e on the fixture and the real build

✔ The 816 located places on a map of the region, drawn by hand from Natural Earth (no tiles, no map library), filterable down to a chapter; every place opens to its names, books, companions and verses; chapters and pericopes show where they happen; the reader boxes every place name. 635 pytest, 227 vitest, 272 / 274 fixture e2e (2 skipped by design) and 210 / 210 real-data e2e; the pipeline adopted the stages the new download does not feed, and the real DB gained `map_shapes` only.

## M81: Place lists on the ground (§16.58, D94; proposed P3)
- [x] `bsim place-lists` (`analysis/place_lists.py`, ~3 s): six lists fixed in `place_lists.lists` (Num 33, Num 34, Josh 15:1–12, Josh 15:21–62, Josh 19, Gen 10), places in the text's order by verse and word; the path against 9,999 random orders, with a nearest-neighbour + 2-opt short path for scale; Judah's districts and the tribes' lots against shuffled labels; every test again on sure sites (vote ≥ 500)
- [x] DB `place_lists`, `place_list_steps`, `place_districts`, `place_district_towns` (+ `meta.place_lists`); API `/place-lists`, `/place-lists/{key}`, `/place-districts/{key}`; findings `place_lists_order`, `place_lists_districts`
- [x] Viewer: Overview → Place lists on the ground (the lists' tests; a list's path on the map in the text's order or the short one, the random orders' histogram, its steps with the longest marked; the districts coloured on the map with their tests); the map draws lines and takes a colour per point; English and Hebrew
- [x] Tests: distances, the short path, random orders, districts (pytest); the stage on a small corpus (word order in a verse, a region left out, a place named again, sure sites), the API, findings (pytest); the page, a list, the short path, districts, Hebrew, the empty state (vitest); e2e on the fixture and the real build

✔ All six lists walk the ground: each path is shorter than all 9,999 random orders of its places (Num 33: 2,172 km against 8,728; Josh 15:21–62: 1,951 against 4,463), 67–88% of the way from random to a short path, and all six still hold on sure sites alone. Judah's districts cluster (27.6 km within against 38.5 shuffled, p 0.0001; sure sites 17.0 against 34.8), seven of the ten with two towns or more on their own, though not the wide Negev district; the tribes' towns, the known answer, at 23.6 against 84.8 km. The longest steps point at two doubtful joins of the gazetteer (Josh 15:3's Hezron as the northern Hazor, Num 34:11's Ain as the southern one), listed as leads. 642 pytest, 233 vitest, 278 / 280 fixture e2e (2 skipped by design) and 216 / 216 real-data e2e: the new page first failed axe's colour contrast (muted text on the chosen row, now full colour), and the old atbash smoke test's flake is fixed (its checkbox follows the URL a render late, so the test waits for it rather than `check()`).

## M82: Equal values, related words? (§16.59, D95; proposed G2)
- [x] `bsim gematria-links` (`analysis/gematria_links.py`, ~50 s with the GPU): 3,373 lemmas with domains, a root and a BEREL vector; every pair of equal standard value against 999 sets of pairs matched on letter count and frequency band, on SDBH domains, root family and vectors; pairs spelled alike left out; one-root pairs as the check; the tradition's equivalences ranked; Gen 1:1's properties over every verse with its own-numbers look-elsewhere control
- [x] DB `gematria_pairs` (+ `meta.gematria_links`); API `/gematria-links`, `/gematria-links/pairs`; findings `gematria_links`, `gematria_measures`, `gematria_genesis`
- [x] Viewer: Patterns → Equal values, related words? (the test and the check, the equivalences, Genesis 1:1's numbers and twins, the pairs sorted and filtered); English and Hebrew
- [x] Tests: prime factors, triangular numbers, properties, matched draws (cell, value, spelling, either side kept), the stage on a small corpus (a name left out, pairs spelled alike, the equivalences, the verse and its twin), the API, findings (pytest); the page, the equivalences, Genesis 1:1, the pairs' sort and filters, Hebrew, the empty state (vitest); e2e on the fixture and the real build

✔ Equal values link nothing. Over 11,328 pairs of equal standard value, semantic domains shared 0.0085 against 0.0097 for matched pairs (p 0.96), one root family 0.01% against 0.04% (p 0.99), BEREL vectors 0.602 against 0.601 (p 0.06), while pairs of one root family, the check, are far closer (domains 0.257 against 0.013, vectors 0.673 against 0.596). נחש = משיח is used more alike than 74% of equal-value pairs, יין = סוד 65%, אחד = אהבה 31%. Only Genesis 1:1 has the five properties claimed for it, but described by its own numbers it shares 7 words, 28 letters and largest prime factor 73 with four verses (Ps 44:5, Ps 54:9, Prov 7:7, Job 24:10), while 63% of verses are alone with theirs. 647 pytest, 238 vitest, 284 / 286 fixture e2e (2 skipped by design) and 222 / 222 real-data e2e: the new page first failed axe's link-in-text-block (a value link in each pair's line, now underlined).

## M83: The geographic arc (§16.60, D96; proposed P4)
- [x] `bsim place-arc` (`analysis/place_arc.py`, ~2 s): every chapter's centre (the mean on the sphere of its located place mentions, once per verse), spread and reach; consecutive placed chapters against 9,999 shuffled orders per book and over all; four known moves against anchor regions; the oracles against the nations against the other prophetic chapters on spread and reach (labels shuffled, α / 2 each)
- [x] DB `place_arc_chapters`, `place_arc_books` (+ `meta.place_arc`); API `/place-arc`, `/place-arc/{book_id}`; findings `place_arc_order`, `place_arc_moves`, `place_arc_oracles`
- [x] Viewer: Overview → The geographic arc (a book's chapters as a numbered path on the map with their steps and spreads, the books' table, the known moves as a table and arrows on the map, the oracles' tests and chapters); `GeoMap` takes a point's title; English and Hebrew
- [x] Tests: centres, spreads, the label test, the stage on a small corpus (a place twice in a verse, an unplaced chapter passed over, a book too short to test, the moves both ways and one unplaced, the oracles), the API, findings (pytest); the page, the book switch, the moves and oracles, Hebrew, the empty state (vitest); e2e on the fixture and the real build

✔ Consecutive chapters lie closer than shuffled: 223 km against 267 km over 556 placed chapters (p 0.0001), and 9 of 31 books on their own (Genesis 228 against 355 km, 2 Kings 145 against 268, Jeremiah 321 against 436). All four known moves hold (Gen 11's centre 135 km from Babylon, Gen 12's 106 km from Jerusalem). The oracles against the nations do not range wider at α / 2: spread 412 against 296 km (p 0.07), reach 331 against 275 km (p 0.19); an oracle names its nation's own towns, and those against Moab are the tightest chapters of all (Jer 48 26 km). 654 pytest, 243 vitest, 290 / 292 fixture e2e (2 skipped by design) and 228 / 228 real-data e2e: the new page first failed axe's link-in-text-block (the chapter links in its lists, now underlined), and its accessibility tests were rerun on their own.

## M84: Named together, near together? (§16.61, D97; proposed P5)
- [x] `bsim place-links` (`analysis/place_links.py`, ~6 s): located places linked by the verses they share (≥ 2, above independence), G² as strength; Spearman's rho between G² and km against 9,999 shuffles of the coordinates, on every located place, sure sites and without the place lists; the decay by km bins; far pairs (≥ 150 km) as leads with Dan–Beersheba as a known answer
- [x] DB `place_links`, `place_link_bins` (+ `meta.place_links`); API `/place-links`, `/place-links/pairs`; findings `place_links_decay`, `place_links_known`
- [x] Viewer: Overview → Named together, near together? (the test and its variants, the scatter, the decay per variant, the known answer and leads with lines on the map, the linked pairs by place and order); English and Hebrew
- [x] Tests: links (a place twice in a verse, a pair below independence), rank correlation, the test and the bins on a line of places, the stage on a small corpus (a place without a point, the variants, a list verse, the known pairs found and not), the API, findings (pytest); the page, the variants, the decay switch, the leads and the known answer, the place filter, Hebrew, the empty state (vitest); e2e on the fixture and the real build

✔ Places named together lie together: over 510 linked pairs of 277 places, rho −0.32 between link strength and km against −0.00 with the points shuffled (p 0.0001); −0.33 on sure sites, −0.30 without the place lists. 6.3% of the pairs within 10 km are linked, 0.2–0.4% beyond 50 km. Dan and Beersheba are the third of 149 far pairs; the others at the top are Babylon and Chaldea, the cities of the Assyrian boast, the exiles' Halah, Habor and Gozan, and Assyria with Egypt. 661 pytest, 249 vitest, 296 / 298 fixture e2e (2 skipped by design) and 234 / 234 real-data e2e.

## M88: The family tree, data (§16.63, D101; proposed F1)
- [x] `read_tipnr()` reads the family columns of a PERSON record (`TipnrFamily`: parents, siblings, partners, offspring, tribe, type, the `(?)` / `(a)` / `(d)` / `(f)` markers) and every reference as written (`eng_refs`, with `Exo.7.10a`); places unchanged (byte for byte)
- [x] `data/kjv.py`: English (KJV) verse numbers to ours, 39 rules (1 Chr 6:1 = 5:27, Joel 3 = 4, ...)
- [x] `bsim genealogy` (`analysis/genealogy.py`, ~3 s): people with Hebrew Bible names, links from both sides of TIPNR, proof verses by cue (construct, sons of, begot, kin, together; wife for spouses; a `nearby` hint for list headings), the review files of `curation/genealogy/` applied with strict validation, one drawn parent each, the married-in beside their spouse, the rest on their tribe's eponym or under "unattached" by book; `bsim genealogy-review <block>` writes the review sheet
- [x] DB `genealogy_persons`, `genealogy_links`, `genealogy_proofs`, `genealogy_conflicts`, `genealogy_blocks` (+ `meta.genealogy`)
- [x] Tests: the family columns, English numbering, the cues and the nearby hint, the stage on a small corpus (placement, proofs, tokens, determinism), a review file applied (confirmed, added, rejected, a conflict, missed), its errors, a cycle, the missing source (pytest)

✔ 2,845 people (2,737 persons, 73 groups, 35 unnamed) and 1,818 parent links, 1,463 (80%) with a verse naming both before any review: construct 616, sons of 461, begot 217, kin 146, together 23; 218 more have a nearby hint and 137 nothing. TIPNR's references hit the name in 98.3% of verses once moved to Hebrew numbering (about 80% without the rules; 1 Chr 6 was 15 verses off). Placed: Adam, 1,553 under a parent, 169 on a tribe, 67 beside a spouse, 1,055 unattached (mostly people with no family in the text). 680 pytest; the stages flagged by the change but unchanged were adopted.

## M89: The family tree, viewer (§16.63, D101; proposed F2)
- [x] API `/genealogy/skeleton`, `/genealogy/person/{id}`, `/genealogy/lookup?q=`
- [x] Viewer: Overview → Family tree (the tree with `d3-hierarchy`, collapse and expand anywhere, children by mother, cross-links, the markers and their legend, the side panel with proof verses, search, a bottom sheet on a phone, pinch and pan via a `usePanZoom` shared with the map); English and Hebrew
- [x] Tests: the API (pytest); the tree, collapsing, the panel, search, Hebrew (vitest); e2e on the fixture and the real build, axe

✔ Overview → Family tree: 2,816 nodes, 64 people drawn beside a spouse and 113 cross-links, laid out only where open and drawn only where in view. Jacob's sons sit under Leah, Bilhah, Zilpah and Rachel, each link with its verses and both names marked. Light and dark, English and Hebrew (mirrored), desktop and phone (bottom sheet). 683 pytest, 272 vitest; fixture e2e 309 passed (one Hebrew axe sweep failed once while other suites ran and passed on rerun); the real-data tree, page and axe sweeps pass.

## M90: The family tree, review block by block (§16.63; proposed F3)
Each block: `bsim genealogy-review`, the Hebrew read against the sheet, `curation/genealogy/NN-<block>.yaml`, rebuild, `docs/genealogy/PROGRESS.md` updated.
- [x] 01 Gen 1–11
- [x] 02 Gen 12–25:18
- [x] 03 Gen 25:19–36
- [x] 04 Gen 37–50
- [x] 05 Exodus–Leviticus
- [x] 06 Numbers–Deuteronomy
- [x] 07 Joshua–Judges
- [x] 08 1–2 Samuel
- [x] 09 1–2 Kings
- [x] 10 Isaiah–Malachi
- [ ] 11 Psalms, Proverbs, Job, Song, Ruth, Lamentations, Ecclesiastes
- [ ] 12 Esther, Daniel
- [ ] 13 Ezra–Nehemiah
- [ ] 14 1 Chr 1
- [ ] 15 1 Chr 2–4
- [ ] 16 1 Chr 5–6
- [ ] 17 1 Chr 7–9
- [ ] 18 1 Chr 10–29
- [ ] 19 2 Chronicles

## M91: The family tree, across books (§16.63; proposed F4)
- [ ] The parallel genealogies against each other: Gen 36 / 1 Chr 1, Gen 46 / Num 26 / 1 Chr 2–8, Ezra 7 / 1 Chr 5:27–41, Samuel–Kings / Chronicles
- [ ] Every tribe attachment checked; "Unattached" kept to the fragments with no known tribe
- [ ] A People group in the jump box and a dossier entry for the people of a unit (the D99 / D100 pattern)

## M87: Dossier entries for places, ciphers and letter values (D100; proposed V2)
- [x] `/dossier/{unit}`: `places` (count, the most named place), `ciphers` (hits, the first one's words and name), `gematria` (the tradition's texts of `gematria.known` among the unit's words; a verse's value and the other verses of it); `known_texts_in` (whole words, up to two prefix letters)
- [x] Viewer: three dossier chips on unit pages, linking to the map of the unit, the cipher hits of the unit, and the verses of a verse's value or the reader's letter-value layer; English and Hebrew. `DossierKind` now comes from the API schema
- [x] Tests: the three entries on a verse and a chapter against the list endpoints, "not computed", the text matching (pytest); the chips, their links and the found rule (vitest); e2e on the fixture (each chip to its page) and the real build (Jeremiah 25's ששך, Genesis 49's יבא שילה)

✔ A unit page now says which places it names, which names hide in a letter swap, and its letter values: Jeremiah 25 names 21 places (most often בבל) and hides בבל in ששך; Genesis 15:2 is worth 3,858, as are 6 other verses, and holds אליעזר. 672 pytest, 260 vitest, 302 / 304 fixture e2e (2 skipped by design) and 244 / 244 real-data e2e. Two needed a second look: the six whole-site accessibility runs had outgrown their 240 s budget (60 pages at about 4 s each: 250 s; now 480 s; no violations), and /phrases failed to load once on the phone and passed when rerun.

## M86: Places in the jump box (§16.57, D99; proposed V1)
- [x] `places.names`: the headword and TIPNR's other Hebrew names whose Strong's number the text uses for the site (ציון for Jerusalem, לוז for Bethel), from `bsim places`; downstream place stages adopted (unchanged)
- [x] API `/places/lookup?q=`: a Hebrew name (pointing ignored, prefixes dropped, ו and י ignored as a last resort) or a Strong's number; its own name, another name, then a prefix; the lemma lookup's prefix drops shared (`form_keys`)
- [x] Jump box: a Places group (kind, verses, first verse) before the words when a place is named by the whole query and no other word is commoner, else after them; Enter before the pause looks places up too. `= 318` was done in M76
- [x] Map: `?p=` outside the view moves the view to centre on it (the jump box, a partner picked)
- [x] Tests: the names kept and dropped, the lookup (pytest); places first and after, Enter before the pause, Hebrew, the map moved and left (vitest); e2e on the fixture (both languages) and the real build (Babylon in view, ציון to Jerusalem)

- [x] Follow-up: names of several words as the text writes them (§16.56): TIPNR's compounds had run together (חברוןעמק), now from the verses that name them (עמק חברון, בית חורן תחתון, ערבת מואב); 33 headwords changed, downstream place stages adopted (they keep ids, not names)

✔ A place's name opens the map at it: בבל moves the map to Babylon, ציון and ירושלים find Jerusalem, עין the eye comes before עין the town. 669 pytest, 258 vitest, 300 / 302 fixture e2e (2 skipped by design) and 242 / 242 real-data e2e; axe clean on the jump box and the map in both languages (the detail line on the highlighted option was too faint, 3.99:1, and is darker now).

## M85: Letters at equal skips (§16.62, D98; proposed G5)
- [x] `bsim els` (`analysis/els.py`, ~5 min with the GPU): 27 names fixed in config at skips 2–1,000 either way in the written letters of the Torah and of Genesis; each against its exact expectation under a letter shuffle; R against 199 letter shuffles, 199 verse shuffles and blocks of the other books; the tradition's five sequences at the start of the books as known answers
- [x] DB `els_terms`, `els_draws` (+ `meta.els`); API `/els`; findings `els_counts`, `els_known`
- [x] Viewer: Patterns → Letters at equal skips (the counts against each control, the draws as dots beside the text, the blocks, name by name, the tradition's sequences and how often they recur); English and Hebrew
- [x] Tests: letter codes, hits against brute force (both ways, a palindrome once), the expectation against every arrangement, the log ratio, finding a sequence, the stage on the fixture's corpus, the API, findings (pytest); the page, the names and the tradition, the scope switch, Hebrew, the empty state (vitest); e2e on the fixture and the real build

✔ No more names at equal skips than chance. The Torah's 304,801 letters hold 1,428,731 hits of 27 names against 1,429,940 expected (R −0.011): p 0.62 against shuffled letters, 0.57 against shuffled verses, 0.33 against the other books; Genesis alone R −0.009 (p 0.47, 0.45, 0.25). The tradition's five sequences (תורה at 50 from Genesis 1:1 and Exodus 1:1, יהוה at 8 from Leviticus 1:1, הרות from Numbers 1:1 and Deuteronomy 1:5) are all in our letters, but not rare: תורה at skip 50 occurs 19 times in the Torah, about 10 expected. 668 pytest, 254 vitest, 300 / 302 fixture e2e (2 skipped by design; the known page-load flake on /speech passed when rerun) and 240 / 240 real-data e2e.

Every suggestion from the 2026-10-09 review is done (M45–M59). From the 2026-10-12 review (each analysis with a claim fixed in advance and a known answer, for the Findings page):

Analyses
- [x] A1 (done, M60) Meter: stresses per colon (accented words, maqaf-joined = one) over the existing cola (`text/accents.py`); balanced vs falling lines per book / chapter. Claim: Lamentations 1–4 have more falling (qinah, 3:2) lines than other poetry (chapter permutation); Isa 14:4–21, Amos 5:2 as known extras, Lam 5 as control. Poetry tab, stress counts on the verse halves
- [x] A2 (done, M61) Root families: Strong's derivation links in HebrewStrong.xml (already downloaded; parse to check) → root families; Leitworte by root (§16.2 is by lemma) checked on Gen 27 ברך, Jonah ירד / גדל, 1 Sam 15 שמע / קול; figura etymologica (infinitive absolute + finite verb, cognate objects; out of scope in §16.10) per book against a shuffle; root chip and concordance by root
- [x] A3 (done, M63) Refrains: Smith–Waterman within a book (`analysis/phrases.py`), phrases recurring ≥ 3 times, gap regularity against a verse shuffle; known list in config (Amos 4:6–11, Isa 9:11–10:4, Ps 42–43, Ps 107, Ps 136, Gen 1); second claim: refrains fall at the turns of §16.29
- [x] A4 (done, M65) Psalm genres and the lament turn: per-psalm address / person / imperatives / SDBH distress vs praise domains, clusters against Gunkel's genres in config (NMI vs shuffled labels); a change point inside laments checked on known turns (Ps 6:9, 13:6, 22:23, 28:6)
- [x] A5 (done, M66) Pentateuch decomposition (Koppel–Dershowitz style): unsupervised two-way split of Genesis–Numbers by synonym choice (SDBH synonym pairs) and function words, divine names held out; agreement with a P / non-P assignment in config against a shuffle; framed as a test either way
- [x] A6 (done, M67) Who speaks to whom: addressee from the introducing clause's אל-complement and vocatives (hand check of 50, as M43); conversation network per book, turn length, last word; "To whom" on the Speech page
- [x] A7 (done, M68) Graded numerical sayings (x / x+1 over consecutive cola: Prov 30:15–31, Amos 1–2, Prov 6:16, Job 5:19, Mic 5:4) and lists / genealogies by repeated verse shapes (`bm25_morph` tokens)

Viewer
- [x] B1 (done, M62) Layered reader: a chapter view with the existing analyses as toggleable overlays on the words (speakers, cola, Leitworte, wordplay, ketiv / qere, phrases shared elsewhere, rare words, turns); `?layers=` in the URL; existing endpoints first
- [x] B2 (done, M69) Pattern search: a small query syntax over `words` (lemma, morph, POS, stem, BHSA phrase function, distance), paged results and CSV
- [x] B3 (done, M70) Notebook: bookmarks, notes and collections on verses and units in the writable `paths.labels` file, Markdown / CSV export

Backend, models, code health
- [x] C1 (done, M64) Extra training pairs from OpenBible and ETCBC between train-split books (eases §8.4's bias); Sefaria / ETCBC / OpenBible dev with a paired bootstrap; test untouched
- [x] C2 (done, M71) Newer encoders on dev: DictaBERT through `train-sup`; multilingual embedders (multilingual-e5-large, Qwen3-Embedding-0.6B) inference only, fp32; availability checked first
- [x] C3 (done, M73) Pericope / chapter retrieval (test nDCG@10 0.068 / 0.157): sequence and phrase coverage as a third fusion list, on dev
- [x] C4 (done, M72) `bsim compare-builds old new`: row and `meta` diff per table (what M54 did by hand)
- [x] C5 (done, M74) Split `api/models.py`, `api/queries.py`, `store/db.py` per feature; `Literal` unions in pydantic so `schema.gen.ts` can replace most of `web/src/api/types.ts`; a panel registry for `UnitPage.tsx`

Suggested order: A1 → A2 → B1 → A3 → C1 (all done, M60–M64).

From the 2026-10-15 review: letters and numbers, and geography. Each is a test with a claim fixed in advance and known answers, as before. Gematria and codes are framed like the sevens check (§16.14), whose verdict can come out either way. Places are shown in Hebrew only (D5, D56); English gazetteer names are internal join keys.

Letters and numbers
- [x] G1 (done, M76) Gematria layer: `text/gematria.py` over the consonantal text in four systems listed in config (standard, mispar gadol with finals 500–900, ordinal, reduced); values per word, verse and lemma in the DB; `/gematria?value=&system=` (words, lemmas, verses, paged); value in the word panel, a reader layer, `= 318` in the jump box, a calculator page. Known values as unit tests: אליעזר 318 (Gen 14:14), נחש = משיח 358, יין = סוד 70
- [x] G2 (done, M82) Do equal values link related words? Claim: words of equal standard gematria are no closer in meaning (SDBH domain overlap, root family §16.38, BEREL word vectors as §16.23) than pairs matched on letter count and frequency band; the traditional equivalences in config ranked. Verse check: the numerical properties claimed for Gen 1:1 (2701 = 37 × 73, 7 words, 28 letters) counted over all 23k verses, a look-elsewhere control
- [x] G3 (done, M77) Atbash and albam: words whose atbash (א↔ת) or albam (א↔ל) form is a name or lemma elsewhere. Known answers: ששך = בבל (Jer 25:26, 51:41), לב קמי = כשדים (Jer 51:1). Claim: atbash gives more cipher → name hits in Jer 25 and 51 than 999 random involutive letter substitutions, and no more elsewhere. Atbash / albam forms in the word panel (linked when they are words), a Ciphers tab with q
- [x] G4 (done, M78) The Masorah's counts: middle letter (the ו of גחון, Lev 11:42), middle words (דרש דרש, Lev 10:16), middle verse (Lev 8:8) of the Torah (Kiddushin 30a) and the Masorah's verse total per book, computed on our text (qere and ketiv apart); how far each lands from the tradition, book counts that differ listed with the reason. A check of our text and versification
- [x] G5 (done, M85) Equidistant letter sequences: terms fixed in config (a rabbis-and-dates list or a smaller list of names), skips up to N over the Torah letter string against Genesis with letters shuffled, with verses shuffled, and a non-Torah block of the same length. Claim: no more hits than the controls; shown as counts against controls, not "codes"

Geography
- [x] P1 (done, M79) Gazetteer: download group `geo`, TIPNR (STEPBible, CC BY 4.0: Strong's → place) and OpenBible.info Bible Geocoding (CC BY 4.0: coordinates with confidence); availability and licenses checked first, recorded in DESIGN §1. Place lemma → site(s) → lat / lon, several sites per Strong's number resolved by the verses in `entity_mentions`; SDBH name subdomains split places into town / region / landform / water and peoples from persons; hand check of 50 (as M43); `places.parquet` and a DB table
- [x] P2 (done, M80) A real map: offline SVG of the region (Natural Earth coastline, rivers, Dead Sea; public domain), projected by hand like the other charts, no tile server or new dependency; points by mentions and kind, filters by book / chapter / unit; place panel (book strip, co-mentioned places); "where this happens" on chapter and pericope pages; a places layer in the reader
- [x] P3 (done, M81) Are place lists ordered on the ground? Claim: consecutive places in boundary and itinerary lists lie closer than in the list shuffled. Known lists in config: Num 33, Num 34, Josh 15:21–62, Josh 19, Gen 10. Second claim: Joshua's town lists cluster by district against a shuffle across districts
- [x] P4 (done, M83) The geographic arc: each chapter's centroid weighted by its place mentions. Claims: consecutive chapters lie closer than in a shuffled order; known moves (Gen 11–12 Ur / Haran → Canaan, Gen 46 → Exodus Egypt, Exod 12 → Numbers wilderness, 2 Kgs 25 Babylon); the oracles against the nations (Amos 1–2, Isa 13–23, Jer 46–51, Ezek 25–32) spread wider than other prophetic chapters. The path of the centroids per book on the P2 map
- [x] P5 (done, M84) Distance decay: place co-mention links (`entity_links`, G²) against distance. Claim: link strength falls with distance (Spearman, against coordinates shuffled among places); far apart but strongly linked pairs as leads ("Dan to Beersheba")

Viewer
- [x] V1 (done, M86; `= 318` in M76) Jump box: `= 318` (gematria), and a place name opens the map at it
- [x] V2 (done, M87) Dossier entries: a unit's gematria and cipher hits and its places

Suggested order: G1 → G3 → G4 (known answers, cheap), then P1 → P2 → P3 (geography needs P1's data first), then G2, P4, P5; G5 last.

From the 2026-10-21 request: a family tree of everyone in the Hebrew Bible. Every link has its verse, conflicts in the text are marked, and the tree collapses at any node. The work is reviewed block by block and handed off in `docs/genealogy/PROGRESS.md`. Names are shown in Hebrew only (D5, D92).

Family tree
- [x] F1 (done, M88) Data: TIPNR's family columns, proof verses by cue, curated review files, the tables
- [x] F2 (done, M89) Viewer: the collapsible tree, side panel, markers, search, responsive
- [ ] F3 (M90) The review in 19 blocks, in canon order
- [ ] F4 (M91) Parallel genealogies against each other, tribe attachments, jump box and dossier
- [ ] F5 (later) Rabbinic identifications as a third kind of conflict, sources fetched from Sefaria

Suggested order: F1 → F2 → F3 → F4; F5 when asked.
