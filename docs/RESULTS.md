# Results — bible-similarity

Metrics only: no verse text and no per-pair listings (those are in the local, gitignored `artifacts/eval/report.md`). Section numbers (§) refer to [DESIGN.md](DESIGN.md). All numbers are from the 2026-10-04 build (config hash `183fd8d2ec2c` for evaluation).

## Setup

| item | value |
|---|---|
| verses / chapters / pericopes / parashiyot | 23,206 / 929 / 3,482 / 54 (MAM versification) |
| OSHB words / aligned to MAM display tokens | 305,517 / 99.96 % |
| gold (Sefaria book↔book links) | 6,018 undirected verse pairs + 818 unit-level links |
| book split train / dev / test (§8.2) | 20 / 6 / 13 books; 4,513 / 602 / 903 verse pairs (75 / 10 / 15 %) |
| dev queries (verse / chapter / pericope) | 884 / 154 / 348 |
| test queries (verse / chapter / pericope) | 1,345 / 232 / 686 |
| parasha | no dev/test gold (all of the Torah is train) |

Dev books: Joshua, Judges, Haggai, Zechariah, Ecclesiastes, Nehemiah. Test books: I Samuel, Ezekiel, Micah, Nahum, Zephaniah, Proverbs, Job, Song of Songs, Ruth, Lamentations, Esther, Daniel, Ezra.

Metrics: recall@{1,5,10,50}, MRR@10 and nDCG@10 with binary relevance, macro-averaged over queries with ≥ 1 gold link; verse predictions have the ±2 same-book neighbours removed; unit gold = ≥ 2 shared verse links or an overlapping unit-level link (§8.3).

## Final systems

| mode | verse | chapter / pericope / parasha |
|---|---|---|
| lexical | `bm25_lemma` (lemma + bigram BM25, formula weight 0.2) | `tfidf` (sublinear TF-IDF on lemma bags) |
| semantic | `berel_sup_csls` (BEREL 3.0 supervised fine-tune + CSLS) | `berel_sup_csls_bma` (best-match average) |
| fused | `fused` (weighted RRF, `w_lex = w_sem = 1`, k = 60) | `fused` (same weights) |

All choices were made on dev; the test split was evaluated once, at the end (M9).

## Test (single run, final systems)

Evaluated 2026-10-04T12:11:49Z.

### verse
| system | recall@1 | recall@5 | recall@10 | recall@50 | mrr@10 | ndcg@10 | queries |
|---|---|---|---|---|---|---|---|
| fused | 0.071 | 0.155 | 0.199 | 0.314 | 0.130 | 0.136 | 1345 |
| bm25_lemma | 0.065 | 0.131 | 0.167 | 0.281 | 0.114 | 0.118 | 1345 |
| berel_sup_csls | 0.064 | 0.133 | 0.166 | 0.266 | 0.115 | 0.118 | 1345 |

### chapter
| system | recall@1 | recall@5 | recall@10 | recall@50 | mrr@10 | ndcg@10 | queries |
|---|---|---|---|---|---|---|---|
| fused | 0.066 | 0.168 | 0.230 | 0.449 | 0.177 | 0.157 | 232 |
| tfidf | 0.077 | 0.153 | 0.204 | 0.416 | 0.179 | 0.153 | 232 |
| berel_sup_csls_bma | 0.063 | 0.156 | 0.228 | 0.410 | 0.171 | 0.152 | 232 |

### pericope
| system | recall@1 | recall@5 | recall@10 | recall@50 | mrr@10 | ndcg@10 | queries |
|---|---|---|---|---|---|---|---|
| fused | 0.023 | 0.067 | 0.106 | 0.215 | 0.072 | 0.068 | 686 |
| tfidf | 0.025 | 0.056 | 0.097 | 0.167 | 0.068 | 0.062 | 686 |
| berel_sup_csls_bma | 0.021 | 0.064 | 0.097 | 0.227 | 0.065 | 0.061 | 686 |

Fusion is the best system at every level on test: verse nDCG@10 0.136 vs 0.118 for either input, chapter 0.157, pericope 0.068.

## Dev (all systems)

### verse
| system | recall@1 | recall@5 | recall@10 | recall@50 | mrr@10 | ndcg@10 | queries |
|---|---|---|---|---|---|---|---|
| fused | 0.098 | 0.213 | 0.274 | 0.400 | 0.184 | 0.189 | 884 |
| bm25_lemma | 0.102 | 0.194 | 0.237 | 0.356 | 0.178 | 0.176 | 884 |
| berel_sup_csls | 0.069 | 0.169 | 0.226 | 0.346 | 0.143 | 0.150 | 884 |
| bm25_surface | 0.081 | 0.162 | 0.203 | 0.297 | 0.143 | 0.144 | 884 |
| berel_sup | 0.072 | 0.162 | 0.210 | 0.341 | 0.141 | 0.144 | 884 |
| bge_m3_csls | 0.080 | 0.149 | 0.183 | 0.259 | 0.135 | 0.135 | 884 |
| berel_simcse_csls | 0.066 | 0.154 | 0.190 | 0.304 | 0.130 | 0.132 | 884 |
| berel_mean_csls | 0.069 | 0.134 | 0.172 | 0.275 | 0.124 | 0.124 | 884 |
| berel_simcse | 0.060 | 0.140 | 0.181 | 0.302 | 0.121 | 0.123 | 884 |
| bge_m3 | 0.071 | 0.140 | 0.167 | 0.228 | 0.124 | 0.123 | 884 |
| berel_mean | 0.060 | 0.121 | 0.161 | 0.253 | 0.111 | 0.113 | 884 |

### chapter
| system | recall@1 | recall@5 | recall@10 | recall@50 | mrr@10 | ndcg@10 | queries |
|---|---|---|---|---|---|---|---|
| tfidf | 0.091 | 0.189 | 0.243 | 0.427 | 0.232 | 0.192 | 154 |
| fused | 0.073 | 0.156 | 0.217 | 0.404 | 0.201 | 0.168 | 154 |
| berel_sup_csls_bma | 0.068 | 0.164 | 0.202 | 0.373 | 0.185 | 0.156 | 154 |
| bge_m3_csls_bma | 0.064 | 0.144 | 0.195 | 0.355 | 0.178 | 0.148 | 154 |
| berel_sup_csls_mean | 0.061 | 0.149 | 0.187 | 0.350 | 0.180 | 0.147 | 154 |
| berel_sup_bma | 0.052 | 0.152 | 0.188 | 0.370 | 0.165 | 0.141 | 154 |
| berel_sup_mean | 0.057 | 0.119 | 0.181 | 0.316 | 0.164 | 0.135 | 154 |
| bge_m3_csls_mean | 0.058 | 0.110 | 0.151 | 0.307 | 0.160 | 0.120 | 154 |
| berel_mean_bma | 0.033 | 0.121 | 0.159 | 0.305 | 0.134 | 0.115 | 154 |
| berel_mean_mean | 0.054 | 0.103 | 0.155 | 0.295 | 0.144 | 0.115 | 154 |

### pericope
| system | recall@1 | recall@5 | recall@10 | recall@50 | mrr@10 | ndcg@10 | queries |
|---|---|---|---|---|---|---|---|
| fused | 0.046 | 0.105 | 0.171 | 0.318 | 0.128 | 0.114 | 348 |
| tfidf | 0.051 | 0.112 | 0.146 | 0.293 | 0.134 | 0.112 | 348 |
| berel_sup_csls_bma | 0.043 | 0.100 | 0.139 | 0.300 | 0.116 | 0.098 | 348 |
| berel_sup_csls_mean | 0.040 | 0.104 | 0.140 | 0.280 | 0.105 | 0.093 | 348 |
| berel_sup_mean | 0.042 | 0.094 | 0.134 | 0.305 | 0.103 | 0.091 | 348 |
| berel_sup_bma | 0.030 | 0.086 | 0.116 | 0.273 | 0.103 | 0.083 | 348 |
| bge_m3_csls_bma | 0.036 | 0.074 | 0.113 | 0.218 | 0.091 | 0.078 | 348 |
| bge_m3_csls_mean | 0.036 | 0.071 | 0.100 | 0.237 | 0.092 | 0.073 | 348 |
| berel_mean_mean | 0.028 | 0.061 | 0.102 | 0.246 | 0.080 | 0.068 | 348 |
| berel_mean_bma | 0.027 | 0.056 | 0.081 | 0.206 | 0.069 | 0.057 | 348 |


### Unit aggregation: BMA vs mean (dev)

**chapter**
| system | ndcg@10 bma | ndcg@10 mean | recall@10 bma | recall@10 mean | recall@50 bma | recall@50 mean |
|---|---|---|---|---|---|---|
| berel_mean | 0.115 | 0.115 | 0.159 | 0.155 | 0.305 | 0.295 |
| berel_sup | 0.141 | 0.135 | 0.188 | 0.181 | 0.370 | 0.316 |
| berel_sup_csls | 0.156 | 0.147 | 0.202 | 0.187 | 0.373 | 0.350 |
| bge_m3_csls | 0.148 | 0.120 | 0.195 | 0.151 | 0.355 | 0.307 |

**pericope**
| system | ndcg@10 bma | ndcg@10 mean | recall@10 bma | recall@10 mean | recall@50 bma | recall@50 mean |
|---|---|---|---|---|---|---|
| berel_mean | 0.057 | 0.068 | 0.081 | 0.102 | 0.206 | 0.246 |
| berel_sup | 0.083 | 0.091 | 0.116 | 0.134 | 0.273 | 0.305 |
| berel_sup_csls | 0.098 | 0.093 | 0.139 | 0.140 | 0.300 | 0.280 |
| bge_m3_csls | 0.078 | 0.073 | 0.113 | 0.100 | 0.218 | 0.237 |

With CSLS, best-match average beats mean pooling at both levels → `unit_aggregation: bma`.

### Fusion weight (dev nDCG@10, `w_sem = 1`)

| unit type | lexical | semantic | w_lex 0.25 | 0.5 | 0.75 | **1.0** | 1.5 | 2.0 |
|---|---|---|---|---|---|---|---|---|
| verse | 0.176 | 0.150 | 0.178 | 0.184 | 0.184 | **0.189** | 0.185 | 0.188 |
| chapter | 0.192 | 0.156 | 0.161 | 0.165 | 0.166 | 0.168 | 0.168 | 0.171 |
| pericope | 0.112 | 0.098 | 0.114 | 0.116 | 0.112 | 0.114 | 0.110 | 0.112 |

One weight for all unit types, chosen on verse dev. At chapter level fusion does not beat TF-IDF on dev (it does on test).

## Training (dev, verse level)

| run | recall@10 | nDCG@10 |
|---|---|---|
| raw BEREL, mean pooling (`berel_mean`) | 0.161 | 0.113 |
| SimCSE epoch 1 / **2** / 3 | 0.176 / **0.181** / 0.179 | — / 0.123 / — |
| supervised, SimCSE init + hard negatives | 0.208 | 0.141 |
| supervised, SimCSE init, no hard negatives | 0.205 | 0.140 |
| **supervised, raw BEREL init + hard negatives** (`berel_sup`) | **0.210** | **0.144** |
| `berel_sup` + CSLS (`berel_sup_csls`) | 0.226 | 0.150 |

CSLS helps every encoder (nDCG@10: `berel_mean` 0.113 → 0.124, `bge_m3` 0.123 → 0.135, `berel_simcse` 0.123 → 0.132, `berel_sup` 0.144 → 0.150). No dense system alone beats `bm25_lemma` (0.176) on dev; fusion does (0.189). Supervised training peaks at 3.8 GB VRAM on the GTX 1080 Ti (fp32).

## Serving

| item | value |
|---|---|
| `results.sqlite` | 241 MB, 4,144,976 matches (3 modes × 4 unit types × top-50), built in ~40–50 s |
| `/similar` (SQLite, k = 50, neighbours excluded) | median 0.53 ms, max 2.3 ms |
| `/search` on CPU, median (max) of 20 queries | lexical 7.7 (14.8) ms, semantic 57 (87) ms, fused 72 (82) ms |
| `/lemmas` (jump box) | ~1 ms; the first call reads the 9,204-lemma list (~0.12 s) |
| `bsim serve` startup | serving after ~12–14 s, query encoder ready after ~32 s |
| spot checks | Ps 14:1 → Ps 53:2 and Ex 20:2 → Deut 5:6 at rank 1 in every mode; II Sam 22 ↔ Ps 18 compare pairs all 51 verses (BMA 0.90) |

## Reproduction

`git clone` → `uv sync` → `uv run bsim all` in an empty clone (2026-10-04, GTX 1080 Ti, Windows 11; BEREL 3.0 and BGE-M3 already in the Hugging Face cache): **38 min 28 s**, exit 0.

| stage | time | stage | time |
|---|---|---|---|
| download | 1:47 | embed | 2:32 |
| build-corpus | 1:34 | topk | 0:15 |
| build-links | 0:25 | units | 0:16 |
| lexical | 0:14 | fuse | 0:31 |
| lexical-topk | 0:14 | evaluate | 0:26 |
| train-simcse | 10:08 | build-db | 0:40 |
| train-sup | 19:28 | | |

Incremental runs (§16.35, 2026-10-10): with download … evaluate adopted, the 26 analysis stages and build-db ran in 17 min (a first run stopped in `senses` on a console encoding error; the rerun skipped the ten stages already done and went on from there); a second `bsim all` with nothing changed took 2.3 s; `--rerun mirrors` ran mirrors (27 s) and build-db (3:09; `mirrors.meta.json` carries a build time, so build-db follows) and skipped the other 38 stages: 3 min 42 s, against 38 min for the whole pipeline.

Every dev and test metric above (all systems, all unit types) came out identical to three decimals, and `results.sqlite` again held 4,144,976 matches (`/similar` median 0.58 ms). `data/` + `models/` + `artifacts/` take 2.8 GB. `bsim serve` on the clone (after `npm ci && npm run build` in `web/`) served the viewer and answered Ps 14:1 → Ps 53:2 at rank 1 in all three modes and the search "בראשית ברא אלהים" → Genesis 1:1 first in every mode.

## Later experiments (dev only)

The test split was run once, at M9; these systems are compared on dev only.

| system | R@1 | R@5 | R@10 | R@50 | MRR@10 | nDCG@10 |
|---|---|---|---|---|---|---|
| fused (final) | 0.098 | 0.213 | 0.274 | 0.400 | 0.184 | 0.189 |
| fused_rerank (cross-encoder, w_ce 0.25) | 0.103 | 0.217 | 0.274 | 0.400 | 0.188 | 0.194 |
| cross-encoder alone (epoch 1) | 0.076 | 0.142 | 0.195 | 0.400 | 0.134 | 0.135 |
| bm25_morph (structural mode) | 0.044 | 0.074 | 0.092 | 0.132 | 0.069 | 0.068 |
| 3-way RRF lex + sem + morph (w_morph 0.1) | | | | | | 0.192 |
| bm25_domain (SDBH semantic domains) | | | | | | 0.075 |
| bm25_lemma_domain (lemmas + domains, β 0.75) | | | | | | 0.180 |
| RRF bm25_lemma_domain + semantic | | | | | | 0.190 |
| bm25_syntax (BHSA clause shapes) | | | | | | 0.027 |
| bm25_morph_syntax (word shapes + clause shapes) | | | | | | 0.072 |

Paired bootstrap (884 dev queries) of fused_rerank − fused nDCG@10: +0.0042, 95 % CI [−0.0007, +0.0092]; the blend weight was chosen on the same queries. Not adopted (DESIGN §16.3, D31). The structural mode is shown in the viewer as its own mode, not fused (§16.5, D32). Semantic domains (§16.22, D56): `bm25_lemma_domain` beats `bm25_lemma` (+0.0045, CI [+0.0003, +0.0087]), but in place of the lexical list in the fusion the cross-fitted gain is −0.0021, CI [−0.0075, +0.0030]: not adopted.

Syntax (§16.26, D60): `bm25_syntax` as a third list in the fusion +0.0005, CI [−0.0031, +0.0044]; `bm25_morph_syntax` against `bm25_morph` +0.0039, CI [−0.0007, +0.0086] (Sefaria), +0.0036, CI [+0.0015, +0.0058] (OpenBible): not adopted; clause-shape neighbours are shown as "built the same way" instead.

Direction of borrowing (§16.27, D61), 35 parallels of accepted direction: language 30 / 35, spelling 29 / 31, smoothing 15 / 28, expansion 15 / 33; language + spelling chosen without each book pair, scored on it: 30 / 32 right, 3 undecided.

Speaker voices (§16.28, D63): 23 speakers, 18 distinct at q ≤ 0.05 against a within-book label shuffle (calibration shuffle: 0 / 23; explicit-only ρ 0.88). Author over character: David (Samuel / Chronicles) cross 0.153, p 0.001; God (Kings / Chronicles) 0.046, p 0.045; Solomon (Kings / Chronicles) no difference, p 0.92. Elihu second of five Job speakers (expected first).

Where the text divides (§16.29, D65), 23,167 verse boundaries scored by lemma and embedding cohesion (window 4, chosen on dev), mean within-book percentile against random boundaries (p 0.001 each): MAM open paragraphs 0.650, closed 0.554 (open − closed +0.095, p 0.001); breaks in both MAM and Leningrad 0.604 vs one only 0.550 (p 0.001); chapter starts with a paragraph break 0.728, without 0.616 (p 0.002); parashot 0.771; style seams 0.611 and 68 % within 2 verses of a division (random 55 %); calibration shuffle 0.507 (p 0.065). As segmentations: MAM paragraphs Pk 0.399 vs 0.463 random (better in 18 / 38 books), chapters 0.438 vs 0.487 (10 / 38). Lists: 250 unmarked turns, 20 chapters in running text (Gen 47:1, Isa 64:1, Hag 2:1, Hos 6:1, Song 7:1, …), 114 quiet breaks.

Written and read (§16.30, D66), 1,260 ketiv / qere of the OSHB: 583 vowel letter, 457 one letter, 56 vowel letter moved, 25 word division, 112 other. Look-alike letters 71 % of one-letter swaps vs 3.9 % by letter frequency (without ו / י 12 % vs 1.3 %, p 1e-12). Written form fuller in 82 % of vowel-letter pairs in the late books vs 40 % elsewhere (books permuted, p 0.006). Aligned parallels write the qere 57 times, the ketiv 11 (p 1e-8). 82 of 142 singular → plural readings are a written ־ו read ־יו. 14 euphemisms. `results.sqlite` 655 MB.

Explicit citations (§16.31, D67): 116 verses with a formula of reference, 41 resolved (BM25 and cosine agree on the source). Against random verses under the same rules: as commanded 55 % vs 32 % (p 0.0008), the word fulfilled 32 % vs 27 % (p 0.32), as it is written 11 % vs 8 % (p 0.36). Gold (20 named sources): 15 at rank 1, 17 in the top 5, resolved 10 / 10 right.

Rare words over a few verses (§16.32, D68): 176 three-verse window pairs sharing ≥ 3 rare lemmas, 171 known parallels; 3 at q ≤ 0.05 (within-chapter verse shuffle), all known; the 5 new pairs (Exod 28 / Deut 33, Deut 29 / Jer 9, Gen 18 / 1 Sam 28, Lev 13 / 14, Ps 103 / Neh 9) at q ≥ 0.82: leads, not findings.

Chiasm at the small scale (§16.33, D69): repeated words mirror their order in 2,099 verses and repeat it in 2,790 (p 5e-23; 43 % of pairs mirrored, 42–44 %; poetry 39 %). Clause pairs reverse their constituents in 23.5 % of poetry vs 16.7 % of prose (genre permuted over chapters, p 0.0003; object-verb 29 % vs 19 %). 94 full mirrors, none beyond chance after BH.

Graded numerical sayings and lists (§16.45, D81): 6,307 number words, 3,240 not part of a compound number; 105 graded pairs in 91 verses (1 / 2 57, 3 / 4 14). The sayings named in advance: 18 of 19 (Deut 32:30 missed). Graded pairs against the books' number values permuted: 105 against 96.2, p 0.196, not borne out (without 1 / 2, described after the first run: 48 against 37.0, p 0.037). Sayings in parallel lines: 12.1 % of 91 against 5.1 % of 511 other number-pair verses, p 0.026. Lists: 69 runs of verses shaped alike over 863 verses against 0.7 with shuffled verse orders; 8 of the 10 named in advance (Num 7 and Neh 3 missed). 6 s.

Who speaks to whom (§16.44, D80): an addressee for 2,901 of 5,489 quotations (explicit 1,264, vocative 494, pronoun 622, turn 521; hand check 42 / 50, explicit 21 / 21, vocative 11 / 11, turn 6 / 9, pronoun 4 / 9). On explicit and vocative addressees: "your servant" 13.1 per 1,000 words in speech to God or a king against 1.5 (p 0.001; without Solomon's temple prayer 11.7); נא after 14 % of the commands to them against 4 % (p 0.003); in 170 exchanges between unequal parties the higher one has the last word 96 times against 89.4 expected (p 0.17), not borne out (first run, before the exchange definition was tightened: 142 / 250 against 130.5, p 0.075). Every addressee: deference p 0.001, נא p 0.001. 4 s.

The Pentateuch's sources (§16.43, D79): Genesis–Numbers split in two by 18 synonym choices and 60 function words, without the reference and without the divine names; against Noth's P (2,787 verses, entered by hand): agreement 78 %, kappa 0.559 against 0.161 for the split shifted within books (p 0.001); within Genesis kappa 0.301 against 0.002 (p 0.004); before Exodus 6 the P-like side has יהוה in 37 % of its divine names against 43 % (p 0.28; the reference itself 1 % against 49 %): not borne out. Leviticus, all P, only 69 % P-like. Kappa 0.37–0.70 over chunk size × smoothing. 6 s.

Psalm genres (§16.42, D78): persons, imperatives, questions and words of distress and praise per word, without superscriptions, in 7 Ward clusters against Gunkel's genres for 119 psalms: NMI 0.262 against 0.082 shuffled (p 0.001); the form alone 0.294, the domains alone 0.142. Six genre profiles named in advance: 6 / 6 (individual laments "I" 24.1 per 100 words against 7.5, communal laments "we" 11.6 against 1.5, hymns plural imperatives 5.4 against 0.7). The turn (where praise − distress per word rises most): 7 of 12 named turns within a verse against 3.4 by chance (p 0.016; within 2 verses p 0.24); individual laments turning above chance 7 / 37 against hymns 2 / 30 (p 0.13, not borne out). 9 s.

More supervision (§16.41, D77): the encoder retrained with OpenBible's and ETCBC's pairs between train books (+29,560 rows to Sefaria's 9,026), chosen by a rule fixed before training among three variants and a reseeded control, and adopted. Dev nDCG@10, fused: Sefaria 0.1895 → 0.1946 (+0.0051, CI [−0.0018, +0.0122]), OpenBible 0.1460 → 0.1516 (+0.0056, CI [+0.0017, +0.0096]), ETCBC 0.8319 → 0.8325; semantic `berel_sup_csls` 0.150 → 0.156; chapter fused 0.168 → 0.171, pericope 0.114 → 0.118. OpenBible alone gains most on Sefaria and OpenBible but loses 0.030 on ETCBC; ETCBC alone the reverse. The tables above and the test split are the Sefaria-only model's (M9); the test split is not rerun. All 18 findings keep their verdict.

Refrains (§16.40, D76): three or more lemmas coming back in three or more verses of a book within 20 verses, scored by burst against the book rate: 925 refrains against 46 runs as strong in books with shuffled verse order (551 distinct; most are lists — census, offerings, genealogies). Named in advance: 8 of 9 found (the Song of Songs' adjuration, too far apart, missed). Even spacing: 27 of 179 testable (15 % vs 5 %, p 3 × 10⁻⁷), almost all lists and Genesis 1. Turns: a refrain verse's sharper neighbouring gap 0.679 against 0.650 (p 0.001). Three choices changed after the first run (the known match, names, untestable spacing), all reported; robust over seed length, gap and names. 6 s.

Root families (§16.38, D74): Strong's derivations at most two links up, kept where the word is the root's strong radicals in a Hebrew shape: 1,225 families over 4,442 of 6,123 content lemmas. A verb with a noun of its own root within three words: 1,677 against 406 with content words permuted within chapters (4.1×, p 0.005 over 200 shuffles); other same-root pairs 514 against 241; 473 infinitive absolutes (Chronicles 0.15 per 1,000 words, Kings 0.9–1.2). Eight named Leitworte: 6 in their chapter's top 12 by root, 6 by lemma (3 rank higher by root, 3 lower): not borne out. 896 hidden key roots (leads). 35 s.

Stresses per line (§16.37, D73), 54,594 accent lines (52,007 split into two stressed members), net fall = falling − rising share of lines of 4–7 stresses: Lamentations 1–4 0.39 (Lam 1 0.19, 2 0.44, 3 0.61, 4 0.32) against 0.17 for 174 prose-accented poetry chapters (p 0.008) and 0.14 for Psalms, Proverbs and Job (p 0.001); line lengths 3–8, 4–6, 5–7, 4–8: p 0.004–0.011 (pool), 0.0004–0.004 (poetic books). 3:2 is Lamentations' commonest line (82 of 237). Lam 5 (control) at the 74th percentile of the pool. The 12 chapters naming קינה: 0.20 against 0.17, p 0.26 (Ezek 19 96th, Ezek 27 93rd percentile). Line lengths and statistic chosen in view of Lamentations; the קינה check fixed before. 5 s.

Who echoes whom (§16.36, D72): 459 of 2,422 cross-book chapter pairs directed (14 cited, 82 borrowed, 363 by the late-language profile at a gap ≥ 0.3). The language direction agrees with the spelling sign of the parallels in 23 of 23 (p 2e-7), with the citations 2 of 2 (too few) and with the borrowing estimates 58 of 59 (same features). 50 language directions run against the canon: 23 among the late Writings, 12 from 1 Kgs 20 alone, Ezek 44 → Lev 21, Judg 5 → Num 24 / Deut 33. Two book contradictions, both known misses of §16.27 (2 Kings ↔ Jeremiah, Psalms ↔ 1 Chronicles). 5 s; DB 655 MB.

ETCBC parallel passages (§16.34, D70), a string-similarity gold: 1,973 parallels (13,645 formula and list pairs set apart). Dev nDCG@10: lexical 0.853, fused 0.832, semantic 0.749; fused recall@10 0.90 / 0.96 / 1.00 by similarity band. All parallels: 94 % in the fused top 10, 80 % share a phrase, 38 % in a strong sequence; 56 % of strong-sequence pairs are ETCBC parallels; 11 % are Sefaria links, 20 % OpenBible.

Unit dossier (D64): `/dossier/{unit}` computed in ~12 ms in-process on the real DB (40 cold chapters, 0.48 s), then cached; `results.sqlite` 652 MB with the voices tables and the new indexes.
