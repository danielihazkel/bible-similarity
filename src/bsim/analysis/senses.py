"""`bsim senses`: how a word's senses and uses differ across the canon (DESIGN.md §16.23).

For every frequent content lemma (`senses.min_count` occurrences as a word's only content lemma,
at least `min_per_group` in each of `min_groups` corpus groups; names left out) two readings of
its occurrences are compared across the corpus groups of `senses.groups` (Torah, Former and
Latter Prophets, Psalms / Proverbs / Job, the Scrolls, the late books):

- **dictionary senses**: the SDBH meaning `bsim lexicon` tagged on the occurrence (only
  occurrences with exactly one matched meaning; at least two meanings with `min_sense_count`);
- **contextual uses**: the word's BEREL vector in its verse (`senses.encoder`, last hidden
  state, mean of its subword tokens, L2-normalized), clustered per lemma by k-means, k in
  2..`max_k` chosen by silhouette. A cluster is described only by Hebrew: the content lemmas of
  its verses (particles and pronouns left out, `structure.leitwort_skip_pos`) most
  over-represented against the lemma's other clusters (Dunning's G²) and the
  occurrences nearest its centre; nothing is translated (D5).

For each reading the dependence between group and sense is the mutual information MI(group;
sense) in bits (the generalized Jensen–Shannon divergence of the groups' sense distributions,
weighted by group size). Its null shuffles the group labels over the occurrences
(`null_reps`): `p` is empirical, `q` Benjamini–Hochberg over the lemmas, and `excess` = MI
minus the null mean (small samples inflate MI). Contextual uses also carry genre and style, so
a shift there means "used differently", not necessarily "means something else"; the dictionary
reading is the sense-only one. Where both exist the clusters are checked against the SDBH
meanings (normalized mutual information against the same with shuffled clusters).

Writes `artifacts/senses/`: `lemmas.parquet` (`lemma, n, groups` JSON counts, `k, silhouette,
use_mi, use_excess, use_p, use_q`, `sense_n, n_senses, sense_mi, sense_excess, sense_p,
sense_q`, `nmi, nmi_null`), `senses.parquet` (`lemma, kind` use | sdbh, `sense` (cluster number
or SDBH meaning id), `n, groups` JSON counts, `collocates` JSON lemmas, `examples` JSON
`[verse_id, idx]`, `domains` JSON codes), `senses.meta.json`.
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.stats import bh_q, g2_table
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS, BY_OSIS
from bsim.data.lexicon import strong_key
from bsim.text.normalize import consonantal

Log = Callable[[str], None]


def word_spans(surfaces: list[str]) -> tuple[str, list[tuple[int, int]]]:
    """The verse text the encoder reads (`text_model`: consonantal word forms joined by spaces)
    and each word's character span in it."""
    parts, spans, pos = [], [], 0
    for s in surfaces:
        c = consonantal(s)
        spans.append((pos, pos + len(c)))
        parts.append(c)
        pos += len(c) + 1
    return " ".join(parts), spans


def token_words(
    offsets: np.ndarray, special: np.ndarray, spans: list[tuple[int, int]]
) -> np.ndarray:
    """For each token the index of the word whose span holds its first character (-1: special,
    padding or a space)."""
    starts = np.array([s for s, _ in spans])
    ends = np.array([e for _, e in spans])
    out = np.full(len(offsets), -1)
    for t, (a, b) in enumerate(offsets):
        if special[t] or b <= a:
            continue
        w = np.searchsorted(starts, a, side="right") - 1
        if w >= 0 and a < ends[w]:
            out[t] = w
    return out


def mutual_info(groups: np.ndarray, senses: np.ndarray, n_groups: int, n_senses: int) -> float:
    """MI(group; sense) in bits from integer labels."""
    table = np.bincount(groups * n_senses + senses, minlength=n_groups * n_senses).reshape(
        n_groups, n_senses
    )
    p = table / table.sum()
    pg, ps = p.sum(1, keepdims=True), p.sum(0, keepdims=True)
    nz = p > 0
    return float((p[nz] * np.log2(p[nz] / (pg @ ps)[nz])).sum())


def shift_test(
    groups: np.ndarray, senses: np.ndarray, reps: int, rng: np.random.Generator
) -> tuple[float, float, float]:
    """(MI, MI minus the null mean, empirical p) with group labels shuffled over occurrences."""
    gi = np.unique(groups, return_inverse=True)[1]
    si = np.unique(senses, return_inverse=True)[1]
    ng, ns = int(gi.max()) + 1, int(si.max()) + 1
    mi = mutual_info(gi, si, ng, ns)
    null = np.array([mutual_info(rng.permutation(gi), si, ng, ns) for _ in range(reps)])
    p = float((1 + np.sum(null >= mi - 1e-12)) / (1 + reps))
    return mi, mi - float(null.mean()), p


def cluster_uses(
    x: np.ndarray, max_k: int, sample: int, seed: int
) -> tuple[np.ndarray, np.ndarray, int, float]:
    """K-means labels, centres, k and silhouette, k in 2..max_k by silhouette."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    best = None
    for k in range(2, max_k + 1):
        if len(x) <= k:
            break
        km = KMeans(n_clusters=k, n_init=4, random_state=seed).fit(x)
        s = silhouette_score(x, km.labels_, sample_size=min(sample, len(x)), random_state=seed)
        if best is None or s > best[3]:
            best = (km.labels_, km.cluster_centers_, k, float(s))
    if best is None:
        return np.zeros(len(x), int), x.mean(0, keepdims=True), 1, 0.0
    return best


def g2_over(k: int, n_a: int, m: int, n_b: int) -> float:
    """Dunning's G² of a lemma in `k` of `n_a` verses here against `m` of `n_b` elsewhere,
    positive only when over-represented here."""
    if k == 0 or k / n_a <= m / max(n_b, 1):
        return 0.0
    return g2_table(k, n_a, k + m, n_a + n_b)


def top_collocates(
    labels: np.ndarray, verse_lemmas: list[set[str]], target: str, top: int, min_verses: int
) -> dict[int, list[str]]:
    """Per cluster the lemmas of its verses most over-represented against the lemma's other
    clusters (Dunning's G²; the target itself excluded)."""
    out: dict[int, list[str]] = {}
    for c in np.unique(labels):
        here = [verse_lemmas[i] for i in np.flatnonzero(labels == c)]
        there = [verse_lemmas[i] for i in np.flatnonzero(labels != c)]
        a, b = Counter(x for s in here for x in s), Counter(x for s in there for x in s)
        scored = [
            (g2_over(n, len(here), b[x], len(there)), x)
            for x, n in a.items()
            if x != target and n >= min_verses
        ]
        out[int(c)] = [x for s, x in sorted(scored, key=lambda t: (-t[0], t[1])) if s > 0][:top]
    return out


def encode_words(
    cfg: dict[str, Any], verses: list[tuple[int, list[str]]], wanted: dict[int, set[int]], log: Log
) -> dict[tuple[int, int], np.ndarray]:
    """(verse_id, word idx) -> L2-normalized word vector for the `wanted` words of each verse."""
    from bsim.embed.context import token_batches
    from bsim.embed.encoders import load_encoder
    from bsim.retrieve.topk import get_device

    sc = cfg["senses"]
    device = get_device(cfg["encoders"].get("device", "cuda"))
    model = load_encoder(
        cfg["encoders"]["systems"][sc["encoder"]], sc["max_seq_length"], str(device)
    )
    model.eval()
    items = [(vid, *word_spans(surf)) for vid, surf in verses if wanted.get(vid)]
    order = np.argsort([len(t) for _, t, _ in items], kind="stable")
    texts = [items[i][1] for i in order]
    out: dict[tuple[int, int], np.ndarray] = {}
    lost = 0
    for b, hidden, enc in token_batches(model, texts, sc["max_seq_length"], sc["batch_size"]):
        for j in range(len(hidden)):
            vid, _, spans = items[order[b + j]]
            tw = token_words(
                enc["offsets"][j], ~enc["attention_mask"][j] | enc["special"][j], spans
            )
            for w in wanted[vid]:
                rows = tw == w
                if not rows.any():
                    lost += 1  # truncated away
                    continue
                v = hidden[j][rows].mean(0)
                out[(vid, w)] = v / max(np.linalg.norm(v), 1e-12)
    log(f"  {len(out):,} word vectors from {len(items):,} verses ({lost} words truncated away)")
    return out


def run_senses(cfg: dict[str, Any], log: Log = print, vectors: dict | None = None) -> Path:
    """`vectors` replaces the encoder (tests): (verse_id, idx) -> vector."""
    proc = resolve_path(cfg, "data_processed")
    sc = cfg["senses"]
    t0 = time.perf_counter()
    rng = np.random.default_rng(sc["seed"])
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id"])
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "idx", "surface", "content_lemmas", "morph"]
    )
    group_of_book: dict[int, str] = {}
    for g, osis in sc["groups"].items():
        for o in osis:
            if o not in BY_OSIS:
                raise RuntimeError(f"senses.groups: unknown book {o!r}")
            group_of_book[BY_OSIS[o].book_id] = g
    missing = [b.osis for b in BOOKS if b.book_id not in group_of_book]
    if missing:
        raise RuntimeError(f"senses.groups leaves out {missing}")
    group_names = list(sc["groups"])
    book_of = dict(zip(verses.verse_id, verses.book_id, strict=True))

    names = set()
    lm_path = proc / "lexicon_lemmas.parquet"
    if lm_path.exists():
        lm = pd.read_parquet(lm_path).dropna(subset=["name_kind"])
        names = set(lm.strong)
    single = words[words.content_lemmas.map(len) == 1].assign(
        lemma=lambda d: d.content_lemmas.map(lambda c: c[0])
    )
    single = single[
        ~single.morph.fillna("").str.contains("Np", regex=False)
        & ~single.lemma.map(strong_key).isin(names)
    ]
    single = single.assign(group=single.verse_id.map(book_of).map(group_of_book))
    counts = single.groupby(["lemma", "group"]).size().unstack(fill_value=0)
    ok = (counts.sum(axis=1) >= sc["min_count"]) & (
        (counts >= sc["min_per_group"]).sum(axis=1) >= sc["min_groups"]
    )
    targets = sorted(counts.index[ok])
    occ = single[single.lemma.isin(set(targets))].reset_index(drop=True)
    log(f"{len(targets)} lemmas, {len(occ):,} occurrences over {len(group_names)} groups")

    # SDBH meanings of the occurrences (one matched meaning only)
    sense_of: dict[tuple[int, int], str] = {}
    domains_of: dict[str, list[str]] = {}
    ws_path = proc / "word_senses.parquet"
    if ws_path.exists():
        ws = pd.read_parquet(ws_path, columns=["verse_id", "idx", "lex_ids", "source"])
        ws = ws[(ws.source == "sdbh") & (ws.lex_ids.map(len) == 1)]
        sense_of = {
            (v, i): ids[0] for v, i, ids in zip(ws.verse_id, ws.idx, ws.lex_ids, strict=True)
        }
        ls_path = proc / "lexicon_senses.parquet"
        if ls_path.exists():
            ls = pd.read_parquet(ls_path, columns=["lex_id", "domains"])
            domains_of = {i: list(d) for i, d in zip(ls.lex_id, ls.domains, strict=True)}
    else:
        log("  no word senses (`bsim lexicon`): contextual uses only")

    if vectors is None:
        surf = words.sort_values(["verse_id", "idx"]).groupby("verse_id").surface.agg(list)
        wanted: dict[int, set[int]] = defaultdict(set)
        for v, i in zip(occ.verse_id, occ.idx, strict=True):
            wanted[int(v)].add(int(i))
        vectors = encode_words(cfg, list(surf.items()), wanted, log)

    # collocates: content lemmas of the verse, particles and pronouns left out (as Leitworte)
    from bsim.analysis.parallelism import lemma_pos

    lw = pd.read_parquet(proc / "words.parquet", columns=["lemma", "morph"])
    skip_pos = set(cfg["structure"]["leitwort_skip_pos"])
    skip = {lem for lem, pos in lemma_pos(lw).items() if pos in skip_pos}
    content = words.groupby("verse_id").content_lemmas.agg(
        lambda c: {x for cl in c for x in cl if x not in skip}
    )
    lemma_rows, sense_rows = [], []
    for lemma, g in occ.groupby("lemma", sort=True):
        keys = [(int(v), int(i)) for v, i in zip(g.verse_id, g.idx, strict=True)]
        keep = [k in vectors for k in keys]
        g, keys = g[keep], [k for k, m in zip(keys, keep, strict=True) if m]
        gl = g.group.to_numpy()
        row: dict[str, Any] = {
            "lemma": lemma,
            "n": len(g),
            "groups": json.dumps({k: int(v) for k, v in Counter(gl).items()}),
        }
        # contextual uses
        x = np.stack([vectors[k] for k in keys]).astype(np.float32)
        labels, centres, k, sil = cluster_uses(x, sc["max_k"], sc["silhouette_sample"], sc["seed"])
        mi, excess, p = shift_test(gl, labels, sc["null_reps"], rng)
        row |= {"k": k, "silhouette": round(sil, 4), "use_mi": mi, "use_excess": excess, "use_p": p}
        verse_lemmas = [content[v] for v, _ in keys]
        cols = top_collocates(
            labels, verse_lemmas, lemma, sc["collocates"], sc["collocate_min_verses"]
        )
        for c in range(k):
            idx = np.flatnonzero(labels == c)
            near = idx[np.argsort(-(x[idx] @ centres[c]))[: sc["examples"]]]
            sense_rows.append(
                (
                    lemma,
                    "use",
                    str(c),
                    len(idx),
                    json.dumps(dict(Counter(gl[idx]))),
                    json.dumps(cols.get(c, []), ensure_ascii=False),
                    json.dumps([list(keys[i]) for i in near]),
                    json.dumps([]),
                )
            )
        # dictionary senses
        sl = np.array([sense_of.get(k_, "") for k_ in keys])
        tagged = sl != ""
        sense_counts = Counter(sl[tagged])
        major = {s for s, n in sense_counts.items() if n >= sc["min_sense_count"]}
        sel = np.array([s in major for s in sl])
        row |= {"sense_n": int(sel.sum()), "n_senses": len(major)}
        if len(major) >= 2:
            smi, sexcess, sp = shift_test(gl[sel], sl[sel], sc["null_reps"], rng)
            row |= {"sense_mi": smi, "sense_excess": sexcess, "sense_p": sp}
            from sklearn.metrics import normalized_mutual_info_score as nmi

            row["nmi"] = float(nmi(sl[sel], labels[sel]))
            row["nmi_null"] = float(
                np.mean([nmi(sl[sel], rng.permutation(labels[sel])) for _ in range(20)])
            )
            for s in sorted(major, key=lambda s: (-sense_counts[s], s)):  # ties: by id
                idx = np.flatnonzero(sl == s)
                ex = rng.choice(idx, size=min(sc["examples"], len(idx)), replace=False)
                sense_rows.append(
                    (
                        lemma,
                        "sdbh",
                        s,
                        len(idx),
                        json.dumps(dict(Counter(gl[idx]))),
                        json.dumps([]),
                        json.dumps([list(keys[i]) for i in sorted(ex)]),
                        json.dumps(domains_of.get(s, [])),
                    )
                )
        lemma_rows.append(row)

    lemmas = pd.DataFrame(lemma_rows)
    for col in ("sense_mi", "sense_excess", "sense_p", "nmi", "nmi_null"):
        if col not in lemmas:
            lemmas[col] = np.nan
    lemmas["use_q"] = bh_q(lemmas.use_p.to_numpy())
    lemmas["sense_q"] = bh_q(lemmas.sense_p.to_numpy())
    senses = pd.DataFrame(
        sense_rows,
        columns=["lemma", "kind", "sense", "n", "groups", "collocates", "examples", "domains"],
    )
    out = resolve_path(cfg, "artifacts") / "senses"
    out.mkdir(parents=True, exist_ok=True)
    lemmas.to_parquet(out / "lemmas.parquet")
    senses.to_parquet(out / "senses.parquet")
    both = lemmas.dropna(subset=["nmi"])
    meta = {
        "config_hash": config_hash(cfg, "senses", "structure.leitwort_skip_pos"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "encoder": sc["encoder"],
        "groups": {g: sc["groups"][g] for g in group_names},
        "lemmas": len(lemmas),
        "occurrences": int(lemmas.n.sum()),
        "use_q_below_0.05": int((lemmas.use_q <= 0.05).sum()),
        "sense_tested": int(lemmas.sense_p.notna().sum()),
        "sense_q_below_0.05": int((lemmas.sense_q <= 0.05).sum()),
        "nmi_mean": round(float(both.nmi.mean()), 4) if len(both) else None,
        "nmi_null_mean": round(float(both.nmi_null.mean()), 4) if len(both) else None,
        "nmi_lemmas": int(len(both)),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "senses.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(
        f"done: {meta['lemmas']} lemmas; uses differ by group (q ≤ 0.05) for "
        f"{meta['use_q_below_0.05']}, dictionary senses for {meta['sense_q_below_0.05']} of "
        f"{meta['sense_tested']}; clusters vs SDBH NMI {meta['nmi_mean']} (shuffled "
        f"{meta['nmi_null_mean']}, {meta['nmi_lemmas']} lemmas) in {meta['seconds']} s -> {out}"
    )
    return out
