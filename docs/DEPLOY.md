# Deploying a public read-only copy

How to serve the viewer to other people: what gets copied, what is left out, the terms of each
source, and the decisions that are yours to make before anything is published. Nothing here
publishes anything. Every step below runs on your machine until you choose a host. The design is
DESIGN.md §10.3 (D137).

## What a public server is

`configs/public.yaml` is `configs/default.yaml` with a few switches turned off:

| Switch | Public | Effect |
|---|---|---|
| `serve.personal` | `false` | Your labels, notebook and label queue: their routes answer 404 (`personal_off`). The viewer leaves them out of the nav, the jump box, the unit page, the workbench, and says so on `/labels` and `/notebook`. |
| `serve.encoder` | `false` | No query encoder. Semantic and fused **search** answer 503, and the search page offers lexical search only. Compare's "links of meaning" (`/align`) is hidden. The precomputed similar-verse lists (lexical, semantic, fused, structural, …) are all still there: they are in the DB. |
| `serve.embeddings` | `true` | The verse vectors (70 MB), for `/compare`, the semantic structure basis and the cosines on a sequence's ladder. `false` (with `deploy-bundle --no-embeddings`) drops them: `/compare` answers 503 and the structure panel shows the lexical basis only. |
| `serve.labels_writable` | `false` | Belt and braces: no writes even if `personal` were on. |
| `serve.cors_origins` | `[]` | The viewer is served from the same origin, so no other site may call the API. |

With the encoder off, the server never imports torch, transformers or sentence-transformers
(`tests/test_deploy.py` checks that it doesn't). The image therefore installs without pyproject's
`ml` dependency group: about 350 MB of Python packages instead of several GB.

## 1. Make the bundle

```
uv run bsim deploy-bundle            # everything that may be served
uv run bsim deploy-bundle --no-nc    # without the CC BY-NC data (below)
```

It writes `bundle/` (gitignored; `deploy.out`), about 860 MB:

- `artifacts/results.sqlite`: the results DB, copied with SQLite's backup API, which is safe while `bsim serve` runs.
- `artifacts/embeddings/<system>.npy`: the verse vectors, unless you pass `--no-embeddings`.
- `artifacts/eval/*.json`: the files the Evaluation page reads (`deploy.eval_files`).
- `bundle.json`: what was copied, emptied and left out.

Never copied: your labels and notebook (`data/labels.sqlite`), Claude's suggestions
(`artifacts/llm/`), models, raw downloads.

`--no-nc` handles the non-commercial data in three ways:
- It empties every table that carries CC BY-NC data (`deploy.noncommercial`).
- It takes those stages off the build's `stages_run`.
- It leaves out `etcbc.json`.

Their pages then say "not computed in this build", the same way they would if the stage had
never run. Findings, the dossier and the unit page skip them.

## 2. Try it locally

```
uv run bsim serve --config configs/public.yaml --port 8001
```

To check the image's premise without Docker, install a virtualenv without the ML group:

```
UV_PROJECT_ENVIRONMENT=.venv-public uv sync --frozen --no-default-groups
.venv-public/Scripts/bsim serve --config configs/public.yaml --port 8001
```

## 3. Build and run the image

```
docker build -t bsim-public .
docker run --rm -p 8000:8000 -v "$PWD/bundle:/app/bundle:ro" bsim-public
```

The image builds the viewer (`npm ci && npm run build`) and installs the server with
`uv sync --frozen --no-default-groups`. It runs as an unprivileged user. It serves
`configs/docker.yaml`, which is the public profile with the surface-index cache inside the image,
so the bundle can be mounted read-only. A health check calls `/api/books`.

The offline app (M146) works on a public server too: visitors can install it, and the pages they
open stay available offline.

## 4. Before publishing: the sources and their terms

| Source | In the bundle as | Terms | What they ask of a public copy |
|---|---|---|---|
| Westminster Leningrad Codex (OSHB) | consonantal text, lemmas, morphology | WLC public domain; OSHB morphology **CC BY 4.0** | attribution (the footer gives it) |
| Sefaria, *Miqra according to the Masorah* | the displayed text with vowels and te'amim | **CC BY-SA** | attribution, and **share-alike**: the text, and anything adapted from it, under CC BY-SA |
| Sefaria schemas | parasha boundaries | Sefaria's terms | attribution |
| Sefaria links | the cross-reference gold set, links on hits, the rabbinic citation counts | **CC BY 4.0** | attribution |
| UBS SDBH | word senses, semantic domains | **CC BY-SA 4.0** | attribution, share-alike |
| OpenScriptures HebrewLexicon | name types | **CC BY 4.0** | attribution |
| OpenBible.info cross-references | a second gold set (Evaluation page) | **CC BY** | attribution |
| OpenBible.info Geocoding | places and coordinates | **CC BY 4.0** | attribution |
| STEPBible TIPNR | which person or place each name is | **CC BY 4.0** | attribution; asks that *the file* not be redistributed, and the bundle holds only identifications derived from it, not the file |
| Natural Earth | the base map | public domain | none |
| Hebcal leyning | haftarot | **BSD 2-Clause** | the copyright notice |
| Ginsburg's Masorah figures (1897) | the Masorah page's reference numbers | public domain | none |
| **ETCBC BHSA** | clauses, phrases, speech, and the analyses built on them | **CC BY-NC 4.0** | attribution, **non-commercial use only** |
| **ETCBC parallels** | a gold set (Evaluation page); **extra training pairs of the encoder in use** | **CC BY-NC 4.0** | as above |
| **Samaritan Pentateuch** (DT-UCPH) | the Witnesses page | **CC BY-NC 4.0** | as above |
| **Dead Sea Scrolls** (ETCBC `dss`) | the Witnesses page | **CC BY-NC 4.0** | as above |
| BEREL 3.0 (base model) | not shipped; the verse vectors come from a model fine-tuned from it | Apache-2.0 | none for the vectors |
| Noto Serif Hebrew, React and the viewer's libraries | in the viewer build | SIL OFL, MIT | notices in the build |

What `--no-nc` removes, from `deploy.noncommercial` in `configs/default.yaml`:

| Source | Stages | Tables (emptied) | Eval files |
|---|---|---|---|
| BHSA | syntax, voices, dialogue, retold, mirrors | clauses, syntax_phrases, syntax_neighbors (the "Clauses" similarity list), speech_chapters, speech_books, voice_\*, dialogue_\*, retold_\*, mirror_\* | none |
| ETCBC parallels | none | none | etcbc.json |
| Samaritan Pentateuch, Dead Sea Scrolls | witnesses | witnesses_\* | none |

### Decisions for you

1. **Non-commercial or not.** A personal, ad-free research site is non-commercial use, and the
   full bundle fits it. Use `--no-nc` if the site could ever be commercial, for example with ads,
   paid access, or hosting by a company for its products.
2. **The encoder in use was trained with the ETCBC parallels (CC BY-NC) as extra positive pairs**
   (`train.supervised.extra_pairs: [openbible, etcbc]`). Its verse vectors, and the semantic and
   fused lists built from them, are therefore in part derived from NC data. Whether a model
   trained on licensed data is an adaptation of it is an unsettled question. `--no-nc` does
   **not** remove the semantic lists. A strictly NC-free copy would need:
   - the encoder retrained without the ETCBC pairs, as the existing variant `openbible`
     (`bsim supervision-exp --only openbible`, about 2.5 h on the GPU);
   - `embed`, `topk`, `fuse` and every downstream stage rerun;
   - a new `build-db`.

   That is a decision about your model and your time, not something to settle in code.
3. **Share-alike.** The displayed text (MAM) and SDBH are CC BY-SA. Publishing the bundle as a
   download would need CC BY-SA terms for those parts. Serving it as a site needs the
   attribution the footer already gives.
4. **The footer.** It credits ETCBC BHSA even after `--no-nc`, which is harmless. It also says
   "For personal and research use", which fits a non-commercial site.
5. **Where.** Any host that runs a container with a 1 GB volume works, for example a small VPS,
   Fly.io or Render. A static host can't serve it, because every page queries the API. Put TLS
   and a rate limit in front of it, through the host or a reverse proxy such as Caddy or nginx.
   Several routes compute on demand, and a public site should cap them per client: `/patterns`,
   `/workbench`, `/source-find`, `/compare`, `/search`.

Nothing is published until you pick a host and push the image or bundle there yourself.
