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
