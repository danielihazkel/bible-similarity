# Design — bible-similarity

Detailed technical design. See [ARCHITECTURE.md](ARCHITECTURE.md) for the system overview and [TASKS.md](TASKS.md) for the build plan. Items marked **⚠ verify** must be confirmed during implementation.

---

## 1. Data sources & licenses

| Source | Used for | Access | License |
|---|---|---|---|
| **OSHB morphhb** (Westminster Leningrad Codex) | lemmas, morphology, model input text, pe/samekh cross-check | `https://raw.githubusercontent.com/openscriptures/morphhb/master/wlc/{Book}.xml` (OSIS XML, 39 files) — pin to a release tag/commit | WLC public domain; morphology CC BY 4.0 |
| **Sefaria — *Miqra according to the Masorah* (MAM)** | display text (pointed + te'amim), pericope markers | `https://storage.googleapis.com/sefaria-export/json/Tanakh/{Section}/{Book}/Hebrew/Miqra according to the Masorah.json` | **CC-BY-SA** (stated in the file's `license` field) |
| **Sefaria schemas** | parasha boundaries | `https://storage.googleapis.com/sefaria-export/schemas/{Book_Slug}.json` (spaces → underscores, e.g. `I_Samuel.json`) → `alts.Parasha.nodes[]` | Sefaria |
| **Sefaria links** | training pairs + evaluation gold | `https://storage.googleapis.com/sefaria-export/links/links{N}.csv`, discovered by listing the bucket (17 files, ~680 MB as of 2026-10) | Sefaria (per-link sources vary; research use) |
| **BEREL 3.0** | base encoder | HF `dicta-il/BEREL_3.0` (BERT, ~0.2B params, fp32 safetensors) | Apache-2.0 |
| **BGE-M3** | multilingual baseline | HF `BAAI/bge-m3` | MIT |

Rules:
- `bsim download` writes `data/raw/manifest.json` with `{url, sha256, md5, bytes, downloaded_at}` per file. Sefaria files are verified against the GCS `md5Hash` (via the JSON API `storage/v1/b/sefaria-export/o`); OSHB files are pinned by commit (`3d15126`, 2024-08-27) and verified against their recorded sha256.
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
- **`verse_id` follows MAM/Sefaria versification** (23,206 verses; D14), the numbering used by the Sefaria links and the display text. OSHB (23,213 verses) differs in three places, resolved by `canon.VERSE_OVERRIDES` (OSHB words of merged verses are concatenated in order):
  - Exodus 20: OSHB 20:13–16 (the four short commandments) = MAM 20:13; OSHB 20:17–26 = MAM 20:14–23.
  - Deuteronomy 5: OSHB 5:17–20 = MAM 5:17; OSHB 5:21–33 = MAM 5:18–30.
  - OSHB Numbers 25:19 (ויהי אחרי המגפה) opens MAM 26:1.
- `build-corpus` **asserts** that per-chapter verse counts agree between MAM and the re-keyed OSHB; any mismatch fails the stage with a report and must be resolved explicitly in `canon.py`.

---

## 3. Text processing

### 3.1 Two text layers per verse
| Field | Source | Use |
|---|---|---|
| `text_display` | MAM, HTML cleaned to plain pointed text with te'amim; *qere* shown, ketiv kept in a separate field for tooltip | viewer |
| `text_model` | OSHB, consonantal | encoder input |
| `lemmas` | OSHB | lexical mode, highlighting |

### 3.2 Normalization (`text/normalize.py`)
- Consonantal text keeps **Hebrew letters (`U+05D0–U+05EA`) and whitespace only**: this removes points, te'amim, meteg, paseq, sof pasuq, inverted nun and the combining grapheme joiner (`U+034F`, used in MAM's ירושלם) with a single rule.
- Maqaf (`U+05BE`) → space.
- Final letters (ך ם ן ף ץ) kept as-is for the encoder input (BEREL saw them); folded to non-final forms **only** for surface-form matching keys.
- Remove morpheme separators `/` from OSHB surface forms.
- Ketiv/qere policy: `text_model` uses the **qere** reading (what is read, closer to rabbinic usage BEREL was trained on); lemmas follow whichever word OSHB tags for that reading. Configurable (`text.kq: qere|ketiv`).
- MAM cleaning: drop footnotes, the inverted nun, `{פ}`/`{ס}` markers (recorded as unit boundaries first, with whether they fall mid-verse), `&nbsp;`/`&thinsp;`/`<br>`, HTML tags; `<big>`/`<small>`/`<b>` content kept (the paseq/legarmeh ׀ stays in `text_display`); qere shown, ketiv moved to `ketiv_note`; `mam-kq-trivial` words kept as they are.
- Display tokens (`normalize.display_tokens`): `text_display` split on whitespace and after each maqaf; `words.display_idx` indexes this list (stored as `verses.display_tokens`).

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
- Weights in BM25: document side uses the formula-weighted term frequency and length; query side is binary BM25 with each term weighted by its max token weight in the query verse. A bigram's weight is the min of its two tokens' weights. `bsim lexical` stores the doc and query matrices; scores = `query @ doc.T` (M5 does the top-k).
- The exported formula list keeps only *closed* n-grams (not a prefix/suffix of a longer formula with the same verse count); down-weighting uses all of them.
- Baseline variant `bm25_surface`: same on normalized surface forms (finals folded, prefixes not stripped) — for the eval report only.
- **Unit level**: sublinear TF-IDF cosine over each unit's lemma bag (unigrams + bigrams, with the same formula down-weighting), sparse matmul all-pairs. With raw count `c` and weighted count `w`, tf = `(1 + log c)·(w/c)`; smooth idf within the unit type; rows L2-normalized.

### 5.2 Semantic
Candidates (all produce L2-normalized float32 vectors from `text_model`):

| System | Encoder |
|---|---|
| `berel_mean` | BEREL 3.0, mean pooling of last hidden state, no training |
| `bge_m3` | BGE-M3 dense vector, no training |
| `berel_simcse` | BEREL 3.0 + unsupervised SimCSE (§7.1) |
| `berel_sup` | BEREL 3.0 + supervised contrastive fine-tune (§7.2; starting from `berel_simcse` lost the dev ablation) |
| `*_csls` | any of the above with CSLS hubness correction |

**CSLS**: `csls(x,y) = 2·cos(x,y) − r(x) − r(y)`, where `r(·)` is the mean cosine to its 10 nearest neighbours. Reduces "hub" verses that appear in everyone's top-k. Kept only if it improves dev metrics.

- Encoders are registered in `encoders.systems` (`name → {model, pooling}`) and all run through sentence-transformers in fp32 at `text.max_seq_length` (128). `pooling: mean` = HF encoder + mean pooling (raw BEREL, tokenizer via `AutoTokenizer`, fast tokenizer asserted); `pooling: native` = the model's own ST config (BGE-M3: CLS + normalize = its dense vector; fine-tuned checkpoints under `models/`). `bsim embed` records `[UNK]` and truncation counts in `{X}.meta.json`.
- `{base}_csls` is resolved by `bsim topk` from `embeddings/{base}.npy`: `r(·)` (`retrieval.csls_neighbors`, self excluded) is computed at top-k time and the stored scores are CSLS values, not cosines.

The final `semantic` system is chosen on **dev** (not test) by nDCG@10.

### 5.3 Fused
Weighted Reciprocal Rank Fusion over the lexical and semantic top-50 lists:
`fused(t) = w_lex / (60 + rank_lex(t)) + w_sem / (60 + rank_sem(t))`, missing ranks contribute 0; the best 50 are kept, ties ordered by target. Weights tuned on dev (`bsim fuse --tune`, grid `fusion.w_lex_grid` = {0.25, 0.5, 0.75, 1.0, 1.5, 2.0}, `w_sem = 1`; the grid goes above 1 because lexical beats semantic on dev). Stored with `lex_score, lex_rank, sem_score, sem_rank` for the viewer's score breakdown.

- Fused lists per unit type (`retrieve/fusion.py:final_lists`): verse = `bm25_lemma` + `berel_sup_csls`; chapter / pericope / parasha = `tfidf` + `berel_sup_csls_bma` (§6.2).
- One weight for every unit type, chosen on verse dev nDCG@10 (2026-10): `w_lex = 1.0` → **0.189** (recall@50 0.400) vs `bm25_lemma` 0.176 and `berel_sup_csls` 0.150. With `w_lex < 1` the fused top-50 is essentially the semantic list (semantic rank 50 outscores lexical rank 1).
- At unit level fusion does not beat TF-IDF on dev: chapter fused 0.168 (best grid point 0.171 at 2.0) vs `tfidf` 0.192; pericope fused 0.114 vs `tfidf` 0.112. The viewer keeps all three modes; this is recorded rather than tuned away per unit type, since unit gold is small (154 chapter / 348 pericope dev queries).

---

## 6. Retrieval

### 6.1 Verse top-k
- Dense: load the `N × d` matrix on GPU; for chunks of 2,048 rows compute `chunk @ E.T` (fp32), set self-similarity to −∞, `torch.topk(k=50)`. CPU fallback: the same code on a CPU torch device.
- Sparse (lexical): scipy sparse matmul per chunk on the CPU, then the same top-k on the device. Hits with score ≤ 0 (no shared terms) are dropped, so a verse can have fewer than 50.
- Within the top-k, ties are ordered by target `verse_id`. Ranks are 1-based. `artifacts/topk/verse/{X}.parquet` gets a `{X}.meta.json` sidecar (retrieval config hash, source artifact hash, device).
- **Only self is excluded at compute time.** Neighbour (±2 verses, same book), same-chapter and same-book exclusion are applied at query time over the stored 50 (§9, §10). The eval harness applies the ±2 neighbour filter to both predictions and gold by default.

### 6.2 Unit aggregation (chapter, pericope, parasha)
Two semantic aggregations, both evaluated:
1. **Mean**: unit vector = normalized mean of member verse vectors → dense top-k as above.
2. **Best-match average (BMA, primary)**: for units A, B with verse sets: `s(A→B) = mean_{a∈A} max_{b∈B} cos(a,b)`, `BMA(A,B) = ½(s(A→B) + s(B→A))`. Computation: for each unit A, `S = E[A] @ E.T` (|A| × N on GPU), segment-max over B's verse ranges (`torch.Tensor.scatter_reduce(..., 'amax')` with a verse→unit index), mean over rows → `s(A→·)`. Symmetrize after both directions are computed. Feasible for 929 chapters and a few thousand pericopes; trivial for 54 parashiyot.
- Lexical units use TF-IDF cosine (§5.1); fused units use RRF over unit-level lexical & semantic lists.
- Parasha ↔ parasha only (Torah); chapters and pericopes over the whole Tanakh. Self excluded; for chapters/pericopes, same-book filtering is a query-time option.
- Implementation (`retrieve/units.py`, `bsim units --system X`): units of a type are disjoint contiguous verse ranges. BMA takes the system's verse scores (CSLS values for `*_csls`) in row chunks; rows and columns are the unit type's member verses only (Torah for parasha). The per-target-unit max is a `scatter_reduce('amax')`, the per-source-unit mean an `index_add_`, and the result is the full symmetric unit × unit matrix (≤ 3,482², ~22 s for 5 systems × 3 unit types). For `*_csls`, mean aggregation applies CSLS over the unit vectors (unit-level `r(·)`).
- Files: `artifacts/topk/{chapter,pericope,parasha}/tfidf.parquet` (zero-score hits dropped) and `{system}_{bma|mean}.parquet` for every aggregation in `units.aggregations`; the final one is `final_systems.unit_aggregation`.
- **BMA vs mean** (dev nDCG@10, 2026-10): with CSLS, BMA wins at both levels: `berel_sup_csls` chapter 0.156 vs 0.147, pericope 0.098 vs 0.093; `bge_m3_csls` chapter 0.148 vs 0.120, pericope 0.078 vs 0.073. Without CSLS it is mixed: `berel_sup` chapter 0.141 vs 0.135 but pericope 0.083 vs 0.091; `berel_mean` chapter 0.115 = 0.115, pericope 0.057 vs 0.068. → `unit_aggregation: bma`.

---

## 7. Training (GTX 1080 Ti, fp32)

Common: `sentence-transformers` (v3+ trainer API), max_seq_length 128 (verified in M2: the longest verse in BEREL tokens is Daniel 3:15 with 60 tokens; Esther 8:9 has 49), mean pooling head on BEREL, fixed seeds, `fp16=False, bf16=False`, checkpoints to `models/{name}/`, training config + config hash saved alongside.

### 7.1 SimCSE (unsupervised)
- Data: all ~23k verses (no labels → no test leakage of gold pairs).
- Loss: MultipleNegativesRankingLoss with `(verse, verse)` pairs; dropout (0.1) provides the noise.
- Batch 64, lr 3e-5, 1–3 epochs (~7 min per epoch on the 1080 Ti). Pick the epoch by dev recall@10 (2026-10: epoch 2, dev recall@10 0.181 vs 0.161 raw BEREL mean pooling).

### 7.2 Supervised contrastive
- Positives: **train-split** Sefaria link pairs (§8), both directions.
- Hard negatives (`train/negatives.py`): for each anchor, verses ranked 5–50 by `bm25_lemma` that are **not** linked to it, not within ±2 neighbours, and not in dev/test books. One hard negative per pair → triplets.
- Loss: **CachedMultipleNegativesRankingLoss** (mini_batch_size 32, batch 256) — large effective batch without exceeding 11 GB.
- Negatives are also excluded when linked to the positive, within ±2 of the positive, or textually identical to the anchor or positive; the rank range applies after the neighbour filter. Pairs with no eligible candidate get a random train-book verse (24 of 9,026 in 2026-10).
- lr 2e-5, warmup 10 %, up to 5 epochs, eval every 10 steps and each epoch end on dev (recall@10 via `DevEvaluator`, as in §7.1); keep the best checkpoint.
- Start point compared on dev (2026-10, recall@10 / nDCG@10): raw BEREL + HN 0.210 / 0.144 > `berel-simcse` + HN 0.208 / 0.141 > `berel-simcse` without HN 0.205 / 0.140. Config: `init_from: base`. With CSLS, `berel_sup_csls` reaches dev nDCG@10 0.150 and is the chosen semantic system. Peak VRAM 3.8 GB.

---

## 8. Gold links, splits & evaluation

### 8.1 Link processing (`data/links.py`)
1. Read all `links*.csv`; keep rows whose `Text 1` **and** `Text 2` are both canon books (D15). `Category == "Tanakh"` is not enough, because commentaries and targumim on Tanakh (`Ibn Ezra on Exodus`, `Aramaic Targum to Psalms`, …) carry that category too: it matches ~675k rows, of which only **6,468** are book↔book.
2. Parse both citations into verse ranges (`refs.parse_ref` + `RefIndex`; book name → `canon.py`; forms `Book C:V`, `Book C:V-V`, `Book C:V-C:V`, whole chapters `Book C`, chapter ranges `Book C-C`). Refs that do not exist in MAM versification (39 in 2026-10, e.g. `Genesis 21:2047-2073`, `Nehemiah 7:6-73`) drop their row and are listed in the report — no clamping.
3. Expand to verse pairs (`links.cartesian_max = 3`):
   - equal-length ranges → positional alignment (handles parallels like `II Samuel 22 ↔ Psalms 18`);
   - both sides ≤ 3 verses → Cartesian product;
   - otherwise → keep as a **unit-level** link only (used for chapter/pericope evaluation, not for verse training).
4. Drop self-pairs and same-book pairs within ±`retrieval.neighbor_window` verses (unit links: overlapping same-book ranges); symmetrize; deduplicate (positional wins over Cartesian; `connection_type` = comma-joined set of non-empty types).
5. Write `links.parquet(src_vid, tgt_vid, src_end_vid, tgt_end_vid, level, rule, connection_type, split)` — both directions stored; verse rows have `*_end_vid == *_vid`, unit rows keep their inclusive ranges — and `links_report.md` (input/drop counts, per split, per book, per type, invalid refs).

Result (2026-10): ~6.0k undirected verse pairs (5,103 rows positional, 508 Cartesian) + 818 unit links; Torah books dominate (Exodus touches 1.1k pairs).

### 8.2 Split by book
- Books are assigned to train / dev / test with a fixed seed so that the pairs are split **75 / 10 / 15**; the assignment is saved in `splits.json`. Loss = L1 distance of achieved pair fractions to the ratios + how far any single book exceeds `splits.max_book_share` (0.35) of the dev or test pairs. Search: `splits.restarts` seeded random assignments, each improved by single-book moves and two-book swaps; best kept. (Pure greedy-by-pair-count put only Leviticus in dev and Numbers + Ecclesiastes in test; the share cap makes dev/test span several books — 6 and 13 in 2026-10.)
- A pair belongs to **test** if either verse is in a test book, else to **dev** if either verse is in a dev book, else **train**. Training uses train pairs only; hard negatives never involve dev/test books.
- A pytest asserts there is no train pair touching a dev/test book.

### 8.3 Metrics
- Verse level: for each query verse with ≥ 1 gold link in the split: **recall@{1,5,10,50}, MRR@10, nDCG@10** (binary relevance). The ±2 neighbour filter is applied to predictions.
- Unit level: chapter (and pericope) pairs are gold when they share ≥ *m* verse links (default *m* = 2) or a unit-level link; same metrics.
  - Shared verse links = distinct directed verse pairs of the split whose two verses fall in the two units (same-unit pairs and verses outside the unit type are ignored). A unit-level link makes every unit overlapping its source range gold for every unit overlapping its target range. The split comes from the link rows; units never cross books, so the book rule carries over.
  - Unit lists are evaluated as stored (self excluded, no neighbour filter). Unit types without gold in a split are skipped: **parasha has no dev/test gold**, because all five Torah books are train. Dev 2026-10: 154 chapter queries / 390 directed pairs, 348 pericope queries / 886 pairs.
- **Test run** (`bsim evaluate --split test`): only the final systems of each unit type (`retrieve/fusion.py:final_systems`: lexical, semantic, fused); it refuses to replace an existing test entry without `--force`.
- Final test run (2026-10-04, nDCG@10 lexical / semantic / fused): verse 0.118 / 0.118 / **0.136** (1,345 queries; recall@50 0.281 / 0.266 / 0.314); chapter 0.153 / 0.152 / **0.157** (232); pericope 0.062 / 0.061 / **0.068** (686). Fusion is best at every level on test, unlike dev at chapter level (§5.3).
- `bsim evaluate` runs every system in `artifacts/topk/` on dev (default) or test (`--split test`, run once at the end) and writes `artifacts/eval/report.md` + `metrics.json` (system × unit type × metric table, plus the 20 worst-missed gold pairs per system for error analysis).
- Metrics are macro-averaged over all gold queries; a query with no predictions scores 0. MRR/nDCG use `eval.rank_k` = 10.
- "Worst misses" = gold pairs absent from the system's filtered top-50, ordered by how many *other* systems have them in their top-10, then by best other-system rank.
- `metrics.json` is keyed by split (`{"splits": {split: {evaluated_at, config_hash, results: {unit_type: {system: metrics}}}}}`); a run replaces its own split only, so the report shows dev next to the single test run.

### 8.4 Known limitation
Sefaria links reflect what commentators and editors linked, biased toward "famous" connections. The supervised model learns that notion of relatedness. The `lexical` mode and the un-supervised baselines remain available in the viewer as an independent view.

---

## 9. Results database (`artifacts/results.sqlite`)

Built by `bsim build-db` (`store/db.py`, DDL in `store/schema.sql`) from the processed tables and the final top-k lists only (`fusion.final_systems`: one system per mode and unit type).

```sql
CREATE TABLE books   (book_id INTEGER PRIMARY KEY, name TEXT, he_name TEXT, osis TEXT, section TEXT, n_chapters INTEGER);
CREATE TABLE verses  (verse_id INTEGER PRIMARY KEY, book_id INTEGER, chapter INTEGER, verse INTEGER,
                      ref TEXT, osis TEXT, text_display TEXT, text_plain TEXT, ketiv_note TEXT,
                      display_tokens TEXT);                       -- JSON list; words.display_idx indexes it
CREATE TABLE words   (verse_id INTEGER, idx INTEGER, display_idx INTEGER, surface TEXT, lemma TEXT,
                      content_lemmas TEXT, morph TEXT, in_formula INTEGER,
                      PRIMARY KEY (verse_id, idx)) WITHOUT ROWID;
CREATE TABLE units   (unit_id TEXT PRIMARY KEY, unit_type TEXT, label_en TEXT, label_he TEXT,
                      book_id INTEGER, start_verse_id INTEGER, end_verse_id INTEGER, n_verses INTEGER, marker TEXT);
CREATE TABLE unit_members (unit_id TEXT, verse_id INTEGER, PRIMARY KEY (unit_id, verse_id)) WITHOUT ROWID;
CREATE TABLE matches (unit_type TEXT, mode TEXT, src_id TEXT, rank INTEGER, tgt_id TEXT, score REAL,
                      lex_score REAL, lex_rank INTEGER, sem_score REAL, sem_rank INTEGER,
                      link_level TEXT, link_type TEXT,           -- Sefaria gold link (verse | unit | NULL)
                      PRIMARY KEY (unit_type, mode, src_id, rank)) WITHOUT ROWID;
CREATE TABLE discoveries (unit_type TEXT, mode TEXT, a_id TEXT, b_id TEXT, score REAL, tie REAL,
                      rank_ab INTEGER, rank_ba INTEGER, a_book INTEGER, b_book INTEGER,
                      PRIMARY KEY (unit_type, mode, a_id, b_id)) WITHOUT ROWID;
CREATE TABLE lemma_gloss (lemma TEXT PRIMARY KEY, he_lemma TEXT, n_words INTEGER, n_verses INTEGER, pos TEXT) WITHOUT ROWID;
CREATE TABLE phrases (a INTEGER, b INTEGER, score REAL, n_tokens INTEGER, a_words TEXT, b_words TEXT, spread INTEGER,
                      a_book INTEGER, b_book INTEGER, PRIMARY KEY (a, b)) WITHOUT ROWID;             -- §16.1
CREATE TABLE structure (unit_id TEXT PRIMARY KEY, unit_type TEXT, n_verses INTEGER,
                      semantic_* / lexical_* inclusio, inclusio_pct, chiasm, chiasm_pct, chiasm_z REAL) WITHOUT ROWID;  -- §16.2
CREATE TABLE lemma_verses (lemma TEXT, verse_id INTEGER, book_id INTEGER,
                      PRIMARY KEY (lemma, verse_id)) WITHOUT ROWID;   -- concordance (263k rows)
CREATE TABLE meta    (key TEXT PRIMARY KEY, value TEXT) WITHOUT ROWID;            -- JSON values
-- after loading: units(unit_type, book_id, start_verse_id), unit_members(verse_id, unit_id),
--                discoveries(unit_type, mode, score DESC, tie DESC)
```
- `src_id`/`tgt_id` use the unit_id strings (`v:123`, …) for uniformity; `lex_*`/`sem_*` are set on fused rows only. The clustered `matches` key makes `/similar` one range scan.
- `words.content_lemmas` = space-joined content lemmas (the `/explain` key); `words.in_formula` = the word carries a token inside a formula occurrence (same `lexical.formulas` code and config as `bsim lexical`).
- `lemma_gloss.he_lemma`: no lexicon is downloaded, so a lemma is shown as its most common consonantal surface form with the OSHB prefix morphemes stripped (`b c d k l m s` → ב ו ה כ ל מ ש; the article's ה is elided after ב/כ/ל; the whole word is kept when it does not start with the expected letters, 1 of 305,517 words). E.g. 430 → אלהים, 776 → ארץ; verbs show their most frequent inflection (559 → יאמר).
- `matches.link_level/link_type` (M14): is the pair a Sefaria gold link (`links.parquet`, all splits)? Verse-level links count as `verse`; unit-level links are expanded to their Cartesian verse pairs (75k) and count as `unit` unless a verse link also joins the pair; connection types are merged. For chapters / pericopes / parashot a gold verse pair maps to the units containing its two verses (pairs inside one unit dropped).
- `discoveries` (M14): per unit type and mode, the unordered pairs (`a` = earlier start verse) where either unit has the other within its top `store.discoveries.max_rank` (10), without any gold link; verse pairs within ±`neighbor_window` of the same book are dropped. `score` = max of the two directional scores, `tie` = max semantic score for fused pairs (RRF scores tie at the top), else `score`. 515,782 rows on the real data (verse semantic 131k).
- `meta`: build date, config hash, OSHB commit, corpus hash, MAM version + license, the system/config hash per unit type and mode, fusion weights, `k`, neighbour window, the semantic system with its encoder (`models/berel-sup`) and embedding file (`embeddings/berel_sup.npy`) for the API, row counts, file size and the `/similar` benchmark.
- Build: written to `results.sqlite.tmp`, every table (and every unit type × mode of `matches`) checked against its source row count, no dangling unit ids, indexes + `ANALYZE` + `VACUUM`, then moved into place; a failed build leaves the previous DB.
- `store.db.similar()` is the `/similar` query: the stored list of one unit with exclusions in SQL (same semantics as `retrieve/filters.py`; `neighbors`/`chapter` for verses, `book` for every unit type), in stored rank order.
- Result (2026-10-04): 4,144,976 matches (verse 3.48M, pericope 522k, chapter 139k, parasha 8k), 9,204 lemmas, **241 MB**, ~50 s to build; `/similar` (k = 50, neighbours excluded) median 0.53 ms, max 2.3 ms. With M14 links + discoveries: **303 MB**, `/similar` median 0.54 ms. Gold-linked share of the stored lists: verse semantic 10,034 / 1.16M; only ~2 % of the semantic top-10 pairs are Sefaria links.

---

## 10. API (FastAPI)

| Endpoint | Purpose |
|---|---|
| `GET /api/books` | book list with chapter counts |
| `GET /api/units/{type}?book=&chapter=` | list units of a type (for navigation); verse units only per book (422 without `book`), optionally per chapter |
| `GET /api/unit/{unit_id}` | unit metadata + its verses (display text) |
| `GET /api/similar/{unit_id}?mode=lexical\|semantic\|fused&k=10&exclude=neighbors,chapter,book` | top-k from `matches`, filtered at query time; each hit includes score + lex/sem breakdown + target text (verse) or label/preview (larger units) |
| `GET /api/explain?a={verse_id}&b={verse_id}` | shared lemmas with word indices in both verses (for highlighting); formula tokens flagged |
| `GET /api/compare?a={unit_id}&b={unit_id}` | verse-level alignment of two units: for each verse in A its best match in B (and vice versa) with cosine, computed from the cached verse matrix; plus shared lemmas per pair |
| `GET /api/search?q=...&mode=&k=&book=` | free-text Hebrew search over verses (§10.1); `k` up to `serve.search.max_k` = 200, `book` ranks only that book's verses |
| `GET /api/export/{list}.csv?<the list's filters>` | every row of a list view (discoveries, concordance, phrases, sequences, changes, rewrites, typescenes, poetry, word-pairs, wordplay, alliteration, rhymes, structure, acrostics, names) as UTF-8 CSV with BOM: the list handler paged up to `serve.export_max_rows`, items flattened (units → labels, lemmas → Hebrew forms, verse texts left out) |
| `GET /api/discoveries?unit_type=verse&mode=semantic&book=&cross_book=&limit=50&offset=0` | strongest pairs without a Sefaria link (§9 `discoveries`), paginated (`limit` ≤ `serve.max_page`), with `total` |
| `GET /api/resolve?q=` | the verse / chapter a reference names (`Gen 1:1`, `1Sam 3`, `בראשית א א`, `תהלים קי"ט קה`), or `unit: null` (`api/resolve.py`: English titles, OSIS ids, Hebrew names and their unambiguous prefixes; Arabic or canonically written Hebrew numerals) |
| `GET /api/words/{verse_id}` | every OSHB word: surface, raw lemma, morph code + Hebrew description per morpheme (`text/morph.py`), content lemmas with verse counts, SDBH domain codes (§16.22) |
| `GET /api/shifts?by=&max_q=&limit=&offset=`, `/api/lemma/{lemma}/senses` | lemmas by how much their senses / uses differ across corpus groups; one lemma's senses and uses by group (§16.23) |
| `GET /api/domains`, `/api/domain/{code}?book=&limit=&offset=`, `/api/unit-domains/{unit_id}` | semantic domains: the tree with counts; a domain concordance (path, subdomains, verses per book, verses with the words in it); a unit's themes (§16.22) |
| `GET /api/lemma/{lemma}?book=&limit=&offset=` | concordance: occurrences, verses per book, a page of verses with the lemma's display tokens |
| `GET /api/meta` | build info; runtime incl. `encoder_ready` / `encoder_error` |
| `GET /api/eval` | `artifacts/eval/metrics.json` splits, `openbible.json`, and the system served per unit type and mode |
| `GET /api/diff?a=&b=` | word-level changes from verse a to verse b (§16.8) |
| `GET /api/phrases/{verse_id}?limit=&offset=`, `GET /api/phrases` | phrase partners of a verse (`X-Total-Count` header) / ranking (§16.1) |
| `GET /api/sequences`, `/api/sequences/{id}`, `/api/changes` | parallel chains (`unit=` filter), one chain as a ladder with diff marks, changes grouped by word (§16.7, §16.8) |
| `GET /api/parallelism/{unit_id}`, `/api/parallelism?sort=prob\|antithetic`, `/api/wordplay` | verse halves (with `relation`, `relation_pairs`), ranking (by antithetic share among units with `typing_min_parallel` parallel verses), sound-alike pairs (`unit=` filter) (§16.9, §16.10, §16.22) |
| `GET /api/structure/{unit_id}`, `/api/structure` | inclusio / chiasm / Leitworte of a unit, ranking (§16.2) |
| `GET /api/entities`, `/api/entities/{lemma}`, `/api/unit-entities/{unit_id}` | people and places (§16.11) |
| `GET /api/map/{type}`, `/api/affinity`, `/api/affinity/{a}/{b}`, `/api/stylometry`, `/api/stylometry/book/{id}`, `/api/seams?book=&limit=&offset=` | corpus map, book affinity, stylometry, style seams (§16.4, §16.6, §16.12) |

### 10.1 Free-text search
- Query is normalized (§3.2; pointed input accepted).
- `semantic`: encode with the final encoder (GPU if available, else CPU — a single short query takes milliseconds), dot product with the verse matrix, top-k.
- `lexical`: OSHB lemmas don't exist for arbitrary text, so a **surface-form BM25** index is used, with greedy Hebrew prefix stripping (combinations of ו ה ב כ ל מ ש, keeping ≥ 2 root letters) applied to both query and corpus tokens.
- `fused`: RRF of the two.
- Implementation (`api/search.py`): the surface index is built from `verses.text_plain` on the first startup and then loaded from `artifacts/api/surface_bm25.pkl` (sidecar pins the DB file's size/mtime and the parameters; D34) (consonantal MAM): tokens are finals-folded, `text.normalize.strip_prefix`-ed (`serve.search.min_root_letters` = 2; greedy, so over-stripping like משה → שה is symmetric and harmless) and, with `serve.search.bigrams`, extended with adjacent bigrams; `lexical.bm25.build_bm25` with the lexical `k1`/`b` and unit weights. The query is binary BM25 over its known terms; zero-score verses are dropped. Semantic search follows the final semantic system: for `*_csls` the score is `2·cos(q, y) − r(q) − r(y)`, `r(q)` = mean of the query's top-`csls_neighbors` cosines, `r(y)` = verse hubness, computed once and cached in `artifacts/api/{base}.hubness.npy` (sidecar pins embedding size/mtime and `csls_neighbors`). Fused = `retrieve.fusion.rrf` of both top-`retrieval.k` lists with the configured weights. Ties by verse id.

### 10.2 Implementation (`src/bsim/api/`)
- `app.py`: `create_app(cfg)` loads everything before serving (a missing DB / embedding file makes `bsim serve` exit 1): DB `meta`, the memory-mapped verse matrix named by `meta.embeddings`, hubness (CSLS only), the encoder (`embed.encoders.load_encoder`, fp32, `serve.device` with CPU fallback, one query at a time under a lock) and the surface index. Requests borrow read-only SQLite connections from a pool (`ServeState.acquire` / `release`; up to `serve.sqlite_pool` kept idle) so each connection's page cache survives the request. CORS for `serve.cors_origins` (Vite dev); every response carries `Server-Timing: app;dur=…`.
- `routes/` (one router per feature) + `models.py` (pydantic): bad parameters → 422, unknown ids → 404. `k` ∈ 1..`retrieval.k` (default `serve.default_k`). `/unit` adds `parents` (the units of other types containing its first verse) and `prev_id`/`next_id`. `/similar` hits carry the target unit + the target verse (verse lists) or a `preview` of the first verse (`serve.preview_chars`); `exclude` is the comma list of `store.db.similar()` (plus `known`: drop Sefaria-linked hits); every hit carries `link: {level, types} | null`. `/explain` lists shared content lemmas in A's word order with `he_lemma` and every occurrence `{idx, display_idx, in_formula}` in both verses (`formula` = all occurrences are formula words). `/compare` returns the best cosine partner of every verse in each direction, the pair's shared lemmas, the units' BMA and all their verses. `/search` echoes `normalized` and the lexical `tokens`. `/meta` = DB meta + runtime (device, embedding shape, startup time).
- The encoder loads on a background thread: importing sentence-transformers alone takes ~15–25 s on this machine, which pushed a synchronous start to ~31 s. Everything else is loaded before serving; while the encoder loads, semantic / fused `/search` answers 503 at once with `Retry-After: serve.encoder_retry_s` (it does not hold a worker thread), and 503 without it if loading failed; `/meta` reports `encoder_ready` and `encoder_error`. `/sequences/{id}` responses are kept in an LRU (`serve.sequence_cache`) like `/structure/{unit}`.
- Result (2026-10-04, real DB): `bsim serve` answers after ~12–14 s wall clock (load_state ~2.7 s with the hubness cache; the first run computes it on GPU in about a second, the 170k-term surface index takes ~2 s), the encoder is ready after ~32 s. `/search` median (max) over 20 queries, `serve.device: cpu`: lexical 7.7 (14.8) ms, semantic 57 (87) ms, fused 72 (82) ms; GPU: 11 / 47 / 62 ms. Spot checks: Ps 14:1 → Ps 53:2 at rank 1 in all three modes; `/compare` II Sam 22 ↔ Ps 18 pairs all 51 verses with their parallel (BMA 0.90); `/similar` ~6–30 ms including texts.

---

## 11. Viewer (React + Vite + TypeScript)

- **Global**: `dir="rtl"` for Hebrew text blocks (UI chrome may be LTR or Hebrew), fonts **Ezra SIL** / **Noto Serif Hebrew** (OFL) for proper te'amim rendering, toggle: *show te'amim / niqqud only / consonants only*. **Interface language** toggle (EN / עב): English by default; Hebrew makes the whole page right to left (D54).
- **Browse**: book → chapter → verse list; each verse clickable; tabs for chapter / parasha / pericope views.
- **Unit detail**: source text on top; results panel with **mode toggle** (lexical / semantic / fused), **k selector** (10 / 20 / 50), **filter checkboxes** (hide neighbours ±2, same chapter, same book), each result showing ref, text, score and a small bar breakdown (lex vs sem rank). Hovering/expanding a verse result calls `/explain` and **highlights shared lemmas** in both texts (formula words styled dimmer).
- **Compare**: pick two units (from a result or manually) → side-by-side columns with best-match verse pairs connected/colour-coded by similarity and shared-lemma highlights.
- **Search**: text box (Hebrew keyboard input), mode toggle, results list linking to unit detail.
- State in the URL (`/unit/v:123?mode=fused&k=20&exclude=neighbors`) so views are shareable/bookmarkable.

### 11.1 Implementation (`web/`)
- Vite + React + TypeScript, TanStack Query (immutable data cached with `staleTime: Infinity`; API errors are not retried), react-router (library mode). Types in `src/api/types.ts` mirror `api/models.py` by hand (narrowing `str` fields to their literal unions); `npm run gen:api` regenerates `schema.gen.ts` from the API's OpenAPI schema (`bsim openapi`) and `drift.gen.ts`, a compile-time check that every hand-written type with a schema of the same name has the same fields and fits it, so `tsc` fails when they drift (D55). Plain CSS: one `styles/global.css` with tokens on `:root` and a dark theme via `prefers-color-scheme`.
- UI chrome is English and LTR by default; Hebrew is rendered in `dir="rtl"` spans in `"Ezra SIL", "SBL Hebrew", "Noto Serif Hebrew"` (Noto bundled via `@fontsource`, Ezra SIL used when installed). Verses render from `display_tokens` (a token ending in maqaf joins the next without a space), so `/explain` `display_idx` maps straight to a span; words without a display alignment are not highlighted.
- Interface language (`src/i18n/`): `en.ts` is the source catalog of every interface string (page groups in `i18n/pages/{parallels,patterns,overview}.ts`, each an English object and a Hebrew one typed against it); `he.ts` has the same shape (`he: Messages`, so a missing key fails `tsc`; a vitest also checks keys and function arities). Static text is a string, text with values a function that formats its own numbers (`Intl`, `en-US` / `he-IL`) and plurals (Hebrew one / two / many). Components read it through `useT()` / `useLocale()` (`context/Locale.tsx`). The choice is a per-viewer preference in `localStorage` (`bsim.locale`), not URL state; `index.html` reads it before the first paint, and the provider sets `<html lang dir>`. In Hebrew: labels and book names are the API's `label_he` / `he_name` only (English shows both), verse references use `Verse.ref_he` (built by the API from `canon`) and the `*_label_he` fields next to every English verse label, chapter:verse pairs use Hebrew numerals (`lib/hebrew.ts` `hebrewNumeral`, as `canon.hebrew_numeral`). Stay English in both: CSV headers and contents, server error details (shown inside `<bdi>`), Sefaria link types, model names, `q` / `p` statistics. Charts keep their left-to-right axes.
- Text modes are client-side Unicode stripping (`lib/hebrew.ts`): *niqqud* drops U+0591–05AF + meteg U+05BD, *consonants* also drops points U+05B0–05BC, 05BF, 05C1–05C2, 05C4–05C5, 05C7 and CGJ; maqaf, sof pasuq and paseq stay. The choice is a per-viewer preference in `localStorage`, not URL state.
- Routes: `/` books, `/browse/:bookId?tab=chapters|verses|parashot|pericopes`, `/unit/:unitId?mode=&k=&exclude=&halves=&structure=`, `/compare?a=&b=&marks=changes`, `/search?q=&mode=&k=`, `/discoveries`, `/lemma/:lemma`, `/phrases`, `/sequences?unit=`, `/sequences/:id`, `/changes`, `/poetry`, `/wordplay?unit=`, `/names`, `/structure`, `/map`, `/style`, `/eval`, `/about` (`/api/meta`). Every page but the landing page is a lazy chunk; a render error shows a message inside the layout (`ErrorBoundary`), and a stale chunk after a rebuild reloads the page once. Defaults are omitted from the URL; `k` ∈ {10, 20, 50}. Without `exclude`, verses hide their ±2 neighbours (as in evaluation) and larger units hide nothing; `exclude=` means none; `neighbors`/`chapter` are dropped for non-verse units (the API rejects them).
- Unit detail: hovering a verse hit (120 ms delay) or pinning it calls `/explain` and highlights shared lemmas in the source and the hit (formula-only occurrences dimmer; hovering a lemma chip focuses its words). Fused hits show lexical / semantic rank bars over the stored top 50. Every hit links to Compare.
- Compare: two unit pickers (type → book → unit), BMA, two columns coloured by each verse's best-partner cosine in five bands, `⇄` for mutual best pairs; hovering a verse outlines and scrolls to its partner and highlights their shared words via `/explain` (`Pair.shared` has no word positions), or with `marks=changes` the word-level changes A → B via `/diff`.
- Search: RTL input with an optional on-screen keypad, a book filter and up to 200 results; the query is sent on submit only. Semantic / fused queries wait until `/api/meta` reports the encoder ready (polled every 2 s); if it failed, the page says so and offers lexical search.
- Navigation and access (H4): `document.title` follows each page's h1; a new route scrolls to the top and focuses `<main>` (a skip link leads there too); every list has a page box (jump to page) and, when the URL points past the end, a link back to the last page; "Export all (CSV)" next to "Export page (CSV)" (`/api/export`); a verse is one tab stop, ←/→ move between its words (right-to-left), Home / End; the Names graph nodes and the Structure heatmap (arrow keys, read out in the caption) work from the keyboard; `prefers-reduced-motion` stops transitions and smooth scrolling; the sequence ladder prints each pair's cosine next to its colour; j / k move between the hits of a unit (pinning verse hits); "Copy link" in the header; on verse units "Mark words by: Changes" shows the `/diff` changes of the active hit.
- Production: `bsim serve` serves `paths.web_dist` (`web/dist`) at `/` with an `index.html` fallback for client routes (paths under `/api` still 404 as JSON); without a build it logs a hint and serves the API only. Dev: `npm run dev` on :5173 proxies `/api` to :8000.

---

## 12. Configuration

`configs/default.yaml` holds every tunable: paths, OSHB commit, `k: 50`, neighbour window `2`, BM25 `k1/b`, formula `T/α`, encoder names, training hyperparameters, seeds, RRF weights, split ratios, unit-gold `m`. Each artifact stores the hash of the config section it depends on; `bsim` warns when an artifact is stale.

The `pipeline` section drives `bsim all` (`bsim/pipeline.py`): the lexical verse systems computed before training, whether every encoder also gets a `_csls` top-k, the systems aggregated by `bsim units`, and the download parallelism. The stage order is fixed in code; `--from`, `--to` and `--skip` select a slice. `bsim all` never replaces a test run: it evaluates test only when `metrics.json` has no test entry (a fresh clone). The ablation runs of M8 (`train-sup --init/--no-hard-negatives/--output`) and the web build (`npm run build` in `web/`) are not part of it.

---

## 13. Testing strategy

- Unit tests: normalization (points stripped, maqaf, finals), lemma parsing, ref parsing & range expansion, split leakage, top-k self-exclusion, filters, RRF, BMA on a toy matrix, metrics against hand-computed values.
- Data assertions (in pipeline, not pytest): verse-count equality, alignment coverage ≥ 99 %, 54 parashiyot, every verse belongs to exactly one chapter and one pericope.
- API: FastAPI `TestClient` against a tiny fixture DB (`bsim.fixture`: six verses in two books, made-up lists and analyses, built through `run_build_db`).
- Viewer: vitest (`npm test`); Playwright end-to-end and axe checks in desktop and phone widths and both interface languages, against the real DB locally (`npm run e2e`, `smoke.spec.ts`) and against the fixture DB served by `bsim fixture-serve` (`npm run e2e:fixture`, `fixture.spec.ts`).
- CI (`.github/workflows/ci.yml`, every push to main and pull request, no data / model / GPU): ruff, pytest, oxlint + `tsc`, vitest, generated API types up to date (`npm run check:api`), viewer build, fixture end-to-end tests in Playwright's Chromium (D55).
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
| D14 | Versification | `verse_id` follows MAM/Sefaria (23,206 verses); OSHB is re-keyed via `canon.VERSE_OVERRIDES` (Decalogue in Ex 20 / Deut 5, Num 25:19 → 26:1) |
| D15 | Link filter & split | Gold = links whose two texts are both canon books (not `Category == Tanakh`); book split balances pair fractions with a 35 % cap on any single book's share of dev/test |
| D16 | Lexical weighting | Formula weight α applies to both BM25 sides (doc tf/length, query term weight = max token weight); bigram weight = min of its tokens; `bm25_surface` uses the same pipeline on `match_key` tokens (its own formulas, not exported); unit TF-IDF tf = `(1 + log c)·(w/c)` |
| D17 | Top-k & eval | One torch top-k path for GPU and CPU; lexical lists drop zero-score hits; ranks 1-based with ties ordered by target id; metrics macro-averaged over gold queries (missing = 0); `metrics.json` keyed by split |
| D18 | Encoders | All encoders via sentence-transformers (fp32, max_len 128) from an `encoders.systems` registry; BEREL baseline = mean pooling; BGE-M3 = its native CLS dense vector; `*_csls` computed at top-k time from the base embeddings (`retrieval.csls_neighbors`), CSLS scores stored as-is |
| D19 | SimCSE | `bsim train-simcse`: MNRL on (verse, verse) over the *distinct* `text_model` strings (repeated formula verses would be false in-batch negatives), `no_duplicates` batch sampler, hidden + attention dropout from `train.simcse.dropout`. Epochs are selected by `train/dev_eval.py:DevEvaluator`, which reproduces `bsim topk` + `bsim evaluate` in memory (±2 neighbour filter) instead of ST's IR evaluator; epoch 0 (raw BEREL) is scored as a reference, never saved. Output `models/berel-simcse/` is a native ST checkpoint (Transformer + mean pooling) + `bsim_train.json`; registered as `berel_simcse` (pooling `native`) |
| D20 | Supervised fine-tune | `bsim train-sup` (`--init`, `--[no-]hard-negatives`, `--output` for ablations): CachedMNRL on train-split verse links (both directions) + one BM25 hard negative per row, `no_duplicates` sampler; checkpoints selected every `eval_steps` by `DevEvaluator` (not ST's IR evaluator). The dev ablation chose raw BEREL over the SimCSE start (`init_from: base`); `final_systems.semantic = berel_sup_csls` |
| D21 | Fusion & units | `bsim units`: BMA (primary) and mean aggregation for every dense / `*_csls` system → `{system}_{bma\|mean}`; unit lexical = `tfidf`. Unit gold = ≥ m shared verse links or overlapping unit-link ranges, no neighbour filter; parasha has no dev/test gold (Torah = train). `bsim fuse`: RRF of `final_lists` (verse `bm25_lemma` + `berel_sup_csls`; units `tfidf` + `berel_sup_csls_bma`), w_lex grid extended to 2.0, one weight for all unit types chosen on verse dev (`w_lex = 1.0`). Test split = final systems only, run once (guarded) |
| D22 | Results DB | `bsim build-db` rebuilds `results.sqlite` from scratch (tmp file + row-count checks, then replace) with the final systems only; DESIGN §9 schema plus `verses.display_tokens`, `words.content_lemmas`/`in_formula`, `units.marker`, `WITHOUT ROWID` matches keyed for `/similar`; `lemma_gloss` = most common prefix-stripped consonantal form (no lexicon); `store.db.similar()` holds the query-time filters for the API |
| D23 | API | `bsim serve` = `api.app.create_app`: per-request read-only SQLite, memory-mapped final verse matrix, CSLS hubness cached under `artifacts/api/`, encoder loaded on a background thread (serving starts without waiting for the sentence-transformers import; semantic search waits, 503 on load failure). Free-text lexical search = surface BM25 over `text_plain` with greedy `strip_prefix` (min 2 letters) + bigrams; semantic search scored like the final system (CSLS for `*_csls`); `/compare` uses plain cosine. 422 for bad parameters, 404 for unknown ids; `Server-Timing` on every response |
| D24 | Viewer | React + Vite + TS in `web/` with TanStack Query and react-router; English LTR chrome, Hebrew in RTL spans built from `display_tokens`; plain CSS (no framework); te'amim / niqqud / consonants toggle by client-side Unicode stripping (localStorage); all view state in the URL, verses default to `exclude=neighbors`; shared-lemma highlights via `/explain` on hover in unit detail and compare; `bsim serve` serves `paths.web_dist` with an SPA fallback |
| D25 | End-to-end | `bsim all` runs stages 1–12 in a fixed order from `bsim/pipeline.py` with the system lists in config `pipeline`; `--from/--to/--skip` select stages; fuse records the dev `w_lex` grid before writing fused lists; the test split runs only when absent (never forced); training ablations and the web build stay manual. Results are published as metrics only in `docs/RESULTS.md` |
| D26 | Gold links in the viewer | Sefaria links (all splits; the viewer is not an evaluation) are flagged per stored match (`link_level` verse/unit) and drive a "Discoveries" list of strong unlinked pairs (top-10 either way, neighbours dropped). Discoveries default to `semantic` mode: CSLS scores are comparable across sources, BM25 scores are not, and fused RRF scores tie at the top (secondary sort by semantic score) |
| D27 | Word study | Morphology is decoded from the OSHB codes into Hebrew labels at request time (no lexicon, English glosses or translations); the concordance is keyed by content lemma (Strong's number) via a `lemma_verses` table; references are resolved by `api/resolve.py` independently of the search modes, and the search page offers the resolved unit next to (or instead of, for non-Hebrew input) the text results |
| D29 | Structure | Inclusio / chiasm are percentiles against each unit's own Monte Carlo null (same-distance pairs for chiasm, max over the frame pairs for inclusio) on a semantic and a lexical verse matrix; there is no gold, so the scores rank candidates for reading; Leitworte by G² with function-word POS skipped |
| D30 | Corpus map | t-SNE + KMeans on mean verse embeddings per unit, clusters named by G² lemmas; book affinity as lift over a size-proportional expectation of fused cross-book verse pairs, books ordered by hierarchical clustering; sklearn / scipy only (no UMAP / HDBSCAN dependency) |
| D31 | Reranker | A BEREL cross-encoder over the fused top-50 (train-book data, in-list negatives, epoch and blend weight on dev) gains only +0.004 dev nDCG@10 (bootstrap CI includes 0): kept as the evaluated `fused_rerank` system, not adopted as a final system; manual stages |
| D32 | Structural mode | A fourth mode over morphology shape n-grams (BM25 verses, TF-IDF units), exposed in the viewer but not fused (3-way RRF does not help on dev) and not available for free-text search |
| D33 | Stylometry | Burrows-style profiles (100 MFW + 25 morphology rates, z-scores, Delta, PCA) of books and chapters, shown as descriptive statistics only |
| D28 | Shared phrases | Phrase-level matches are an alignment over the lexical candidates rather than a new retrieval system: Smith-Waterman on content-lemma streams with idf × formula-weight match scores (§16.1); not evaluated against the gold links (no phrase-level gold), thresholds read off samples |
| D35 | Parallel sequences | Same-order parallels as synteny chains over the fused verse top-20 (DP, max step 3, gap 0.25, ≥ 4 pairs) with q-values from a within-chapter verse-order shuffle (20 reps); stored with per-pair gold flags; `/sequences`, `/sequences/{id}`, Sequences page + ladder view + unit panel (q ≤ 0.2). Descriptive, no tuning against gold |
| D36 | Parallel diffs | Word-level Needleman-Wunsch over lemma keys for the verse pairs of q ≤ 0.05 sequences (A = earlier in canon), pairs below 30 % shared lemmas left out as loose; changes grouped by lemma (or written form for spelling / form); served as `/changes`, `/diff`, ladder marks and a Changes page |
| D37 | Te'amim parallelism | Cola from the main accent pause (etnahta; oleh-ve-yored in the poetic-accent books); a logistic regression on half-to-half relations only (cosine, shared lemmas, shape overlap, balance) trained on Psalms / Proverbs / Job vs narrative and law; checked by held-out-book AUC and the ranks of known embedded poems; `/parallelism`, unit-page halves toggle, Poetry page |
| D38 | Wordplay | Paronomasia candidates = nearby different-lemma words whose prefix-stripped consonant skeletons differ by one edit and whose vowel patterns match; ranked by rarity, with a within-chapter word shuffle giving the corpus-level excess (≈ 400 vs 279) rather than per-pair proofs; `/wordplay`, Wordplay page, unit panel |
| D39 | People and places | Names = OSHB `Np` lemmas (divine names out), person / place / mixed / unclear from context cues (directional ה, עיר / ארץ, ב / מ vs בן / בת, verbs of speech); verse co-occurrence links scored by G², 25 per name; `/entities`, `/entities/{lemma}`, `/unit-entities/{unit}`, Names page with an ego network |
| D40 | Style seams | Change points inside books = peaks of a Burrows-Delta curve between the 600 words before and after each verse boundary (§16.6 features, chapter SDs), thresholded per book by the 95th percentile of shuffled-verse maxima; `/seams`, shift chart on the Style page |
| D41 | Second gold | OpenBible cross-references (≥ 5 votes, Hebrew Bible only, KJV-versification-unsafe chapters dropped, Sefaria split rule) as an evaluation-only, dev-only gold set; reported next to Sefaria, never used for tuning |
| D44 | Multiple testing | Analyses that test many units report Benjamini–Hochberg q (`analysis/stats.py`): acrostics, rewrites, inclusio / chiasm; claims about numbers (Leitworte in sevens) are checked against count-matched baselines with control divisors (§16.14) |
| D45 | Acrostics | First letters of verses and of te'amim cola; best alphabetic chain per chapter (gaps of up to 8 lines, skipped letter −1, both פ/ע orders) against line-order shuffles, BH over chapters; validated on the known acrostics (§16.15) |
| D46 | Rewrites | Book-pair summary of the word diffs: recurring substitutions / omissions / additions by G² against the pair's own change rate, BH q, plus a spelling-direction profile; computed in `bsim diffs`, no new stage (§16.16) |
| D52 | Serving and viewer 4 | List totals cached per (DB file, query) — indexes on the book columns made counts slower and pages no faster; full CSV export by paging the list handlers; search past `retrieval.k` and per book; verse picker per chapter; viewer: page jump and past-the-end recovery, per-route titles, focus reset and skip link, one tab stop per verse, keyboard heatmap / name graph, reduced motion, j / k between hits, copy link, word changes on verse hits, two-layer scatter |
| D49 | Finer accents | Full disjunctive hierarchy (prose / poetic tables) for clause spans; cross-verse bicola scored with the halves model; parallelism typing by negation dropped (fails on Prov 10–15) for G² word pairs across parallel members (§16.18) |
| D50 | Sound | Phoneme-level sounds (begadkefat merged, shin / sin apart); alliteration over content words with shape-conditioned chance and BH; rhyme as runs of distinct words ending alike (§16.19) |
| D57 | Senses across the canon | Two readings compared by corpus group, kept apart: SDBH meanings (sense change) and k-means clusters of pretrained-BEREL word vectors (use change, genre included), each with MI against a shuffled-group null and BH q; clusters described by Hebrew collocates only, never glosses; clusters validated against SDBH by NMI (§16.23) |
| D56 | Lexicon and domains | Revises D27's "no lexicon": SDBH (CC BY-SA) word senses and semantic domains, tagged per word occurrence from SDBH's own references, and Strong's name types. Glosses and definitions are never stored or shown (D5): the viewer shows domain names, the top two levels also in Hebrew. Domains as a retrieval signal were tested against `fused` on dev and not adopted (§16.22); `bm25_domain` / `tfidf_domain` are shown as their own `domain` mode, not fused (as structural, D32) |
| D55 | CI and API types | GitHub Actions runs every check that needs no data, model or GPU; the pytest fixture DB moves into the package (`bsim.fixture`) so `bsim fixture-serve` can serve it to Playwright and `bsim openapi` can build the schema. The viewer keeps its hand-written, narrower types and gains a generated drift check instead of being replaced by the generated ones; response models share `ApiModel`, which marks defaulted fields required in the schema since every response includes them. First run: drift found (`SearchResponse.book`, `SequencesResponse.direction`, fields typed optional that are always sent) and three contrast / link-style issues on Compare and Style fixed (§13) |
| D54 | Interface language | Optional Hebrew interface (EN / עב, English default, fully RTL) from typed catalogs in `web/src/i18n` with no i18n dependency. This is the interface's language, not a translation: the "Hebrew only, no translations" rule is about scripture, which is Hebrew in both. CSV exports, server error details and statistics stay English (§11.1) |
| D53 | Retrieval experiments | Contextual (±1 verse, window and late-chunked) BEREL-sup embeddings and training-free MaxSim over BEREL / BEREL-sup tokens, tested against `fused` on dev with a paired bootstrap, 2-fold cross-fitting and OpenBible as an untouched second gold; none clears CI > 0, so the final systems are unchanged (§16.21) |
| D51 | Action sequences | Verb-lemma Smith–Waterman between pericopes against a verb-order shuffle; textual parallels flagged; classic type-scenes reported as not recovered (§16.20) |
| D47 | Sequence orders | Reverse and mixed chains next to forward ones, found in that order with overlap dedup and scored against their own kind's shuffle chains; forward ids kept; none survive, reported as such (§16.7) |
| D48 | Network | Fused unit top-10 as a weighted graph (adjacent units dropped): PageRank, Louvain communities at resolution 3, server-side spring layout per community; networkx as a declared dependency (§16.17) |
| D43 | Serving 3 | Pooled read-only connections (`serve.sqlite_pool`); semantic `/search` fails fast (503 + `Retry-After`) while the encoder loads; `/meta` `encoder_error`; batched `verse_links` and `/changes` examples (one query each instead of one per row); `/sequences/{id}` LRU; `/units/verse` per book only; `/eval` serves the metrics to a viewer page |
| D42 | Serving 2 | `/search` query embeddings in an LRU (`serve.search.query_cache`); read-only connections with a `serve.sqlite_cache_mb` page cache, mmap and `query_only`; `/phrases/{verse}` capped by `limit`; `api/routes/` split into feature routers sharing `_common` checks |
| D34 | Serving | `/structure/{unit}` responses kept in a bounded in-memory LRU (`serve.structure_cache`) instead of a pipeline table: they are deterministic per DB and only a few hundred units are viewed. The surface BM25 index is pickled under `artifacts/api/` with a sidecar pinning the DB file and parameters. GZip ≥ `serve.gzip_min_bytes`; GET `/api` 200s carry `Cache-Control: public, max-age=serve.api_max_age` (`/meta` is `no-store`), `/assets/*` immutable. `/compare` refuses units over `serve.max_compare_verses` |

---

## 16. Pattern analyses (`src/bsim/analysis/`)

### 16.1 Shared phrases (`bsim phrases`, `analysis/phrases.py`)
- Candidates: unordered verse pairs from the final lexical verse lists (`bm25_lemma`, top `phrases.candidate_rank` = 50; ±`neighbor_window` neighbours dropped): 759,181 pairs.
- Each pair's content-lemma streams are aligned with Smith-Waterman (linear gaps). A match scores the smaller of the two token weights, weight = `log(N/df)` × formula weight (the `lexical.formulas` detector, α = 0.2), so rare words dominate and formula words barely count; mismatch / gap cost 1.5. The best local alignment is kept when it matches ≥ `min_tokens` (3) tokens with score ≥ `min_score` (14). Thresholds were chosen by reading samples: at 10–12 most three-token hits were gapped topic overlaps, at 14 the borderline cases are short real allusions (Gen 9:7 ↔ Ex 1:7 פרו ורבו שרצו, Ps 109:5 ↔ Prov 17:13 רעה תחת טובה).
- `spread` = verses sharing the exact matched lemma sequence; an idiom used in many verses (כי על כן) forms a clique of pairs, so the leaderboard hides `spread > 3` by default (a Kings / Isaiah / Chronicles triple survives).
- Result (2026-10-04): 18,163 phrase pairs in 51 s on CPU (pure Python DP), 8,068 across books; the top is the synoptic material (Kings ↔ Chronicles / Isaiah / Jeremiah), and below rank ~1,500 most cross-book pairs have no Sefaria link (Hos 13:8 ↔ Prov 17:12, Mal 1:11 ↔ Ps 113:3, Amos 5:11 ↔ Zeph 1:13, Deut 32:36 ↔ Ps 135:14).
- Served from the `phrases` table: `/similar` verse hits carry `phrase: {score, n_tokens}`, `/phrases/{verse_id}` lists a verse's phrase partners, `/phrases` is the paginated leaderboard (`book`, `cross_book`, `min_tokens`, `max_spread`); matched words are returned as display-token indices for highlighting.

### 16.2 Inner-unit structure (`bsim structure`, `analysis/structure.py`, `/structure`)
- Each chapter / pericope / parasha (≤ `structure.max_verses` = 200 verses) gets two verse × verse similarity matrices: `semantic` (cosine of the final semantic system's verse embeddings) and `lexical` (cosine of tf-idf content-lemma bags, `idf = log(N/df)`).
- **Inclusio**: the best of the frame pairs first ↔ last, second ↔ last and first ↔ penultimate (for n ≥ 6; otherwise first ↔ last only), so a Psalm superscription or closing formula does not hide the frame, as a percentile of the best of as many random non-adjacent pairs of the same unit (a max-of-3 null for a max-of-3 statistic).
- **Chiasm**: mean similarity of the mirror pairs (i, n−1−i), the adjacent centre pair left out (n ≥ 5, ≥ 2 pairs), against a Monte Carlo null of random pairs at the same distances (`samples` = 2000, seeded), because similarity decays with distance. `pct` = share of null means below the observed mean, `z` in null SDs. With 4,464 scored units about 5 % would pass 0.95 by chance (2.4 % semantic / 1.9 % lexical do), so the UI presents high scores as leads, not findings; since M29 each score also has a Benjamini–Hochberg q (§16.14), under which no chiasm survives. Chiasm at verse granularity is coarse; list-like units (Num 7, Num 33, Josh 21) score high because repeated paragraphs line up.
- **Echoes**: the `echoes` (8) most similar non-adjacent verse pairs.
- **Leitworte**: content lemmas over-represented in the unit by Dunning's G² against the rest of the corpus (count ≥ `leitwort_min_count` = 3, observed > expected), skipping conjunctions, prepositions, particles and pronouns by their most common OSHB part of speech (`lemma_gloss.pos`); counts that are multiples of 7 or 10 are flagged (Buber–Rosenzweig), though across the corpus 7 is no more frequent than other divisors (§16.14). E.g. Ps 29 קול ×7, Gen 1 רקיע ×9 / מינהו ×10, Gen 22 אברהם ×20 / יחיד ×3.
- `bsim structure` (5–6 s) writes `artifacts/structure/units.parquet` → `structure` table for the ranking (`/structure?unit_type=&by=semantic_chiasm|lexical_chiasm|semantic_inclusio|lexical_inclusio&min_verses=`); `/structure/{unit_id}` recomputes one unit with the same code (30–100 ms; Ps 119, 176 verses, 260 ms) and adds the matrices, echoes and Leitworte with their display-token positions. Spot checks: Ps 8 inclusio 8:2 ↔ 8:10 (0.89, 100th percentile); Ps 118 / 136 / 103 / 1 at the 100th.

### 16.3 Cross-encoder reranking (`bsim train-rerank`, `bsim rerank`, `train/rerank.py`) — not adopted
- Model: BEREL 3.0 as a cross-encoder (`[CLS] a [SEP] b`, one logit, max 256 tokens), fp32, BCE loss. Training data from train books only: each train-split anchor's links are positives, and up to 7 negatives per anchor come from its own fused top-50 (not linked in any split, train book, not a ±2 neighbour, different text): 46,483 pairs (9,026 positive), batch 32, lr 2e-5, 3 epochs, 15 min on the 1080 Ti.
- Selection on dev (884 verse queries, ±2 neighbours dropped, as in the report). Cross-encoder alone, nDCG@10 by epoch: 0.135 / 0.128 / 0.120 (epoch 1 kept): it is worse than the fused list it reorders (0.189) and overfits the train links as training continues.
- Blend `w_ce / (60 + ce_rank) + 1 / (60 + fused_rank)` on dev: w_ce 0.25 → 0.194, 0.5 → 0.193, 1 → 0.180, 2 → 0.165, 4 → 0.150, alone → 0.135. Scoring all 1,160,300 (verse, candidate) pairs takes 27 min.
- Paired bootstrap of the best blend vs fused over the 884 dev queries: +0.0042 nDCG@10, 95 % CI [−0.0007, +0.0092] (88 queries better, 66 worse, 730 unchanged), with w_ce chosen on the same queries. Too small and too uncertain to replace the fused lists, so `final_systems.fused` stays `fused` (DB / UI unchanged) and `fused_rerank` is kept as an evaluated system in the dev report. The test split is not run again (it was run once, at M9).
- Likely limits: ~9k training pairs of "famous" Sefaria links (§8.4), with in-list negatives that are often unlabelled true parallels. The stages stay manual (not in `bsim all`).

### 16.4 Corpus map (`bsim map`, `analysis/corpus_map.py`, `/map`, `/affinity`)
- Unit vector = mean of the unit's verse embeddings (final semantic system), L2-normalized. Layout per unit type (chapter, pericope, parasha): t-SNE (cosine, PCA init, perplexity 30, seeded), scaled to 0..1.
- Clusters: KMeans on the unit vectors (`map.clusters`: chapter 20, pericope 30, parasha 8), labelled by the cluster's top-5 G² lemmas (function words skipped, as for Leitworte). The chapter clusters come out as recognisable genres and blocks: wisdom (רשעים כסיל צדיק לב חכמה), praise psalms (הללו עולם יה חסד), the Tabernacle (אמה רחב זהב אדנים), sacrifices (כהן הקריב כבשים איל), genealogies and borders, the Exodus narrative, Esther, oracles against the nations.
- Book affinity: unordered cross-book verse pairs within either verse's fused top `map.affinity_rank` (10): 88,187 pairs. `lift` = observed / expected, expected ∝ `n_a · n_b` (book sizes in verses). `book_order` = leaf order of an average-linkage clustering on `log(1 + lift)`; it groups the prophets, poetry / wisdom, Torah law and the histories. Highest lifts (≥ 30 pairs): Ezra–Nehemiah 18.1, Haggai–Zechariah 16.7, I Kings–II Chronicles 6.8, Hosea–Micah 6.6. The 10 strongest verse pairs per book pair are kept for the UI.
- `bsim map` (≈ 30 s, CPU) writes `artifacts/map/*.parquet` → `map_points`, `map_clusters`, `book_affinity`, `book_examples` + `meta.book_order`; `/map/{unit_type}` (points + labelled clusters), `/affinity` (cells + order), `/affinity/{a}/{b}` (example pairs, book `a` first).

### 16.5 Structural mode (`lexical/morph.py`, `bm25_morph`, `tfidf_morph`)
- Each OSHB word becomes a coarse shape token: per morpheme the part of speech plus the syntactically telling feature (verb form, noun state, pronoun / suffix / particle type), without lexeme, stem, person, gender or number: `HC/Vqw3ms` → `C+Vw`, `HR/Td/Ncmsa` → `R+Td+Na`. A verse is indexed as the 1–3-grams of its shape tokens (`lexical.morph.max_n`): BM25 for verses (`bm25_morph`, built by `bsim lexical`), unit TF-IDF over the same tokens for chapters / pericopes / parashot (`tfidf_morph`).
- It is the fourth viewer mode, `structural` (`final_systems.structural` / `unit_structural`), stored in `matches` like the others (DB 309 → 402 MB). It is not offered for free-text search (no morphology for arbitrary text).
- What it finds: verses with the same grammatical shape whatever their words, e.g. Prov 10:1 → other antithetic proverbs (Prov 27:7, 17:22, 25:15); Gen 1:3 → the other `ויאמר אלהים יהי …` fiats; Ex 20:13 → Deut 5:17 and other `לא ת…` prohibitions.
- Dev: nDCG@10 0.068 (Sefaria links are thematic, not grammatical). A 3-way RRF with lexical + semantic (w_morph 0.1 / 0.25 / 0.5 / 1) gives 0.192 / 0.189 / 0.186 / 0.182 vs fused 0.189: no meaningful gain, so the fused list is unchanged and structural stays a separate mode.

### 16.6 Stylometry (`bsim stylometry`, `analysis/stylometry.py`, `/stylometry`)
- Features, as rates per word of a unit: the 100 most frequent content lemmas (`stylometry.mfw`) and 25 morphology rates (parts of speech, verb forms, construct state, article, conjunction, object marker, pronominal suffix, Aramaic).
- Books: z-scores across the 39 books, Burrows' Delta = mean |z_a − z_b|, average-linkage order. The order groups the Former Prophets, the Torah law books and the late books (Esther, Daniel, Ezra, Nehemiah, Chronicles: the usual Late Biblical Hebrew group); Isaiah, Jeremiah and Ezekiel are each other's nearest neighbours.
- Chapters (≥ `min_words` = 150; 783 of 929): PCA of the z-scores. PC1 (7 %) runs from list-like prose (article, את, nouns) to poetry / prophecy (yiqtol, suffixes, לא, כי); PC2 (6 %) from genealogies / numbers (construct, מאות, אלף) to narrative (ויאמר, wayyiqtol).
- Per book the 8 most over- and under-used features (z) and the nearest books; e.g. Psalms: more cohortatives, imperatives, suffixes, נפש, אתה; fewer particles and conjunctions.
- Presented as descriptive statistics, not as claims about authorship or date. `bsim stylometry` (~9 s) → `stylo_points`, `stylo_delta`, `stylo_features` + `meta.stylometry`.

### 16.7 Parallel sequences (`bsim sequences`, `analysis/sequences.py`, `/sequences`)
- Goal: passages that run parallel verse by verse in the same order (synoptic accounts, retellings, command ↔ execution, repeated lists), which pairwise verse similarity cannot show. Synteny detection over the verse lists, not unit pairs, so chains cross chapter and pericope boundaries.
- Candidates: unordered verse pairs within either verse's fused top `candidate_rank` = 20, neighbours dropped; weight `(21 − rank) / 20` of the better direction (294,460 pairs).
- Chaining: DP over pairs sorted by (a, b); a pair extends the best chain ending at (a − da, b − db), 1 ≤ da, db ≤ `max_step` = 3, within the same books, minus `gap` = 0.25 per skipped verse; chains restart below 0, are read greedily from the best end pair (each pair once), need `min_pairs` = 4 and non-overlapping spans (tandem repeats dropped).
- Null: verse order shuffled within every chapter (both ends of each pair; weights kept), so two chapters on one topic still match but their order is destroyed; `null_reps` = 20. `q` = (null chains per replicate ≥ s) / (observed chains ≥ s), monotone — the expected share of chance chains among those at least this strong.
- Result (2026-10-04): 1,228 chains, ~852 chance chains per shuffle (mostly short), 78 with q < 0.05 (43 across books, 20 within one chapter, 26 with no Sefaria link on any aligned pair); `bsim sequences` ~33 s. Top: II Kgs 18:16–20:12 ↔ Isa 36–38 (68 pairs), Ezra 2 ↔ Neh 7 (65; Sefaria links 2), I Kgs 7–8 ↔ II Chr 4–7 (63), II Sam 22 ↔ Ps 18 (51), Ex 26 ↔ 36, Ex 28 ↔ 39, Ex 25 ↔ 37, Ex 29 ↔ Lev 8, II Kgs 24–25 ↔ Jer 52, Lev 11 ↔ Deut 14, Ex 20 ↔ Deut 5. Retellings inside one story: Gen 24:2–16 ↔ 24:34–46 (the servant's report, q 0.016), Gen 40–41 (Pharaoh's dreams), Job 1 ↔ 2, Esther 2–4 ↔ 7–8. Gen 20 ↔ 26 (wife–sister) appears only weakly (5 pairs, q 0.25); Gen 12 not at all.
- Other orders (M32, `sequences.directions`): `reverse` chains let the b side retreat (a pair extends one ending at (a − da, b + db): A B C … ↔ … C′ B′ A′; a reverse chain nested inside one passage is a chiasm at verse level and is kept), `mixed` chains let it step either way (the same scene told in another order; monotone mixed chains are dropped as duplicates). Kinds are found in the order forward → reverse → mixed, a later chain dropped when ≥ `max_overlap` = 0.5 of its pairs are already in a kept chain; each kind is scored against the same shuffles' chains of its own kind. Forward ids are unchanged (forward chains are numbered first).
- Result of the other orders (2026-10-05; the stage now takes ~120 s): 1,166 reverse and 1,221 mixed chains, **none with q < 0.05** (best reverse q 0.33, best mixed 0.08). Under a within-chapter verse shuffle, mirrored order is no rarer than chance anywhere — including the much-cited chiastic readings that do come out on top among reverse chains (Esther 4–5 ↔ 6–8, the Dinah story Gen 33:17–34:14 ↔ 34:17–35:7, Balaam Num 22–23) — and mixed chains cannot beat a null made of reordered verses by construction. The wife–sister stories are found but not significant: Gen 20:1–7 ↔ 26:6–11 forward (q 0.26), Gen 12 ↔ 26 and 20 ↔ 26 reverse (4 pairs, q ≈ 0.6), Gen 12 ↔ 20 forward (q 0.68); as whole passages they rank each other in the top 5 and share one network community (§16.17). The Sequences page shows same-order chains by default and the others on request.
- Limits: in-order significance only (see above); within-chapter repeats (Num 7, Num 29, Lev 13) are real but list-like (UI filter); verse granularity misses parallels that split or merge verses unevenly beyond `max_step`. No gold for chains: `n_gold` (aligned pairs Sefaria links) is descriptive, not an evaluation.

### 16.8 How parallels differ (`bsim diffs`, `analysis/diffs.py`, `/changes`, `/diff`)
- Input: the aligned verse pairs of sequences with q ≤ `diffs.max_q` = 0.05, repeats inside one chapter left out (`same_chapter: false`). A = the earlier verse in canon order (Samuel–Kings before Chronicles, Ps 14 before 53).
- Words: one OSHB word each, keyed by its content lemmas (prefix particles are not lemmas); a word with no content lemma (a suffixed preposition, בּוֹ) is keyed by its prefix lemmas (`~b`). Needleman-Wunsch over the keys (match 2, mismatch 1, gap 1); labels `same`, `spelling` (same key, only ו / י after the first letter differ — a leading ו / י is a conjunction or verb prefix), `form` (same key, other differences), `substitution`, `omitted`, `added`, `moved` (dropped and re-added in the same pair).
- A chain's edge pairs may be only loosely parallel and a global alignment of unrelated verses is all substitutions, so a pair is diffed only when ≥ `min_shared` = 0.3 of the shorter verse's words keep their key; the API returns `loose` and no marks for the others.
- Served: `diff_changes` (one row per non-`same` word, with keys and written forms) + `meta.diffs`. `/changes?op&a_book&b_book` groups by key (substitution / added / omitted / moved) or by written form (spelling / form), with counts, sequences and 3 example pairs; `/diff?a&b` diffs any two verses on the fly; `/sequences/{id}` rows carry `a_marks` / `b_marks` (display token → op) and `loose`.
- Result (2026-10-05): 1,003 verse pairs diffed, 63 too loose. Changes: substitution 1,469, omitted 1,635, added 1,432, form 982, spelling 592, moved 228. The counts surface known Late Biblical Hebrew and Chronicler habits without being told: יהוה → אלהים (Chronicles and Ps 53), אל → על, דוד → דויד (plene), יהואש → יואש, ארונה → ארנן, חירם → חורם, אנכי → אני, ממלכות → מלכות. Spelling groups are plene / defective pairs (דוד → דויד 82, אתם → אותם, הספר → הסופר, חלקיה → חלקיהו); form groups show command → execution in the Tabernacle chains (ועשית → ויעש 29, תעשה → עשה, וצפית → ויצף). Added / omitted lists are led by function words (את, כל, אשר).
- Limits: word order inside a verse is only partly captured (`moved` needs the same key on both sides); keys are OSHB lemmas, so a synonym with another Strong's number is a substitution and a homograph with one number is not; no gold — descriptive only. Recurring changes per book pair: §16.16.

### 16.9 Verse halves and poetic parallelism (`bsim parallelism`, `text/accents.py`, `analysis/parallelism.py`, `/parallelism`)
- Until M24 the te'amim were display-only. `text/accents.py` reads the main pause of each verse from the MAM accents: etnahta (U+0591) in every book; in the poetic-accent books (Psalms, Proverbs, Job 3:2–42:6) oleh-ve-yored (ole U+05AB + merkha on that word or the next) is a stronger pause before it. A pause on the last word is ignored. Result: 21,250 verses with 2 cola, 370 with 3, 1,586 with 1.
- Features per pair of consecutive cola (mean over a verse's pairs): `cos` of the two cola embedded with the final encoder's base (`berel_sup`; 43,610 cola, ~50 s on the 1080 Ti), `shared` content lemmas, `shape` (multiset overlap of `lexical.morph.word_token` shapes / longer colon), `balance` (shorter / longer colon length).
- Prototype findings (dev notes): raw `cos` separates a poem from its prose neighbours within a book (Ex 15 0.66 vs Ex 14 0.56; Deut 32 0.63 vs 31 0.52) but not across books (law repeats itself: Leviticus ≈ Psalms); poetry restates with *other* words (shared lemmas Psalms 0.19 vs Kings 1.16). A book-relative own-vs-others percentile and verse length were tried and dropped (book- and length-dependent).
- Model: standardized logistic regression (`C` = 1) on the four features, positives = the poetic-accent books, negatives = narrative / law (`train_negative`); the prophets, Song, Lamentations, Ecclesiastes etc. are never seen. Coefficients: cos +0.83, shared −1.85, shape +0.10, balance +0.92. `prob` per verse; a verse is "parallel" at `parallel_at` = 0.5.
- Checks (2026-10-05): leave-one-poetic-book-out AUC Ps 0.85, Prov 0.90, Job 0.87. Known poems inside prose books (negatives in training) among 435 narrative / law chapters with ≥ 6 verses: Deut 33 #2, Deut 32 #3, Gen 49 #4, 2 Sam 22 #5, Ex 15 #6, Num 23 #21, Num 24 #22, 2 Sam 1 #40, Judg 5 #83, 1 Sam 2 #95 (the chapter is mostly prose; at pericope level 1 Sam 2:1–10 ranks 6th outside the poetic books). Unseen books by share of parallel verses: Song 29 %, Habakkuk 24 %, Nahum 21 %, Lamentations 21 %, Micah 20 %, Isaiah 18 % … Kings / Chronicles / Nehemiah 3–4 %. The top prose-book chapter is Num 33 (the station list: formulaic halves "they set out from X / and camped at Y") — list parallelism, not poetry; legal "if … / then …" chapters (Ex 21–22, Lev 2, 13) also score.
- Served: `parallelism` table + `meta.parallelism` (coefficients, AUCs, poem ranks). `/parallelism/{unit}` = cola, pauses, features and prob per verse; `/parallelism?unit_type&book&exclude_poetic&min_verses` = units ranked by mean prob with the share of parallel verses, plus per-book shares. Viewer: "Verse halves (te'amim)" toggle on unit pages (‖ at each pause, ∥ badge on parallel verses, `?halves=1`), Poetry page (book bars, ranked units, poetic books hidden by default).
- Limits: verse-internal only (a bicolon spread over two verses is missed); the accent pause is the Masoretic reading division, not always the poetic line; the model learns what the poetic books' parallelism looks like, so list-like and casuistic prose also scores; descriptive, no gold.

### 16.10 Wordplay (`bsim wordplay`, `analysis/wordplay.py`, `/wordplay`)
- Goal: paronomasia — different words that sound alike, close together (Isa 5:7 מִשְׁפָּט / מִשְׂפָּח, צְדָקָה / צְעָקָה).
- A word is what is heard: the pointed surface without its prefix morphemes, as a consonant skeleton (finals folded, ו / י after the first letter dropped) plus its vowel pattern (shureq = qubbuts; dagesh, meteg, shin dots ignored). Content words only (no particles, prepositions, conjunctions, pronouns; proper nouns and gentilics `Ng` skipped: name lists are built alike).
- Pairs: different lemmas within `window` = 8 words (verses crossed, chapters not) whose skeletons (≥ 3 letters) differ by one substitution, an adjacent swap or one added letter, **and** whose vowel patterns are identical. Without the vowel rule there were 10,242 pairs and no excess over chance (Hebrew roots are three letters; almost every word has one-letter neighbours); with it 400.
- Score: mean idf of the two lemmas minus 0.15 per word between them. Null: word order shuffled within each chapter (20 reps) → about 279 pairs per shuffle, so roughly 120 of the 400 are more than chance. Single pairs cannot be shown significant this way (best q ≈ 0.05), so the list is presented as ranked candidates with the corpus-level excess.
- Result (2026-10-05): the top is dense with known puns — Judg 12:6 שבלת / סבלת (shibboleth), Isa 22:5 מבוסה / מבוכה, Gen 6:14 גפר / כפר, Isa 54:8 שצף / קצף, Ezek 9:4 נאנחים / נאנקים, Isa 29:6 רעם / רעש, Judg 5:26 מחקה / מחצה, Jer 10:11 ארקא / ארעא (both Aramaic forms of "earth"); Isa 5:7 ranks 52nd and 95th. Noise: technical terms side by side (I Kgs 7:33), Aramaic lists in Ezra.
- Served: `wordplay` table + `meta.wordplay`; `/wordplay?book&kind&unit` (paginated; both words' display tokens for highlighting, one or two verses). Viewer: Wordplay page; "Wordplay" panel on unit pages.
- Limits: written vowels approximate sound (no stress, no begadkefat spirantization); one-word distance only (no sound patterns across a line: alliteration, rhyme); different-lemma pairs only, so figura etymologica and root repetition (Leitwort, §16.2) are out of scope.

### 16.11 People and places (`bsim entities`, `analysis/entities.py`, `/entities`)
- Names = OSHB proper nouns (`Np`, 2,551 lemmas; the divine names 3068 / 3069 / 3050 are left out → 2,548). OSHB does not say person or place, and no lexicon is downloaded, so the kind is read from contexts: place cues = directional ה (`Sd`), a preceding עיר / ארץ, the prefixes ב / מ; person cues = a neighbouring בן / בת, a preceding אמר / דבר. `place = 3·dir + 3·city/land + in/from`, `person = 2·son + 3·speech` (shares of occurrences); person or place when one is ≥ 1.5× the other and ≥ 0.05, else mixed, unclear without cues.
- Since M39 (§16.22) Strong's part of speech decides first and the cues below only decide the rest: 1,653 person, 734 place, 5 mixed, 156 unclear.
- Result from the cues alone (2026-10-05): 909 person, 333 place, 16 mixed, 1,290 unclear (mostly rare names in lists). Spot checks: משה, דוד, שאול, אברהם → person; ירושלם, מצרים, בבל, ירדן, כנען → place; יהודה → mixed (tribe and land). Tribes and peoples come out as persons (ישראל, אפרים, "sons of Ammon"); ציון too (בת ציון).
- Links: two names co-occur when they share a verse; pairs with ≥ 2 shared verses and more than expected are scored by Dunning's G² (3,971 pairs); each name keeps its 25 strongest. E.g. David → Saul, Jonathan, Solomon, Abner, Achish, Jesse, Hadadezer, Joab; Moses → Aaron, Israel, Pharaoh, Sinai, Eleazar; Abraham → Isaac, Sarah, Jacob, Heth, Abimelech, Ephron.
- Served: `entities`, `entity_mentions` (lemma × verse), `entity_links` + `meta.entities`; `/entities?kind&book&q` (most mentioned; in a book: mentions there; `q` matches the consonantal name), `/entities/{lemma}` (verses per book, first / last mention, partners and the links among them), `/unit-entities/{unit}` (a unit's names). Viewer: Names page (name chips by kind, a 39-book strip, an ego network of partners), name chips under the text of chapters / pericopes / parashot.
- Limits: one Strong's number may cover several people (many Zechariahs) and one person may have several (Jehoash / Joash); verse co-occurrence is coarse (lists and genealogies link everyone in them); the kind heuristic is a guess, shown as such.

### 16.12 Where the style changes (`bsim seams`, `analysis/seams.py`, `/seams`)
- The §16.6 features (100 MFW + 25 morphology rates incl. Aramaic) counted per verse. At every verse boundary of a book the `block_words` = 600 words before and after (whole verses) are compared by Burrows' Delta, each feature scaled by its SD across chapters (≥ 150 words). The curve peaks where the style turns.
- Threshold per book: verse order shuffled 50 times; the 95th percentile of the shuffled curves' maxima (a book shows a seam by chance with ≈ 5 % probability). Seams = peaks above it, strongest first, ≥ 600 words apart, each with the 6 features that change most (z after − before).
- Result (2026-10-05): 241 seams in 29 books (median 9; ~25 s). Known boundaries recovered, often a few verses late because the window is 600 words wide: Daniel 8:1 (Aramaic → Hebrew; Aramaic z −9.7) and 2:21 (Hebrew → Aramaic, true 2:4), Ezra 4:21 (Aramaic letters, true 4:8), Prov 22:17 (the "words of the wise") and 24:30, Isa 36:2 (the narrative chapters 36–39) and 40:9 (true 40:1), Zech 9:4 (true 9:1), Job 3:8 (end of the prose frame) and 32:1 (Elihu), Ezek 40:5 (the temple vision), 1 Chr 10:1 (genealogies → narrative), Gen 4:16 / 6:11 (the Gen 5 genealogy), Num 7:11 / 7:89, Neh 7:5 / 8:4, Ezra 2:70 (lists).
- Served: `seam_curve`, `seams` + `meta.seams`; `/seams?book` (curve with chapter / verse, threshold, seams with labelled features) or without a book the strongest seams by shift / threshold. Viewer: Style page "Where the style changes" — shift chart with threshold and peaks for the chosen book, seam list with ↑ / ↓ features; corpus list without a book.
- Limits: list-like passages (genealogies, census, offerings) dominate because their rates are extreme; window-width blur; descriptive (genre, language, speaker or source shifts look alike).

### 16.13 A second gold set: OpenBible cross-references (`bsim eval-openbible`, `eval/openbible.py`)
- Why: Sefaria links train the semantic model and are the gold (§8.4), so the systems are only ever measured against the connections the commentary tradition made famous. OpenBible.info's crowd-voted cross-references (CC-BY, Treasury of Scripture Knowledge based; downloaded on first use to `data/raw/openbible/`) are an independent check — evaluation only, dev split only, nothing tuned on them.
- Gold: Hebrew Bible ↔ Hebrew Bible references with ≥ `min_votes` = 5 votes; target ranges expanded (≤ 10 verses). OpenBible numbers verses the English (KJV) way. Rather than a renumbering table, references touching chapters where KJV and Hebrew differ (`openbible.unsafe_chapters`: all Psalms because of the titles; Gen 31–32, Exod 7–8 / 21–22, … Joel 2–4, Mal 3–4) or verses the Hebrew chapter lacks are dropped. Pairs are undirected, neighbours dropped, and split by the Sefaria rule (test if either book is a test book, else dev if either is dev).
- Result (2026-10-05): 187,117 Hebrew Bible references → 30,311 verse pairs (139,022 under 5 votes, 22,714 unsafe / unresolved). Dev: 6,318 directed pairs over 2,541 query verses vs Sefaria's 1,204 — only 188 shared (3 % of OpenBible, 16 % of Sefaria). nDCG@10 OpenBible / Sefaria: fused 0.146 / 0.189, lexical 0.133 / 0.176, semantic 0.111 / 0.150, structural 0.039 / 0.068. The order of the systems holds on independent gold, and the Sefaria-trained encoder loses about as much as BM25 (−26 % vs −24 %), so it has not merely learned Sefaria's notion of a parallel.
- Outputs: `data/processed/openbible_links.parquet`, `artifacts/eval/openbible.json` + `openbible.md`. Pipeline stage `eval-openbible` after `evaluate` (needs network on first run).
- Limits: dropping the versification-unsafe chapters removes all of Psalms; TSK-style references include many thematic / topical links, which neither lexical nor semantic similarity targets.

### 16.14 Significance across many tests (`analysis/stats.py`)
- Every pattern analysis scores hundreds or thousands of units, so a per-unit p ≤ 0.05 is expected for ~5 % of them by chance. Shared helpers: `empirical_p` (Monte Carlo, `(1 + #null ≥ obs) / (1 + reps)`, never 0), `pct_to_p` (a percentile against `samples` null draws → upper-tail p) and `bh_q` (Benjamini–Hochberg q-values; NaN p stays NaN).
- Applied to: acrostics (§16.15), rewrites (§16.16) and inclusio / chiasm (`structure.{basis}_{inclusio|chiasm}_q`, BH within each unit type). Sequences and wordplay keep their null-ratio q (§16.7, §16.10), which is an empirical FDR of the same kind.
- Result (2026-10-05): of 4,464 scored units, 284 (semantic) / 300 (lexical) inclusio frames have q ≤ 0.05 — topped by the Hallelujah-framed psalms (8, 106, 118, 135, 145, 146, 150), Jonah 2, Num 23 — and **no chiasm survives** (the chiasm percentiles are as many as chance gives; the ranking stays a list of leads).
- Sevens: Leitwort counts (§16.2) are often said to come in multiples of 7 or 10. `bsim structure` counts, over every chapter's Leitworte (top 12, ≥ 3 occurrences), the multiples of m against those expected from lemmas with similar counts (the share of multiples among all content-lemma counts within the m consecutive integers centred on each count), for m = 6 … 13 (`structure.leitwort_moduli`) so that 7 and 10 have controls. Result: 776 multiples of 7 vs 669.5 expected (1.16×, 9,241 Leitworte), 309 vs 219.6 for 10 (1.41×) — but every divisor shows an excess that grows with m (6: 1.18×, 8: 1.32×, 12: 1.66×), the signature of an imperfect count baseline, and **7 has the smallest**. Nothing singles out 7; the Structure page says so (`meta.leitwort_numbers`).

### 16.15 Acrostics (`bsim acrostics`, `analysis/acrostic.py`, `/acrostics`)
- Goal: alphabetic acrostics, whole and broken, in any line unit: a verse (Ps 25, 34, 145, Prov 31, Lam 1, 2, 4), a half-verse (Ps 111, 112), a block of verses (Ps 37, Lam 3, Ps 119); letters missing or swapped (Ps 9–10, Nahum 1; פ before ע in Lam 2–4).
- Lines: the first letter of every verse, and of every colon (the te'amim cola of §16.9), from the MAM display text (finals folded). A chain is a run of lines whose letters advance through the alphabet, at most `max_line_gap` = 8 lines apart (blocks), a skipped letter costing `missing_penalty` = 1: score = letters − skipped. Dynamic programming per chapter, over both line units and both orders (standard, פ/ע swapped); the best is kept with its lines.
- Null: the chapter's lines shuffled (letter mix kept), the same best-of-variants score; p = `empirical_p`; 199 shuffles first and all 9,999 only when fewer than 10 reach the score (21 s for 929 chapters instead of 281 s); q = BH over all chapters.
- Result (2026-10-05): 13 chapters with q ≤ 0.05 and all 13 are known acrostics — Ps 119, 34, 145, 37, 111, 112, 25, 9, Prov 31, Lam 1–4 (Lam 2–4 in the פ/ע order) — 13 of the 14 listed in `acrostics.known` (recall 0.93). Nahum 1 (a broken half-alphabet in irregular half-lines) is not found. Next, as candidates only: Job 33 (q 0.40), Prov 9 (0.66), I Kgs 22 (0.84).
- Served: `acrostics` table + `meta.acrostics`; `/acrostics?max_q&book` (default q ≤ 0.05), `/acrostics/{unit}` (null without one). Viewer: Acrostics page (the alphabet with found / skipped letters); on a chapter that is one, a bar with "Mark the letters" (`?acrostic=1`).
- Limits: a title or a word before the letter (Ps 25:1 לדוד, אליך) loses that letter; only the first letter of a line is read (no internal or telestich acrostics); chapters only (Ps 9–10 is found as Ps 9's half).

### 16.16 Systematic rewrites (`bsim diffs`, `analysis/diffs.py`, `/rewrites`, `/rewrite-profiles`)
- Goal: the habits of a later text against its source — changes that recur between two books more than their overall rate of change explains, rather than single differences.
- Per book pair (A = earlier in canon order) over the word alignments of §16.8: for each `substitution` a_key → b_key, `omitted` a_key and `added` b_key seen ≥ `diffs.rewrite_min_count` = 2 times, `n`, the `base` = words with that key on the side the change starts from (A; B for additions), `rate` = n / base, and Dunning's G² of the 2 × 2 table (word has the key or not) × (undergoes this change or not) over that side's words; p from χ²(1) when over-represented; q = BH over all rows. Per pair also a profile: diffed verse pairs and words, counts per change, and the direction of the spelling changes (B adds a ו / י vowel letter, or drops one).
- Result (2026-10-05): 550 rewrites, 151 with q ≤ 0.05. Top: II Sam → I Chr יהוה → אלהים (14 of 61, G² 78; also I Kgs → II Chr), II Kgs → II Chr יהואש → יואש (7 of 8), II Sam → I Chr אל → על and ארונה → ארנן, ממלכות → מלכות, Hiram חירם → חורם, II Kgs → Isa בראדך → מרדך. Spelling: Chronicles writes fuller than Samuel (135 vowel letters added vs 15 dropped) and Kings (112 vs 30); Exodus 25–31 → 35–40 goes the other way (16 vs 25). Repeats inside one book (the tabernacle chapters, the lists of Numbers) also rank and are best read with a book pair selected.
- Served: `rewrites`, `rewrite_profiles`; Viewer: Changes page → "Systematic rewrites" (book pair, profile, table with links to the examples).
- Limits: only strong parallel sequences are diffed (§16.8), so most book pairs have a handful of verses; a substitution with different Strong's numbers may be a synonym or a spelling of a name (both are listed); no direction is claimed beyond canon order.

### 16.17 Network of echoes (`bsim network`, `analysis/network.py`, `/network`)
- Goal: the corpus as a graph rather than as lists — which passages the rest of the Bible echoes most, and which groups of passages echo each other across books.
- Graph per unit type (chapter, pericope): an edge when either unit has the other in its final fused top `edge_rank` = 10, weight `(11 − rank) / 10` of the better direction; consecutive units of one book are not linked (`skip_adjacent`), or each book would chain into one community. Chapters: 929 nodes, 5,771 edges; pericopes: 3,482 nodes, 22,488 edges.
- Centrality: weighted PageRank (damping 0.85), plus strength, partners and the share of the strength reaching other books. Communities: Louvain (networkx, `resolution` = 3, seeded; resolution 1 gives about 15 genre-sized groups), labelled by G² lemmas (as the map clusters, §16.4) and books. Layout: seeded spring layout inside each community, stored as x, y.
- Result (2026-10-05, 5 s): 28 chapter / 49 pericope communities. Most echoed chapters: Jer 50, Ps 31, Ps 119, Jer 4, Jer 51, Ps 89, Jer 6, Isa 10. Communities that cross books: Esther with the Daniel court tales, the Aramaic of Daniel and Ezra, Haggai–Zechariah–Malachi, Deuteronomy with Joshua, Ezekiel's temple measurements with the tabernacle chapters, the oracles against the nations (Isa, Jer, Amos), Hosea with Jeremiah and Amos, Elijah–Elisha across Kings and Chronicles. Among pericopes the Abraham cycle forms one community holding all three wife–sister stories and the Abimelech covenant (Gen 21:22–34).
- Served: `network_nodes`, `network_edges`, `network_communities`; `/network/{type}` (communities + top PageRank), `/network/{type}/{community}` (nodes with layout + edges among them), `/unit-network/{unit}` (rank, community). Viewer: Network page (community list, SVG graph of one community: size = centrality, colour = section, every node a link; table fallback), a line on chapter / pericope pages ("n-th most echoed … its community").
- Limits: edges inherit the fused lists' biases (formulaic and list-like texts link densely); communities depend on `resolution`; PageRank rewards long, varied units (Ps 119, Jer 50–51) that resemble many others.

### 16.18 Finer accent structure and word pairs (`text/accents.py`, `bsim parallelism`)
- Accent hierarchy (Wickes, Yeivin): prose level 1 etnahta; 2 segolta, shalshelet, zaqef qatan / gadol, tipeha; 3 revia, zarqa (MAM encodes it with the zinor mark), pashta, yetiv, tevir; 4 geresh, gershayim, pazer, qarne para, telisha gedola. Poetry: 1 etnahta, oleh-ve-yored; 2 revia, shalshelet gedola, tsinnor; 3 dehi, pazer. Legarmeh is not read. `token_levels` gives the pause after each word, `clauses` splits at level ≤ 2 (most verses: 4–6 clauses). Served as `parallelism.clauses`; the viewer's "Finer clauses" marks them with a thin bar inside the halves.
- Bicola across two verses: for two consecutive one-colon verses of a chapter the §16.9 features are measured between the verses and scored with the same model (`next_prob`, on the first). Result: 576 such pairs, 192 at p ≥ 0.5 — nearly all short list items (I Chr 1, Nehemiah, Joshua's town lists), a few in Lamentations and the Song. One-colon verses are rare in poetry, so this extends the coverage only a little; shown as ∥↓.
- Typing parallelism (synonymous / antithetic) was tried with a negation-asymmetry cue (one half negated, the other not): it marks Prov 10–15, the classic antithetic chapters, *least* often (11 % vs 12–21 % elsewhere), because antithesis there is carried by contrasting words (צדיק / רשע, חכם / כסיל), which needs a lexicon (D27). Dropped; done with SDBH antonyms in §16.22 (Prov 10–15 then rank first).
- Word pairs instead: ordered content-lemma pairs across the two members of parallel lines (halves with p ≥ 0.5, verse pairs with `next_prob` ≥ 0.5; 4,511 members), Dunning's G², BH q, seen ≥ 3 times in ≥ 3 chapters (one list's formulas stay out). Result (2026-10-05): 1,513 pairs, 683 with q ≤ 0.05 — צדיק // רשע (28, and 14 the other way), יום // שנה, חכם // כסיל, עולם // דור, מוסר // תוכחת, פה // לשון, פה // שפה, חכמה // בינה / תבונה / דעת, חסד // אמונה, ציון // ירושלם, אויב // שנא, ים // מים, אל // שדי, ברזל // נחשת, משל // חידה, צדיק // ישר, רחום // חנון; noise from repeated prose formulas that the classifier scores as parallel (the itinerary יסעו // יחנו, offerings). Served: `word_pairs`, `/word-pairs`; Poetry page → Word pairs.

### 16.19 Alliteration and rhyme (`bsim sound`, `analysis/sound.py`, `/alliteration`, `/rhymes`)
- Sounds are phonemes: ב / כ / פ count as one sound with or without dagesh (פַּחַד וָפַחַת וָפָח, Isa 24:17, is p / f / f), שׁ and שׂ apart.
- Alliteration: per colon (≥ 3 content words; function words skipped; each lemma once, as repeating a word is repetition), the initial sound after the prefix particles and its count. Chance is conditioned on word shape (`lexical.morph.word_token`): grammar fixes many first letters (every wayyiqtol starts with י), so each word has its shape's sound rates (smoothed, `shape_smoothing` = 50); p bounds the chance any sound reaches the count (exact Poisson-binomial tails, Bonferroni over sounds); BH over cola. Result: 45,194 cola, 6,298 scored, **no colon survives** (Isa 24:17 p = 0.007, q = 0.55; Nah 1:10 סירים סבכים near the top); fewer cola reach p < 0.01 than the nominal 1 % (the bound is conservative), so there is no evidence of excess either way. Shown as ranked candidates.
- Rhyme: runs of ≥ 3 consecutive cola within a chapter whose last words end alike (last two consonants with the vowel under the first) while the words differ; p = f(ending)^(run − 1) × positions, BH. Result: 113 runs, 4 with q ≤ 0.05 — Job 10:8–11 (‑נִי ×8), Josh 23:10–13 (‑כֶם), Ps 104:29–30 (‑וּן), Dan 6:14–15. Biblical rhyme is suffix rhyme; the commonest endings are ‑ים, ‑וָה, ‑יו.
- Served: `alliteration`, `rhymes` + `meta.sound`; Wordplay page → Alliteration / Rhyme.

### 16.20 Action sequences (`bsim typescenes`, `analysis/typescenes.py`, `/typescenes`)
- Goal: type-scenes — the same actions in the same order with other people and words. Each pericope (≤ 80 verses) becomes its sequence of verb lemmas, the 13 verbs found in > 15 % of pericopes left out (אמר, היה, בוא, ראה, …); candidates share verbs worth ≥ 8 idf (each pericope keeps its 15 strongest; 30,295 pairs); Smith–Waterman (match = the verb's idf, mismatch −1, gap −0.5) keeps alignments of ≥ 4 verbs; the null shuffles verb order inside every pericope (5 reps), so q measures order beyond shared vocabulary. Pairs joined by a significant parallel sequence (§16.7) are flagged `parallel_text`.
- Result (2026-10-05, 142 s): 36 alignments with q ≤ 0.05, 29 of them textual parallels (II Sam 22 ↔ Ps 18, Ex 29 ↔ Lev 8, II Kgs 18–19 ↔ Isa 36–37, I Kgs 22 ↔ II Chr 18). The other 7: Dan 7:1–14 ↔ 7:15–28 (vision and its interpretation), Dan 2:31–45 ↔ 7:1–14 (the two four-kingdom visions), Dan 3 ↔ Dan 6 (accused, thrown in, rescued), Lev 8 ↔ 9 (ordination and first sacrifices), Lev 15 ↔ Num 19 and within Lev 15 (purification procedures), Ps 40 ↔ 70 (a textual parallel the sequence chains miss).
- Negative result: the classic literary type-scenes are not recovered. At chapter level Gen 24 ↔ Gen 29 (the well) scores 5.4 with verbs and nouns against random chapter pairs at a median 2.0 / 95th percentile 4.0, Gen 18 ↔ Judg 13 1.9; with verbs only all stay within the random range. They vary their verbs (ירד / דלה / שאב) more than their order constrains them.
- Served: `typescenes`, `/typescenes?book&max_q&hide_textual&unit`; viewer: Parallels → Action sequences.

### 16.21 Contextual embeddings and late interaction (`bsim embed-context`, `bsim maxsim`, `bsim retrieval-exp`) — not adopted
- **Contextual embeddings** (`embed/context.py`): every verse is encoded with BEREL-sup together with one verse on each side, never across a chapter boundary (window tokens max 124, none truncated at 256). One forward pass gives two systems: `berel_sup_ctx` (mean of every window token) and `berel_sup_late` (mean of the centre verse's tokens only, read in context: "late chunking"). Both get CSLS top-k lists like the other encoders.
- **MaxSim** (`retrieve/maxsim.py`): ColBERT-style late interaction without training. Each verse's own token vectors (special tokens dropped, L2-normalized; 334k tokens) score its fused top-50 candidates by the mean best cosine per token, averaged over both directions. 1.16M pairs take about 40 s per encoder on the 1080 Ti, for BEREL-sup and plain BEREL. The scores reorder the fused list, blended with the fused rank by RRF like the cross-encoder.
- **Protocol** (`eval/experiments.py`), dev only, nDCG@10 with ±2 neighbours dropped. Each family's members (the context list alone, in place of the semantic list, or as a third RRF list at w 0.25 / 0.5 / 1; MaxSim at w 0.25–2 or alone) are compared with `fused` (Sefaria 0.1895, 884 queries; OpenBible 0.1460, 2,541 queries) by a paired bootstrap over queries:
  - *selected*: the member best on Sefaria dev, scored on the same queries, as in M18
  - *cross-fitted*: chosen on one half of the queries, scored on the other half
  - *OpenBible*: the selected member on the second gold, which no choice looks at

  Adopted only if the cross-fitted CI excludes 0 and the OpenBible gain is not negative. The harness reproduces M18's cross-encoder figure (+0.0042, CI [−0.0008, +0.0093]).
- **Results (2026-10-05)** — nDCG@10 gain over fused (95 % CI):

  | family | best member | selected | cross-fitted | OpenBible |
  |---|---|---|---|---|
  | context window (`berel_sup_ctx_csls`) | third list w 0.25 | +0.0031 [−0.0026, +0.0086] | +0.0031 [−0.0026, +0.0086] | +0.0005 [−0.0021, +0.0033] |
  | late chunking (`berel_sup_late_csls`) | in place of semantic | +0.0047 [−0.0057, +0.0153] | +0.0032 [−0.0050, +0.0114] | −0.0005 [−0.0055, +0.0045] |
  | MaxSim, BEREL-sup | w 0.25 | −0.0001 [−0.0033, +0.0033] | −0.0001 [−0.0033, +0.0033] | −0.0016 [−0.0036, +0.0004] |
  | MaxSim, BEREL | w 0.25 | −0.0029 [−0.0069, +0.0012] | −0.0029 [−0.0069, +0.0012] | −0.0001 [−0.0024, +0.0022] |
  | cross-encoder (M18) | w 0.25 | +0.0042 [−0.0008, +0.0093] | +0.0027 [−0.0038, +0.0091] | +0.0018 [−0.0010, +0.0047] |

- **Reading:**
  - Context on its own is much worse than the verse (window alone 0.106, late alone 0.148, vs `berel_sup_csls` 0.150): the gold links are verse-to-verse, and the neighbours blur the verse.
  - Late chunking is as good as the plain verse embedding and could replace it, but it adds nothing measurable.
  - MaxSim alone (0.163) is below the fused list, and every blend lowers it: word-to-word matching repeats what BM25 over lemmas already captures.
  - No family clears the bar, so `final_systems` stay unchanged and the DB / UI are unaffected. `fused_maxsim` and the context lists remain evaluated systems in the dev report. The stages are manual (not in `bsim all`); the test split is not run again.

### 16.22 Word senses and semantic domains (`bsim lexicon`, `data/lexicon.py`, `lexical/domains.py`)
- **Sources** (`bsim download --only lexicon`, pinned commits in `sources.sdbh` / `sources.hebrew_lexicon`; D56):
  - the UBS Dictionary of Biblical Hebrew (SDBH v0.9.3, CC BY-SA 4.0): 16,573 meanings, 16,294 of them with lexical semantic domains (419 domains in up to five levels, a 3-digit code per level), plus Hebrew synonyms and antonyms and every verse word the meaning is attested in;
  - OpenScriptures HebrewStrong.xml (CC BY 4.0): Strong's part of speech, whose `n-pr-m` / `n-pr-f` / `n-pr-loc` mark 1,607 person, 674 place and 97 person-or-place names.

  Glosses and definitions are read but never stored or shown: domains are classification labels for the interface, not a translation of the text (D5).
- **Word senses.** An SDBH reference `BBBCCCVVVSSWWW` names a book in Protestant order and a morpheme position in OSHB's verse: words count 2, 4, 6, … over the lemma parts of each word, plus one for the article hidden in a preposition (`Rd`); pronominal suffixes do not count. Each reference is matched to the nearest morpheme within `lexicon.search_window` (2) whose Strong number (no prefix, padding or homograph letter) is one of the meaning's. 265,704 of 288,148 references match (92.2 %; 249,950 at the exact position); the 3 verses MAM splits or joins are skipped. Of 299,516 lemma morphemes, 258,747 get the meaning SDBH attests there and 3,841 more take their lemma's meanings (weights split when they differ, `lexicon.ambiguous: split`); a matched meaning without a domain leaves its morpheme untagged rather than falling back to the lemma.
- **Outputs** (`data/processed`): `word_senses.parquet` (verse, word, lemma part, Strong, meanings, domains with weights, source), `lexicon_senses`, `lexicon_domains`, `lexicon_relations` (13,741 synonym and 2,098 antonym lemma pairs, both directions; a pair given both ways keeps its antonym reading), `lexicon_lemmas` (Strong's part of speech and name type).
- **Domain retrieval** (`lexical/domains.py`): every content morpheme becomes its domain codes, weighted by its share of each, plus its broader domains at `lexical.domain.ancestor_weight`. `bsim lexical` builds `bm25_domain` over these tokens, `tfidf_domain_{unit}` for larger units, and, for the experiment, `bm25_lemma_domain`: `bm25_lemma`'s tokens plus the domain tokens at `expansion_weight` (0.75).
- **Results (dev, nDCG@10, `bsim retrieval-exp`, same protocol as §16.21)**:
  - `bm25_domain` alone: Sefaria 0.075, OpenBible 0.066 (with broader domains at 0.5: 0.066 / 0.062, so `ancestor_weight` is 0).
  - `bm25_lemma_domain` alone: 0.180 vs `bm25_lemma` 0.176 (+0.0045, CI [+0.0003, +0.0087]; OpenBible +0.0067, CI [+0.0039, +0.0093]). Domains do help the word list.
  - Against `fused`:

  | family | best member | selected | cross-fitted | OpenBible |
  |---|---|---|---|---|
  | `bm25_domain` | third list w 0.25 | −0.0017 [−0.0069, +0.0034] | −0.0017 [−0.0069, +0.0034] | +0.0003 [−0.0026, +0.0033] |
  | `bm25_lemma_domain` | in place of lexical | +0.0003 [−0.0038, +0.0044] | −0.0021 [−0.0075, +0.0030] | +0.0042 [+0.0016, +0.0069] |

  - Neither is adopted: what domains add to the lemma list, the semantic list already supplies once the two are fused. The lexical mode stays word-based, so its shared-lemma explanations remain exact.
- **Synonymous and antithetic parallelism** (`bsim parallelism`, §16.9; revisits §16.18). Each pair of members of a parallel verse (`prob ≥ parallel_at`) is *antithetic* when a lemma of one half and a different lemma of the other are SDBH antonyms, else *synonymous* when they are SDBH synonyms or two different lemmas share a domain; a verse takes its strongest pair's type, stored with the word pairs that decided it (`relation`, `relation_pairs`). Of 4,173 parallel verses, 376 are antithetic and 2,022 synonymous.
  - Prov 10–15, the classic antithetic chapters that D49's negation cue placed *last*, now come first: 69.1 % of their parallel verses are antithetic against 6.8 % elsewhere (149 verses, one-sided Fisher p = 4 × 10⁻⁷⁷).
  - Antonym pairs across the halves of a line are 8.8 % of member pairs against 1.5 % when each first half is paired with another line's second half (50 shuffles, p = 0.02, the smallest 50 shuffles allow).
  - Outside Proverbs the antithetic verses are mostly true contrasts (Ps 115:16 שמים / ארץ, Deut 7:22 מעט / רבה, Isa 57:15 רום / שפל, Ps 92:3 בקר / לילה), with some noise from SDBH's broader antonyms (Exod 19:1 יצא / בוא).
  - Caveat: SDBH's lexicographers may have drawn some antonym pairs from these very verses, so the Proverbs check confirms the typing more than it discovers anything.
  - Ranked by antithetic share (chapters with ≥ `typing_min_parallel` = 10 parallel verses), Prov 12, 28, 13, 11, 14, 10, 15 lead; Prov 28, outside the check, is the other antithetic collection of the book (Prov 28–29).
- **Served** (`build-db`: `domains`, `domain_verses`, `words.domains`, `parallelism.relation*`, `entities.kind_*`; empty / NULL without `bsim lexicon`):
  - the `domain` mode (`bm25_domain`, unit `tfidf_domain`) next to structural, not fused: similar units by shared semantic fields whatever the words (Gen 1:1 → Prov 8:22–26, wisdom "at the beginning");
  - `/domains` (the tree, levels 1–3, deeper on each domain's page) and `/domains/{code}` (path, subdomains, verses per book, verses with the domain's words highlighted);
  - a unit's *themes* (`/unit-domains`): domains of any level below the top whose word weight is over-represented against the corpus share (Dunning's G², weight ≥ `serve.domains.min_weight`, the `serve.domains.top` strongest); Genesis 1 → Shine, Exist, Time, Land, Animals; Job 1 → Names of Supernatural Beings, Flee, Revile, Innocent;
  - domain chips in the word panel, `∥≠` and the deciding pairs on antithetic verse halves, the Poetry ranking by antithetic share, a name's kind source on Names.

  Domain names are SDBH's English labels; the two top levels (22 names) are also in the Hebrew catalog (`i18n/pages/domains.ts`), deeper ones stay English inside `<bdi>` in the Hebrew interface.
- **People and places** (`bsim entities`, §16.11): Strong's part of speech now decides first (`kind_source: lexicon` for 2,253 of 2,548 names); the context cues decide the rest (names Strong's gives both readings, or none). Where both decide (1,108 names) they agree 94.8 % of the time (person/place 35, place/person 23 disagreements), which validates the cue heuristic. `unclear` names drop to 156.

### 16.23 Senses and uses across the canon (`bsim senses`, `analysis/senses.py`, `/shifts`, `/lemma/{lemma}/senses`)
- **Question:** does a word mean or do something different in different parts of the canon (roadmap A3)?
- **Words compared:** 611 content lemmas with ≥ 50 occurrences as a word's only content lemma, ≥ 10 in each of ≥ 2 of six groups: Torah, Former Prophets, Latter Prophets, Psalms / Proverbs / Job, the Scrolls (Song, Ruth, Lamentations, Ecclesiastes, Esther), the late books (Daniel, Ezra–Nehemiah, Chronicles). Names are left out (OSHB `Np` and Strong's name types). 215,928 occurrences.
- **Two readings of each occurrence:**
  - *Dictionary sense*: the SDBH meaning tagged on it by `bsim lexicon` (occurrences with exactly one matched meaning; meanings with ≥ 5 of them; 384 lemmas have ≥ 2).
  - *Use in context*: its vector from pretrained BEREL (`berel_mean`, last layer, mean of the word's subword tokens, mapped by character offsets on `text_model`), clustered per lemma by k-means, k ∈ 2..4 by silhouette. A cluster is described only in Hebrew: the content lemmas of its verses most over-represented against the lemma's other clusters (G², particles and pronouns left out) and its occurrences nearest the centre.
- **Statistic:** MI(group; sense) in bits, i.e. the generalized Jensen–Shannon divergence of the groups' distributions. The null shuffles group labels over occurrences (200 times); p is empirical, q is Benjamini–Hochberg over lemmas, and the ranking uses the excess over the null mean (MI is inflated in small samples). With 200 shuffles the smallest q is 0.008.
- **Results (2026-10-05):**
  - Dictionary senses depend on the group for 296 of 384 lemmas (q ≤ 0.05). The strongest are textbook cases:
    - גאל: the blood avenger (Numbers, Joshua), redeeming property (Leviticus, Ruth), God the redeemer (Isaiah, Psalms);
    - פקד: muster (Numbers), punish (prophets), appoint (Kings);
    - עדות / עדת: the ark of the testimony (Torah), "your testimonies" (Psalms);
    - קנה: menorah branches (Exodus), measuring reed (Ezekiel).
  - Contextual uses depend on the group for 539 of 611 lemmas. This reading also carries genre and register, so it means "used differently", not necessarily "means something else". Its ranking is still informative:
    - תורה splits without supervision into the written "book of the Torah" (Torah, Former Prophets, late books), poetic "instruction" (Psalms, prophets) and ritual "torah of the burnt offering / leprosy";
    - נפש separates the legal "that person shall be cut off" (Torah) from the poetic "my soul" (Psalms).
  - **Check:** the clusters recover the SDBH meanings with NMI 0.20 on average against 0.03 for shuffled clusters (384 lemmas). Unsupervised contextual vectors do find dictionary senses, partially.
- **Served:** `lemma_shifts` and `lemma_senses` (+ `meta.senses`); `/shifts?by=sense|use&max_q=`; `/lemma/{lemma}/senses`. Viewer: Overview → Shifts, and *Senses across the canon* on every concordance page (share of each sense per group, domains, Hebrew collocates, highlighted examples).
- **Limits:**
  - BEREL's last layer and verse-only context.
  - SDBH tags 90 % of the text and some of its meanings are fine-grained.
  - Group sizes differ by an order of magnitude.
  - No diachronic claim: the groups mix date and genre.
