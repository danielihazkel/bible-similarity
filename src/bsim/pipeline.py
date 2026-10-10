"""`bsim all`: the offline pipeline end to end (ARCHITECTURE.md §4, stages 1–12 + analyses).

Stages run in a fixed dependency order and call the same runners as the single-stage
commands; the system lists come from `pipeline` in the config. The test split is evaluated
only when `metrics.json` has no test entry yet (it is run once, never replaced here).

Runs are incremental (DESIGN.md §16.35, `bsim/incremental.py`): a stage whose code, config keys
and input files are unchanged since it last succeeded is skipped; `--force` runs them all.
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


def stage_echoes(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.echoes import run_echoes

    run_echoes(cfg, log=log)


def stage_mirrors(cfg: dict[str, Any], log: Log) -> None:
    from bsim.analysis.mirrors import run_mirrors

    run_mirrors(cfg, log=log)


def stage_eval_etcbc(cfg: dict[str, Any], log: Log) -> None:
    """Third gold set (dev only), after the parallel analyses it also scores."""
    from bsim.eval.etcbc import run_eval_etcbc

    run_eval_etcbc(cfg, log=log)


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
    "echoes": "stage_echoes",
    "mirrors": "stage_mirrors",
    "eval-etcbc": "stage_eval_etcbc",
    "build-db": "stage_build_db",
}


# stage -> the earlier stages whose outputs it reads. A stage's inputs are these stages' outputs
# plus every file it is seen to open; the list is what the audit hook cannot see (model folders
# read by native code, globbed systems, files only checked for existence) and what an adopted
# stage relies on. `bsim all` notes a read from a stage missing here.
_CORPUS = ("download", "build-corpus")
_MODELS = ("train-simcse", "train-sup")
_TOPK = ("lexical-topk", "topk", "units", "fuse")
DEPS: dict[str, tuple[str, ...]] = {
    "download": (),
    "build-corpus": ("download",),
    "build-links": (*_CORPUS,),
    "lexicon": (*_CORPUS,),
    "syntax": (*_CORPUS, "lexicon"),
    "lexical": (*_CORPUS, "lexicon", "syntax"),
    "lexical-topk": (*_CORPUS, "lexical"),
    "train-simcse": (*_CORPUS,),
    "train-sup": (*_CORPUS, "build-links", "lexical", "lexical-topk", "train-simcse"),
    "embed": (*_CORPUS, *_MODELS),
    "topk": (*_CORPUS, "lexical", "embed"),
    "units": (*_CORPUS, "lexical", "embed"),
    "fuse": (*_CORPUS, "build-links", *_TOPK[:3]),
    "evaluate": (*_CORPUS, "build-links", *_TOPK),
    "eval-openbible": (*_CORPUS, "build-links", *_TOPK),
    "phrases": (*_CORPUS, "lexical", "lexical-topk", "fuse"),
    "sequences": (*_CORPUS, *_TOPK),
    "diffs": (*_CORPUS, "sequences"),
    "typescenes": (*_CORPUS, "sequences"),
    "parallelism": (*_CORPUS, "lexicon", *_MODELS),
    "acrostics": (*_CORPUS, "parallelism"),
    "wordplay": (*_CORPUS,),
    "sound": (*_CORPUS, "parallelism"),
    "entities": (*_CORPUS, "lexicon"),
    "senses": (*_CORPUS, "lexicon", *_MODELS),
    "dating": (*_CORPUS, "parallelism", "sequences"),
    "borrowing": (*_CORPUS, "sequences", "diffs", "dating"),
    "seams": (*_CORPUS,),
    "structure": (*_CORPUS, "embed"),
    "map": (*_CORPUS, "embed", *_TOPK),
    "network": (*_CORPUS, *_TOPK),
    "stylometry": (*_CORPUS,),
    "voices": (*_CORPUS, "syntax"),
    "segments": (*_CORPUS, "build-links", "embed", "seams"),
    "ketiv": (*_CORPUS, "sequences", "diffs"),
    "citations": (*_CORPUS, "lexical", "embed"),
    "allusions": (*_CORPUS, *_TOPK, "sequences"),
    "echoes": (*_CORPUS, "network", "citations", "borrowing", "dating"),
    "mirrors": (*_CORPUS, "syntax", "parallelism", "dating"),
    "eval-etcbc": (*_CORPUS, "build-links", *_TOPK, "eval-openbible", "phrases", "sequences"),
}
DEPS["build-db"] = tuple(s for s in STAGES if s != "build-db")


def downstream(stages: Iterable[str]) -> set[str]:
    """The stages that depend, directly or not, on any of `stages` (themselves excluded)."""
    found: set[str] = set()
    frontier = set(stages)
    while frontier:
        frontier = {s for s, d in DEPS.items() if s not in found and frontier & set(d)}
        found |= frontier
    return found - set(stages)


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
    *,
    force: bool = False,
    rerun: Iterable[str] = (),
    dry_run: bool = False,
    adopt: bool = False,
) -> dict[str, float]:
    """Run the selected stages in order, skipping those up to date; returns seconds per stage run.

    `force` runs every selected stage, `rerun` the named ones; `dry_run` only says which stages
    would run and why; `adopt` records the selected stages as up to date without running them
    (for artifacts built before incremental runs, or by hand).
    """
    from bsim import incremental as inc

    stages = select_stages(start, stop, skip)
    rerun = set(rerun)
    unknown = sorted(rerun - set(STAGES))
    if unknown:
        raise ValueError(f"unknown stage(s) {unknown}; stages: {', '.join(STAGES)}")
    order = list(STAGES)
    state = inc.State(resolve_path(cfg, "pipeline_state"))
    scope = inc.Scope.from_config(cfg)

    def reason(name: str) -> str | None:
        if force:
            return "forced"
        if name in rerun:
            return "--rerun"
        return inc.stale_reason(name, globals()[STAGES[name]], cfg, state, DEPS[name])

    if adopt:
        for name in stages:
            inc.adopt(name, globals()[STAGES[name]], cfg, state)
            log(f"adopted {name}: its current outputs count as up to date")
        state.save()
        return {}
    if dry_run:
        stale = {name: r for name in stages if (r := reason(name))}
        after = downstream(stale) & set(stages)
        for name in stages:
            if name in stale:
                log(f"  run      {name:<15} {stale[name]}")
            elif name in after:
                ups = [d for d in DEPS[name] if d in stale or d in after]
                log(f"  maybe    {name:<15} if {', '.join(ups)} change what they write")
            else:
                log(f"  skip     {name:<15} up to date")
        return {}

    timings: dict[str, float] = {}
    t_all = time.perf_counter()
    for i, name in enumerate(stages, 1):
        why = reason(name)
        if why is None:
            log(f"=== [{i}/{len(stages)}] {name}: up to date, skipped ===")
            continue
        log(f"=== [{i}/{len(stages)}] {name} ({why}) ===")
        fn = globals()[STAGES[name]]
        before = scope.snapshot()
        tracked = inc.TrackedConfig(cfg)
        t0 = time.perf_counter()
        try:
            with inc.tracking_reads(scope) as reads:
                fn(tracked, log)
        except RuntimeError as e:
            raise RuntimeError(f"stage {name!r} failed: {e}") from e
        timings[name] = time.perf_counter() - t0
        inc.record(
            name, fn, cfg, state, order=order, deps=DEPS[name], seen=tracked.seen, reads=reads,
            before=before, after=scope.snapshot(), seconds=timings[name], log=log,
        )  # fmt: skip
        state.save()
        log(f"=== {name} done in {_fmt_secs(timings[name])} ===")
    log(f"stage timings ({len(timings)} run, {len(stages) - len(timings)} up to date):")
    for name, secs in timings.items():
        log(f"  {name:<15} {_fmt_secs(secs)}")
    log(f"  {'total':<15} {_fmt_secs(time.perf_counter() - t_all)}")
    return timings
