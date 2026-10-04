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


def _not_implemented(stage: str, milestone: str) -> None:
    typer.echo(f"`{stage}` is not implemented yet (planned in {milestone}, see docs/TASKS.md).")
    raise typer.Exit(code=1)


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
    model: Annotated[str, typer.Option(help="Encoder system name, e.g. berel_mean")],
    config: ConfigOpt = None,
) -> None:
    """Embed all verses with an encoder."""
    load_config(config)
    _not_implemented("embed", "M6")


@app.command("train-simcse")
def train_simcse(config: ConfigOpt = None) -> None:
    """Unsupervised SimCSE adaptation of BEREL."""
    load_config(config)
    _not_implemented("train-simcse", "M7")


@app.command("train-sup")
def train_sup(config: ConfigOpt = None) -> None:
    """Supervised contrastive fine-tune on Sefaria links."""
    load_config(config)
    _not_implemented("train-sup", "M8")


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
    system: Annotated[str, typer.Option(help="Retrieval system name")],
    config: ConfigOpt = None,
) -> None:
    """Aggregate to chapter / pericope / parasha top-k."""
    load_config(config)
    _not_implemented("units", "M9")


@app.command()
def fuse(config: ConfigOpt = None) -> None:
    """Fuse lexical and semantic rankings with weighted RRF."""
    load_config(config)
    _not_implemented("fuse", "M9")


@app.command()
def evaluate(
    split: Annotated[str, typer.Option(help="dev or test")] = "dev",
    config: ConfigOpt = None,
) -> None:
    """Evaluate all systems against Sefaria links."""
    if split not in {"dev", "test"}:
        raise typer.BadParameter("split must be 'dev' or 'test'")
    from bsim.eval.report import run_evaluate

    try:
        run_evaluate(load_config(config), split=split, log=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


@app.command("build-db")
def build_db(config: ConfigOpt = None) -> None:
    """Build artifacts/results.sqlite for the viewer."""
    load_config(config)
    _not_implemented("build-db", "M10")


@app.command()
def serve(config: ConfigOpt = None) -> None:
    """Run the FastAPI viewer backend."""
    load_config(config)
    _not_implemented("serve", "M11")


@app.command("all")
def run_all(config: ConfigOpt = None) -> None:
    """Run the full offline pipeline end to end."""
    load_config(config)
    _not_implemented("all", "M13")


if __name__ == "__main__":
    app()
