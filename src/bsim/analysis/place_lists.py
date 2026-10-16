"""`bsim place-lists`: are the place lists of the text ordered on the ground? (DESIGN.md §16.58)

The text lists places: the stations of the wilderness (Num 33), the borders of the land (Num 34,
Josh 15:1–12), the towns of Judah and of the tribes (Josh 15, 19), the cities of the table of
nations (Gen 10). With the gazetteer's points (`bsim places`, §16.56), two claims, fixed in
`place_lists` before the first run:

- **Order.** A list's places in the order the text names them (verse, then word; a place named
  again keeps its first place; regions, which have no single site, left out by `places`) make a
  path. Its length (great-circle km between consecutive places) is set against `shuffles` random
  orders of the same places, one-sided: `p` is the share of random orders as short. For scale, a
  short path through the same places (nearest neighbour, then 2-opt) and `order_score`, how far the
  text's path goes from the random mean towards that short one (0: no better than random; 1: as
  short).
- **Districts.** Judah's towns come in districts, each closed by "ערים ... וחצריהן" (Josh
  15:21–62); the tribes' lots likewise (Josh 18:21–28, 19). The mean distance between two towns of
  one district is set against the same with the district labels shuffled over the towns (sizes
  kept); per district, its own mean against the same shuffles.

Both are run on every located place (`all`) and again on sure sites alone (`sure`: an OpenBible
vote of at least `sure_score`). The second matters: an obscure town is often placed by the
company it keeps in the list, which would make the first circular.

Writes `artifacts/place_lists/`: `lists.parquet` (per list and variant: places, path km, the
random orders' mean and histogram, `p`, the short path, `order`), `steps.parquet` (each list's
located places in order with the km from the one before and the short path's order),
`districts.parquet` (per grouping, variant and district: towns, mean km apart, the shuffles' mean,
`p`), `members.parquet` (the towns of each district) and `place_lists.meta.json`.
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

from bsim.config import config_hash, resolve_path
from bsim.data.refs import RefIndex

Log = Callable[[str], None]

EARTH_KM = 6371.0
VARIANTS = ("all", "sure")


def distances(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Great-circle km between every two points (haversine)."""
    la, lo = np.radians(lat)[:, None], np.radians(lon)[:, None]
    h = np.sin((la - la.T) / 2) ** 2 + np.cos(la) * np.cos(la.T) * np.sin((lo - lo.T) / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


def path_km(d: np.ndarray, order: np.ndarray) -> float:
    return float(d[order[:-1], order[1:]].sum()) if len(order) > 1 else 0.0


def shuffled_paths(d: np.ndarray, reps: int, rng: np.random.Generator) -> np.ndarray:
    """The path lengths of `reps` random orders of the points."""
    n = len(d)
    orders = np.argsort(rng.random((reps, n)), axis=1)
    return d[orders[:, :-1], orders[:, 1:]].sum(axis=1)


def short_path(d: np.ndarray) -> np.ndarray:
    """A short open path through every point: nearest neighbour from each start, the best improved
    by 2-opt. A yardstick, not the shortest. Solved as a cycle through an extra point at distance
    0 from all, which the open path's two ends join."""
    n = len(d)
    if n <= 3:
        return np.arange(n)
    best, best_len = None, np.inf
    for s in range(n):
        seen = np.zeros(n, dtype=bool)
        order = [s]
        seen[s] = True
        for _ in range(n - 1):
            row = np.where(seen, np.inf, d[order[-1]])
            nxt = int(row.argmin())
            order.append(nxt)
            seen[nxt] = True
        length = path_km(d, np.array(order))
        if length < best_len:
            best, best_len = order, length
    m = n + 1
    dd = np.zeros((m, m))
    dd[:n, :n] = d
    tour = np.array([n, *best])
    improved = True
    while improved:
        improved = False
        for i in range(m - 2):
            a, b = tour[i], tour[i + 1]
            c, e = tour[i + 2 : m], np.roll(tour, -1)[i + 2 : m]
            gain = dd[a, b] + dd[c, e] - dd[a, c] - dd[b, e]
            if i == 0:
                gain = gain[:-1]  # the last edge closes back to `a`
            j = int(gain.argmax()) if len(gain) else -1
            if j >= 0 and gain[j] > 1e-9:
                tour[i + 1 : i + 3 + j] = tour[i + 1 : i + 3 + j][::-1]
                improved = True
    k = int(np.flatnonzero(tour == n)[0])
    return np.concatenate([tour[k + 1 :], tour[:k]])


def histogram(null: np.ndarray, observed: float, bins: int) -> dict[str, Any]:
    """The random orders' lengths binned over a range that holds the text's path too."""
    lo, hi = float(min(null.min(), observed)), float(max(null.max(), observed))
    counts, _ = np.histogram(null, bins=bins, range=(lo, hi if hi > lo else lo + 1))
    return {"lo": round(lo, 1), "hi": round(hi, 1), "counts": counts.tolist()}


def list_places(
    mentions: pd.DataFrame, first_word: dict[tuple[str, int], int], span: tuple[int, int]
) -> pd.DataFrame:
    """The places a span names, in the order it names them (first mention of each)."""
    m = mentions[mentions.verse_id.between(*span)].copy()
    m["word"] = [
        first_word.get((lem, v), 10**6) for lem, v in zip(m.lemma, m.verse_id, strict=True)
    ]
    m = m.sort_values(["verse_id", "word", "place_id"], kind="stable")
    return m.drop_duplicates("place_id", keep="first").reset_index(drop=True)


def score_order(
    pts: pd.DataFrame, reps: int, rng: np.random.Generator, bins: int
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    """The path of the points in their order against random orders; with the km of each step and
    the short path's order."""
    d = distances(pts.lat.to_numpy(float), pts.lon.to_numpy(float))
    n = len(pts)
    obs = path_km(d, np.arange(n))
    null = shuffled_paths(d, reps, rng)
    short = short_path(d)
    short_len = path_km(d, short)
    mean = float(null.mean())
    steps = np.r_[np.nan, d[np.arange(n - 1), np.arange(1, n)]] if n else np.array([])
    res = {
        "n": n,
        "path_km": round(obs, 1),
        "null_mean": round(mean, 1),
        "null_sd": round(float(null.std()), 1),
        "p": float((1 + np.sum(null <= obs)) / (1 + reps)),
        "short_km": round(short_len, 1),
        "order_score": round((mean - obs) / (mean - short_len), 3) if mean > short_len else None,
        "hist": histogram(null, obs, bins),
    }
    return res, steps, short


def score_districts(
    pts: pd.DataFrame, reps: int, rng: np.random.Generator
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Mean km between two towns of one district against district labels shuffled over the towns."""
    d = distances(pts.lat.to_numpy(float), pts.lon.to_numpy(float))
    groups, lab = np.unique(pts.district.to_numpy(int), return_inverse=True)
    iu = np.triu_indices(len(lab), 1)
    pair_d = d[iu]
    k = len(groups)

    def within(labels: np.ndarray) -> tuple[float, np.ndarray]:
        a, b = labels[iu[0]], labels[iu[1]]
        same = a == b
        sums = np.bincount(a[same], weights=pair_d[same], minlength=k)
        pairs = np.bincount(a[same], minlength=k)
        with np.errstate(invalid="ignore", divide="ignore"):
            return float(pair_d[same].mean()), sums / pairs

    obs, obs_per = within(lab)
    null = np.empty(reps)
    null_per = np.empty((reps, len(groups)))
    for r in range(reps):
        null[r], null_per[r] = within(rng.permutation(lab))
    # the share of towns whose nearest town is of their own district
    near = np.where(np.eye(len(lab), dtype=bool), np.inf, d).argmin(axis=1)
    summary = {
        "n": len(lab),
        "districts": len(groups),
        "within_km": round(obs, 1),
        "null_mean": round(float(null.mean()), 1),
        "p": float((1 + np.sum(null <= obs)) / (1 + reps)),
        "all_km": round(float(pair_d.mean()), 1),
        "nearest_same": round(float((lab[near] == lab).mean()), 3),
    }
    per = []
    for i, g in enumerate(groups):
        n = int((lab == i).sum())
        col = null_per[:, i]
        per.append({
            "district": int(g), "n": n,
            "within_km": None if n < 2 else round(float(obs_per[i]), 1),
            "null_mean": None if n < 2 else round(float(np.mean(col)), 1),
            "p": None if n < 2 else float((1 + np.sum(col <= obs_per[i])) / (1 + reps)),
        })  # fmt: skip
    return summary, per


def run_place_lists(cfg: dict[str, Any], log: Log = print) -> Path:
    lc = cfg["place_lists"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "place_lists"
    t0 = time.perf_counter()
    reps, bins, min_n = int(lc["shuffles"]), int(lc["bins"]), int(lc["min_places"])
    sure_score = int(lc["sure_score"])
    rng = np.random.default_rng(int(lc["seed"]))

    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter",
                                                               "verse"])  # fmt: skip
    index = RefIndex(verses)
    places = pd.read_parquet(
        art / "places" / "places.parquet",
        columns=["place_id", "kind", "lat", "lon", "score", "coord_source"],
    )
    mentions = pd.read_parquet(art / "places" / "mentions.parquet",
                               columns=["lemma", "verse_id", "place_id"])  # fmt: skip
    spans = {li["key"]: index.resolve(li["ref"]) for li in lc["lists"]}
    for g in lc["districts"]:
        for ref in g["groups"]:
            spans[ref] = index.resolve(ref)
    lo, hi = min(s[0] for s in spans.values()), max(s[1] for s in spans.values())
    words = pd.read_parquet(proc / "words.parquet", columns=["verse_id", "idx", "content_lemmas"])
    words = words[words.verse_id.between(lo, hi)]
    first_word: dict[tuple[str, int], int] = {}
    for v, i, lems in zip(words.verse_id, words.idx, words.content_lemmas, strict=True):
        for lem in lems if lems is not None else []:
            first_word.setdefault((str(lem), int(v)), int(i))
    mentions = mentions.merge(places, on="place_id")
    mentions["sure"] = (mentions.coord_source == "openbible") & (
        mentions.score.fillna(-1) >= sure_score
    )

    def located(df: pd.DataFrame, kinds: list[str], variant: str) -> pd.DataFrame:
        df = df[df.kind.isin(kinds) & df.lat.notna()]
        return df[df.sure] if variant == "sure" else df

    # order
    list_rows, step_rows = [], []
    for li in lc["lists"]:
        span = spans[li["key"]]
        named = list_places(mentions, first_word, span)
        named = named[named.kind.isin(li["places"])]
        for variant in VARIANTS:
            pts = located(named, li["places"], variant).reset_index(drop=True)
            row = {"list_key": li["key"], "variant": variant, "ref": li["ref"],
                   "kind": li["kind"], "first_vid": span[0], "last_vid": span[1],
                   "n_named": len(named)}  # fmt: skip
            if len(pts) < min_n:
                list_rows.append(row | {"n": len(pts)})
                continue
            res, steps, short = score_order(pts, reps, rng, bins)
            list_rows.append(row | res | {"hist": json.dumps(res["hist"])})
            if variant == "all":
                short_pos = np.empty(len(pts), dtype=int)
                short_pos[short] = np.arange(len(pts))
                for i, r in enumerate(pts.itertuples(index=False)):
                    step_rows.append((li["key"], i + 1, int(r.place_id), int(r.verse_id),
                                      None if np.isnan(steps[i]) else round(float(steps[i]), 1),
                                      bool(r.sure), int(short_pos[i]) + 1))  # fmt: skip
        log(f"  {li['key']}: {row['n_named']} places named")
    lists = pd.DataFrame(list_rows)
    for c in ("path_km", "null_mean", "null_sd", "p", "short_km", "order_score"):
        if c not in lists:
            lists[c] = np.nan
    lists = lists[
        ["list_key", "variant", "ref", "kind", "first_vid", "last_vid", "n_named", "n", "path_km",
         "null_mean", "null_sd", "p", "short_km", "order_score", "hist"]  # fmt: skip
    ]
    steps_df = pd.DataFrame(step_rows, columns=["list_key", "pos", "place_id", "verse_id", "km",
                                                "sure", "short_pos"])  # fmt: skip

    # districts
    dist_rows, member_rows, groupings = [], [], {}
    for g in lc["districts"]:
        parts = []
        for i, ref in enumerate(g["groups"]):
            named = list_places(mentions, first_word, spans[ref])
            parts.append(named[named.kind.isin(g["places"])].assign(district=i + 1))
        towns = pd.concat(parts).drop_duplicates("place_id", keep="first")
        for r in towns[towns.lat.notna()].itertuples(index=False):
            member_rows.append((g["key"], int(r.district), int(r.place_id), int(r.verse_id),
                                bool(r.sure)))  # fmt: skip
        groupings[g["key"]] = {"groups": list(g["groups"]), "n_named": len(towns)}
        for variant in VARIANTS:
            pts = located(towns, g["places"], variant).reset_index(drop=True)
            if len(pts) < min_n or pts.district.nunique() < 2:
                groupings[g["key"]][variant] = {"n": len(pts)}
                continue
            summary, per = score_districts(pts, reps, rng)
            groupings[g["key"]][variant] = summary
            for d in per:
                ref = g["groups"][d["district"] - 1]
                first, last = spans[ref]
                dist_rows.append({"grouping": g["key"], "variant": variant, "ref": ref,
                                  "first_vid": first, "last_vid": last} | d)  # fmt: skip
    districts = pd.DataFrame(
        dist_rows,
        columns=["grouping", "variant", "district", "ref", "first_vid", "last_vid", "n",
                 "within_km", "null_mean", "p"],  # fmt: skip
    )
    members = pd.DataFrame(member_rows, columns=["grouping", "district", "place_id", "verse_id",
                                                 "sure"])  # fmt: skip

    out.mkdir(parents=True, exist_ok=True)
    lists.to_parquet(out / "lists.parquet")
    steps_df.to_parquet(out / "steps.parquet")
    districts.to_parquet(out / "districts.parquet")
    members.to_parquet(out / "members.parquet")
    alpha = float(lc["alpha"])
    tested = lists[lists.p.notna()]

    def held(variant: str) -> dict[str, int]:
        t = tested[tested.variant == variant]
        return {"n": len(t), "held": int((t.p <= alpha).sum())}

    meta = {
        "config_hash": config_hash(cfg, "place_lists"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "shuffles": reps,
        "alpha": alpha,
        "sure_score": sure_score,
        "min_places": min_n,
        "lists": {
            r.list_key: {k: (None if pd.isna(getattr(r, k)) else getattr(r, k))
                         for k in ("n", "path_km", "null_mean", "p", "short_km", "order_score")}
            for r in lists[lists.variant == "all"].itertuples(index=False)
        },  # fmt: skip
        "order": {v: held(v) for v in VARIANTS},
        "districts": groupings,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    meta = json.loads(json.dumps(meta, default=lambda x: x.item() if hasattr(x, "item") else x))
    (out / "place_lists.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                               "utf-8")  # fmt: skip
    o = meta["order"]
    dd = {k: (v.get("all") or {}).get("p") for k, v in groupings.items()}
    log(
        f"done: lists shorter than random orders at {alpha}: {o['all']['held']}/{o['all']['n']}"
        f" (sure sites only: {o['sure']['held']}/{o['sure']['n']}); districts p {dd}"
        f" ({meta['seconds']} s) -> {out}"
    )
    return out
