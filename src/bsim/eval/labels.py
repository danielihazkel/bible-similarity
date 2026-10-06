"""Your labels as a third gold set (DESIGN.md §16.25).

Sefaria's links follow the commentary tradition and OpenBible's the Treasury of Scripture
Knowledge; both favour famous connections (§8.4). Pairs you judge in the viewer (`real`, `not`,
`unsure`, `store/labels.py`) are a third set, and the only one with *negatives*: pairs a system
proposed that are not connections. Two readings:

- **separation** (`separation`): over the labelled pairs of a unit type, how well each mode's
  ranks tell `real` from `not` — the share of each found within `labels.k` (either unit ranks the
  other), the precision of what it finds, and the AUC of the reciprocal rank (a pair outside the
  list scores 0). Served live by `/api/labels/eval` from the DB's lists;
- **retrieval** (`bsim eval-labels`): the `real` verse pairs of the `labels.split` split (the
  Sefaria split rule of the two books, as for OpenBible) as gold for the final verse systems, with
  the usual metrics, side by side with separation over the same split; plus how many of your
  `real` pairs Sefaria or OpenBible already have.

Labels are judged on what the viewer showed, mostly the top of one mode's lists: the numbers
describe that sample, not the canon. Nothing is tuned on them. Writes
`artifacts/eval/labels.json` + `labels.md`.
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.eval.metrics import evaluate_system, metric_names
from bsim.store.labels import read_labels

Log = Callable[[str], None]
Pair = tuple[str, str]


def separation(
    ranks: Mapping[Pair, int | None],
    labels: Mapping[Pair, str],
    k: int,
    min_pairs: int,
) -> dict[str, Any]:
    """How a mode's ranks (`None` = not in either list) separate `real` from `not` pairs."""
    real = [ranks.get(p) for p, lab in labels.items() if lab == "real"]
    nots = [ranks.get(p) for p, lab in labels.items() if lab == "not"]
    found_real = sum(r is not None and r <= k for r in real)
    found_not = sum(r is not None and r <= k for r in nots)
    auc = None
    if len(real) >= min_pairs and len(nots) >= min_pairs:
        from sklearn.metrics import roc_auc_score

        score = [0.0 if r is None else 1.0 / r for r in real + nots]
        auc = round(float(roc_auc_score([1] * len(real) + [0] * len(nots), score)), 4)
    return {
        "n_real": len(real),
        "n_not": len(nots),
        "found_real": found_real,
        "found_not": found_not,
        "recall": round(found_real / len(real), 4) if real else None,
        "precision": round(found_real / (found_real + found_not), 4)
        if found_real + found_not
        else None,
        "auc": auc,
    }


def db_ranks(
    conn: sqlite3.Connection, unit_type: str, pairs: Iterable[Pair]
) -> dict[str, dict[Pair, int]]:
    """mode -> pair -> best rank of either unit in the other's stored list (pairs not listed are
    left out)."""
    pairs = list(pairs)
    ids = sorted({i for p in pairs for i in p})
    wanted = set(pairs)
    out: dict[str, dict[Pair, int]] = {}
    for mode in (
        m
        for (m,) in conn.execute(
            "SELECT DISTINCT mode FROM matches WHERE unit_type = ?", (unit_type,)
        )
    ):
        out[mode] = {}
    for i in range(0, len(ids), 500):
        chunk = ids[i : i + 500]
        rows = conn.execute(
            f"SELECT mode, src_id, tgt_id, rank FROM matches WHERE unit_type = ?"
            f" AND src_id IN ({', '.join('?' * len(chunk))})",
            (unit_type, *chunk),
        )
        for mode, s, t, r in rows:
            p = (s, t) if (s, t) in wanted else (t, s)
            if p in wanted:
                best = out[mode].get(p)
                out[mode][p] = r if best is None else min(best, r)
    return out


def live_eval(
    conn: sqlite3.Connection, labels: list[dict[str, Any]], k: int, min_pairs: int
) -> list[dict[str, Any]]:
    """Separation per unit type and mode over every label (`/api/labels/eval`)."""
    out = []
    for unit_type in sorted({lab["unit_type"] for lab in labels}):
        of_type = {
            (lab["a_id"], lab["b_id"]): lab["label"]
            for lab in labels
            if lab["unit_type"] == unit_type
        }
        for mode, ranks in db_ranks(conn, unit_type, of_type).items():
            out.append(
                {"unit_type": unit_type, "mode": mode, **separation(ranks, of_type, k, min_pairs)}
            )
    return out


def verse_labels(
    labels: list[dict[str, Any]], book: Any, split_of_book: Mapping[int, str]
) -> pd.DataFrame:
    """Verse-unit labels as `a, b, label, split` (verse ids; the Sefaria split rule)."""
    rows = []
    for lab in labels:
        if lab["unit_type"] != "verse":
            continue
        a, b = int(lab["a_id"].removeprefix("v:")), int(lab["b_id"].removeprefix("v:"))
        sa, sb = split_of_book[int(book[a])], split_of_book[int(book[b])]
        split = "test" if "test" in (sa, sb) else "dev" if "dev" in (sa, sb) else "train"
        rows.append((a, b, lab["label"], split))
    return pd.DataFrame(rows, columns=["a", "b", "label", "split"])


def ranks_from_lists(ranked: Mapping[int, list[int]], pairs: Iterable[tuple[int, int]]) -> dict:
    """pair -> best rank of either verse in the other's list (1-based)."""
    out = {}
    for a, b in pairs:
        r = [lst.index(t) + 1 for s, t in ((a, b), (b, a)) if t in (lst := ranked.get(s, []))]
        if r:
            out[(a, b)] = min(r)
    return out


def run_eval_labels(cfg: dict[str, Any], log: Log = print) -> dict[str, Any]:
    from bsim.data.canon import BOOKS
    from bsim.eval.openbible import gold_of, overlap
    from bsim.eval.report import EvalContext, ranked_lists
    from bsim.retrieve.fusion import final_systems

    t0 = time.perf_counter()
    lc, ev = cfg["labels"], cfg["eval"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    path = resolve_path(cfg, "labels")
    labels = read_labels(path)
    if not labels:
        raise RuntimeError(f"no labels in {path}; judge some pairs in the viewer first")
    split = lc["split"]
    splits = json.loads((proc / "splits.json").read_text("utf-8"))
    split_of_book = {b.book_id: splits["books"][b.sefaria] for b in BOOKS}
    ctx = EvalContext.load(cfg, split)
    vl = verse_labels(labels, ctx.book_id, split_of_book)
    counts = {
        s: {
            lab: int(((vl.split == s) & (vl.label == lab)).sum())
            for lab in ("real", "not", "unsure")
        }
        for s in ("train", "dev", "test")
    }
    log(f"{len(labels)} labels, {len(vl)} of verse pairs; {split}: {counts[split]}")
    sel = vl[vl.split == split]
    gold: dict[int, set[int]] = {}
    for a, b in zip(sel.a[sel.label == "real"], sel.b[sel.label == "real"], strict=True):
        gold.setdefault(int(a), set()).add(int(b))
        gold.setdefault(int(b), set()).add(int(a))
    judged = {(int(a), int(b)): lab for a, b, lab in zip(sel.a, sel.b, sel.label, strict=True)}

    results: dict[str, dict[str, Any]] = {}
    for mode, system in final_systems(cfg, "verse").items():
        f = art / "topk" / "verse" / f"{system}.parquet"
        if not f.exists():
            log(f"skip {mode}: {f} missing")
            continue
        ranked = ranked_lists(ctx.filter("verse", ctx.read(f, "verse")))
        results[mode] = {
            "system": system,
            "retrieval": evaluate_system(ranked, gold, ev["ks"], ev["rank_k"]) if gold else None,
            "separation": separation(
                ranks_from_lists(ranked, judged), judged, lc["k"], lc["min_pairs"]
            ),
        }
        s = results[mode]["separation"]
        log(
            f"{mode} ({system}): finds {s['found_real']}/{s['n_real']} real,"
            f" {s['found_not']}/{s['n_not']} not; AUC {s['auc']}"
        )

    sefaria = ctx.gold("verse")
    ob_path = proc / "openbible_links.parquet"
    openbible = gold_of(pd.read_parquet(ob_path), split) if ob_path.exists() else None
    n_real = sum(map(len, gold.values()))
    out = {
        "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "config_hash": config_hash(cfg, "labels", "retrieval", "eval", "final_systems"),
        "split": split,
        "labels": len(labels),
        "counts": counts,
        "gold": {
            "real_pairs": n_real // 2,
            "also_sefaria": overlap(gold, sefaria) // 2,
            "also_openbible": None if openbible is None else overlap(gold, openbible) // 2,
        },
        "results": results,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (art / "eval").mkdir(parents=True, exist_ok=True)
    (art / "eval" / "labels.json").write_text(json.dumps(out, indent=2) + "\n", "utf-8")
    (art / "eval" / "labels.md").write_text(report(out, ev), "utf-8")
    return out


def report(out: dict[str, Any], ev: dict[str, Any]) -> str:
    g, c = out["gold"], out["counts"][out["split"]]
    names = metric_names(ev["ks"], ev["rank_k"])
    lines = [
        f"# Your labels as a gold set ({out['split']} split)",
        "",
        f"{out['labels']} labels; verse pairs in {out['split']}: {c['real']} real, {c['not']} not,"
        f" {c['unsure']} unsure. Of the real pairs, {g['also_sefaria']} are Sefaria links"
        + ("" if g["also_openbible"] is None else f" and {g['also_openbible']} OpenBible ones")
        + ".",
        "",
        "## Separation of real from not",
        "",
        "| mode | system | real found | not found | precision | AUC |",
        "|---|---|---|---|---|---|",
    ]
    for mode, r in out["results"].items():
        s = r["separation"]
        lines.append(
            f"| {mode} | {r['system']} | {s['found_real']}/{s['n_real']}"
            f" | {s['found_not']}/{s['n_not']} | {s['precision']} | {s['auc']} |"
        )
    lines += ["", "## Retrieval of the real pairs", "", "| mode | " + " | ".join(names) + " |"]
    lines.append("|" + "---|" * (1 + len(names)))
    for mode, r in out["results"].items():
        if r["retrieval"]:
            lines.append(
                f"| {mode} | " + " | ".join(f"{r['retrieval'][n]:.3f}" for n in names) + " |"
            )
    return "\n".join(lines) + "\n"
