"""`bsim psalms`: the form of each psalm, Gunkel's genres, the lament's turn (DESIGN.md §16.42).

Form criticism sorts the psalms by their form: the hymn calls a group to praise and speaks of God,
the individual lament speaks to God in the first person singular, in distress, and often turns to
praise before its end ("the certainty of being heard": Ps 6:9, 13:6, 22:23). Two questions: does
the form, counted from the words, recover Gunkel's genres; and where does a lament turn?

- **Words.** Each psalm (chapter of Psalms) without its superscription: a leading run of
  `title_lemmas` (למנצח, מזמור, לדוד, משכיל, שיר המעלות ...) in the first verse, and in the second
  when the first is all title.
- **Features**, per word (`features`): first person singular and plural, second person (verbs,
  suffixes, pronouns), imperatives, plural imperatives, interrogatives (OSHB morphology), and the
  shares of words in the SDBH domains of `distress` and `praise`.
- **Genres** (`genres`, the core of Gunkel-Begrich, entered by hand; mixed and disputed psalms
  left out). The features are standardized over the 150 psalms and grouped by Ward clustering
  into as many clusters as genres; the clusters are compared with the genres of the labelled
  psalms by normalized mutual information against the labels permuted (`draws`). `checks`, fixed
  in advance: a genre's mean of a feature against the other labelled psalms, one-sided, labels
  permuted, Benjamini-Hochberg over the checks.
- **The turn.** Per psalm, each verse's mood = praise words - distress words; the split of its
  verses (at least `min_side` on each side) where the mood rate (mood / words) rises most from
  before to after is its turn, tested against the verse order shuffled within the psalm (`draws`).
  Checks fixed in advance: (1) `known_turns` named by scholarship, found when the split starts
  within `tolerance` verses, against the chance of a random split (Poisson binomial); (2) the share
  of individual laments with a turn at `alpha` against the hymns' (Fisher, one-sided).
- **Robustness:** titles kept; the form features alone (no domains); the domains alone; the
  tolerance 0 and 2.

Writes `artifacts/psalms/`: `psalms.parquet` (one row per psalm: `chapter, unit_id, genre,
cluster, words`, the features, `turn_vid, turn_verse, turn_stat, turn_p, before, after`),
`verses.parquet` (`verse_id, unit_id, verse, words, distress, praise`) and `psalms.meta.json`.
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
from scipy import stats

from bsim.analysis.stats import bh_q, empirical_p
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BY_SEFARIA

Log = Callable[[str], None]
FORM = ("first_singular", "first_plural", "second", "imperative", "imperative_plural", "question")
DOMAINS = ("distress", "praise")


def strongs(lemma: str) -> list[str]:
    """The Strong's numbers of a word's lemma parts (prefixes dropped, letters stripped)."""
    out = []
    for part in str(lemma).split("/"):
        digits = "".join(ch for ch in part if ch.isdigit())
        if digits:
            out.append(digits)
    return out


def morph_counts(morph: str) -> dict[str, int]:
    """Person, imperative and interrogative counts of one word's OSHB morphology."""
    c = dict.fromkeys(FORM, 0)
    if not isinstance(morph, str) or not morph:
        return c
    for p in morph[1:].split("/"):
        person = number = None
        if p[:1] == "V" and len(p) >= 6 and p[2] in "pqiwhjv":
            person, number = p[3], p[5]
            if p[2] == "v":
                c["imperative"] += 1
                c["imperative_plural"] += number == "p"
        elif p[:2] in ("Sp", "Pp") and len(p) >= 5:
            person, number = p[2], p[4]
        if p[:2] in ("Ti", "Pi"):
            c["question"] += 1
        if person == "1":
            c["first_singular"] += number == "s"
            c["first_plural"] += number == "p"
        elif person == "2":
            c["second"] += 1
    return c


def title_mask(words: pd.DataFrame, title: set[str]) -> np.ndarray:
    """True for the words of each psalm's superscription: a leading run of title lemmas in its
    first verse, continued into the second when the first is all title. `words` holds one psalm
    after another (`chapter, verse`), in order."""
    mask = np.zeros(len(words), bool)
    pos = 0
    for _, g in words.groupby("chapter", sort=False):
        idx = np.arange(pos, pos + len(g))
        pos += len(g)
        for v in (1, 2):
            sel = idx[g.verse.to_numpy() == v]
            all_title = True
            for i in sel:
                parts = strongs(words.lemma.iat[i])
                if parts and all(x in title for x in parts):
                    mask[i] = True
                else:
                    all_title = False
                    break
            if not all_title or len(sel) == 0:
                break
    return mask


def domain_flags(senses: pd.DataFrame, prefixes: list[str]) -> set[tuple[int, int]]:
    """(verse_id, idx) of the words with a sense in one of the domains."""
    pre = tuple(prefixes)
    hit = senses.domains.map(lambda ds: any(str(d).startswith(pre) for d in ds))
    s = senses[hit]
    return set(zip(s.verse_id.astype(int), s.idx.astype(int), strict=True))


def ward_clusters(x: np.ndarray, k: int) -> np.ndarray:
    from scipy.cluster.hierarchy import fcluster, linkage

    return fcluster(linkage(x, method="ward"), k, criterion="maxclust").astype(int)


def standardize(x: np.ndarray) -> np.ndarray:
    sd = x.std(axis=0)
    return (x - x.mean(axis=0)) / np.where(sd > 0, sd, 1)


def nmi_test(
    clusters: np.ndarray, labels: np.ndarray, draws: int, rng: np.random.Generator
) -> dict[str, float]:
    from sklearn.metrics import normalized_mutual_info_score as nmi

    obs = float(nmi(labels, clusters))
    null = np.array([nmi(rng.permutation(labels), clusters) for _ in range(draws)])
    return {"nmi": obs, "null": float(null.mean()), "p": empirical_p(obs, null)}


def profile_check(
    values: np.ndarray, labels: np.ndarray, genre: str, higher: bool, draws: int,
    rng: np.random.Generator,
) -> dict[str, float]:  # fmt: skip
    """The genre's mean minus the other labelled psalms', one-sided, labels permuted."""
    sign = 1 if higher else -1

    def diff(lab: np.ndarray) -> float:
        g = lab == genre
        return float(values[g].mean() - values[~g].mean())

    obs = diff(labels)
    null = np.array([diff(rng.permutation(labels)) for _ in range(draws)])
    g = labels == genre
    return {
        "mean": float(values[g].mean()),
        "rest": float(values[~g].mean()),
        "p": empirical_p(sign * obs, sign * null),
    }


def split_stats(mood: np.ndarray, words: np.ndarray, min_side: int) -> np.ndarray:
    """Rate after - rate before for each split s (verses [0, s) | [s, n)), s = min_side ..
    n - min_side; rows of `mood` / `words` may be several orders (2-d)."""
    m, w = np.atleast_2d(mood), np.atleast_2d(words)
    n = m.shape[1]
    cm, cw = np.cumsum(m, axis=1), np.cumsum(w, axis=1)
    s = np.arange(min_side, n - min_side + 1)
    before = cm[:, s - 1] / np.maximum(cw[:, s - 1], 1)
    after = (cm[:, -1:] - cm[:, s - 1]) / np.maximum(cw[:, -1:] - cw[:, s - 1], 1)
    return after - before


def find_turn(
    mood: np.ndarray, words: np.ndarray, min_side: int, draws: int, rng: np.random.Generator
) -> dict[str, Any] | None:
    """The split where the mood rate rises most, with its p against shuffled verse orders."""
    n = len(mood)
    if n < 2 * min_side:
        return None
    st = split_stats(mood, words, min_side)[0]
    j = int(np.argmax(st))
    s = j + min_side
    order = np.argsort(rng.random((draws, n)), axis=1)
    null = split_stats(mood[order], words[order], min_side).max(axis=1)
    cm, cw = np.cumsum(mood), np.cumsum(words)
    return {
        "split": s,
        "stat": float(st[j]),
        "p": empirical_p(float(st[j]), null),
        "before": float(cm[s - 1] / max(cw[s - 1], 1)),
        "after": float((cm[-1] - cm[s - 1]) / max(cw[-1] - cw[s - 1], 1)),
        "n_splits": len(st),
    }


def poisson_binomial_sf(probs: list[float], k: int) -> float:
    """P(at least k successes) of independent trials with these probabilities."""
    dist = np.zeros(len(probs) + 1)
    dist[0] = 1.0
    for p in probs:
        dist[1:] = dist[1:] * (1 - p) + dist[:-1] * p
        dist[0] *= 1 - p
    return float(dist[k:].sum())


def psalm_frame(
    words: pd.DataFrame, distress: set, praise: set, drop_titles: bool, title: set[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(per psalm: words and feature rates; per verse: words, distress, praise)."""
    w = words.copy()
    if drop_titles:
        w = w[~title_mask(w, title)]
    key = list(zip(w.verse_id.astype(int), w.idx.astype(int), strict=True))
    w["distress"] = [k in distress for k in key]
    w["praise"] = [k in praise for k in key]
    counts = pd.DataFrame([morph_counts(m) for m in w.morph], index=w.index)
    w = pd.concat([w, counts], axis=1)
    cols = [*FORM, *DOMAINS]
    per_verse = (
        w.groupby(["verse_id", "chapter", "verse"], sort=True)
        .agg(words=("idx", "size"), distress=("distress", "sum"), praise=("praise", "sum"))
        .reset_index()
    )
    per_psalm = w.groupby("chapter")[cols].sum()
    n = w.groupby("chapter").size()
    rates = per_psalm.div(n, axis=0)
    rates.insert(0, "words", n)
    return rates, per_verse


def genre_tests(
    rates: pd.DataFrame, genre_of: dict[int, str], feats: list[str], k: int, draws: int,
    seed: int,
) -> dict[str, Any]:  # fmt: skip
    """Ward clusters of the standardized features against the labelled genres."""
    rng = np.random.default_rng(seed)
    clusters = ward_clusters(standardize(rates[feats].to_numpy(float)), k)
    lab = rates.index.map(lambda c: genre_of.get(int(c))).to_numpy(dtype=object)
    sel = np.array([x is not None for x in lab])
    out = nmi_test(clusters[sel], lab[sel].astype(str), draws, rng)
    out["clusters"] = clusters
    return out


def run_psalms(cfg: dict[str, Any], log: Log = print) -> Path:
    pc = cfg["psalms"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "psalms"
    t0 = time.perf_counter()
    for f in ("verses.parquet", "words.parquet", "word_senses.parquet"):
        if not (proc / f).exists():
            raise RuntimeError(f"{proc / f} missing; run `bsim build-corpus`, `bsim lexicon`")
    book = BY_SEFARIA[pc["book"]].book_id
    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "verse"]
    )
    pv = verses[verses.book_id == book].sort_values("verse_id")
    words = pd.read_parquet(proc / "words.parquet", columns=["verse_id", "idx", "lemma", "morph"])
    words = words[words.verse_id.isin(pv.verse_id)].merge(
        pv[["verse_id", "chapter", "verse"]], on="verse_id"
    ).sort_values(["verse_id", "idx"], ignore_index=True)
    senses = pd.read_parquet(proc / "word_senses.parquet", columns=["verse_id", "idx", "domains"])
    senses = senses[senses.verse_id.isin(pv.verse_id)]
    distress, praise = domain_flags(senses, pc["distress"]), domain_flags(senses, pc["praise"])
    title = {str(x) for x in pc["title_lemmas"]}
    genre_of = {int(c): g for g, cs in pc["genres"].items() for c in cs}
    k, draws, alpha = len(pc["genres"]), pc["draws"], pc["alpha"]
    feats = list(pc["features"])

    rates, per_verse = psalm_frame(words, distress, praise, True, title)
    rates_kept, per_verse_kept = psalm_frame(words, distress, praise, False, title)

    # genres
    main = genre_tests(rates, genre_of, feats, k, draws, pc["seed"])
    clusters = main.pop("clusters")
    rates["genre"] = rates.index.map(lambda c: genre_of.get(int(c)))
    rates["cluster"] = clusters
    lab = rates.genre.to_numpy(dtype=object)
    sel = np.array([x is not None for x in lab])
    crosstab = (
        rates[sel].groupby(["genre", "cluster"]).size().rename("n").reset_index().to_dict("records")
    )
    rng = np.random.default_rng(pc["seed"] + 1)
    checks = []
    for genre, feat, direction in pc["checks"]:
        r = profile_check(
            rates[feat].to_numpy(float)[sel], lab[sel].astype(str), genre, direction == "higher",
            draws, rng,
        )  # fmt: skip
        checks.append({"genre": genre, "feature": feat, "direction": direction, **r})
    for c, q in zip(checks, bh_q(np.array([c["p"] for c in checks])), strict=True):
        c["q"] = float(q)
    profiles = {
        g: {f: float(rates.loc[rates.genre == g, f].mean()) for f in feats}
        for g in pc["genres"]
    }
    cluster_profiles = {
        int(c): {f: float(rates.loc[rates.cluster == c, f].mean()) for f in feats}
        for c in sorted(rates.cluster.unique())
    }

    # the turn of each psalm
    def turns(pv_: pd.DataFrame, seed: int) -> dict[int, dict[str, Any]]:
        rng_ = np.random.default_rng(seed)
        res = {}
        for ch, g in pv_.groupby("chapter"):
            g = g[g.words > 0]
            t = find_turn(
                (g.praise - g.distress).to_numpy(float), g.words.to_numpy(float),
                pc["min_side"], draws, rng_,
            )  # fmt: skip
            if t is not None:
                t["verse"] = int(g.verse.iat[t["split"]])
                t["verse_id"] = int(g.verse_id.iat[t["split"]])
                t["verses"] = g.verse.astype(int).tolist()
                res[int(ch)] = t
        return res

    keys = zip(pv.chapter.astype(int), pv.verse.astype(int), strict=True)
    vid_of = dict(zip(keys, pv.verse_id.astype(int), strict=True))

    def known_check(tr: dict[int, dict[str, Any]], tol: int) -> dict[str, Any]:
        rows, probs = [], []
        for ref in pc["known_turns"]:
            ch, v = (int(x) for x in ref.split()[-1].split(":"))
            t = tr.get(ch)
            if t is None:
                rows.append({"ref": ref, "verse_id": vid_of.get((ch, v)), "found": None})
                continue
            starts = t["verses"][pc["min_side"] : len(t["verses"]) - pc["min_side"] + 1]
            near = sum(abs(s - v) <= tol for s in starts)
            probs.append(near / len(starts))
            rows.append(
                {"ref": ref, "chapter": ch, "verse": v, "verse_id": vid_of[ch, v],
                 "turn_verse": t["verse"], "turn_vid": t["verse_id"], "p": t["p"],
                 "found": abs(t["verse"] - v) <= tol, "chance": near / len(starts)}
            )  # fmt: skip
        found = sum(bool(r["found"]) for r in rows)
        return {
            "found": found,
            "n": len(rows),
            "expected": float(sum(probs)),
            "p": poisson_binomial_sf(probs, found),
            "rows": rows,
        }

    def lament_vs_hymn(tr: dict[int, dict[str, Any]]) -> dict[str, Any]:
        def counts(genre: str) -> tuple[int, int]:
            cs = [c for c in pc["genres"][genre] if c in tr]
            return sum(tr[c]["p"] <= alpha for c in cs), len(cs)

        a, n_a = counts("lament_individual")
        b, n_b = counts("hymn")
        _, p = stats.fisher_exact([[a, n_a - a], [b, n_b - b]], alternative="greater")
        return {"laments": a, "n_laments": n_a, "hymns": b, "n_hymns": n_b, "p": float(p)}

    tr = turns(per_verse, pc["seed"] + 2)
    known = known_check(tr, pc["tolerance"])
    lvh = lament_vs_hymn(tr)
    tr_kept = turns(per_verse_kept, pc["seed"] + 2)

    robust = {
        "titles_kept": {
            "nmi": genre_tests(rates_kept, genre_of, feats, k, draws, pc["seed"])["nmi"],
            "known": known_check(tr_kept, pc["tolerance"])["found"],
            "laments_vs_hymns_p": lament_vs_hymn(tr_kept)["p"],
        },
        "form_only": {
            key: v for key, v in genre_tests(
                rates, genre_of, [f for f in feats if f in FORM], k, draws, pc["seed"]
            ).items() if key != "clusters"
        },  # fmt: skip
        "domains_only": {
            key: v for key, v in genre_tests(
                rates, genre_of, [f for f in feats if f in DOMAINS], k, draws, pc["seed"]
            ).items() if key != "clusters"
        },  # fmt: skip
        "tolerance": {
            str(t): {key: known_check(tr, t)[key] for key in ("found", "expected", "p")}
            for t in (0, 1, 2)
        },
    }

    # outputs
    ch = pv.groupby("chapter")
    rates = rates.reset_index()
    rates["unit_id"] = [f"c:{book}:{int(c)}" for c in rates.chapter]
    for col in ("turn_vid", "turn_verse"):
        rates[col] = pd.array([None] * len(rates), dtype="Int64")
    for col in ("turn_stat", "turn_p", "before", "after"):
        rates[col] = pd.array([None] * len(rates), dtype="Float64")
    for i, c in enumerate(rates.chapter):
        t = tr.get(int(c))
        if t is not None:
            rates.loc[i, ["turn_vid", "turn_verse"]] = [t["verse_id"], t["verse"]]
            rates.loc[i, ["turn_stat", "turn_p", "before", "after"]] = [
                t["stat"], t["p"], t["before"], t["after"]
            ]
    out.mkdir(parents=True, exist_ok=True)
    cols = ["unit_id", "chapter", "genre", "cluster", "words", *feats, "turn_vid", "turn_verse",
            "turn_stat", "turn_p", "before", "after"]  # fmt: skip
    rates[cols].to_parquet(out / "psalms.parquet")
    per_verse.assign(unit_id=[f"c:{book}:{int(c)}" for c in per_verse.chapter])[
        ["verse_id", "unit_id", "verse", "words", "distress", "praise"]
    ].to_parquet(out / "verses.parquet")
    labelled = rates[rates.genre.notna()]
    meta = {
        "config_hash": config_hash(cfg, "psalms"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "psalms": int(ch.ngroups),
        "labelled": int(len(labelled)),
        "genres": {g: int((labelled.genre == g).sum()) for g in pc["genres"]},
        "features": feats,
        "k": k,
        "alpha": alpha,
        "draws": draws,
        "title_words": int(len(words) - rates.words.sum()),
        "genre_test": main,
        "crosstab": crosstab,
        "checks": checks,
        "checks_held": sum(c["q"] <= alpha for c in checks),
        "profiles": profiles,
        "cluster_profiles": cluster_profiles,
        "known_turns": known,
        "laments_vs_hymns": lvh,
        "tolerance": pc["tolerance"],
        "min_side": pc["min_side"],
        "robustness": robust,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "psalms.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
    log(
        f"done: {meta['psalms']} psalms ({meta['labelled']} labelled), {meta['title_words']} title"
        f" words; genres NMI {main['nmi']:.3f} vs {main['null']:.3f} (p {main['p']:.4f}); checks"
        f" {meta['checks_held']} / {len(checks)}; known turns {known['found']} / {known['n']}"
        f" (expected {known['expected']:.2f}, p {known['p']:.4f}); turns in laments"
        f" {lvh['laments']} / {lvh['n_laments']} vs hymns {lvh['hymns']} / {lvh['n_hymns']}"
        f" (p {lvh['p']:.4f}) ({meta['seconds']} s) -> {out}"
    )
    return out
