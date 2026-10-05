# bible-similarity

Find, for every **verse, chapter, parasha and Masoretic pericope** of the Hebrew Bible, the top-k most similar units. Four similarity modes are available:

- **lexical**: shared wording (BM25 / TF-IDF over OSHB lemmas, with repeated formulas down-weighted)
- **semantic**: shared meaning (BEREL 3.0 fine-tuned with SimCSE and Sefaria cross-links)
- **fused**: both combined (weighted reciprocal rank fusion)
- **structural**: shared grammatical shape (morphology n-grams; shown, not fused)

On top of retrieval, the pipeline looks for patterns in the text: shared phrases, passages that run parallel verse by verse (in the same, mirrored or another order) and how they differ word by word and which changes are systematic, inclusio / chiasm / Leitworte, alphabetic acrostics, parallel verse halves and finer clauses from the te'amim, fixed word pairs of parallel lines, recurring action sequences, wordplay, alliteration and rhyme, people and places, a corpus map, a network of echoes between passages, stylometry and style seams.

Everything is precomputed into SQLite and browsed in a local FastAPI + React viewer: shared-word highlighting, side-by-side comparison with word-level changes, free-text Hebrew search, a concordance, list pages for every analysis and an evaluation page.

Status: milestones M0–M28 and hardening rounds H1–H3 are done (see [docs/TASKS.md](docs/TASKS.md)). On the held-out test books, fused retrieval reaches nDCG@10 **0.136** at verse level (lexical 0.118, semantic 0.118), 0.157 for chapters and 0.068 for pericopes; see [docs/RESULTS.md](docs/RESULTS.md).

## Docs
- [Architecture](docs/ARCHITECTURE.md): system overview, pipeline stages, repo layout, stack
- [Design](docs/DESIGN.md): data sources, text processing, models, evaluation, DB/API/UI design, decision log
- [Tasks](docs/TASKS.md): milestones with acceptance criteria
- [Results](docs/RESULTS.md): evaluation metrics (dev, the single test run, ablations)

## Quickstart
Requirements: [uv](https://docs.astral.sh/uv/), an NVIDIA GPU with a driver for CUDA 12.6 (developed on a GTX 1080 Ti; training on CPU is impractically slow), Node 20+ for the viewer, internet access for the first run, and about 11 GB (Python environment 4.5 GB, Hugging Face models ~3 GB, `data/` + `models/` + `artifacts/` 2.8 GB) of free disk.

```bash
uv sync                      # installs PyTorch cu126 (needed for Pascal GPUs such as the GTX 1080 Ti)
uv run bsim all              # download → corpus → links → lexical → train → embed → top-k → eval → DB
(cd web && npm ci && npm run build)   # viewer → web/dist
uv run bsim serve            # API + viewer on http://localhost:8000
```

`bsim all` took 38 minutes on the GTX 1080 Ti from an empty clone, with BEREL 3.0 and BGE-M3 already in the Hugging Face cache (they are fetched on first use, about 3 GB). It runs these stages, each also available as its own command (`uv run bsim --help`):

`download` → `build-corpus` → `build-links` → `lexical` → `lexical-topk` → `train-simcse` → `train-sup` → `embed` → `topk` → `units` → `fuse` → `evaluate` → `eval-openbible` → `phrases` → `sequences` → `diffs` → `typescenes` → `parallelism` → `acrostics` → `wordplay` → `sound` → `entities` → `seams` → `structure` → `map` → `network` → `stylometry` → `build-db`

Re-run part of it with `--from`, `--to` and `--skip`, e.g. `uv run bsim all --from embed` after retraining, or `--skip download`. The test split is evaluated only on the first run; later runs refresh dev metrics and keep the recorded test numbers (`bsim evaluate --split test --force` replaces them).

Viewer development: run `uv run bsim serve` and, in `web/`, `npm run dev` (http://localhost:5173, proxies `/api`). `npm run lint` and `npm test` check the frontend; `npm run e2e` runs the Playwright smoke and accessibility tests against a running `bsim serve`.

## Data & licenses
- Hebrew text and morphology: [OSHB morphhb](https://github.com/openscriptures/morphhb) (WLC: public domain; morphology: CC BY 4.0)
- Display text: Sefaria, *Miqra according to the Masorah* (CC-BY-SA)
- Parasha boundaries and cross-links: [Sefaria-Export](https://github.com/Sefaria/Sefaria-Export)
- Models: [BEREL 3.0](https://huggingface.co/dicta-il/BEREL_3.0) (Apache-2.0), [BGE-M3](https://huggingface.co/BAAI/bge-m3) (MIT)

The data is downloaded by `bsim download` and is not stored in this repository. For personal and research use.
