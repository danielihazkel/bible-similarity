"""`bsim mainline`: the narrative main line and where a story pauses (DESIGN.md §16.91, D153; M164).

Biblical narrative moves on a chain of wayyiqtol clauses (ויקם … וילך … ויאמר); the narrator steps
off it to set a scene, describe, or tell what had happened before: והנחש היה ערום (Gen 3:1), ולבן
שתי בנות (Gen 29:16). The BHSA clauses (§16.26) give each clause's type, so the chain and its pauses
can be read off.

- **The narrator's clauses.** Clauses outside quoted speech in the narrator's domains
  (`domains`: N, D and BHSA's undecided ?), independent ones only (`rela` NA): a subordinate clause
  belongs to the clause it hangs on.
- **Main line and background.** A wayyiqtol clause (`main_types`: Way0, WayX) is the main line;
  every other independent narrator clause (x-qatal, nominal, participle …) background.
- **Pauses.** In the narrative books (`books`), a run of at least `min_run` background clauses
  inside the chain: a main-line clause just before it and just after it in the narrator's stream
  through the book (quoted speech left out; across paragraph breaks, which in 1 Sam 3:1-3 fall
  between every verse), and at most `max_run` clauses: a longer run is a body of other text (a
  law code, a list, Daniel's Aramaic chapters, which have no wayyiqtol), not a pause. Its clause
  types listed; its paragraph, that of its first clause.
- **The claim, fixed before the first run.** A story sets its scene first: background is more
  common among the first `opening` narrator clauses of a paragraph than among the rest, against
  the clause order shuffled within each paragraph (`shuffles`), one-sided at `alpha`.
- **Known answers.** Pauses the commentaries point to (`known`: a range of verses each; found when
  a pause overlaps it).

Writes `artifacts/mainline/`: `pericopes.parquet` (`unit_id, book_id, first_vid, last_vid, main,
background, share` = main / (main + background)), `pauses.parquet` (`pause_id, unit_id, book_id,
first_vid, last_vid, n_clauses, types` JSON, `known`), `books.parquet` (`book_id, main,
background, share, pauses`), `clauses.parquet` (`clause, verse_id, words, role` main |
background: for the reader) and `mainline.meta.json`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.stats import empirical_p
from bsim.config import config_hash, resolve_path, write_meta
from bsim.data.canon import BY_OSIS
from bsim.data.refs import RefIndex

Log = Callable[[str], None]


def narrator_clauses(clauses: pd.DataFrame, mc: dict[str, Any]) -> pd.DataFrame:
    """The independent narrator clauses in text order, each `main` (wayyiqtol) or not."""
    c = clauses[
        ~clauses.speech.astype(bool)
        & clauses.domain.isin(mc["domains"])
        & clauses.rela.isin(mc["independent"])
    ].copy()
    c["main"] = c.typ.isin(mc["main_types"])
    return c.sort_values("clause").reset_index(drop=True)


def runs(flags: np.ndarray, min_run: int, inside: bool = False) -> list[tuple[int, int]]:
    """(first, last) indexes of the runs of True at least `min_run` long; with `inside`, only
    those with a False just before and just after (inside the chain)."""
    out, start = [], None
    for i, f in enumerate([*flags.tolist(), None]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            if i - start >= min_run and (not inside or (f is False and start > 0)):
                out.append((start, i - 1))
            start = None
    return out


def opening_excess(bg: np.ndarray, groups: list[np.ndarray], opening: int) -> float:
    """Background share among the first `opening` clauses of each group, less the share among
    the rest (groups of fewer than `opening` + 1 clauses left out)."""
    first = rest = n_first = n_rest = 0
    for idx in groups:
        if len(idx) <= opening:
            continue
        b = bg[idx]
        first += int(b[:opening].sum())
        rest += int(b[opening:].sum())
        n_first += opening
        n_rest += len(idx) - opening
    if not n_first or not n_rest:
        return 0.0
    return first / n_first - rest / n_rest


def run_mainline(cfg: dict[str, Any], log: Log = print) -> Path:
    mc = cfg["mainline"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "mainline"
    t0 = time.perf_counter()
    path = proc / "syntax_clauses.parquet"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim syntax` first")
    clauses = pd.read_parquet(path)
    verses = pd.read_parquet(proc / "verses.parquet")
    units = pd.read_parquet(proc / "units.parquet")
    peri = units[units.unit_type == "pericope"].sort_values("start_verse_id").reset_index(drop=True)
    book_of = dict(zip(verses.verse_id, verses.book_id, strict=True))

    c = narrator_clauses(clauses, mc)
    # each clause's paragraph: the pericope whose span holds its verse
    starts = peri.start_verse_id.to_numpy()
    k = np.searchsorted(starts, c.verse_id.to_numpy(), side="right") - 1
    c["unit_id"] = peri.unit_id.to_numpy()[np.clip(k, 0, len(peri) - 1)]
    c = c[k >= 0].reset_index(drop=True)
    c["book_id"] = c.verse_id.map(book_of)
    bg = (~c.main).to_numpy()
    groups = [idx.to_numpy() for _, idx in c.groupby("unit_id", sort=False).groups.items()]
    log(f"{len(c)} narrator clauses ({int(c.main.sum())} main line) in {len(groups)} paragraphs")

    # pauses: background runs inside the chain, in the narrator's stream through each narrative book
    narrative = {BY_OSIS[o].book_id for o in mc["books"]}
    rows = []
    for _, idx in c[c.book_id.isin(narrative)].groupby("book_id", sort=True).groups.items():
        idx = idx.to_numpy()
        for a, b in runs(bg[idx], mc["min_run"], inside=True):
            if b - a + 1 > mc["max_run"]:
                continue  # a law, a list, an Aramaic chapter: a body of other text, not a pause
            seg = c.iloc[idx[a : b + 1]]
            rows.append((seg.unit_id.iloc[0], int(seg.book_id.iloc[0]), int(seg.verse_id.min()),
                         int(seg.verse_id.max()), int(len(seg)),
                         json.dumps(seg.typ.tolist())))  # fmt: skip
    pauses = pd.DataFrame(
        rows, columns=["unit_id", "book_id", "first_vid", "last_vid", "n_clauses", "types"]
    )
    pauses = pauses.sort_values(["n_clauses", "first_vid"], ascending=[False, True], kind="stable")
    pauses = pauses.reset_index(drop=True)
    pauses.insert(0, "pause_id", np.arange(1, len(pauses) + 1))

    # the claim: background first, against the order shuffled within paragraphs
    observed = opening_excess(bg, groups, mc["opening"])
    rng = np.random.default_rng(mc["seed"])
    null = np.empty(mc["shuffles"])
    for s in range(mc["shuffles"]):
        shuffled = bg.copy()
        for idx in groups:
            shuffled[idx] = rng.permutation(bg[idx])
        null[s] = opening_excess(shuffled, groups, mc["opening"])
    p = empirical_p(observed, null)
    claim = {
        "excess": round(observed, 4),
        "null_mean": round(float(null.mean()), 4),
        "p": p,
        "holds": bool(observed > null.mean() and p <= mc["alpha"]),
        "paragraphs": int(sum(len(i) > mc["opening"] for i in groups)),
    }
    log(f"background first: {observed:+.3f} against {null.mean():+.3f} by chance, p {p:.4g}")

    # known answers
    index = RefIndex(verses)
    known, known_ids = [], set()
    for ref in mc["known"]:
        lo, hi = index.resolve(ref)
        hit = pauses[(pauses.first_vid <= hi) & (pauses.last_vid >= lo)]
        known.append({"ref": ref, "found": not hit.empty,
                      "pause": int(hit.pause_id.iloc[0]) if not hit.empty else None})  # fmt: skip
        known_ids |= set(hit.pause_id)
    pauses["known"] = pauses.pause_id.isin(known_ids)
    n_found = sum(k["found"] for k in known)
    log(f"known: {n_found} of {len(known)} found")

    def shares(g: pd.DataFrame) -> pd.Series:
        m, b = int(g.main.sum()), int((~g.main).sum())
        return pd.Series({"main": m, "background": b, "share": m / (m + b) if m + b else None})

    per = c.groupby("unit_id", sort=False).apply(shares, include_groups=False).reset_index()
    per = per.merge(peri[["unit_id", "book_id", "start_verse_id", "end_verse_id"]], on="unit_id")
    per = per.rename(columns={"start_verse_id": "first_vid", "end_verse_id": "last_vid"})
    per = per[["unit_id", "book_id", "first_vid", "last_vid", "main", "background", "share"]]
    books = c.groupby("book_id").apply(shares, include_groups=False).reset_index()
    books["pauses"] = books.book_id.map(pauses.groupby("book_id").size()).fillna(0).astype(int)
    words = clauses.set_index("clause").words
    reader = c[["clause", "verse_id"]].assign(
        words=c.clause.map(words).map(lambda w: json.dumps([int(x) for x in w])),
        role=np.where(c.main, "main", "background"),
    )

    out.mkdir(parents=True, exist_ok=True)
    per.to_parquet(out / "pericopes.parquet", index=False)
    pauses.to_parquet(out / "pauses.parquet", index=False)
    books.to_parquet(out / "books.parquet", index=False)
    reader.to_parquet(out / "clauses.parquet", index=False)
    meta = {
        "config_hash": config_hash(cfg, "mainline"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "clauses": int(len(c)),
        "main": int(c.main.sum()),
        "background": int(bg.sum()),
        "pauses": int(len(pauses)),
        "min_run": mc["min_run"],
        "opening": mc["opening"],
        "claim": claim,
        "shuffles": int(mc["shuffles"]),
        "alpha": mc["alpha"],
        "known": known,
        "known_found": n_found,
        "known_holds": n_found >= mc["known_share"] * len(known),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    write_meta(out / "mainline.meta.json", meta)
    log(f"done: {len(pauses)} pauses ({meta['seconds']} s) -> {out}")
    return out / "pauses.parquet"
