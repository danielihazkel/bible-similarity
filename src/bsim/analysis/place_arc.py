"""`bsim place-arc`: where each chapter takes place, and how the text moves (DESIGN.md §16.60)

Every chapter that names places (`bsim places`, §16.56) has a centre: the mean on the sphere of
the points it names, one per (place, verse) mention, and a spread (the mean km of those mentions
from the centre). Three claims, fixed in `place_arc` before the first run:

- **The arc.** Within a book, consecutive placed chapters lie closer than in a shuffled order:
  the sum of km between the centres of consecutive placed chapters against `shuffles` random
  orders of the same chapters, per book and over all books together (each book shuffled on its
  own), one-sided.
- **Known moves.** Abram from Mesopotamia to Canaan (Gen 11 → 12), Jacob's house down to Egypt,
  Israel out of Egypt into the wilderness, Judah to Babylon: the centre of the span after lies
  nearer the region the text goes to than the centre of the span before does, and the span
  before nearer the region it leaves. Known answers, a check of the centres.
- **The oracles against the nations** (Amos 1–2, Isa 13–23, Jer 46–51, Ezek 25–32) are wider
  than the other chapters of the prophets: on `spread`, or on `reach` (the centre's km from the
  canaan anchor, Jerusalem), the oracles' mean against labels shuffled over the placed prophetic
  chapters, one-sided at α / 2 each.

Writes `artifacts/place_arc/`: `chapters.parquet` (every chapter: mentions, places, centre,
spread, reach, the km from the book's placed chapter before, the place named most, oracle /
prophetic), `books.parquet` (per book: placed chapters, mean step, the shuffles' mean, `p`) and
`place_arc.meta.json` (the arc over all books, the moves, the oracles' tests).
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

from bsim.analysis.place_lists import EARTH_KM, distances
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS
from bsim.data.refs import RefIndex, parse_ref

Log = Callable[[str], None]

MEASURES = ("spread", "reach")


def km_to(lat: np.ndarray, lon: np.ndarray, lat0: float, lon0: float) -> np.ndarray:
    """Great-circle km from each point to one point (haversine)."""
    la, lo, la0, lo0 = np.radians(lat), np.radians(lon), np.radians(lat0), np.radians(lon0)
    h = np.sin((la - la0) / 2) ** 2 + np.cos(la) * np.cos(la0) * np.sin((lo - lo0) / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


def centre(lat: np.ndarray, lon: np.ndarray) -> tuple[float, float]:
    """The mean of points on the sphere (their unit vectors averaged), as (lat, lon)."""
    la, lo = np.radians(lat), np.radians(lon)
    x, y, z = (np.cos(la) * np.cos(lo)).mean(), (np.cos(la) * np.sin(lo)).mean(), np.sin(la).mean()
    return float(np.degrees(np.arctan2(z, np.hypot(x, y)))), float(np.degrees(np.arctan2(y, x)))


def place_spans(pts: pd.DataFrame) -> dict[str, Any]:
    """The centre of a set of mentions (`lat`, `lon`, `place_id`), their spread and the place
    named most (the first named, on a tie)."""
    lat, lon = pts.lat.to_numpy(float), pts.lon.to_numpy(float)
    c_lat, c_lon = centre(lat, lon)
    counts = pts.groupby("place_id", sort=False).size()
    return {
        "n_mentions": len(pts),
        "n_places": int(pts.place_id.nunique()),
        "lat": round(c_lat, 4),
        "lon": round(c_lon, 4),
        "spread_km": round(float(km_to(lat, lon, c_lat, c_lon).mean()), 1),
        "top_place": int(counts.idxmax()),
    }


def shuffled_steps(d: np.ndarray, reps: int, rng: np.random.Generator) -> np.ndarray:
    """The summed consecutive km of `reps` random orders of the points."""
    orders = np.argsort(rng.random((reps, len(d))), axis=1)
    return d[orders[:, :-1], orders[:, 1:]].sum(axis=1)


def label_test(values: np.ndarray, is_in: np.ndarray, reps: int, rng: np.random.Generator) -> dict:
    """The mean of the labelled values against the labels shuffled, one-sided (higher)."""
    k = int(is_in.sum())
    obs = float(values[is_in].mean())
    null = np.array([values[rng.permutation(len(values))[:k]].mean() for _ in range(reps)])
    return {
        "n": k,
        "n_other": int(len(values) - k),
        "observed": round(obs, 1),
        "other": round(float(values[~is_in].mean()), 1),
        "median": round(float(np.median(values[is_in])), 1),
        "other_median": round(float(np.median(values[~is_in])), 1),
        "null_mean": round(float(null.mean()), 1),
        "p": float((1 + np.sum(null >= obs)) / (1 + reps)),
    }


def chapters_of(ref: str) -> set[tuple[int, int]]:
    """The (book_id, chapter) pairs of a whole-chapter ref ("Isaiah 13-23")."""
    r = parse_ref(ref)
    return {(r.book.book_id, c) for c in range(r.c1, r.c2 + 1)}


def run_place_arc(cfg: dict[str, Any], log: Log = print) -> Path:
    ac = cfg["place_arc"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "place_arc"
    t0 = time.perf_counter()
    reps, alpha = int(ac["shuffles"]), float(ac["alpha"])
    min_m, min_ch = int(ac["min_mentions"]), int(ac["min_chapters"])
    rng = np.random.default_rng(int(ac["seed"]))
    regions = {k: (float(v["lat"]), float(v["lon"])) for k, v in ac["regions"].items()}
    home = regions["canaan"]

    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter",
                                                               "verse"])  # fmt: skip
    index = RefIndex(verses)
    places = pd.read_parquet(art / "places" / "places.parquet",
                             columns=["place_id", "kind", "lat", "lon"])  # fmt: skip
    places = places[places.kind.isin(ac["kinds"]) & places.lat.notna()]
    mentions = (
        pd.read_parquet(art / "places" / "mentions.parquet", columns=["verse_id", "place_id"])
        .drop_duplicates()
        .merge(places, on="place_id")
        .merge(verses[["verse_id", "book_id", "chapter"]], on="verse_id")
        .sort_values(["verse_id", "place_id"])
    )

    # chapters
    abbr = {b.book_id: b.osis for b in BOOKS}
    prophetic = {b.book_id for b in BOOKS if b.osis in set(ac["prophets"])}
    oracle = set().union(*(chapters_of(r) for r in ac["oracles"]))
    spans = verses.groupby(["book_id", "chapter"]).verse_id.agg(["min", "max"])
    by_ch = dict(tuple(mentions.groupby(["book_id", "chapter"])))
    rows = []
    for (b, c), (first, last) in spans.iterrows():
        pts = by_ch.get((b, c))
        row = {"book_id": int(b), "chapter": int(c), "first_vid": int(first), "last_vid": int(last),
               "n_mentions": 0 if pts is None else len(pts),
               "oracle": (b, c) in oracle, "prophetic": b in prophetic}  # fmt: skip
        if pts is not None and len(pts) >= min_m:
            row |= place_spans(pts)
            row["reach_km"] = round(float(km_to(np.array([row["lat"]]), np.array([row["lon"]]),
                                                *home)[0]), 1)  # fmt: skip
        rows.append(row)
    ch = pd.DataFrame(rows)
    ch["placed"] = ch.lat.notna()

    # the arc: consecutive placed chapters against shuffled orders, per book and over all
    ch["step_km"] = np.nan
    ch["prev_chapter"] = pd.NA
    book_rows, nulls, observed = [], [], 0.0
    for b, g in ch[ch.placed].groupby("book_id", sort=True):
        d = distances(g.lat.to_numpy(float), g.lon.to_numpy(float))
        n = len(g)
        steps = d[np.arange(n - 1), np.arange(1, n)]
        ch.loc[g.index[1:], "step_km"] = steps.round(1)
        ch.loc[g.index[1:], "prev_chapter"] = g.chapter.to_numpy()[:-1]
        row = {"book_id": int(b), "abbr": abbr[int(b)], "chapters": int((ch.book_id == b).sum()),
               "n": n}  # fmt: skip
        if n >= min_ch:
            null = shuffled_steps(d, reps, rng)
            nulls.append(null)
            observed += float(steps.sum())
            row |= {
                "mean_step": round(float(steps.mean()), 1),
                "null_mean": round(float(null.mean()) / (n - 1), 1),
                "ratio": round(float(steps.sum() / null.mean()), 3),
                "p": float((1 + np.sum(null <= steps.sum())) / (1 + reps)),
            }
        book_rows.append(row)
    books = pd.DataFrame(book_rows)
    for col in ("mean_step", "null_mean", "ratio", "p"):
        if col not in books:
            books[col] = np.nan
    tested = books[books.p.notna()]
    total_null = np.sum(nulls, axis=0) if nulls else np.array([np.nan])
    n_steps = int((tested.n - 1).sum())
    arc = {
        "chapters": len(ch),
        "placed": int(ch.placed.sum()),
        "books": len(tested),
        "steps": n_steps,
        "mean_step": round(observed / n_steps, 1) if n_steps else None,
        "null_mean": round(float(total_null.mean()) / n_steps, 1) if n_steps else None,
        "p": float((1 + np.sum(total_null <= observed)) / (1 + reps)) if n_steps else None,
        "books_held": int((tested.p <= alpha).sum()),
    }

    # known moves
    moves = []
    for mv in ac["moves"]:
        ends = {}
        for side in ("from", "to"):
            lo, hi = index.resolve(mv[side])
            pts = mentions[mentions.verse_id.between(lo, hi)]
            ends[side] = (lo, hi, place_spans(pts) if len(pts) >= min_m else None)
        res = {"key": mv["key"], "from_ref": mv["from"], "to_ref": mv["to"],
               "from_region": mv["from_region"], "to_region": mv["to_region"],
               "from_vids": list(ends["from"][:2]), "to_vids": list(ends["to"][:2])}  # fmt: skip
        a, z = ends["from"][2], ends["to"][2]
        if a is None or z is None:
            moves.append(res | {"holds": None})
            continue

        def near(s: dict[str, Any], region: str) -> float:
            return float(km_to(np.array([s["lat"]]), np.array([s["lon"]]), *regions[region])[0])

        def nearest(s: dict[str, Any]) -> str:
            return min(regions, key=lambda r: near(s, r))

        jump = distances(np.array([a["lat"], z["lat"]]), np.array([a["lon"], z["lon"]]))[0, 1]
        res |= {
            "from": a | {"to_from_region": round(near(a, mv["from_region"]), 1),
                         "to_to_region": round(near(a, mv["to_region"]), 1),
                         "nearest": nearest(a)},
            "to": z | {"to_from_region": round(near(z, mv["from_region"]), 1),
                       "to_to_region": round(near(z, mv["to_region"]), 1),
                       "nearest": nearest(z)},
            "km": round(float(jump), 1),
        }  # fmt: skip
        res["holds"] = bool(
            res["to"]["to_to_region"] < res["from"]["to_to_region"]
            and res["from"]["to_from_region"] < res["to"]["to_from_region"]
        )
        moves.append(res)

    # the oracles against the nations
    pro = ch[ch.placed & ch.prophetic].reset_index(drop=True)
    is_or = pro.oracle.to_numpy(bool)
    oracles: dict[str, Any] = {
        "refs": list(ac["oracles"]),
        "chapters": int(ch.oracle.sum()),
        "placed": int(is_or.sum()),
        "alpha": alpha / len(MEASURES),
    }
    if is_or.any() and (~is_or).any():
        for m in MEASURES:
            oracles[m] = label_test(pro[f"{m}_km"].to_numpy(float), is_or, reps, rng)
        oracles["holds"] = any(oracles[m]["p"] <= oracles["alpha"] for m in MEASURES)

    out.mkdir(parents=True, exist_ok=True)
    cols = ["book_id", "chapter", "first_vid", "last_vid", "n_mentions", "n_places", "lat", "lon",
            "spread_km", "reach_km", "top_place", "step_km", "prev_chapter", "oracle",
            "prophetic"]  # fmt: skip
    ch = ch.reindex(columns=cols)
    for c in ("n_places", "top_place", "prev_chapter"):
        ch[c] = ch[c].astype("Int64")
    ch.to_parquet(out / "chapters.parquet")
    books.reindex(columns=["book_id", "abbr", "chapters", "n", "mean_step", "null_mean", "ratio",
                           "p"]).to_parquet(out / "books.parquet")  # fmt: skip
    meta = {
        "config_hash": config_hash(cfg, "place_arc"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "shuffles": reps,
        "alpha": alpha,
        "min_mentions": min_m,
        "min_chapters": min_ch,
        "regions": {k: {"lat": v[0], "lon": v[1]} for k, v in regions.items()},
        "arc": arc,
        "moves": moves,
        "oracles": oracles,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    meta = json.loads(json.dumps(meta, default=lambda x: x.item() if hasattr(x, "item") else x))
    (out / "place_arc.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                             "utf-8")  # fmt: skip
    held = sum(bool(m.get("holds")) for m in moves)
    o = {m: (oracles.get(m) or {}).get("p") for m in MEASURES}
    log(
        f"done: {arc['placed']}/{arc['chapters']} chapters placed; consecutive chapters"
        f" {arc['mean_step']} km apart against {arc['null_mean']} shuffled (p {arc['p']},"
        f" {arc['books_held']}/{arc['books']} books); moves {held}/{len(moves)}; oracles p {o}"
        f" ({meta['seconds']} s) -> {out}"
    )
    return out
