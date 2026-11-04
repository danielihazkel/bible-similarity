"""Training pairs for `bsim train-sup` (DESIGN.md §7.2, §16.41).

Sefaria's train-split verse links (both directions), and with `train.supervised.extra_pairs` the
train-split pairs of the other golds: OpenBible's cross-references (§16.13, at least
`extra_min_votes` votes) and ETCBC's parallels (§16.34). Both golds split a pair by the Sefaria
rule (train only when neither book is a dev or test book), so dev and test books never enter
training and the dev golds stay held out. A pair Sefaria links (any split) is not added again, and
a pair two extra sources share is added once, under the first source named.

`labels` (D132, §16.79) is your judgements (`paths.labels`, `store/labels.py`): the `real` verse
pairs as positives, split by the same rule, so only pairs between two train books train; the
`not` ones become explicit hard negatives (`label_negatives`, `train/negatives.py`). It needs
`labels.min_train` real train pairs, so that a handful of labels does not make a variant.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import resolve_path

# source -> (file under paths.data_processed, the command that writes it)
EXTRA_SOURCES = {
    "openbible": ("openbible_links.parquet", "build-golds"),
    "etcbc": ("etcbc_links.parquet", "build-golds"),
}
LABELS = "labels"  # your labels (paths.labels), not a file under data_processed
SEFARIA = "sefaria"


def judged_pairs(cfg: dict[str, Any], label: str) -> pd.DataFrame:
    """Your verse pairs labelled `label` (`src_vid, tgt_vid, split`, both directions, every
    split; the split by the Sefaria rule of the two books)."""
    from bsim.data.canon import BY_SEFARIA
    from bsim.eval.labels import verse_labels
    from bsim.store.labels import read_labels

    proc = resolve_path(cfg, "data_processed")
    for file, cmd in (("splits.json", "build-links"), ("verses.parquet", "build-corpus")):
        if not (proc / file).exists():
            raise RuntimeError(f"{proc / file} missing; run `bsim {cmd}` first")
    splits = json.loads((proc / "splits.json").read_text("utf-8"))["books"]
    book = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id"])
    book = book.sort_values("verse_id").book_id.to_numpy()
    vl = verse_labels(
        read_labels(resolve_path(cfg, "labels")),
        book,
        {BY_SEFARIA[name].book_id: sp for name, sp in splits.items()},
    )
    vl = vl[vl.label == label]
    fwd = pd.DataFrame({"src_vid": vl.a, "tgt_vid": vl.b, "split": vl.split})
    back = pd.DataFrame({"src_vid": vl.b, "tgt_vid": vl.a, "split": vl.split})
    return pd.concat([fwd, back], ignore_index=True).astype(
        {"src_vid": "int64", "tgt_vid": "int64"}
    )


def label_links(cfg: dict[str, Any]) -> pd.DataFrame:
    """Your `real` verse pairs as an extra source, refused below `labels.min_train` train pairs."""
    df = judged_pairs(cfg, "real")
    n, need = int((df.split == "train").sum()) // 2, cfg["labels"]["min_train"]
    if n < need:
        raise RuntimeError(
            f"extra_pairs: labels needs {need} real verse pairs between train books, there are {n};"
            " label more from the queue (/labels?tab=queue)"
        )
    return df


def label_negatives(cfg: dict[str, Any]) -> dict[int, set[int]]:
    """Your `not` verse pairs between train books: verse -> verses it is not connected to."""
    df = judged_pairs(cfg, "not")
    out: dict[int, set[int]] = {}
    for s, t in zip(df.src_vid[df.split == "train"], df.tgt_vid[df.split == "train"], strict=True):
        out.setdefault(int(s), set()).add(int(t))
    return out


def extra_links(cfg: dict[str, Any], source: str) -> pd.DataFrame:
    """A gold's verse pairs (`src_vid, tgt_vid, split`, both directions, every split)."""
    if source == LABELS:
        return label_links(cfg)
    if source not in EXTRA_SOURCES:
        known = sorted([*EXTRA_SOURCES, LABELS])
        raise RuntimeError(f"unknown extra_pairs source {source!r}; known: {known}")
    name, cmd = EXTRA_SOURCES[source]
    path = resolve_path(cfg, "data_processed") / name
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim {cmd}` first")
    df = pd.read_parquet(path)
    if source == "openbible":
        df = df[df.votes >= cfg["train"]["supervised"]["extra_min_votes"]]
    return df[["src_vid", "tgt_vid", "split"]].reset_index(drop=True)


def merge_pairs(sefaria: pd.DataFrame, extras: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Train pairs `src_vid, tgt_vid, source`: Sefaria's train rows, then each extra source's
    train rows whose undirected pair is not yet in (Sefaria counted over every split)."""
    seen = {(min(a, b), max(a, b)) for a, b in zip(sefaria.src_vid, sefaria.tgt_vid, strict=True)}
    tr = sefaria[sefaria.split == "train"]
    parts = [pd.DataFrame({"src_vid": tr.src_vid, "tgt_vid": tr.tgt_vid, "source": SEFARIA})]
    for source, df in extras.items():
        t = df[df.split == "train"]
        key = [(min(a, b), max(a, b)) for a, b in zip(t.src_vid, t.tgt_vid, strict=True)]
        new = np.array([k not in seen for k in key], bool)
        parts.append(
            pd.DataFrame(
                {
                    "src_vid": t.src_vid.to_numpy()[new],
                    "tgt_vid": t.tgt_vid.to_numpy()[new],
                    "source": source,
                }
            )
        )
        seen.update(key)
    out = pd.concat(parts, ignore_index=True)
    return out.astype({"src_vid": "int64", "tgt_vid": "int64"})


def training_pairs(cfg: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(train pairs `src_vid, tgt_vid, source`; every verse pair of the sources used, any split,
    `src_vid, tgt_vid` — what a hard negative must not be)."""
    path = resolve_path(cfg, "data_processed") / "links.parquet"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim build-links` first")
    links = pd.read_parquet(path)
    sefaria = links[links.level == "verse"]
    extras = {s: extra_links(cfg, s) for s in cfg["train"]["supervised"]["extra_pairs"]}
    linked = pd.concat(
        [sefaria[["src_vid", "tgt_vid"]], *(df[["src_vid", "tgt_vid"]] for df in extras.values())],
        ignore_index=True,
    )
    return merge_pairs(sefaria, extras), linked
