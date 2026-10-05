"""`bsim eval-openbible`: a second, independent gold set (DESIGN.md §16.13).

Sefaria's links are the training and evaluation gold, and they reflect the connections the
commentary tradition made famous (§8.4). OpenBible.info's cross-references (CC-BY; crowd-voted,
derived from the Treasury of Scripture Knowledge) are an independent set: they are only used to
*evaluate* — on the dev split, never on test, and nothing is tuned on them.

- Only Hebrew Bible ↔ Hebrew Bible references with at least `min_votes` votes. A target range
  expands to its verses (at most `max_range`).
- OpenBible uses English (KJV) versification. Where it differs from the Hebrew (MAM) numbering
  — Psalm titles, and the chapters listed in `unsafe_chapters` (Gen 31–32, Exod 7–8, Joel 2–3,
  Mal 3–4, …) — references are dropped rather than renumbered; so is any reference to a verse the
  Hebrew chapter does not have.
- Pairs are undirected, neighbours (±`retrieval.neighbor_window` in a book) are dropped (the
  systems never return them), and each pair gets the Sefaria split rule of its two books: test if
  either is a test book, else dev if either is a dev book, else train. Only dev is scored.

The final verse systems (`final_systems`) are scored with the usual metrics against this gold and,
side by side, against the Sefaria dev gold; the overlap of the two gold sets is reported.

Writes `data/processed/openbible_links.parquet` (`src_vid, tgt_vid, votes, split`, both directions)
and `artifacts/eval/openbible.json` + `openbible.md`.
"""

from __future__ import annotations

import io
import json
import time
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.data.canon import BY_OSIS
from bsim.eval.metrics import evaluate_system
from bsim.eval.report import EvalContext, ranked_lists
from bsim.retrieve.fusion import final_systems

Log = Callable[[str], None]


def fetch(cfg: dict[str, Any], log: Log) -> Path:
    """The cross-reference file under `paths.data_raw/openbible/`, downloaded once."""
    import requests

    ob = cfg["openbible"]
    raw = resolve_path(cfg, "data_raw") / "openbible"
    path = raw / ob["file"]
    if path.exists():
        return path
    log(f"downloading {ob['url']}")
    r = requests.get(ob["url"], timeout=120)
    r.raise_for_status()
    raw.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        z.extract(ob["file"], raw)
    return path


def read_refs(path: Path) -> pd.DataFrame:
    """`frm, to, votes` rows (the header line carries a licence note in a fourth column)."""
    refs = pd.read_csv(
        path,
        sep="\t",
        skiprows=1,
        header=None,
        usecols=[0, 1, 2],
        names=["frm", "to", "votes"],
        index_col=False,
        dtype={"frm": str, "to": str, "votes": "Int64"},
    )
    return refs.dropna().astype({"votes": int})


def parse_ref(ref: str) -> tuple[str, int, int] | None:
    """`Gen.1.1` -> ("Gen", 1, 1); None for anything else."""
    parts = ref.split(".")
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        return None
    return parts[0], int(parts[1]), int(parts[2])


def unsafe(osis: str, chapter: int, unsafe_chapters: dict[str, list[int] | str]) -> bool:
    rule = unsafe_chapters.get(osis)
    return rule == "all" or (isinstance(rule, list) and chapter in rule)


def resolve(
    ref: str,
    verse_of: dict[tuple[str, int, int], int],
    unsafe_chapters: dict[str, Any],
    max_range: int,
) -> list[int] | None:
    """Verse ids of a reference or range (`A-B`), or None (not Hebrew Bible, versification-unsafe,
    unknown verse, or too long)."""
    ends = ref.split("-")
    if len(ends) > 2:
        return None
    parsed = [parse_ref(e) for e in ends]
    if any(p is None for p in parsed):
        return None
    ids = []
    for osis, ch, v in parsed:  # type: ignore[misc]
        if osis not in BY_OSIS or unsafe(osis, ch, unsafe_chapters):
            return None
        vid = verse_of.get((osis, ch, v))
        if vid is None:
            return None
        ids.append(vid)
    lo, hi = ids[0], ids[-1]
    if hi < lo or hi - lo + 1 > max_range:
        return None
    return list(range(lo, hi + 1))


def gold_links(
    refs: pd.DataFrame,
    verses: pd.DataFrame,
    split_of_book: dict[int, str],
    cfg: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, int]]:
    """(`src_vid, tgt_vid, votes, split` in both directions, counts of what was dropped)."""
    ob = cfg["openbible"]
    window = cfg["retrieval"]["neighbor_window"]
    verse_of = {}
    for vid, osis in zip(verses.verse_id, verses.osis, strict=True):
        p = parse_ref(osis)
        if p is not None:
            verse_of[p] = int(vid)
    book = verses.book_id.to_numpy()
    kept: dict[tuple[int, int], int] = {}
    stats = {"references": len(refs), "hebrew_bible": 0, "unresolved": 0, "votes": 0}
    for frm, to, votes in zip(refs.frm, refs.to, refs.votes, strict=True):
        a_book = frm.split(".")[0]
        b_book = to.split("-")[0].split(".")[0]
        if a_book not in BY_OSIS or b_book not in BY_OSIS:
            continue
        stats["hebrew_bible"] += 1
        if votes < ob["min_votes"]:
            stats["votes"] += 1
            continue
        src = resolve(frm, verse_of, ob["unsafe_chapters"], 1)
        tgt = resolve(to, verse_of, ob["unsafe_chapters"], ob["max_range"])
        if not src or not tgt:
            stats["unresolved"] += 1
            continue
        for t in tgt:
            a, b = min(src[0], t), max(src[0], t)
            if a == b or (book[a] == book[b] and b - a <= window):
                continue
            kept[(a, b)] = max(kept.get((a, b), votes), votes)
    rows = []
    for (a, b), votes in kept.items():
        sa, sb = split_of_book[int(book[a])], split_of_book[int(book[b])]
        split = "test" if "test" in (sa, sb) else "dev" if "dev" in (sa, sb) else "train"
        rows += [(a, b, votes, split), (b, a, votes, split)]
    df = pd.DataFrame(rows, columns=["src_vid", "tgt_vid", "votes", "split"])
    stats["pairs"] = len(kept)
    return df.sort_values(["src_vid", "tgt_vid"], ignore_index=True), stats


def gold_of(links: pd.DataFrame, split: str) -> dict[int, set[int]]:
    sel = links[links.split == split]
    gold: dict[int, set[int]] = {}
    for s, t in zip(sel.src_vid.to_numpy(), sel.tgt_vid.to_numpy(), strict=True):
        gold.setdefault(int(s), set()).add(int(t))
    return gold


def overlap(a: dict[int, set[int]], b: dict[int, set[int]]) -> int:
    return sum(len(t & b.get(s, set())) for s, t in a.items())


def run_eval_openbible(cfg: dict[str, Any], log: Log = print) -> dict[str, Any]:
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    t0 = time.perf_counter()
    path = fetch(cfg, log)
    refs = read_refs(path)
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "osis"])
    splits = json.loads((proc / "splits.json").read_text("utf-8"))
    from bsim.data.canon import BOOKS

    split_of_book = {b.book_id: splits["books"][b.sefaria] for b in BOOKS}
    links, stats = gold_links(refs, verses.sort_values("verse_id"), split_of_book, cfg)
    links.to_parquet(proc / "openbible_links.parquet")
    log(
        f"{stats['hebrew_bible']} Hebrew Bible references -> {stats['pairs']} verse pairs"
        f" ({stats['votes']} under {cfg['openbible']['min_votes']} votes,"
        f" {stats['unresolved']} versification-unsafe or unresolved)"
    )

    split = "dev"
    ctx = EvalContext.load(cfg, split)
    ob_gold, sef_gold = gold_of(links, split), ctx.gold("verse")
    ev = cfg["eval"]
    results: dict[str, dict[str, Any]] = {}
    for mode, system in final_systems(cfg, "verse").items():
        f = art / "topk" / "verse" / f"{system}.parquet"
        if not f.exists():
            raise RuntimeError(f"{f} missing; run the pipeline up to `bsim fuse` first")
        ranked = ranked_lists(ctx.filter("verse", ctx.read(f, "verse")))
        results[mode] = {
            "system": system,
            "openbible": evaluate_system(ranked, ob_gold, ev["ks"], ev["rank_k"]),
            "sefaria": evaluate_system(ranked, sef_gold, ev["ks"], ev["rank_k"]),
        }
        o, s = results[mode]["openbible"], results[mode]["sefaria"]
        key = f"ndcg@{ev['rank_k']}"
        log(f"{mode} ({system}): {key} OpenBible {o[key]:.3f} · Sefaria {s[key]:.3f}")
    n_ob, n_sef = sum(map(len, ob_gold.values())), sum(map(len, sef_gold.values()))
    both = overlap(ob_gold, sef_gold)
    out = {
        "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "config_hash": config_hash(cfg, "openbible", "retrieval", "eval", "final_systems"),
        "split": split,
        "stats": stats,
        "gold": {
            "openbible_dev_pairs": n_ob,
            "openbible_dev_queries": len(ob_gold),
            "sefaria_dev_pairs": n_sef,
            "shared_pairs": both,
            "openbible_also_in_sefaria": round(both / n_ob, 4) if n_ob else None,
            "sefaria_also_in_openbible": round(both / n_sef, 4) if n_sef else None,
        },
        "results": results,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (art / "eval").mkdir(parents=True, exist_ok=True)
    (art / "eval" / "openbible.json").write_text(json.dumps(out, indent=2) + "\n", "utf-8")
    (art / "eval" / "openbible.md").write_text(report(out, ev), "utf-8")
    log(f"done: {len(ob_gold)} dev queries, {n_ob} pairs ({both} also Sefaria links)")
    return out


def report(out: dict[str, Any], ev: dict[str, Any]) -> str:
    g = out["gold"]
    names = [f"recall@{k}" for k in ev["ks"]] + [f"mrr@{ev['rank_k']}", f"ndcg@{ev['rank_k']}"]
    lines = [
        "# OpenBible cross-references as a second gold set (dev split)",
        "",
        f"OpenBible dev gold: {g['openbible_dev_pairs']} directed pairs over"
        f" {g['openbible_dev_queries']} query verses; Sefaria dev gold: {g['sefaria_dev_pairs']}"
        f" pairs. Shared: {g['shared_pairs']} ({g['openbible_also_in_sefaria']} of OpenBible,"
        f" {g['sefaria_also_in_openbible']} of Sefaria).",
        "",
        "| mode | system | gold | " + " | ".join(names) + " |",
        "|" + "---|" * (3 + len(names)),
    ]
    for mode, r in out["results"].items():
        for gold in ("openbible", "sefaria"):
            m = r[gold]
            cells = " | ".join(f"{m[n]:.3f}" for n in names)
            lines.append(f"| {mode} | {r['system']} | {gold} | {cells} |")
    return "\n".join(lines) + "\n"
