"""`bsim` command line: one command per pipeline stage (ARCHITECTURE.md §4)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from bsim.config import load_config

app = typer.Typer(
    help="Hebrew Bible similarity pipeline.",
    no_args_is_help=True,
    add_completion=False,
)

ConfigOpt = Annotated[
    Path | None, typer.Option("--config", "-c", help="Config file (default: configs/default.yaml)")
]


@app.command()
def download(
    only: Annotated[
        list[str] | None,
        typer.Option(help="Restrict to groups: oshb, text, schemas, links (repeatable)"),
    ] = None,
    workers: Annotated[int, typer.Option(help="Parallel downloads")] = 8,
    config: ConfigOpt = None,
) -> None:
    """Download OSHB, Sefaria MAM text, schemas and links into data/raw."""
    from bsim.data.download import GROUPS, run_download

    groups = only or list(GROUPS)
    unknown = set(groups) - set(GROUPS)
    if unknown:
        raise typer.BadParameter(f"unknown groups {sorted(unknown)}; choose from {GROUPS}")
    try:
        run_download(load_config(config), groups=groups, workers=workers, log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command("build-corpus")
def build_corpus(config: ConfigOpt = None) -> None:
    """Parse, normalize and align texts; build verses/words/units tables."""
    from bsim.data.corpus import run_build_corpus

    try:
        run_build_corpus(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command("build-links")
def build_links(config: ConfigOpt = None) -> None:
    """Filter and expand Sefaria Tanakh links; split by book."""
    from bsim.data.links import run_build_links

    try:
        run_build_links(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def lexical(config: ConfigOpt = None) -> None:
    """Build the lemma BM25 index and detect formulas."""
    from bsim.lexical.build import run_lexical

    try:
        run_lexical(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def embed(
    model: Annotated[
        list[str], typer.Option(help="Encoder system name, e.g. berel_mean (repeatable)")
    ],
    config: ConfigOpt = None,
) -> None:
    """Embed all verses with an encoder."""
    from bsim.embed.encoders import run_embed

    cfg = load_config(config)
    try:
        for name in model:
            run_embed(cfg, name, log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command("train-simcse")
def train_simcse(config: ConfigOpt = None) -> None:
    """Unsupervised SimCSE adaptation of BEREL."""
    from bsim.train.simcse import run_train_simcse

    try:
        run_train_simcse(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command("train-sup")
def train_sup(
    init: Annotated[
        str | None,
        typer.Option(help="Start point: a checkpoint under models/ or 'base' (default: config)"),
    ] = None,
    hard_negatives: Annotated[
        bool | None,
        typer.Option("--hard-negatives/--no-hard-negatives", help="BM25 hard negatives"),
    ] = None,
    output: Annotated[
        str | None, typer.Option(help="Output checkpoint name under models/ (default: config)")
    ] = None,
    config: ConfigOpt = None,
) -> None:
    """Supervised contrastive fine-tune on Sefaria links."""
    from bsim.train.supervised import run_train_sup

    try:
        run_train_sup(
            load_config(config),
            log=typer.echo,
            init=init,
            hard_negatives=hard_negatives,
            output=output,
        )
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def topk(
    system: Annotated[
        list[str], typer.Option(help="Retrieval system name, e.g. bm25_lemma (repeatable)")
    ],
    config: ConfigOpt = None,
) -> None:
    """Compute verse-level top-k for one or more systems."""
    from bsim.retrieve.topk import run_topk

    cfg = load_config(config)
    try:
        for name in system:
            run_topk(cfg, name, log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def units(
    system: Annotated[
        list[str],
        typer.Option(help="'tfidf' (lexical) or a dense / *_csls verse system (repeatable)"),
    ],
    config: ConfigOpt = None,
) -> None:
    """Aggregate to chapter / pericope / parasha top-k."""
    from bsim.retrieve.units import run_units

    cfg = load_config(config)
    try:
        for name in system:
            run_units(cfg, name, log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def fuse(
    tune: Annotated[
        bool, typer.Option(help="Score fusion.w_lex_grid on dev instead of writing fused lists")
    ] = False,
    config: ConfigOpt = None,
) -> None:
    """Fuse lexical and semantic rankings with weighted RRF."""
    from bsim.retrieve.fusion import run_fuse, run_fuse_tune

    try:
        (run_fuse_tune if tune else run_fuse)(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def evaluate(
    split: Annotated[str, typer.Option(help="dev or test")] = "dev",
    force: Annotated[
        bool, typer.Option(help="Replace an existing test run (the test split is run once)")
    ] = False,
    config: ConfigOpt = None,
) -> None:
    """Evaluate all systems against Sefaria links."""
    if split not in {"dev", "test"}:
        raise typer.BadParameter("split must be 'dev' or 'test'")
    from bsim.eval.report import run_evaluate

    try:
        run_evaluate(load_config(config), split=split, log=typer.echo, force=force)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command("train-rerank")
def train_rerank(config: ConfigOpt = None) -> None:
    """Fine-tune the cross-encoder reranker on train-split links (epoch chosen on dev)."""
    from bsim.train.rerank import run_train_rerank

    try:
        run_train_rerank(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def rerank(
    tune: Annotated[bool, typer.Option(help="Score rerank.w_ce_grid on dev first")] = False,
    config: ConfigOpt = None,
) -> None:
    """Rerank the fused verse lists with the cross-encoder."""
    from bsim.train.rerank import run_rerank

    try:
        run_rerank(load_config(config), log=typer.echo, tune=tune)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command("embed-context")
def embed_context(config: ConfigOpt = None) -> None:
    """Embed every verse with its neighbours (window and late-chunked systems; dev experiment)."""
    from bsim.embed.context import run_embed_context

    try:
        run_embed_context(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def maxsim(config: ConfigOpt = None) -> None:
    """Score the fused verse lists by token late interaction (MaxSim)."""
    from bsim.retrieve.maxsim import run_maxsim

    try:
        run_maxsim(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command("retrieval-exp")
def retrieval_exp(config: ConfigOpt = None) -> None:
    """Compare contextual and MaxSim lists with the fused lists on dev (bootstrap CIs)."""
    from bsim.eval.experiments import run_retrieval_experiments

    try:
        run_retrieval_experiments(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def phrases(config: ConfigOpt = None) -> None:
    """Find shared phrases between verses (local alignment of lemma streams)."""
    from bsim.analysis.phrases import run_phrases

    try:
        run_phrases(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def sequences(config: ConfigOpt = None) -> None:
    """Find passages that run parallel verse by verse in the same order."""
    from bsim.analysis.sequences import run_sequences

    try:
        run_sequences(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def diffs(config: ConfigOpt = None) -> None:
    """Align parallel sequences word by word and record what changed."""
    from bsim.analysis.diffs import run_diffs

    try:
        run_diffs(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def parallelism(config: ConfigOpt = None) -> None:
    """Split verses at their main accent pauses and score how parallel the halves are."""
    from bsim.analysis.parallelism import run_parallelism

    try:
        run_parallelism(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def acrostics(config: ConfigOpt = None) -> None:
    """Find alphabetic acrostics, whole or broken, in every chapter."""
    from bsim.analysis.acrostic import run_acrostics

    try:
        run_acrostics(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def network(config: ConfigOpt = None) -> None:
    """Build the network of echoes between chapters / pericopes: central passages, communities."""
    from bsim.analysis.network import run_network

    try:
        run_network(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def typescenes(config: ConfigOpt = None) -> None:
    """Align the verb sequences of pericopes: the same actions in the same order."""
    from bsim.analysis.typescenes import run_typescenes

    try:
        run_typescenes(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def sound(config: ConfigOpt = None) -> None:
    """Find alliteration within cola and rhyme across consecutive cola."""
    from bsim.analysis.sound import run_sound

    try:
        run_sound(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def wordplay(config: ConfigOpt = None) -> None:
    """Find sound-alike words close together (paronomasia)."""
    from bsim.analysis.wordplay import run_wordplay

    try:
        run_wordplay(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def entities(config: ConfigOpt = None) -> None:
    """Classify names as people or places and link the ones that appear together."""
    from bsim.analysis.entities import run_entities

    try:
        run_entities(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def seams(config: ConfigOpt = None) -> None:
    """Find where the style of each book changes (stylometric seams)."""
    from bsim.analysis.seams import run_seams

    try:
        run_seams(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command("eval-openbible")
def eval_openbible(config: ConfigOpt = None) -> None:
    """Score the final verse systems on OpenBible cross-references (dev split only)."""
    from bsim.eval.openbible import run_eval_openbible

    try:
        run_eval_openbible(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def structure(config: ConfigOpt = None) -> None:
    """Score inclusio and chiasm for every chapter, pericope and parasha."""
    from bsim.analysis.structure import run_structure

    try:
        run_structure(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command("map")
def corpus_map(config: ConfigOpt = None) -> None:
    """Lay out units in 2-D, cluster them and measure book-to-book affinity."""
    from bsim.analysis.corpus_map import run_map

    try:
        run_map(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def stylometry(config: ConfigOpt = None) -> None:
    """Style profiles: feature rates, Burrows' Delta between books, chapter PCA."""
    from bsim.analysis.stylometry import run_stylometry

    try:
        run_stylometry(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command("build-db")
def build_db(config: ConfigOpt = None) -> None:
    """Build artifacts/results.sqlite for the viewer."""
    from bsim.store.db import run_build_db

    try:
        run_build_db(load_config(config), log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command()
def serve(
    host: Annotated[str | None, typer.Option(help="Bind address (default: serve.host)")] = None,
    port: Annotated[int | None, typer.Option(help="Port (default: serve.port)")] = None,
    config: ConfigOpt = None,
) -> None:
    """Run the FastAPI viewer backend."""
    import uvicorn

    from bsim.api.app import create_app

    cfg = load_config(config)
    try:
        api = create_app(cfg, log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e
    uvicorn.run(api, host=host or cfg["serve"]["host"], port=port or cfg["serve"]["port"])


@app.command("all")
def run_all(
    start: Annotated[
        str | None, typer.Option("--from", help="First stage to run (default: download)")
    ] = None,
    stop: Annotated[
        str | None, typer.Option("--to", help="Last stage to run (default: build-db)")
    ] = None,
    skip: Annotated[list[str] | None, typer.Option(help="Stage to leave out (repeatable)")] = None,
    config: ConfigOpt = None,
) -> None:
    """Run the full offline pipeline end to end (download ... build-db)."""
    from bsim import pipeline

    try:
        pipeline.select_stages(start, stop, skip or ())
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e
    try:
        pipeline.run_all(
            load_config(config), log=typer.echo, start=start, stop=stop, skip=skip or ()
        )
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
