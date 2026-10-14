"""What each analysis stage puts in `results.sqlite` (DESIGN.md §9): its files, tables and meta.

One `Source` per stage: the folder under `paths.artifacts` it writes, each Parquet file and the
table it fills (columns as in `schema.sql`), and the keys of its `*.meta.json` copied into the DB
`meta`. A `required` file must exist (`bsim build-db` stops and names the stage); any other may be
missing, and its table is then empty (the stage was not run, or ran without `bsim lexicon` /
`bsim syntax`). A table's `fix` adapts a non-empty frame: integer flags, a book column, an id,
columns that artifacts of an older stage lack. `store/db.py` loads every source, inserts every
table and adds the meta.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from bsim.config import resolve_path
from bsim.data.canon import BOOKS
from bsim.store.links import sequence_gold
from bsim.store.schema import COLUMNS


@dataclass(frozen=True)
class Context:
    """What a table's fix may need beyond its own frame."""

    cfg: dict[str, Any]
    verses: pd.DataFrame  # verse_id, book_id, ...
    gold: pd.DataFrame  # the Sefaria verse pairs (`links.gold_verse_pairs`)

    def book_of(self, verse_ids: pd.Series) -> pd.Series:
        return verse_ids.map(self.verses.set_index("verse_id").book_id)


Fix = Callable[[pd.DataFrame, Context], pd.DataFrame]


@dataclass(frozen=True)
class Table:
    name: str  # the DB table (its columns: schema.sql)
    stem: str  # the Parquet file under the source's folder
    required: bool = False
    fix: Fix | None = None


@dataclass(frozen=True)
class Source:
    stage: str  # `bsim {stage}` writes the folder
    folder: str  # under paths.artifacts
    tables: tuple[Table, ...]
    meta_file: str | None = None  # under the folder
    meta: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] = field(
        default=lambda m, cfg: {}
    )  # (the meta file, cfg) -> DB meta entries


def keys(name: str, *names: str) -> Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]:
    """The DB meta entry `name`: these keys of the stage's meta file."""
    return lambda m, cfg: {name: {k: m.get(k) for k in names}}


def as_int(*cols: str) -> Fix:
    return lambda d, ctx: d.assign(**{c: d[c].astype(int) for c in cols})


def numbered(col: str) -> Fix:
    return lambda d, ctx: d.assign(**{col: range(1, len(d) + 1)})


def then(*fixes: Fix) -> Fix:
    def run(d: pd.DataFrame, ctx: Context) -> pd.DataFrame:
        for f in fixes:
            d = f(d, ctx)
        return d

    return run


def book_from(col: str) -> Fix:
    return lambda d, ctx: d.assign(book_id=ctx.book_of(d[col]))


def _sequences(d: pd.DataFrame, ctx: Context) -> pd.DataFrame:
    return sequence_gold(d, ctx.gold).assign(
        same_chapter=lambda x: x.same_chapter.astype(int),
        # artifacts from before reverse / mixed chains hold forward chains only
        direction=lambda x: x.direction if "direction" in x else "forward",
    )


def _parallelism(d: pd.DataFrame, ctx: Context) -> pd.DataFrame:
    if "clauses" not in d:  # artifacts from before the clause segmentation
        d = d.assign(clauses=d.cola, next_prob=None)
    if "relation" not in d:  # run without the lexicon
        d = d.assign(relation=None, relation_pairs=None)
    return d


def _entities(d: pd.DataFrame, ctx: Context) -> pd.DataFrame:
    if "kind_source" not in d:  # run without the lexicon
        d = d.assign(kind_cues=d.kind, kind_source="cues")
    return d


def _speakers(d: pd.DataFrame, ctx: Context) -> pd.DataFrame:
    return d.assign(books=[json.dumps([int(b) for b in bs]) for bs in d.books])


SOURCES: tuple[Source, ...] = (
    Source(
        "phrases",
        "phrases",
        (
            Table(
                "phrases",
                "verse",
                required=True,
                fix=lambda d, ctx: d.assign(a_book=ctx.book_of(d.a), b_book=ctx.book_of(d.b)),
            ),
        ),
    ),
    Source(
        "sequences",
        "sequences",
        (Table("sequences", "verse", required=True, fix=_sequences),),
    ),
    Source(
        "diffs",
        "diffs",
        (
            Table("diff_changes", "changes", required=True),
            Table("rewrites", "rewrites", required=True),
            Table("rewrite_profiles", "profiles", required=True),
        ),
        "diffs.meta.json",
        keys("diffs", "verse_pairs", "loose_pairs", "ops", "rewrites"),
    ),
    Source(
        "acrostics",
        "acrostics",
        (Table("acrostics", "units", required=True),),
        "acrostics.meta.json",
        keys("acrostics", "known_q", "known_recall", "report_q"),
    ),
    Source(
        "parallelism",
        "parallelism",
        (
            Table("parallelism", "verses", required=True, fix=_parallelism),
            Table("word_pairs", "word_pairs"),
        ),
        "parallelism.meta.json",
        lambda m, cfg: {
            "parallelism": {
                k: m.get(k)
                for k in (
                    "coefficients",
                    "held_out_auc",
                    "known_poems",
                    "book_means",
                    "cross_pairs",
                    "cross_parallel",
                    "typing",
                )
            }
            | {"parallel_at": cfg["parallelism"]["parallel_at"]}
        },
    ),
    Source(
        "typescenes",
        "typescenes",
        (
            Table(
                "typescenes", "pairs", required=True, fix=as_int("parallel_text")
            ),
        ),
    ),
    Source(
        "sound",
        "sound",
        (
            Table(
                "alliteration",
                "alliteration",
                required=True,
                fix=book_from("verse_id"),
            ),
            Table("rhymes", "rhymes", required=True, fix=book_from("start_vid")),
        ),
        "sound.meta.json",
        keys("sound", "cola", "alliterations", "rhymes", "rhymes_q_below_0.05", "top_endings"),
    ),
    Source(
        "wordplay",
        "wordplay",
        (Table("wordplay", "pairs", required=True, fix=book_from("a_vid")),),
        "wordplay.meta.json",
        keys("wordplay", "pairs", "null_pairs_per_rep", "kinds"),
    ),
    Source(
        "entities",
        "entities",
        (
            Table("entities", "entities", required=True, fix=_entities),
            Table("entity_mentions", "mentions", required=True),
            Table("entity_links", "links", required=True),
        ),
        "entities.meta.json",
        keys("entities", "names", "kinds", "pairs", "kind_sources", "lexicon_vs_cues"),
    ),
    Source(
        "senses",
        "senses",
        (
            Table("lemma_shifts", "lemmas"),
            Table("lemma_senses", "senses"),
        ),
        "senses.meta.json",
        keys("senses", "groups", "encoder", "lemmas", "nmi_mean", "nmi_null_mean", "nmi_lemmas"),
    ),
    Source(
        "dating",
        "dating",
        (
            Table("dating_chapters", "chapters", fix=as_int("out_of_domain")),
            Table("dating_books", "books", fix=as_int("out_of_domain")),
        ),
        "dating.meta.json",
        keys(
            "dating",
            "features",
            "coefficients",
            "train_chapters",
            "held_out_auc",
            "held_out_auc_grammar",
            "held_out_books",
            "synoptic",
        ),
    ),
    Source(
        "borrowing",
        "borrowing",
        (
            Table("borrowing_sequences", "sequences"),
            Table("borrowing_books", "books"),
        ),
        "borrowing.meta.json",
        keys(
            "borrowing",
            "checks",
            "used_signs",
            "held_out",
            "used_vote",
            "known_sequences",
            "sequences",
        ),
    ),
    Source(
        "voices",
        "voices",
        (
            Table("voice_speakers", "speakers", fix=_speakers),
            Table("voice_features", "features"),
            Table("voice_pairs", "pairs"),
        ),
        "voices.meta.json",
        keys(
            "voices",
            "speakers",
            "features",
            "speech_clauses",
            "words",
            "significant",
            "calibration",
            "sensitivity",
            "order",
            "checks",
        ),
    ),
    Source(
        "segments",
        "segments",
        (
            Table("segment_gaps", "gaps"),
            Table("segment_books", "books"),
        ),
        "segments.meta.json",
        keys(
            "segments",
            "window",
            "window_grid",
            "gaps",
            "groups",
            "contrasts",
            "calibration",
            "seams",
            "agreement",
            "kinds",
        ),
    ),
    Source(
        "ketiv",
        "ketiv",
        (
            Table("kq_pairs", "pairs"),
            Table("kq_letters", "letters", fix=as_int("lookalike")),
            Table("kq_books", "books"),
        ),
        "ketiv.meta.json",
        keys("ketiv", "pairs", "classes", "grammar", "euphemisms", "features", "checks"),
    ),
    Source(
        "citations",
        "citations",
        (
            Table("citations", "citations"),
            Table("citation_books", "books"),
        ),
        "citations.meta.json",
        keys(
            "citations",
            "citations",
            "resolved",
            "families",
            "gold",
            "word_lag_median",
            "book_pairs",
        ),
    ),
    Source(
        "allusions",
        "allusions",
        (Table("allusions", "pairs"),),
        "allusions.meta.json",
        keys(
            "allusions",
            "rare_lemmas",
            "window",
            "pairs",
            "known",
            "max_q",
            "strong",
            "strong_known",
            "best_new_q",
        ),
    ),
    Source(
        "echoes",
        "echoes",
        (
            Table("echo_edges", "edges"),
            Table("echo_books", "books"),
            Table("echo_chapters", "chapters"),
        ),
        "echoes.meta.json",
        keys(
            "echoes",
            "language_gap",
            "pairs",
            "network_pairs",
            "in_domain",
            "bases",
            "checks",
            "language_forward",
            "language_backward",
            "cycles",
        ),
    ),
    Source(
        "mirrors",
        "mirrors",
        (
            Table("mirror_verses", "verses", fix=as_int("poetic")),
            Table(
                "mirror_clauses",
                "clauses",
                fix=then(numbered("pair_id"), as_int("poetic")),
            ),
        ),
        "mirrors.meta.json",
        keys("mirrors", "words", "clauses", "full_mirrors", "full_mirrors_q", "min_words"),
    ),
    Source(
        "meter",
        "meter",
        (
            Table("meter_lines", "lines"),
            Table(
                "meter_chapters",
                "chapters",
                fix=lambda d, ctx: d.rename(columns={"group": "grp"}),
            ),
        ),
        "meter.meta.json",
        keys(
            "meter",
            "min_stresses",
            "max_stresses",
            "min_lines",
            "pool_quantile",
            "pool_prob",
            "lines",
            "split",
            "test",
            "test_poetic",
            "test_chapters",
            "control",
            "named",
            "grid",
            "groups",
        ),
    ),
    Source(
        "roots",
        "roots",
        (
            Table("lemma_roots", "lemmas"),
            Table(
                "root_pairs",
                "pairs",
                fix=then(numbered("pair_id"), book_from("verse_id")),
            ),
            Table("root_books", "books"),
            Table("root_leitworte", "leitworte", fix=as_int("hidden")),
        ),
        "roots.meta.json",
        keys(
            "roots",
            "entries",
            "derived",
            "joined",
            "lemmas",
            "families",
            "family_lemmas",
            "window",
            "shuffles",
            "pairs",
            "tests",
            "known",
            "known_top_lemma",
            "known_top_root",
            "known_better",
            "top",
            "hidden",
        ),
    ),
    Source(
        "refrains",
        "refrains",
        (
            Table("refrains", "refrains", fix=as_int("strongest")),
            Table("refrain_verses", "occurrences"),
        ),
        "refrains.meta.json",
        keys(
            "refrains",
            "min_tokens",
            "min_count",
            "max_gap",
            "alpha",
            "shuffles",
            "candidates",
            "detect",
            "refrains",
            "distinct",
            "known",
            "known_found",
            "known_share",
            "regular",
            "turns",
        ),
    ),
    Source(
        "psalms",
        "psalms",
        (
            Table("psalms", "psalms"),
            Table("psalm_verses", "verses"),
        ),
        "psalms.meta.json",
        keys(
            "psalms",
            "psalms",
            "labelled",
            "genres",
            "features",
            "k",
            "alpha",
            "draws",
            "title_words",
            "genre_test",
            "crosstab",
            "checks",
            "checks_held",
            "profiles",
            "cluster_profiles",
            "known_turns",
            "laments_vs_hymns",
            "tolerance",
            "min_side",
            "robustness",
        ),
    ),
    Source(
        "pentateuch",
        "pentateuch",
        (
            Table("pentateuch_verses", "verses", fix=as_int("core")),
            Table("pentateuch_chapters", "chapters"),
        ),
        "pentateuch.meta.json",
        keys(
            "pentateuch",
            "verses",
            "assigned",
            "reference_p",
            "p_like",
            "chunks",
            "core_verses",
            "synonym_sets",
            "alpha",
            "draws",
            "agreement",
            "tests",
            "confusion",
            "books",
            "names",
            "features",
            "synonyms",
            "grid",
            "prefixes",
        ),
    ),
    Source(
        "dialogue",
        "dialogue",
        (
            Table("dialogue_pairs", "pairs"),
            Table("dialogue_exchanges", "exchanges"),
        ),
        "dialogue.meta.json",
        keys(
            "dialogue",
            "quotations",
            "with_addressee",
            "addressee",
            "reliable",
            "hand_check",
            "pairs",
            "exchanges",
            "unequal",
            "shuffles",
            "alpha",
            "tests",
            "sensitivity",
            "opener",
            "lengths",
        ),
    ),
    Source(
        "forms",
        "forms",
        (
            Table("forms_sayings", "sayings"),
            Table("forms_pairs", "pairs"),
            Table("forms_lists", "lists"),
            Table("forms_books", "books"),
        ),
        "forms.meta.json",
        keys(
            "forms",
            "window",
            "alpha",
            "shuffles",
            "numbers",
            "free",
            "sayings",
            "graded_pairs",
            "steps",
            "chance",
            "parallel",
            "known",
            "known_found",
            "known_share",
            "lists",
        ),
    ),
    Source(
        "seams",
        "seams",
        (
            Table("seam_curve", "curve", required=True),
            Table("seams", "seams", required=True),
        ),
        "seams.meta.json",
        lambda m, cfg: {
            "seams": {
                "thresholds": m.get("thresholds", {}),
                "block_words": cfg["seams"]["block_words"],
            }
        },
    ),
    Source(
        "structure",
        "structure",
        (Table("structure", "units", required=True),),
        "units.meta.json",
        lambda m, cfg: {"leitwort_numbers": m.get("leitwort_numbers")},
    ),
    Source(
        "network",
        "network",
        (
            Table("network_nodes", "nodes", required=True),
            Table("network_edges", "edges", required=True),
            Table("network_communities", "communities", required=True),
        ),
    ),
    Source(
        "map",
        "map",
        (
            Table("map_points", "points", required=True),
            Table("map_clusters", "clusters", required=True),
            Table("book_affinity", "book_affinity", required=True),
            Table("book_examples", "book_examples", required=True),
        ),
        "map.meta.json",
        lambda m, cfg: {"book_order": m.get("book_order", [b.book_id for b in BOOKS])},
    ),
    Source(
        "stylometry",
        "stylometry",
        (
            Table("stylo_points", "points", required=True),
            Table("stylo_delta", "book_delta", required=True),
            Table("stylo_features", "book_features", required=True),
        ),
        "stylometry.meta.json",
        keys("stylometry", "book_order", "axes", "book_words", "features"),
    ),
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text("utf-8")) if path.exists() else {}


def load(cfg: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, Any]]]:
    """(table -> frame as written by its stage, stage -> its meta file)."""
    art = resolve_path(cfg, "artifacts")
    frames, metas = {}, {}
    for s in SOURCES:
        folder = art / s.folder
        for t in s.tables:
            path = folder / f"{t.stem}.parquet"
            if path.exists():
                frames[t.name] = pd.read_parquet(path)
            elif t.required:
                raise RuntimeError(f"{path} missing; run `bsim {s.stage}` first")
            else:
                frames[t.name] = pd.DataFrame()
        metas[s.stage] = _read_json(folder / s.meta_file) if s.meta_file else {}
    return frames, metas


def tables(frames: dict[str, pd.DataFrame], ctx: Context) -> dict[str, pd.DataFrame]:
    """Every source table ready to insert: fixed, or empty with its columns."""
    out = {}
    for s in SOURCES:
        for t in s.tables:
            df = frames[t.name]
            if len(df) and t.fix is not None:
                df = t.fix(df, ctx)
            out[t.name] = df if len(df) else pd.DataFrame(columns=COLUMNS[t.name])
    return out


def meta(metas: dict[str, dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    """The DB meta entries of every source."""
    out: dict[str, Any] = {}
    for s in SOURCES:
        out |= s.meta(metas[s.stage], cfg)
    return out
