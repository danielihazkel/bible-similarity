# CLAUDE.md

Hebrew Bible similarity project. Read these before working:
- `docs/ARCHITECTURE.md`: pipeline stages, artifact contract, repo layout
- `docs/DESIGN.md`: the authoritative technical decisions (§15 decision log). §16, the pattern analyses, is in `docs/design/ANALYSES.md` under the same numbers: read only the sections you need.
- `docs/TASKS.md`: open milestones and the current series; tick boxes as tasks are completed. Finished milestones are in `docs/TASKS_DONE.md` (no need to read it).

## Conventions
- Python 3.11, managed with `uv` (`uv run ...`). Package code lives in `src/bsim/`, and the CLI is `bsim` (Typer).
- GPU is a GTX 1080 Ti (Pascal sm_61): fp32 only, never enable fp16/bf16. Keep PyTorch on the **cu126** index.
- Hebrew versification and Jewish canon order everywhere. `verse_id` = canon ordinal = embedding row index.
- Hebrew only: no translations of scripture in the pipeline or the UI. The interface itself is English or Hebrew (D54): every UI string goes in the catalogs (`web/src/i18n/en.ts` / `he.ts`, page groups in `i18n/pages/`), never inline. Hebrew strings use the terms and conventions of `docs/HEBREW_UI.md`.
- Every tunable value goes in `configs/default.yaml`, not in code.
- `data/`, `models/` and `artifacts/` are gitignored. Never commit downloaded texts or results.
- Choose models and tune weights on the **dev** split. The test split is run once, at M9.
- Use `AutoTokenizer` for BEREL, never `BertTokenizer`.
- Run `uv run ruff check . && uv run pytest` before considering a task done.
