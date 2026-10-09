"""`bsim eval-etcbc`: ETCBC's parallel passages as a third gold set (DESIGN.md §16.34).

The ETCBC *parallels* notebook (Dirk Roorda, Martijn Naaijer; Text-Fabric, CC BY-NC like the
BHSA) links verses whose text is nearly the same — the `crossref` edge feature between BHSA verse
nodes, each with its similarity in percent (≥ 75). Unlike Sefaria's links (the commentary
tradition) or OpenBible's (crowd votes, mostly thematic), it is a string-similarity gold: the
synoptic parallels and the repeated passages. It is only used to evaluate, nothing is tuned on it.

- **Pairs:** every edge mapped to verse ids by book, chapter and verse (`data.bhsa.BOOKS`; the
  verse grids agree, a BHSA verse without a verse id is counted and dropped), undirected,
  neighbours (±`retrieval.neighbor_window`) dropped, split by the Sefaria book rule (test if
  either book is a test book, else dev if either is dev); only dev is scored for retrieval.
- **Parallels, not formulas:** a verse repeated many times is a formula (וידבר יהוה אל משה
  לאמר has 157 partners) or a list item (the offerings of Num 7), not a parallel, and such
  cliques make up most edges. A pair is a *parallel* when both verses have at most
  `etcbc.max_partners` partners; only those are the gold, the others are counted.
- **Retrieval** (dev): the final verse systems against this gold and, side by side, Sefaria's;
  recall@10 of the fused list per similarity band (`etcbc.bands`).
- **Parallels** (all pairs; the pattern analyses are not tuned on any split): the share of ETCBC
  pairs inside a strong sequence (§16.7, q ≤ `etcbc.max_q`), sharing a phrase (§16.1) or in the
  fused top 10 either way; and the share of strong sequences' verse pairs that ETCBC lists.
- **Overlap** of the dev gold with Sefaria's and OpenBible's.

Writes `data/processed/etcbc_links.parquet` (`src_vid, tgt_vid, similarity, split`, both
directions, parallels only) and `artifacts/eval/etcbc.json` + `etcbc.md`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.data.bhsa import BOOKS as BHSA_BOOKS
from bsim.data.bhsa import _nodes, load_bhsa
from bsim.data.canon import BOOKS
from bsim.eval.metrics import evaluate_system
from bsim.eval.openbible import gold_of, overlap
from bsim.eval.report import EvalContext, ranked_lists
from bsim.retrieve.fusion import final_systems

Log = Callable[[str], None]


def read_edges(path: Path) -> list[tuple[int, int, int]]:
    """(from, to, value) of a Text-Fabric edge feature with values (`@edgeValues`)."""
    lines = path.read_text("utf-8").split("\n")
    i = next(k for k, line in enumerate(lines) if not line.startswith("@")) + 1
    out: list[tuple[int, int, int]] = []
    node = 0
    for line in lines[i:]:
        if not line:
            continue
        f = line.split("\t")
        if len(f) == 3:
            sources, targets, value = _nodes(f[0]), f[1], f[2]
        else:  # the source is implicit: the node after the previous one
            sources, targets, value = [node + 1], f[0], f[1]
        for s in sources:
            out.extend((s, t, int(value)) for t in _nodes(targets))
        node = sources[-1]
    return out


def verse_ids(raw_bhsa: Path, verses: pd.DataFrame) -> tuple[dict[int, int], int]:
    """BHSA verse node -> verse id, and how many BHSA verses have none."""
    otype, F = load_bhsa(raw_bhsa, ("book", "chapter", "verse"))
    of_osis: dict[str, int] = {}
    for vid, refs in zip(verses.verse_id, verses.oshb_osis, strict=True):
        for r in refs:
            of_osis.setdefault(r, int(vid))
    out, missing = {}, 0
    v0, v1 = otype["verse"]
    for v in range(v0, v1 + 1):
        vid = of_osis.get(f"{BHSA_BOOKS[F['book'][v]]}.{F['chapter'][v]}.{F['verse'][v]}")
        if vid is None:
            missing += 1
        else:
            out[v] = vid
    return out, missing


def gold_links(
    edges: list[tuple[int, int, int]],
    vid_of: dict[int, int],
    book_of: dict[int, int],
    split_of_book: dict[int, str],
    window: int,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Undirected verse pairs (both directions in the frame), neighbours dropped, split by the
    Sefaria rule; the best similarity of the pair's edges."""
    best: dict[tuple[int, int], int] = {}
    unmapped = neighbours = 0
    for s, t, val in edges:
        a, b = vid_of.get(s), vid_of.get(t)
        if a is None or b is None:
            unmapped += 1
            continue
        if a == b or (book_of[a] == book_of[b] and abs(a - b) <= window):
            neighbours += 1
            continue
        key = (min(a, b), max(a, b))
        best[key] = max(best.get(key, 0), val)
    rows = []
    for (a, b), val in best.items():
        sa, sb = split_of_book[book_of[a]], split_of_book[book_of[b]]
        split = "test" if "test" in (sa, sb) else "dev" if "dev" in (sa, sb) else "train"
        rows += [(a, b, val, split), (b, a, val, split)]
    links = pd.DataFrame(rows, columns=["src_vid", "tgt_vid", "similarity", "split"])
    return links, {
        "edges": len(edges),
        "unmapped": unmapped,
        "neighbours": neighbours,
        "pairs": len(best),
    }


def parallels_only(links: pd.DataFrame, max_partners: int) -> pd.DataFrame:
    """The pairs whose two verses each have at most `max_partners` partners."""
    deg = links.groupby("src_vid").tgt_vid.nunique()
    keep = (links.src_vid.map(deg) <= max_partners) & (links.tgt_vid.map(deg) <= max_partners)
    return links[keep].reset_index(drop=True)


def coverage(pairs: set[tuple[int, int]], art: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    """Shares of the ETCBC pairs found by the pattern analyses, and of the strong sequences'
    pairs that ETCBC lists."""
    ec = cfg["etcbc"]
    out: dict[str, Any] = {"pairs": len(pairs)}
    seq_path = art / "sequences" / "verse.parquet"
    if seq_path.exists():
        seq = pd.read_parquet(seq_path, columns=["q", "pairs"])
        strong = {
            (min(a, b), max(a, b))
            for ps in seq.loc[seq.q <= ec["max_q"], "pairs"]
            for a, b, *_ in json.loads(ps)
        }
        out["in_sequence"] = _share(pairs, strong)
        out["sequence_pairs"] = len(strong)
        out["sequence_pairs_in_etcbc"] = _share(strong, pairs)
    phr_path = art / "phrases" / "verse.parquet"
    if phr_path.exists():
        ph = pd.read_parquet(phr_path, columns=["a", "b"])
        out["in_phrase"] = _share(
            pairs, {(min(a, b), max(a, b)) for a, b in zip(ph.a, ph.b, strict=True)}
        )
    fused = art / "topk" / "verse" / f"{cfg['final_systems']['fused']}.parquet"
    if fused.exists():
        f = pd.read_parquet(fused, columns=["src_id", "tgt_id", "rank"])
        f = f[f["rank"] <= 10]
        top = {
            (min(a, b), max(a, b))
            for a, b in zip(f.src_id.str[2:].astype(int), f.tgt_id.str[2:].astype(int), strict=True)
        }
        out["in_fused_top10"] = _share(pairs, top)
    return out


def _share(a: set[tuple[int, int]], b: set[tuple[int, int]]) -> float | None:
    return round(len(a & b) / len(a), 4) if a else None


def run_eval_etcbc(cfg: dict[str, Any], log: Log = print) -> dict[str, Any]:
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    raw = resolve_path(cfg, "data_raw")
    t0 = time.perf_counter()
    path = raw / "etcbc_parallels" / cfg["sources"]["etcbc_parallels"]["files"][0]
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim download --only parallels` first")
    if not (raw / "bhsa" / "otype.tf").exists():
        raise RuntimeError("BHSA files missing; run `bsim download --only syntax` first")
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "oshb_osis"])
    vid_of, missing = verse_ids(raw / "bhsa", verses)
    splits = json.loads((proc / "splits.json").read_text("utf-8"))
    split_of_book = {b.book_id: splits["books"][b.sefaria] for b in BOOKS}
    book_of = dict(zip(verses.verse_id.astype(int), verses.book_id.astype(int), strict=True))
    links, stats = gold_links(
        read_edges(path), vid_of, book_of, split_of_book, cfg["retrieval"]["neighbor_window"]
    )
    stats["bhsa_verses_unmapped"] = missing
    links = parallels_only(links, cfg["etcbc"]["max_partners"])
    stats["parallels"] = len(links) // 2
    stats["formula_pairs"] = stats["pairs"] - stats["parallels"]
    links.to_parquet(proc / "etcbc_links.parquet")
    log(
        f"{stats['edges']} ETCBC edges -> {stats['pairs']} verse pairs, {stats['parallels']}"
        f" parallels ({stats['formula_pairs']} in formulas and lists)"
    )

    split = "dev"
    ctx = EvalContext.load(cfg, split)
    et_gold, sef_gold = gold_of(links, split), ctx.gold("verse")
    ob_path = proc / "openbible_links.parquet"
    ob_gold = gold_of(pd.read_parquet(ob_path), split) if ob_path.exists() else {}
    ev = cfg["eval"]
    dev = links[links.split == split]
    sim_of = dict(zip(zip(dev.src_vid, dev.tgt_vid, strict=True), dev.similarity, strict=True))
    results: dict[str, dict[str, Any]] = {}
    bands: dict[str, Any] = {}
    for mode, system in final_systems(cfg, "verse").items():
        f = art / "topk" / "verse" / f"{system}.parquet"
        if not f.exists():
            raise RuntimeError(f"{f} missing; run the pipeline up to `bsim fuse` first")
        ranked = ranked_lists(ctx.filter("verse", ctx.read(f, "verse")))
        results[mode] = {
            "system": system,
            "etcbc": evaluate_system(ranked, et_gold, ev["ks"], ev["rank_k"]),
            "sefaria": evaluate_system(ranked, sef_gold, ev["ks"], ev["rank_k"]),
        }
        if mode == "fused":
            top10 = {q: set(list(r)[:10]) for q, r in ranked.items()}
            for lo, hi in cfg["etcbc"]["bands"]:
                band = [(q, t) for (q, t), s in sim_of.items() if lo <= s <= hi]
                hits = sum(t in top10.get(q, set()) for q, t in band)
                bands[f"{lo}-{hi}"] = {
                    "pairs": len(band),
                    "recall@10": round(hits / len(band), 4) if band else None,
                }
        e, s = results[mode]["etcbc"], results[mode]["sefaria"]
        key = f"ndcg@{ev['rank_k']}"
        log(f"{mode} ({system}): {key} ETCBC {e[key]:.3f} · Sefaria {s[key]:.3f}")
    n_et = sum(map(len, et_gold.values()))
    all_pairs = {(min(a, b), max(a, b)) for a, b in zip(links.src_vid, links.tgt_vid, strict=True)}
    out = {
        "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "config_hash": config_hash(cfg, "etcbc", "retrieval", "eval", "final_systems"),
        "split": split,
        "max_partners": cfg["etcbc"]["max_partners"],
        "stats": stats,
        "gold": {
            "etcbc_dev_pairs": n_et,
            "etcbc_dev_queries": len(et_gold),
            "sefaria_dev_pairs": sum(map(len, sef_gold.values())),
            "shared_sefaria": overlap(et_gold, sef_gold),
            "etcbc_also_in_sefaria": round(overlap(et_gold, sef_gold) / n_et, 4) if n_et else None,
            "etcbc_also_in_openbible": round(overlap(et_gold, ob_gold) / n_et, 4)
            if n_et and ob_gold
            else None,
        },
        "results": results,
        "bands": bands,
        "coverage": coverage(all_pairs, art, cfg),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (art / "eval").mkdir(parents=True, exist_ok=True)
    (art / "eval" / "etcbc.json").write_text(json.dumps(out, indent=2) + "\n", "utf-8")
    (art / "eval" / "etcbc.md").write_text(report(out, ev), "utf-8")
    c = out["coverage"]
    log(
        f"done: {len(et_gold)} dev queries, {n_et} pairs; all {c['pairs']} pairs: sequence"
        f" {c.get('in_sequence')}, phrase {c.get('in_phrase')}, fused top 10"
        f" {c.get('in_fused_top10')} ({out['seconds']} s)"
    )
    return out


def report(out: dict[str, Any], ev: dict[str, Any]) -> str:
    g, c = out["gold"], out["coverage"]
    names = [f"recall@{k}" for k in ev["ks"]] + [f"mrr@{ev['rank_k']}", f"ndcg@{ev['rank_k']}"]
    lines = [
        "# ETCBC parallel passages as a third gold set (dev split)",
        "",
        f"ETCBC dev gold: {g['etcbc_dev_pairs']} directed pairs over {g['etcbc_dev_queries']}"
        f" query verses; also Sefaria links: {g['etcbc_also_in_sefaria']}, also OpenBible:"
        f" {g['etcbc_also_in_openbible']}.",
        "",
        "| mode | system | gold | " + " | ".join(names) + " |",
        "|" + "---|" * (3 + len(names)),
    ]
    for mode, r in out["results"].items():
        for gold in ("etcbc", "sefaria"):
            cells = " | ".join(f"{r[gold][n]:.3f}" for n in names)
            lines.append(f"| {mode} | {r['system']} | {gold} | {cells} |")
    lines += ["", "Fused recall@10 by similarity band: " + ", ".join(
        f"{b} {v['recall@10']} ({v['pairs']})" for b, v in out["bands"].items())]  # fmt: skip
    lines += [
        "",
        f"All {c['pairs']} pairs: in a strong sequence {c.get('in_sequence')}, sharing a phrase"
        f" {c.get('in_phrase')}, in the fused top 10 {c.get('in_fused_top10')}; strong sequence"
        f" pairs listed by ETCBC {c.get('sequence_pairs_in_etcbc')} of {c.get('sequence_pairs')}.",
    ]
    return "\n".join(lines) + "\n"
