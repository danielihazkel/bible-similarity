"""`bsim place-links`: do places named together lie together? (DESIGN.md §16.61)

Two places are linked when at least `min_together` verses name both (`bsim places`, §16.56), and
the link's strength is Dunning's G² against independence over the verses, as for the names of
§16.11. The claim, fixed in `place_links` before the first run: **link strength falls with
distance**. Spearman's rho between the linked pairs' G² and their great-circle km is set against
`shuffles` runs with the coordinates shuffled among the linked places (who is linked with whom and
how strongly kept, where they lie drawn again), one-sided.

Three variants: every located place (`all`, the test); sure sites alone (`sure`: both places an
OpenBible vote of at least `sure_score`); and without the verses of the text's place and town
lists (`no_lists`), which name neighbours by design. For each, the decay curve: the pairs of
places named in `min_together` verses or more, by distance bin, with the share linked and the
linked pairs' median G².

Leads: pairs at least `far_km` apart, most strongly linked first, the places the text sets
together though they lie far apart. A known answer: "from Dan to Beersheba" (`known`) is among
the `top` leads.

Writes `artifacts/place_links/`: `pairs.parquet` (the linked pairs of `all`: verses together,
each place's verses, expected, G², km, lead rank), `bins.parquet` (per variant and bin) and
`place_links.meta.json` (per variant: places, pairs, rho, the shuffles' mean and 90% range, `p`;
the known answers).
"""

from __future__ import annotations

import itertools
import json
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from bsim.analysis.place_lists import distances
from bsim.analysis.stats import g2_table
from bsim.config import config_hash, resolve_path
from bsim.data.refs import RefIndex

Log = Callable[[str], None]

VARIANTS = ("all", "sure", "no_lists")
CHUNK = 1000  # shuffles ranked at once


def link_pairs(mentions: pd.DataFrame, n_total: int, min_together: int) -> pd.DataFrame:
    """`a, b, n_together, n_a, n_b, expected, g2` for places sharing ≥ `min_together` verses
    more often than independence expects (a < b); `mentions` is (verse_id, place_id)."""
    n_verses = mentions.groupby("place_id").size().to_dict()
    together: Counter[tuple[int, int]] = Counter()
    for ids in mentions.groupby("verse_id").place_id.agg(lambda s: sorted(set(s))):
        together.update(itertools.combinations(ids, 2))
    rows = []
    for (a, b), k in sorted(together.items()):
        expected = n_verses[a] * n_verses[b] / n_total
        if k >= min_together and k > expected:
            rows.append((a, b, k, n_verses[a], n_verses[b], expected,
                         g2_table(k, n_verses[a], n_verses[b], n_total)))  # fmt: skip
    return pd.DataFrame(rows, columns=["a", "b", "n_together", "n_a", "n_b", "expected", "g2"])


def rho_ranks(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Pearson's r of rank vectors: `x` one (n,), `y` one per row (m, n)."""
    xc = x - x.mean()
    yc = y - y.mean(axis=1, keepdims=True)
    return (yc @ xc) / (np.sqrt((yc**2).sum(axis=1)) * np.sqrt((xc**2).sum()))


def decay_test(
    pairs: pd.DataFrame, lat: dict[int, float], lon: dict[int, float], reps: int,
    rng: np.random.Generator,
) -> tuple[dict[str, Any], np.ndarray]:  # fmt: skip
    """Spearman's rho between G² and km against the coordinates shuffled among the places;
    with each pair's km."""
    ids = sorted(set(pairs.a) | set(pairs.b))
    pos = {p: i for i, p in enumerate(ids)}
    d = distances(np.array([lat[p] for p in ids]), np.array([lon[p] for p in ids]))
    ia, ib = pairs.a.map(pos).to_numpy(), pairs.b.map(pos).to_numpy()
    km = d[ia, ib]
    g = rankdata(pairs.g2.to_numpy())
    obs = float(rho_ranks(g, rankdata(km)[None, :])[0])
    null = np.empty(reps)
    for start in range(0, reps, CHUNK):
        m = min(CHUNK, reps - start)
        perm = np.argsort(rng.random((m, len(ids))), axis=1)
        null[start : start + m] = rho_ranks(g, rankdata(d[perm[:, ia], perm[:, ib]], axis=1))
    res = {
        "places": len(ids),
        "pairs": len(pairs),
        "rho": round(obs, 4),
        "null_mean": round(float(null.mean()), 4),
        "null_q05": round(float(np.quantile(null, 0.05)), 4),
        "null_q95": round(float(np.quantile(null, 0.95)), 4),
        "p": float((1 + np.sum(null <= obs)) / (1 + reps)),
        "median_km": round(float(np.median(km)), 1),
    }
    return res, km


def decay_bins(
    pairs: pd.DataFrame, n_verses: pd.Series, lat: dict[int, float], lon: dict[int, float],
    edges: list[float], min_together: int,
) -> list[dict[str, Any]]:  # fmt: skip
    """Every pair of places named in `min_together` verses or more, by km: how many, how many
    linked, the linked pairs' median G²."""
    ids = sorted(n_verses[n_verses >= min_together].index)
    d = distances(np.array([lat[p] for p in ids]), np.array([lon[p] for p in ids]))
    iu = np.triu_indices(len(ids), 1)
    pos = {p: i for i, p in enumerate(ids)}
    g2 = np.full((len(ids), len(ids)), np.nan)
    for a, b, v in zip(pairs.a, pairs.b, pairs.g2, strict=True):
        if a in pos and b in pos:
            g2[pos[a], pos[b]] = g2[pos[b], pos[a]] = v
    km, link = d[iu], g2[iu]
    bounds = [*edges, np.inf]
    out = []
    for i in range(len(edges)):
        sel = (km >= bounds[i]) & (km < bounds[i + 1])
        linked = link[sel & ~np.isnan(link)]
        n = int(sel.sum())
        out.append({
            "bin": i + 1, "lo_km": float(bounds[i]),
            "hi_km": None if np.isinf(bounds[i + 1]) else float(bounds[i + 1]),
            "pairs": n, "linked": len(linked),
            "share": round(len(linked) / n, 5) if n else None,
            "median_g2": round(float(np.median(linked)), 2) if len(linked) else None,
        })  # fmt: skip
    return out


def run_place_links(cfg: dict[str, Any], log: Log = print) -> Path:
    lc = cfg["place_links"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "place_links"
    t0 = time.perf_counter()
    reps, alpha, min_t = int(lc["shuffles"]), float(lc["alpha"]), int(lc["min_together"])
    rng = np.random.default_rng(int(lc["seed"]))

    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter",
                                                               "verse"])  # fmt: skip
    index = RefIndex(verses)
    places = pd.read_parquet(
        art / "places" / "places.parquet",
        columns=["place_id", "he", "lat", "lon", "score", "coord_source"],
    )
    places = places[places.lat.notna()]
    lat = dict(zip(places.place_id, places.lat.astype(float), strict=True))
    lon = dict(zip(places.place_id, places.lon.astype(float), strict=True))
    sure = set(places.place_id[(places.coord_source == "openbible")
                               & (places.score.fillna(-1) >= int(lc["sure_score"]))])  # fmt: skip
    mentions = pd.read_parquet(
        art / "places" / "mentions.parquet", columns=["verse_id", "place_id"]
    )
    mentions = mentions[mentions.place_id.isin(lat)].drop_duplicates()
    in_lists = np.zeros(len(verses), dtype=bool)
    vid = verses.verse_id.to_numpy()
    for ref in lc["lists"]:
        lo, hi = index.resolve(ref)
        in_lists |= (vid >= lo) & (vid <= hi)
    list_vids = set(vid[in_lists])

    scopes = {
        "all": (mentions, len(verses)),
        "sure": (mentions[mentions.place_id.isin(sure)], len(verses)),
        "no_lists": (mentions[~mentions.verse_id.isin(list_vids)], int((~in_lists).sum())),
    }
    tests, bin_rows, main = {}, [], None
    for variant in VARIANTS:
        m, n_total = scopes[variant]
        pairs = link_pairs(m, n_total, min_t)
        if len(pairs) < 3:
            tests[variant] = {"pairs": len(pairs)}
            continue
        res, km = decay_test(pairs, lat, lon, reps, rng)
        tests[variant] = res | {"verses": n_total}
        n_verses = m.groupby("place_id").size()
        for b in decay_bins(pairs, n_verses, lat, lon, [float(e) for e in lc["bins"]], min_t):
            bin_rows.append({"variant": variant} | b)
        if variant == "all":
            main = pairs.assign(km=km.round(1))
        log(f"  {variant}: {res['pairs']} pairs of {res['places']} places, rho {res['rho']}"
            f" (shuffled {res['null_mean']}, p {res['p']})")  # fmt: skip

    # leads: far apart, strongly linked
    known: list[dict[str, Any]] = []
    if main is not None:
        far = main[main.km >= float(lc["far_km"])]
        far = far.sort_values(["g2", "a", "b"], ascending=[False, True, True])
        rank = pd.Series(np.arange(1, len(far) + 1), index=far.index)
        main["lead_rank"] = rank.reindex(main.index).astype("Int64")
        he = dict(zip(places.place_id, places.he, strict=True))
        for ha, hb in lc["known"]:
            hit = main[((main.a.map(he) == ha) & (main.b.map(he) == hb))
                       | ((main.a.map(he) == hb) & (main.b.map(he) == ha))]  # fmt: skip
            row = hit.sort_values("n_together", ascending=False).head(1)
            r = None if row.empty or pd.isna(row.lead_rank.iloc[0]) else int(row.lead_rank.iloc[0])
            known.append({
                "a": ha, "b": hb, "found": not row.empty,
                "a_id": None if row.empty else int(row.a.iloc[0]),
                "b_id": None if row.empty else int(row.b.iloc[0]),
                "km": None if row.empty else float(row.km.iloc[0]),
                "g2": None if row.empty else round(float(row.g2.iloc[0]), 2),
                "rank": r, "holds": r is not None and r <= int(lc["top"]),
            })  # fmt: skip
    else:
        main = pd.DataFrame(columns=["a", "b", "n_together", "n_a", "n_b", "expected", "g2", "km",
                                     "lead_rank"])  # fmt: skip

    out.mkdir(parents=True, exist_ok=True)
    main.round({"expected": 4, "g2": 4}).reset_index(drop=True).to_parquet(out / "pairs.parquet")
    pd.DataFrame(bin_rows, columns=["variant", "bin", "lo_km", "hi_km", "pairs", "linked", "share",
                                    "median_g2"]).to_parquet(out / "bins.parquet")  # fmt: skip
    meta = {
        "config_hash": config_hash(cfg, "place_links"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "shuffles": reps,
        "alpha": alpha,
        "min_together": min_t,
        "sure_score": int(lc["sure_score"]),
        "lists": list(lc["lists"]),
        "far_km": float(lc["far_km"]),
        "leads": int(lc["leads"]),
        "top": int(lc["top"]),
        "tests": tests,
        "known": known,
        "far_pairs": int(main.lead_rank.notna().sum()),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    meta = json.loads(json.dumps(meta, default=lambda x: x.item() if hasattr(x, "item") else x))
    (out / "place_links.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                               "utf-8")  # fmt: skip
    a = tests.get("all") or {}
    log(
        f"done: rho {a.get('rho')} against {a.get('null_mean')} shuffled (p {a.get('p')});"
        f" known leads {[(k['a'], k['b'], k['rank']) for k in known]}"
        f" ({meta['seconds']} s) -> {out}"
    )
    return out
