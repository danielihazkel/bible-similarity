# Design — bible-similarity

Detailed technical design. See [ARCHITECTURE.md](ARCHITECTURE.md) for the system overview and [TASKS.md](TASKS.md) for the build plan. Items marked **⚠ verify** must be confirmed during implementation.

---

## 1. Data sources & licenses

| Source | Used for | Access | License |
|---|---|---|---|
| **OSHB morphhb** (Westminster Leningrad Codex) | lemmas, morphology, model input text, pe/samekh cross-check | `https://raw.githubusercontent.com/openscriptures/morphhb/master/wlc/{Book}.xml` (OSIS XML, 39 files) — pin to a release tag/commit | WLC public domain; morphology CC BY 4.0 |
| **Sefaria — *Miqra according to the Masorah* (MAM)** | display text (pointed + te'amim), pericope markers | `https://storage.googleapis.com/sefaria-export/json/Tanakh/{Section}/{Book}/Hebrew/Miqra according to the Masorah.json` | **CC-BY-SA** (stated in the file's `license` field) |
| **Sefaria schemas** | parasha boundaries | `https://storage.googleapis.com/sefaria-export/schemas/{Book}.json` → `alts.Parasha.nodes[]` | Sefaria |
| **Sefaria links** | training pairs + evaluation gold | `https://storage.googleapis.com/sefaria-export/links/links{0..12}.csv` | Sefaria (per-link sources vary; research use) |
| **BEREL 3.0** | base encoder | HF `dicta-il/BEREL_3.0` (BERT, ~0.2B params, fp32 safetensors) | Apache-2.0 |
| **BGE-M3** | multilingual baseline | HF `BAAI/bge-m3` | MIT |

Rules:
- `bsim download` writes `data/raw/manifest.json` with `{url, sha256, bytes, downloaded_at}` per file. The OSHB commit SHA is recorded.
- Raw data is never committed. Sefaria fallback if the bucket layout changes: the public API (`/api/v3/texts/{ref}?version=hebrew|Miqra according to the Masorah`, `/api/v2/raw/index/{book}`). **⚠ verify** fallback only if needed.
- BEREL tokenizer: must use `AutoTokenizer` / `BertTokenizerFast` (the model card warns `BertTokenizer` gives bad results).

### 1.1 Confirmed source formats
- **OSHB** `<verse osisID="Ruth.1.1">` contains `<w lemma="c/1961" morph="HC/Vqw3ms" id="08xeN">וַ/יְהִ֗י</w>` (morpheme boundaries marked with `/` in both lemma and surface), plus `<seg type="x-maqqef|x-sof-pasuq|x-paseq|x-pe|x-samekh">` and ketiv/qere words (`type="x-ketiv"` / `x-qere`). Lemmas are Strong's-based numbers, optionally with a sense letter (`1121 a`); prefixes are letters (`b`, `c`, `d`, `k`, `l`, `m`, `s`).
- **MAM JSON**: `text` is `list[chapter][verse] -> str` with embedded HTML: `<span class="mam-spi-pe">{פ}</span>`, `<span class="mam-spi-samekh">{ס}</span>`, ketiv/qere spans (`mam-kq`, `mam-kq-k`, `mam-kq-q`, `mam-kq-trivial`), footnotes (`<sup class="footnote-marker">`, `<i class="footnote">`), `<big>`, `<small>`, `<b>`, `<br>`, `&nbsp;`.
- **Links CSV** header: `Citation 1,Citation 2,Conection Type,Text 1,Text 2,Category 1,Category 2` (note Sefaria's typo "Conection"). Citations may be ranges (`Exodus 1:1-6:1`).
- **Schema** `alts.Parasha.nodes[]`: each node has `sharedTitle` (e.g. `Bereshit`), `heTitle`, `wholeRef` (e.g. `Genesis 1:1-6:8`), and aliyah `refs`.

---

## 2. Canonical identifiers & versification

- **Hebrew (Masoretic) versification throughout** — both OSHB and MAM use it (e.g. Malachi 3 has 24 verses, Joel has 4 chapters).
- **Canon order**: Jewish order — Torah, Nevi'im (Joshua…Malachi, Twelve as separate books), Ketuvim (Psalms, Proverbs, Job, Song of Songs, Ruth, Lamentations, Ecclesiastes, Esther, Daniel, Ezra, Nehemiah, I & II Chronicles), following Sefaria's category tree.
- `canon.py` holds the book table: `book_id, sefaria_name, osis_name, he_name, section (Torah|Prophets|Writings), n_chapters`.
- **`verse_id`** = 0-based ordinal of the verse in canon order. It is the row index of every embedding matrix. Also stored: `ref` (Sefaria style, `Genesis 1:1`), `osis` (`Gen.1.1`), `book_id`, `chapter`, `verse`.
- `build-corpus` **asserts** that per-chapter verse counts agree between OSHB and MAM; any mismatch fails the stage with a report (none are expected; if one appears it is resolved explicitly in `canon.py`).

---

## 3. Text processing

### 3.1 Two text layers per verse
| Field | Source | Use |
|---|---|---|
| `text_display` | MAM, HTML cleaned to plain pointed text with te'amim; *qere* shown, ketiv kept in a separate field for tooltip | viewer |
| `text_model` | OSHB, consonantal | encoder input |
| `lemmas` | OSHB | lexical mode, highlighting |

### 3.2 Normalization (`text/normalize.py`)
- Strip cantillation and vowel points: Unicode `U+0591–U+05C7` except letters; remove `U+05BD` meteg, `U+05C0` paseq, `U+05C3` sof pasuq.
- Maqaf (`U+05BE`) → space.
- Final letters (ך ם ן ף ץ) kept as-is for the encoder input (BEREL saw them); folded to non-final forms **only** for surface-form matching keys.
- Remove morpheme separators `/` from OSHB surface forms.
- Ketiv/qere policy: `text_model` uses the **qere** reading (what is read, closer to rabbinic usage BEREL was trained on); lemmas follow whichever word OSHB tags for that reading. Configurable (`text.kq: qere|ketiv`).
- MAM cleaning: drop footnotes, `{פ}`/`{ס}` markers (recorded as unit boundaries first), `&nbsp;`, HTML tags; `<big>`/`<small>` letters kept as normal letters.

### 3.3 Lemma tokens
- Parse `lemma="c/1961"` → morphemes `["c", "1961"]`; keep numeric (content) lemmas only, dropping prefix particles (`b,c,d,k,l,m,s`) and the sense letter normalised as part of the key (`1121a`).
- Function-word lemmas (את, אשר, כי, על, אל, לא, כל, …) remain in the token stream; BM25 IDF handles them, and they are needed for bigrams.

### 3.4 Word alignment (OSHB ↔ MAM) for highlighting
MAM (Aleppo-based) and WLC (Leningrad) differ in a handful of letters (plene/defective spelling, rare word differences). Per verse, tokenize both consonantal texts, run `difflib.SequenceMatcher` on the token lists, map equal and 1:1 replaced tokens. Store `words.display_idx` (nullable). `corpus_report.md` reports the alignment coverage; acceptance threshold **≥ 99 %** of OSHB words aligned.

---

## 4. Units

| Unit | Definition | `unit_id` |
|---|---|---|
| verse | one verse | `v:{verse_id}` |
| chapter | standard chapter | `c:{book}:{chapter}` |
| parasha | Sefaria `alts.Parasha` `wholeRef` (54; combined parashiyot not created as extra units) | `p:{sharedTitle}` |
| pericope | span between consecutive MAM `{פ}`/`{ס}` markers; each pericope records its closing marker type (`pe`=petucha, `samekh`=setuma) | `s:{n}` |

- Pericope breaks that occur **mid-verse** (*piska be'emtza pasuk*) are snapped to the end of that verse.
- Pericopes run across chapter boundaries but not across books (a book end is always a break).
- OSHB `x-pe`/`x-samekh` counts are compared to MAM per book in `corpus_report.md` (Genesis: MAM 43 pe / 48 samekh vs OSHB 42 / 50 — differences are expected, MAM is authoritative).
- Very long pericopes are kept whole (they are retrieved through best-match aggregation, which does not care about length).
- Tables: `units(unit_id, unit_type, label_en, label_he, book_id, start_verse_id, end_verse_id, n_verses)`; `unit_members(unit_id, verse_id)`. All units are contiguous verse ranges.

---

## 5. Similarity modes

### 5.1 Lexical (`bm25_lemma`)
- Documents = verses; tokens = content lemmas + lemma bigrams (adjacent content lemmas).
- BM25 (k1 = 1.2, b = 0.75, tuned on dev), implemented as sparse matrices: query weights × document weights → scipy sparse matmul gives all-pairs scores in one pass.
- **Formula down-weighting** (`lexical/formulas.py`): find lemma n-grams (n = 3..6) that occur in more than *T* verses (default *T* = 15; e.g. *וידבר ה' אל משה לאמר*, *ויאמר ה' אל משה*, *כה אמר ה'*). Tokens inside a formula occurrence get weight × α (default α = 0.2). Tuned on dev; the list is exported to `formulas.parquet` for inspection.
- Baseline variant `bm25_surface`: same on normalized surface forms (finals folded, prefixes not stripped) — for the eval report only.
- **Unit level**: sublinear TF-IDF cosine over each unit's lemma bag (with the same formula down-weighting), sparse matmul all-pairs.

### 5.2 Semantic
Candidates (all produce L2-normalized float32 vectors from `text_model`):

| System | Encoder |
|---|---|
| `berel_mean` | BEREL 3.0, mean pooling of last hidden state, no training |
| `bge_m3` | BGE-M3 dense vector, no training |
| `berel_simcse` | BEREL 3.0 + unsupervised SimCSE (§7.1) |
| `berel_sup` | `berel_simcse` + supervised contrastive fine-tune (§7.2) |
| `*_csls` | any of the above with CSLS hubness correction |

**CSLS**: `csls(x,y) = 2·cos(x,y) − r(x) − r(y)`, where `r(·)` is the mean cosine to its 10 nearest neighbours. Reduces "hub" verses that appear in everyone's top-k. Kept only if it improves dev metrics.

The final `semantic` system is chosen on **dev** (not test) by nDCG@10.

### 5.3 Fused
Weighted Reciprocal Rank Fusion over the lexical and semantic top-50 lists:
`fused(t) = w_lex / (60 + rank_lex(t)) + w_sem / (60 + rank_sem(t))`, missing ranks contribute 0. Weights tuned on dev (grid over `w_lex ∈ {0.25…1.0}`, `w_sem = 1`). Stored with `lex_score, lex_rank, sem_score, sem_rank` for the viewer's score breakdown.

---

## 6. Retrieval

### 6.1 Verse top-k
- Dense: load the `N × d` matrix on GPU; for chunks of 2,048 rows compute `chunk @ E.T` (fp32), set self-similarity to −∞, `torch.topk(k=50)`. CPU fallback: numpy + `argpartition`.
- Sparse (lexical): sparse matmul per chunk, then the same top-k.
- **Only self is excluded at compute time.** Neighbour (±2 verses, same book), same-chapter and same-book exclusion are applied at query time over the stored 50 (§9, §10). The eval harness applies the ±2 neighbour filter to both predictions and gold by default.

### 6.2 Unit aggregation (chapter, pericope, parasha)
Two semantic aggregations, both evaluated:
1. **Mean**: unit vector = normalized mean of member verse vectors → dense top-k as above.
2. **Best-match average (BMA, primary)**: for units A, B with verse sets: `s(A→B) = mean_{a∈A} max_{b∈B} cos(a,b)`, `BMA(A,B) = ½(s(A→B) + s(B→A))`. Computation: for each unit A, `S = E[A] @ E.T` (|A| × N on GPU), segment-max over B's verse ranges (`torch.Tensor.scatter_reduce(..., 'amax')` with a verse→unit index), mean over rows → `s(A→·)`. Symmetrize after both directions are computed. Feasible for 929 chapters and a few thousand pericopes; trivial for 54 parashiyot.
- Lexical units use TF-IDF cosine (§5.1); fused units use RRF over unit-level lexical & semantic lists.
- Parasha ↔ parasha only (Torah); chapters and pericopes over the whole Tanakh. Self excluded; for chapters/pericopes, same-book filtering is a query-time option.

---

## 7. Training (GTX 1080 Ti, fp32)

Common: `sentence-transformers` (v3+ trainer API), max_seq_length 128 (**⚠ verify** in M2 that the longest verse, Esther 8:9, fits after BEREL tokenization; raise to 160 if not), mean pooling head on BEREL, fixed seeds, `fp16=False, bf16=False`, checkpoints to `models/{name}/`, training config + config hash saved alongside.

### 7.1 SimCSE (unsupervised)
- Data: all ~23k verses (no labels → no test leakage of gold pairs).
- Loss: MultipleNegativesRankingLoss with `(verse, verse)` pairs; dropout (0.1) provides the noise.
- Batch 64, lr 3e-5, 1–3 epochs (a few minutes per epoch on the 1080 Ti). Pick the epoch by dev recall@10.

### 7.2 Supervised contrastive
- Positives: **train-split** Sefaria link pairs (§8), both directions.
- Hard negatives (`train/negatives.py`): for each anchor, verses ranked 5–50 by `bm25_lemma` that are **not** linked to it, not within ±2 neighbours, and not in dev/test books. One hard negative per pair → triplets.
- Loss: **CachedMultipleNegativesRankingLoss** (mini_batch_size 32, batch 256) — large effective batch without exceeding 11 GB.
- lr 2e-5, warmup 10 %, up to 5 epochs, eval every N steps on dev (recall@10 via an `InformationRetrievalEvaluator` built from dev links); keep the best checkpoint.
- Start from `models/berel-simcse` (fallback: raw BEREL, compared on dev).

---

## 8. Gold links, splits & evaluation

### 8.1 Link processing (`data/links.py`)
1. Read all `links*.csv`; keep rows with `Category 1 == Category 2 == "Tanakh"`.
2. Parse both citations into verse ranges (book name → `canon.py`; handle `Book C:V`, `Book C:V-V`, `Book C:V-C:V`, whole chapters `Book C`).
3. Expand to verse pairs:
   - equal-length ranges → positional alignment (handles parallels like `II Samuel 22 ↔ Psalms 18`);
   - both sides ≤ 3 verses → Cartesian product;
   - otherwise → keep as a **unit-level** link only (used for chapter/pericope evaluation, not for verse training).
4. Drop self-pairs and pairs within ±2 verses; symmetrize; deduplicate. Keep `connection_type` for analysis.
5. Write `links.parquet(src_vid, tgt_vid, connection_type, level)` and `links_report.md` (counts per book, per type).

### 8.2 Split by book
- Books are assigned to train / dev / test with a fixed seed so that the pairs are split roughly **75 / 10 / 15**. Greedy balancing by pair count; the assignment is saved in `splits.json`.
- A pair belongs to **test** if either verse is in a test book, else to **dev** if either verse is in a dev book, else **train**. Training uses train pairs only; hard negatives never involve dev/test books.
- A pytest asserts there is no train pair touching a dev/test book.

### 8.3 Metrics
- Verse level: for each query verse with ≥ 1 gold link in the split: **recall@{1,5,10,50}, MRR@10, nDCG@10** (binary relevance). The ±2 neighbour filter is applied to predictions.
- Unit level: chapter (and pericope) pairs are gold when they share ≥ *m* verse links (default *m* = 2) or a unit-level link; same metrics.
- `bsim evaluate` runs every system in `artifacts/topk/` on dev (default) or test (`--split test`, run once at the end) and writes `artifacts/eval/report.md` + `metrics.json` (system × unit type × metric table, plus the 20 worst-missed gold pairs per system for error analysis).

### 8.4 Known limitation
Sefaria links reflect what commentators and editors linked, biased toward "famous" connections. The supervised model learns that notion of relatedness. The `lexical` mode and the un-supervised baselines remain available in the viewer as an independent view.

---

## 9. Results database (`artifacts/results.sqlite`)

```sql
CREATE TABLE books   (book_id INTEGER PRIMARY KEY, name TEXT, he_name TEXT, osis TEXT, section TEXT, n_chapters INTEGER);
CREATE TABLE verses  (verse_id INTEGER PRIMARY KEY, book_id INTEGER, chapter INTEGER, verse INTEGER,
                      ref TEXT, osis TEXT, text_display TEXT, text_plain TEXT, ketiv_note TEXT);
CREATE TABLE words   (verse_id INTEGER, idx INTEGER, display_idx INTEGER, surface TEXT, lemma TEXT, morph TEXT,
                      PRIMARY KEY (verse_id, idx));
CREATE TABLE units   (unit_id TEXT PRIMARY KEY, unit_type TEXT, label_en TEXT, label_he TEXT,
                      book_id INTEGER, start_verse_id INTEGER, end_verse_id INTEGER, n_verses INTEGER);
CREATE TABLE unit_members (unit_id TEXT, verse_id INTEGER, PRIMARY KEY (unit_id, verse_id));
CREATE TABLE matches (unit_type TEXT, mode TEXT, src_id TEXT, rank INTEGER, tgt_id TEXT, score REAL,
                      lex_score REAL, lex_rank INTEGER, sem_score REAL, sem_rank INTEGER,
                      PRIMARY KEY (unit_type, mode, src_id, rank));
CREATE TABLE lemma_gloss (lemma TEXT PRIMARY KEY, he_lemma TEXT);   -- for showing shared lemmas
CREATE TABLE meta    (key TEXT PRIMARY KEY, value TEXT);            -- model names, config hash, build date, source SHAs
```
Size estimate: verse matches ≈ 23.2k × 50 × 3 modes ≈ 3.5M rows (~200 MB). `src_id`/`tgt_id` use the unit_id strings (`v:123`, …) for uniformity.

---

## 10. API (FastAPI)

| Endpoint | Purpose |
|---|---|
| `GET /api/books` | book list with chapter counts |
| `GET /api/units/{type}?book=` | list units of a type (for navigation) |
| `GET /api/unit/{unit_id}` | unit metadata + its verses (display text) |
| `GET /api/similar/{unit_id}?mode=lexical\|semantic\|fused&k=10&exclude=neighbors,chapter,book` | top-k from `matches`, filtered at query time; each hit includes score + lex/sem breakdown + target text (verse) or label/preview (larger units) |
| `GET /api/explain?a={verse_id}&b={verse_id}` | shared lemmas with word indices in both verses (for highlighting); formula tokens flagged |
| `GET /api/compare?a={unit_id}&b={unit_id}` | verse-level alignment of two units: for each verse in A its best match in B (and vice versa) with cosine, computed from the cached verse matrix; plus shared lemmas per pair |
| `GET /api/search?q=...&mode=&k=` | free-text Hebrew search over verses (§10.1) |
| `GET /api/meta` | build info |

### 10.1 Free-text search
- Query is normalized (§3.2; pointed input accepted).
- `semantic`: encode with the final encoder (GPU if available, else CPU — a single short query takes milliseconds), dot product with the verse matrix, top-k.
- `lexical`: OSHB lemmas don't exist for arbitrary text, so a **surface-form BM25** index is used, with greedy Hebrew prefix stripping (combinations of ו ה ב כ ל מ ש, keeping ≥ 2 root letters) applied to both query and corpus tokens.
- `fused`: RRF of the two.

---

## 11. Viewer (React + Vite + TypeScript)

- **Global**: `dir="rtl"` for Hebrew text blocks (UI chrome may be LTR or Hebrew), fonts **Ezra SIL** / **Noto Serif Hebrew** (OFL) for proper te'amim rendering, toggle: *show te'amim / niqqud only / consonants only*.
- **Browse**: book → chapter → verse list; each verse clickable; tabs for chapter / parasha / pericope views.
- **Unit detail**: source text on top; results panel with **mode toggle** (lexical / semantic / fused), **k selector** (10 / 20 / 50), **filter checkboxes** (hide neighbours ±2, same chapter, same book), each result showing ref, text, score and a small bar breakdown (lex vs sem rank). Hovering/expanding a verse result calls `/explain` and **highlights shared lemmas** in both texts (formula words styled dimmer).
- **Compare**: pick two units (from a result or manually) → side-by-side columns with best-match verse pairs connected/colour-coded by similarity and shared-lemma highlights.
- **Search**: text box (Hebrew keyboard input), mode toggle, results list linking to unit detail.
- State in the URL (`/unit/v:123?mode=fused&k=20&exclude=neighbors`) so views are shareable/bookmarkable.

---

## 12. Configuration

`configs/default.yaml` holds every tunable: paths, OSHB commit, `k: 50`, neighbour window `2`, BM25 `k1/b`, formula `T/α`, encoder names, training hyperparameters, seeds, RRF weights, split ratios, unit-gold `m`. Each artifact stores the hash of the config section it depends on; `bsim` warns when an artifact is stale.

---

## 13. Testing strategy

- Unit tests: normalization (points stripped, maqaf, finals), lemma parsing, ref parsing & range expansion, split leakage, top-k self-exclusion, filters, RRF, BMA on a toy matrix, metrics against hand-computed values.
- Data assertions (in pipeline, not pytest): verse-count equality, alignment coverage ≥ 99 %, 54 parashiyot, every verse belongs to exactly one chapter and one pericope.
- API: FastAPI `TestClient` against a tiny fixture DB.
- Sanity spot-checks printed by `bsim evaluate`: top-5 lists for a few well-known verses (e.g. Ps 14:1, Ex 20:2, II Sam 22:2).

---

## 14. Risks & open items

| Risk | Mitigation |
|---|---|
| Sefaria bucket layout or file names change | manifest + API fallback; paths in config |
| MAM vs WLC textual differences break alignment | difflib alignment, coverage report, highlight only aligned words |
| PyTorch drops cu126 / Pascal entirely | pin torch version + index in `uv.lock` |
| Sparse links in some books → noisy per-book metrics | report per-split totals; greedy-balanced split |
| Formula verses dominate results | formula down-weighting + CSLS + query-time filters |
| Supervised model overfits to "famous" links | keep lexical and SimCSE modes available; book-level split |
| BEREL tokenizer misuse | always `AutoTokenizer`; test that tokenization of a sample verse has no `[UNK]` |

---

## 15. Decision log

| # | Topic | Decision |
|---|---|---|
| D1 | Similarity | Multiple modes: `lexical`, `semantic`, `fused` (switchable in viewer) |
| D2 | Units | Verse, chapter, parasha (Torah only), Masoretic pericope |
| D3 | Text sources | OSHB/WLC for lemmas & model input; Sefaria MAM for display, parasha & pericope metadata; aligned by ref. No ETCBC |
| D4 | License posture | Personal / research use (MAM is CC-BY-SA; attribute in viewer footer) |
| D5 | Language | Hebrew only; no translation anywhere |
| D6 | ML scope | Baselines → SimCSE → supervised contrastive with hard negatives → RRF fusion |
| D7 | Gold data | Sefaria Tanakh↔Tanakh links only; split by book 75/10/15 |
| D8 | Hardware | GTX 1080 Ti: fp32, PyTorch cu126, CachedMNRL; BGE-M3 inference only |
| D9 | Deliverable | Offline pipeline → SQLite → FastAPI + React (Vite, TS) viewer |
| D10 | Viewer features | Mode switch + score breakdown, shared-lemma highlighting, side-by-side compare, free-text search |
| D11 | Top-k | Store k = 50 per unit per mode (self excluded); neighbour/chapter/book filters at query time |
| D12 | Tooling | uv + pyproject; git; raw data downloaded by scripts into gitignored `data/`; models/results local |
| D13 | Docs | Markdown in `docs/` |
