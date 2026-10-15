"""`bsim places`: the gazetteer, every place the text names with where it lies (DESIGN.md §16.56).

- **Which place a mention is.** A name of the text is an OSHB `Np` lemma (`bsim entities`), and
  one Strong's number may be several places (Abel) or a place and a person (Tekoa). TIPNR lists,
  for every place and person, its Strong's numbers with every verse (`data/geo.py`). A mention
  (lemma × verse) goes to the TIPNR record of its Strong's number whose verses come nearest: the
  verse itself, or within `max_shift` verses where English and Hebrew numbering differ (`exact`,
  `shifted`). A Strong's number with only one place and no person takes the rest (`only`); what is
  left, or nearer a person, is no place.
- **Where it lies.** A TIPNR place joins its OpenBible.info record by the OpenBible name TIPNR
  gives, else by the TIPNR ids OpenBible links to (several: the one sharing most verses). Its
  point is the best-voted identification (`score`, 0 to 1000; `runner_up` = the second-best
  vote's share of the best, how contested the site is); without one, TIPNR's own map point.
- **What kind.** SDBH tags every name occurrence with a subdomain (`places.sdbh`: Names of
  Locations, Landforms, Waterbodies, Groups, People). A site's kind is its mentions' commonest
  subdomain; a location is split into town and region by OpenBible's types (`places.ob_kinds`).
  The same subdomains split every name of the text into person, people and place (`name_kinds`).

Writes `artifacts/places/`: `places.parquet` (one row per site the text names), `mentions.parquet`
(lemma × verse -> site, with how it was matched), `name_kinds.parquet` (every name's subdomain
shares), `basemap.parquet` (Natural Earth's land, lakes and rivers in `places.map.box`,
`data/basemap.py`, §16.57) and `places.meta.json`.
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.data.basemap import shapes
from bsim.data.geo import AncientPlace, TipnrRecord, read_openbible, read_tipnr
from bsim.text.normalize import consonantal

Log = Callable[[str], None]

KINDS = ("town", "region", "landform", "water")
NAME_KINDS = ("person", "people", "location", "landform", "water")


def base_strong(lemma: str) -> int | None:
    m = re.match(r"\d+", str(lemma))
    return int(m.group()) if m else None


def tipnr_key(uid: str) -> str:
    """A TIPNR unique name up to its first reference (`Babylon@Gen.10.10-Rev` ->
    `Babylon@Gen.10.10`): OpenBible links to an older TIPNR whose names did not carry the range."""
    name, _, ref = uid.partition("@")
    return f"{name}@{ref.split('-')[0]}"


def ob_base(friendly_id: str) -> str:
    """An OpenBible name without its number (`Bethel 2` -> `Bethel`)."""
    return re.sub(r" \d+$", "", friendly_id)


def openbible_match(
    rec: TipnrRecord,
    by_base: dict[str, list[AncientPlace]],
    by_tipnr: dict[str, list[AncientPlace]],
) -> AncientPlace | None:
    """The OpenBible record of a TIPNR place. Candidates: the records of the OpenBible name TIPNR
    gives (`Bethel_1`; OpenBible numbers a name's places `Bethel 1`, `Bethel 2`) and those linking
    to this TIPNR place. The one sharing most verses with it wins (then the best voted); a record
    sharing none is taken only when it is the name TIPNR gives or links to this place."""
    given = rec.openbible.replace("_", " ")
    named = ob_base(given)
    exact = {p.id for p in by_base.get(named, []) if p.friendly_id == given}
    linked = by_tipnr.get(tipnr_key(rec.uid), [])
    cands = {p.id: p for p in [*by_base.get(named, []), *linked]}
    if not cands:
        return None
    refs = {r for n in rec.names for r in n.refs}

    def rank(p: AncientPlace) -> tuple[int, int]:
        return len(refs & set(p.refs)), p.best.score if p.best else -1

    best = max(cands.values(), key=rank)
    if rank(best)[0] == 0 and best.id not in exact and best not in linked:
        return None
    return best


def resolve_mentions(
    mentions: pd.DataFrame,
    records: list[TipnrRecord],
    vid_of: dict[tuple[int, int, int], int],
    max_shift: int,
) -> pd.DataFrame:
    """Each mention (`lemma, verse_id`) with the TIPNR place it is (`place`, None: no place),
    `how` (exact | shifted | only | person | none) and `shift` (verses to the nearest reference)."""
    # base Strong's number -> [(record, sorted verse ids of its references)]
    cands: dict[int, list[tuple[TipnrRecord, np.ndarray]]] = defaultdict(list)
    for rec in records:
        refs: dict[int, set[int]] = defaultdict(set)
        for n in rec.names:
            refs[n.strong] |= {vid_of[r] for r in n.refs if r in vid_of}
        for s, vids in refs.items():
            cands[s].append((rec, np.array(sorted(vids), dtype=np.int64)))
    rows = []
    for lemma, vid in zip(mentions.lemma, mentions.verse_id, strict=True):
        s = base_strong(lemma)
        best: tuple[int, TipnrRecord] | None = None
        for rec, vids in cands.get(s, []) if s is not None else []:
            if len(vids):
                d = int(np.abs(vids - vid).min())
                if best is None or d < best[0]:
                    best = (d, rec)
        places = [rec for rec, _ in cands.get(s, []) if rec.category == "PLACE"] if s else []
        persons = [rec for rec, _ in cands.get(s, []) if rec.category != "PLACE"] if s else []
        if best is not None and best[0] <= max_shift:
            d, rec = best
            if rec.category == "PLACE":
                rows.append((lemma, vid, rec.uid, "exact" if d == 0 else "shifted", d))
            else:
                rows.append((lemma, vid, None, "person", d))
        elif len(places) == 1 and not persons:
            rows.append((lemma, vid, places[0].uid, "only", best[0] if best else None))
        else:
            rows.append((lemma, vid, None, "none", best[0] if best else None))
    out = pd.DataFrame(rows, columns=["lemma", "verse_id", "place", "how", "shift"])
    out["place"] = out.place.astype(object).where(out.place.notna(), None)
    out["shift"] = out["shift"].astype("Int64")
    return out


def sdbh_kinds(senses: pd.DataFrame, sdbh: dict[str, str]) -> pd.DataFrame:
    """Per (verse_id, strong): the weight of each name subdomain (`NAME_KINDS` columns)."""
    rows = []
    for v, s, doms, ws in zip(senses.verse_id, senses.strong, senses.domains, senses.weights,
                              strict=True):  # fmt: skip
        got = Counter()
        for d, w in zip(doms, ws, strict=True):
            if str(d) in sdbh:
                got[sdbh[str(d)]] += float(w)
        if got:
            rows.append((int(v), int(s), *[got.get(k, 0.0) for k in NAME_KINDS]))
    out = pd.DataFrame(rows, columns=["verse_id", "strong", *NAME_KINDS])
    return out.groupby(["verse_id", "strong"], as_index=False).sum()


def run_places(cfg: dict[str, Any], log: Log = print) -> Path:
    pc = cfg["places"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    raw = resolve_path(cfg, "data_raw") / "geo"
    out = art / "places"
    t0 = time.perf_counter()
    tipnr_path = raw / Path(cfg["sources"]["tipnr"]["files"][0]).name
    ob_path = raw / Path(cfg["sources"]["openbible_geo"]["files"][0]).name
    ne = {Path(f).name: raw / Path(f).name for f in cfg["sources"]["natural_earth"]["files"]}
    for p in (tipnr_path, ob_path, *ne.values()):
        if not p.exists():
            raise FileNotFoundError(f"{p} is missing: run `bsim download --only geo`")

    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "verse"]
    )
    vid_of = {
        (int(b), int(c), int(v)): int(i)
        for i, b, c, v in zip(
            verses.verse_id, verses.book_id, verses.chapter, verses.verse, strict=True
        )
    }
    entities = pd.read_parquet(art / "entities" / "entities.parquet", columns=["lemma", "he"])
    mentions = pd.read_parquet(art / "entities" / "mentions.parquet", columns=["lemma", "verse_id"])
    records = read_tipnr(tipnr_path)
    ancient = read_openbible(ob_path)
    log(f"TIPNR: {len(records):,} records; OpenBible: {len(ancient):,} ancient places")

    # which place each mention is
    res = resolve_mentions(mentions, records, vid_of, int(pc["max_shift"]))
    res["strong"] = res.lemma.map(base_strong).astype("Int64")

    # what kind each mention is (SDBH)
    senses = pd.read_parquet(
        proc / "word_senses.parquet", columns=["verse_id", "strong", "domains", "weights"]
    )
    senses = senses[senses.strong.astype(str).str.fullmatch(r"\d+")].astype({"strong": int})
    kinds = sdbh_kinds(senses, {str(k): v for k, v in pc["sdbh"].items()})
    res = res.merge(kinds, on=["verse_id", "strong"], how="left")
    res[list(NAME_KINDS)] = res[list(NAME_KINDS)].fillna(0.0)

    # every name: its subdomain shares and commonest kind
    nk = res.groupby("lemma")[list(NAME_KINDS)].sum()
    total = nk.sum(axis=1)
    name_kinds = nk.div(total.where(total > 0, 1), axis=0).round(4)
    name_kinds["kind"] = np.where(total > 0, nk.idxmax(axis=1), None)
    name_kinds["n_verses"] = res.groupby("lemma").size()
    name_kinds = name_kinds.reset_index()

    # where each site lies
    by_base: dict[str, list[AncientPlace]] = defaultdict(list)
    by_tipnr: dict[str, list[AncientPlace]] = defaultdict(list)
    for p in ancient:
        by_base[ob_base(p.friendly_id)].append(p)
        for uid in p.tipnr:
            by_tipnr[tipnr_key(uid)].append(p)
    rec_of = {r.uid: r for r in records if r.category == "PLACE"}
    ob_kind = {t: k for k, types in pc["ob_kinds"].items() for t in types}
    he_of = dict(zip(entities.lemma, entities.he, strict=True))
    placed = res[res.place.notna()]
    site_rows = []
    for uid, g in placed.groupby("place", sort=True):
        rec = rec_of[uid]
        ob = openbible_match(rec, by_base, by_tipnr)
        best = ob.best if ob else None
        lemma_counts = g.lemma.value_counts()
        # its Hebrew name: TIPNR's headword (בית אל, where the name's lemma is בית)
        head = rec.names[0].hebrew if rec.names else ""
        he = consonantal(head) if head else he_of.get(lemma_counts.index[0], "")
        sd = g[list(NAME_KINDS)].sum()
        sd_kind = sd.idxmax() if sd.sum() > 0 else None
        types = ob.types if ob else []
        ob_kinds = [ob_kind[t] for t in types if t in ob_kind]
        if sd_kind in ("landform", "water"):
            kind, source = sd_kind, "sdbh"
        elif ob_kinds:
            kind, source = Counter(ob_kinds).most_common(1)[0][0], "openbible"
        else:
            kind, source = None, None
        if best:
            lon, lat, score, src = best.lon, best.lat, best.score, "openbible"
        elif rec.lonlat:
            (lon, lat), score, src = rec.lonlat, None, "tipnr"
        else:
            lon = lat = score = src = None
        runner = (
            round(ob.identifications[1].score / best.score, 3)
            if ob and best and len(ob.identifications) > 1 and best.score
            else None
        )
        site_rows.append({
            "tipnr": uid, "he": he,
            "lemmas": json.dumps(lemma_counts.index.tolist()),
            "n_verses": int(g.verse_id.nunique()),
            "first_vid": int(g.verse_id.min()), "kind": kind, "kind_source": source,
            "sdbh_kind": sd_kind, "lat": lat, "lon": lon, "score": score, "coord_source": src,
            "runner_up": runner, "n_identifications": len(ob.identifications) if ob else 0,
            "openbible": ob.id if ob else None, "ob_types": json.dumps(types),
        })  # fmt: skip
    # numbered in canon order of first mention: TIPNR's English names are join keys, never shown
    places = pd.DataFrame(site_rows).sort_values(["first_vid", "tipnr"], ignore_index=True)
    places.insert(0, "place_id", range(1, len(places) + 1))
    places["score"] = places["score"].astype("Int64")
    for c in ("kind", "kind_source", "sdbh_kind", "coord_source", "openbible"):
        places[c] = places[c].astype(object)
    ment = res[res.place.notna()][["lemma", "verse_id", "place", "how", "shift"]]
    ment = (
        ment.assign(place_id=ment.place.map(dict(zip(places.tipnr, places.place_id, strict=True))))
        .drop(columns="place")[["lemma", "verse_id", "place_id", "how", "shift"]]
        .sort_values(["verse_id", "lemma"], kind="stable", ignore_index=True)
    )

    # the hand check: a fixed draw of mentions, judged by hand after the rules were set
    hc = pc.get("hand_check") or {}
    rng = np.random.default_rng(int(pc["seed"]))
    draw = rng.choice(len(ment), size=min(int(pc["sample"]), len(ment)), replace=False)
    sample = ment.iloc[np.sort(draw)]

    # the base map
    mc = pc["map"]
    box = tuple(float(x) for x in mc["box"])
    layers = [
        ("ne_10m_land.geojson", "land", None),
        ("ne_10m_lakes.geojson", "lakes", None),
        ("ne_10m_rivers_lake_centerlines.geojson", "rivers", int(mc["river_rank"])),
    ]
    shape_rows = [
        s
        for file, layer, rank in layers
        for s in shapes(ne[file], layer, box, float(mc["tolerance"]), int(mc["digits"]),  # type: ignore[arg-type]
                        float(mc["min_area"]), rank)  # fmt: skip
    ]
    basemap = pd.DataFrame(
        [(i + 1, s["layer"], s["name"], s["rank"], json.dumps(s["rings"], separators=(",", ":")))
         for i, s in enumerate(shape_rows)],
        columns=["shape_id", "layer", "name", "rank", "rings"],
    )  # fmt: skip
    basemap["rank"] = basemap["rank"].astype(float)

    out.mkdir(parents=True, exist_ok=True)
    basemap.to_parquet(out / "basemap.parquet")
    places.to_parquet(out / "places.parquet")
    ment.to_parquet(out / "mentions.parquet")
    name_kinds.to_parquet(out / "name_kinds.parquet")
    (out / "sample.json").write_text(
        json.dumps(sample.astype(object).where(sample.notna(), None).to_dict("records"),
                   ensure_ascii=False, indent=1),
        "utf-8",
    )  # fmt: skip
    how = res.how.value_counts().to_dict()
    multi = placed.groupby("strong").place.nunique()
    meta = {
        "config_hash": config_hash(cfg, "places", "sources.tipnr", "sources.openbible_geo"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "max_shift": int(pc["max_shift"]),
        "tipnr": {k: sum(r.category == k for r in records) for k in ("PLACE", "PERSON", "OTHER")},
        "openbible": len(ancient),
        "mentions": len(res),
        "how": {k: int(how.get(k, 0)) for k in ("exact", "shifted", "only", "person", "none")},
        "places": len(places),
        "placed_names": int(placed.lemma.nunique()),
        "located": int(places.lat.notna().sum()),
        "located_openbible": int((places.coord_source == "openbible").sum()),
        "kinds": {k: int((places.kind == k).sum()) for k in KINDS},
        "unkinded": int(places.kind.isna().sum()),
        "multi_site_strongs": int((multi > 1).sum()),
        "name_kinds": {k: int((name_kinds.kind == k).sum()) for k in NAME_KINDS},
        "hand_check": hc,
        "map": {"box": list(box), "shapes": {k: int((basemap.layer == k).sum()) for k in
                                             ("land", "lakes", "rivers")},
                "points": int(sum(len(r) for s in shape_rows for r in s["rings"]))},  # fmt: skip
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "places.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
    log(
        f"done: {meta['mentions']:,} name mentions -> {meta['how']}; {meta['places']:,} sites"
        f" ({meta['located']:,} located, {meta['located_openbible']:,} by OpenBible), kinds"
        f" {meta['kinds']} ({meta['unkinded']} unknown); {meta['multi_site_strongs']} Strong's"
        f" numbers with several sites ({meta['seconds']} s) -> {out}"
    )
    return out
