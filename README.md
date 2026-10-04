# bible-similarity

Find, for every **verse, chapter, parasha and Masoretic pericope** of the Hebrew Bible, the top-k most similar units. Three similarity modes are available:

- **lexical**: shared wording (BM25 / TF-IDF over OSHB lemmas, with repeated formulas down-weighted)
- **semantic**: shared meaning (BEREL 3.0 fine-tuned with SimCSE and Sefaria cross-links)
- **fused**: both combined (weighted reciprocal rank fusion)

The results are precomputed into SQLite and browsed in a local FastAPI + React viewer. The viewer supports shared-word highlighting, side-by-side unit comparison and free-text Hebrew search.

> Status: planning. See the docs below; implementation follows [docs/TASKS.md](docs/TASKS.md).

## Docs
- [Architecture](docs/ARCHITECTURE.md): system overview, pipeline stages, repo layout, stack
- [Design](docs/DESIGN.md): data sources, text processing, models, evaluation, DB/API/UI design, decision log
- [Tasks](docs/TASKS.md): milestones with acceptance criteria

## Quickstart (once implemented)
```bash
uv sync                      # installs PyTorch cu126 (needed for Pascal GPUs such as the GTX 1080 Ti)
uv run bsim all              # download → corpus → links → lexical → train → embed → top-k → eval → DB
uv run bsim serve            # http://localhost:8000
```

## Data & licenses
- Hebrew text and morphology: [OSHB morphhb](https://github.com/openscriptures/morphhb) (WLC: public domain; morphology: CC BY 4.0)
- Display text: Sefaria, *Miqra according to the Masorah* (CC-BY-SA)
- Parasha boundaries and cross-links: [Sefaria-Export](https://github.com/Sefaria/Sefaria-Export)
- Models: [BEREL 3.0](https://huggingface.co/dicta-il/BEREL_3.0) (Apache-2.0), [BGE-M3](https://huggingface.co/BAAI/bge-m3) (MIT)

The data is downloaded by `bsim download` and is not stored in this repository. For personal and research use.
