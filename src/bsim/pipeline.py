"""`bsim all`: the offline pipeline end to end (ARCHITECTURE.md §4, stages 1–12 + analyses).

Stages run in a fixed dependency order and call the same runners as the single-stage
commands; the system lists come from `pipeline` in the config. The test split is evaluated
only when `metrics.json` has no test entry yet (it is run once, never replaced here).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from typing import Any

from bsim.config import resolve_path

Log = Callable[[str], None]


def stage_download(cfg: dict[str, Any], log: Log) -> None:
    from bsim.data.download import GROUPS, run_download

    run_download(cfg, groups=GROUPS, workers=cfg["pipeline"]["download_workers"], log=log)


def stage_build_corpus(cfg: dict[str, Any], log: Log) -> None:
    from bsim.data.corpus import run_build_corpus

    run_build_corpus(cfg, log=log)


def stage_build_links(cfg: dict[str, Any], log: Log) -> None:
    from bsim.data.links import run_build_links

    run_build_links(cfg, log=log)


def stage_lexicon(cfg: dict[str, Any], log: Log) -> None:
    from bsim.data.lexicon import run_lexicon

    run_lexicon(cfg, log=log)


def stage_syntax(cfg: dict[str, Any], log: Log) -> None:
    from bsim.data.bhsa import run_syntax

    run_syntax(cfg, log=log)


def stage_lexical(cfg: dict[str, Any], log: Log) -> None:
    from bsim.lexical.build import run_lexical

    run_lexical(cfg, log=log)


def stage_lexical_topk(cfg: dict[str, Any], log: Log) -> None:
    """Lexical verse top-k; `train-sup` mines its hard negatives from `bm25_lemma`."""
    from bsim.retrieve.topk import run_topk

    for name in cfg["pipeline"]["lexical_systems"]:
        run_topk(cfg, name, log=log)


def stage_train_simcse(cfg: dict[str, Any], log: Log) -> None:
    from bsim.train.simcse import run_train_simcse

    run_train_simcse(cfg, log=log)


def stage_train_sup(cfg: dict[str, Any], log: Log) -> None:
    from bsim.train.supervised import run_train_sup

    run_train_sup(cfg, log=log)


def stage_embed(cfg: dict[str, Any], log: Log) -> None:
    from bsim.embed.encoders import run_embed

    for name in cfg["encoders"]["systems"]:
        run_embed(cfg, name, log=log)


def dense_systems(cfg: dict[str, Any]) -> list[str]:
    """Every encoder system, followed by its `_csls` variant when `pipeline.csls`."""
    from bsim.retrieve.topk import CSLS_SUFFIX

    csls = cfg["pipeline"]["csls"]
    return [
        s
        for name in cfg["encoders"]["systems"]
        for s in ([name, name + CSLS_SUFFIX] if csls else [name])
    ]


def stage_topk(cfg: dict[str, Any], log: Log) -> None:
    from bsim.retrieve.topk import run_topk

    for name in dense_systems(cfg):
        run_topk(cfg, name, log=log)


def stage_units(cfg: dict[str, Any], log: Log) -> None:
    from bsim.retrieve.units import run_units

    for name in cfg["pipeline"]["unit_systems"]:
        run_units(cfg, name, log=log)


def stage_fuse(cfg: dict[str, Any], log: Log) -> None:
    """Record the dev `w_lex` grid, then write the fused lists with the configured weights."""
    from bsim.retrieve.fusion import run_fuse, run_fuse_tune

    run_fuse_tune(cfg, log=log)
    run_fuse(cfg, log=log)


def stage_evaluate(cfg: dict[str, Any], log: Log) -> None:
    from bsim.eval.report import load_metrics, run_evaluate

    run_evaluate(cfg, split="dev", log=log)
    done = load_metrics(resolve_path(cfg, "artifacts") / "eval" / "metrics.json")["splits"]
    if "test" in done:
        log(
            f"test split already evaluated ({done['test']['evaluated_at']}), skipped "
            "(`bsim evaluate --split test --force` replaces it)"
        )
    else:
        run_evaluate(cfg, split="test", log=log)


def stage_eval_openbible(cfg: dict[str, Any], log: Log) -> None:
    """Second gold set (dev only); downloads the OpenBible file on first use."""
    from bsim.eval.openbible import run_eval_openbible

    run_eval_openbible(cfg, log=log)


def stage_phrases(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.phrases import run_phrases

    run_phrases(cfg, log=log)


def stage_sequences(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.sequences import run_sequences

    run_sequences(cfg, log=log)


def stage_diffs(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.diffs import run_diffs

    run_diffs(cfg, log=log)


def stage_parallelism(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.parallelism import run_parallelism

    run_parallelism(cfg, log=log)


def stage_acrostics(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.acrostic import run_acrostics

    run_acrostics(cfg, log=log)


def stage_typescenes(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.typescenes import run_typescenes

    run_typescenes(cfg, log=log)


def stage_sound(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.sound import run_sound

    run_sound(cfg, log=log)


def stage_wordplay(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.wordplay import run_wordplay

    run_wordplay(cfg, log=log)


def stage_entities(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.entities import run_entities

    run_entities(cfg, log=log)


def stage_dating(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.dating import run_dating

    run_dating(cfg, log=log)


def stage_senses(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.senses import run_senses

    run_senses(cfg, log=log)


def stage_borrowing(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.borrowing import run_borrowing

    run_borrowing(cfg, log=log)


def stage_seams(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.seams import run_seams

    run_seams(cfg, log=log)


def stage_structure(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.structure import run_structure

    run_structure(cfg, log=log)


def stage_map(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.corpus_map import run_map

    run_map(cfg, log=log)


def stage_network(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.network import run_network

    run_network(cfg, log=log)


def stage_stylometry(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.stylometry import run_stylometry

    run_stylometry(cfg, log=log)


def stage_voices(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.voices import run_voices

    run_voices(cfg, log=log)


def stage_segments(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.segments import run_segments

    run_segments(cfg, log=log)


def stage_ketiv(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.ketiv import run_ketiv

    run_ketiv(cfg, log=log)


def stage_citations(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.citations import run_citations

    run_citations(cfg, log=log)


def stage_allusions(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.allusions import run_allusions

    run_allusions(cfg, log=log)


def stage_mirrors(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.mirrors import run_mirrors

    run_mirrors(cfg, log=log)


def stage_build_db(cfg: dict[str, Any], log: Log) -> None:
    from bsim.store.db import run_build_db

    run_build_db(cfg, log=log)


# name -> function name in this module (looked up at run time, so tests can patch stages)
STAGES: dict[str, str] = {
    "download": "stage_download",
    "build-corpus": "stage_build_corpus",
    "build-links": "stage_build_links",
    "lexicon": "stage_lexicon",
    "syntax": "stage_syntax",
    "lexical": "stage_lexical",
    "lexical-topk": "stage_lexical_topk",
    "train-simcse": "stage_train_simcse",
    "train-sup": "stage_train_sup",
    "embed": "stage_embed",
    "topk": "stage_topk",
    "units": "stage_units",
    "fuse": "stage_fuse",
    "evaluate": "stage_evaluate",
    "eval-openbible": "stage_eval_openbible",
    "phrases": "stage_phrases",
    "sequences": "stage_sequences",
    "diffs": "stage_diffs",
    "typescenes": "stage_typescenes",
    "parallelism": "stage_parallelism",
    "acrostics": "stage_acrostics",
    "wordplay": "stage_wordplay",
    "sound": "stage_sound",
    "entities": "stage_entities",
    "senses": "stage_senses",
    "dating": "stage_dating",
    "borrowing": "stage_borrowing",
    "seams": "stage_seams",
    "structure": "stage_structure",
    "map": "stage_map",
    "network": "stage_network",
    "stylometry": "stage_stylometry",
    "voices": "stage_voices",
    "segments": "stage_segments",
    "ketiv": "stage_ketiv",
    "citations": "stage_citations",
    "allusions": "stage_allusions",
    "mirrors": "stage_mirrors",
    "build-db": "stage_build_db",
}


def select_stages(
    start: str | None = None, stop: str | None = None, skip: Iterable[str] = ()
) -> list[str]:
    """Stages from `start` to `stop` (inclusive, in pipeline order) minus `skip`."""
    names = list(STAGES)
    skip = list(skip)
    unknown = [s for s in [start, stop, *skip] if s is not None and s not in STAGES]
    if unknown:
        raise ValueError(f"unknown stage(s) {unknown}; stages: {', '.join(names)}")
    lo = names.index(start) if start else 0
    hi = names.index(stop) if stop else len(names) - 1
    if lo > hi:
        raise ValueError(f"--from {start} comes after --to {stop}")
    selected = [s for s in names[lo : hi + 1] if s not in skip]
    if not selected:
        raise ValueError("no stages selected")
    return selected


def _fmt_secs(secs: float) -> str:
    m, s = divmod(round(secs), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}"


def run_all(
    cfg: dict[str, Any],
    log: Log = print,
    start: str | None = None,
    stop: str | None = None,
    skip: Iterable[str] = (),
) -> dict[str, float]:
    """Run the selected stages in order; returns seconds per stage."""
    stages = select_stages(start, stop, skip)
    timings: dict[str, float] = {}
    t_all = time.perf_counter()
    for i, name in enumerate(stages, 1):
        log(f"=== [{i}/{len(stages)}] {name} ===")
        t0 = time.perf_counter()
        try:
            globals()[STAGES[name]](cfg, log)
        except RuntimeError as e:
            raise RuntimeError(f"stage {name!r} failed: {e}") from e
        timings[name] = time.perf_counter() - t0
        log(f"=== {name} done in {_fmt_secs(timings[name])} ===")
    log("stage timings:")
    for name, secs in timings.items():
        log(f"  {name:<13} {_fmt_secs(secs)}")
    log(f"  {'total':<13} {_fmt_secs(time.perf_counter() - t_all)}")
    return timings
