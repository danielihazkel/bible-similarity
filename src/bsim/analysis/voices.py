"""`bsim voices`: does a speaker have a style of their own? (DESIGN.md §16.28)

The BHSA speakers of `bsim syntax` (§16.26) split the direct speech of the Bible by who says it.
Each speaker's words are profiled with the stylometry features (§16.6: the `stylometry.mfw` most
frequent content lemmas and the morphology rates), and compared in units of each feature's spread
over chapters (Burrows' Delta: mean |rate_a − rate_b| / sd).

- Speakers: the speaker lemma of a quotation clause; the divine names (`syntax.divine`) are one
  speaker, `divine`. Only persons are profiled: proper names (OSHB `Np`) other than the peoples in
  `voices.exclude` (ישראל); a speaker that is a common noun (king, servant, messenger …) is not
  one person, so it is not profiled, but its speech stays in the reference. A speaker needs
  `min_words` words.
- Distinctiveness: Delta between a speaker and all *other attributed speech in the same books*,
  so a speaker is compared with what others say in their own book (genre and book held fixed).
  Null: the speaker labels permuted over the attributed speech clauses of each book
  (`shuffles`), which keeps the clauses, their lengths and each book's mix; p by
  `stats.empirical_p`, Benjamini–Hochberg q over the speakers. `effect` = (Delta − null mean) /
  null sd ranks speakers fairly across sizes (a small speaker's Delta is larger by chance alone).
- Calibration: one more permutation scored as if it were observed: almost no speaker should
  pass q ≤ 0.05. Sensitivity: the same with explicitly introduced speech only (`n_explicit`;
  carried and enclosing attributions are less reliable, §16.26), Spearman ρ of the effects.
- Pairs: Delta between every two speakers and the narrator (narration words) and unattributed
  speech; descriptive.
- Checks fixed in advance (`voices.checks`):
    author    one speaker in two corpora (David in Samuel / Chronicles, God in Kings /
              Chronicles, Solomon in Kings / Chronicles): `cross` = d(A, narrator B) +
              d(B, narrator A) − d(A, narrator A) − d(B, narrator B) is positive when each
              portrayal sounds like its own book's narrator (the author's voice over the
              character's); null: the speaker's clauses re-split between A and B. `d_ab` with
              the same null says whether the two portrayals differ at all. A side with fewer
              than `min_words` words is reported as underpowered.
    distinct  a speaker named in advance as the most distinct of a book (Elihu in Job): its
              rank by effect among that book's speakers.

Writes `artifacts/voices/{speakers,features,pairs}.parquet` + `voices.meta.json`; without
`bsim syntax` output the tables are empty.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse

from bsim.analysis.stats import bh_q, empirical_p
from bsim.analysis.stylometry import MORPH_LABELS, feature_counts, feature_matrix
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BY_OSIS
from bsim.data.lexicon import strong_key

Log = Callable[[str], None]

DIVINE, NARRATOR, UNATTRIBUTED = "divine", "narrator", "unattributed"
SPEAKER_COLUMNS = [
    "key", "n_words", "n_explicit", "n_clauses", "main_book", "books", "delta", "null_mean",
    "effect", "p", "q",
]  # fmt: skip
FEATURE_COLUMNS = ["key", "side", "rank", "feature", "label", "rate", "rate_ref", "z"]
PAIR_COLUMNS = ["a", "b", "delta"]


def word_clauses(clauses: pd.DataFrame) -> pd.DataFrame:
    """`verse_id, idx, row` per OSHB word: the position of its clause in `clauses` (a word split
    over clauses keeps its last clause, as `speech.word_types`)."""
    c = clauses.reset_index(drop=True)
    c = c.assign(row=np.arange(len(c)))[["verse_id", "words", "row"]].explode("words")
    c = c.dropna(subset=["words"])
    c = c.assign(idx=c.words.astype(int)).drop_duplicates(["verse_id", "idx"], keep="last")
    return c[["verse_id", "idx", "row"]].reset_index(drop=True)


def proper_names(words: pd.DataFrame) -> set[str]:
    """Lemmas OSHB tags as a proper noun (`Np`) in most of their occurrences."""
    tagged: Counter[str] = Counter()
    seen: Counter[str] = Counter()
    for lemma, morph in zip(words.lemma, words.morph, strict=True):
        if not isinstance(morph, str) or not isinstance(lemma, str):
            continue
        for part, m in zip(lemma.split("/"), morph[1:].split("/"), strict=False):
            lem = part.replace(" ", "")
            if lem[:1].isdigit():
                seen[lem] += 1
                tagged[lem] += m.startswith("Np")
    return {lem for lem, n in seen.items() if tagged[lem] * 2 > n}


def speaker_key(speaker: object, divine: set[str]) -> str | None:
    """The voice a quotation is counted under: `divine` for the divine names, else the lemma."""
    if not isinstance(speaker, str) or not speaker:
        return None
    return DIVINE if strong_key(speaker) in divine else speaker


def group_sums(
    lab: np.ndarray, n_groups: int, x: np.ndarray, nw: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Feature counts and words summed per group (`lab` −1: left out)."""
    ok = lab >= 0
    m = sparse.csr_matrix(
        (np.ones(int(ok.sum())), (lab[ok], np.flatnonzero(ok))), shape=(n_groups, len(lab))
    )
    return np.asarray(m @ x), np.asarray(m @ nw)


def rates(counts: np.ndarray, words: np.ndarray) -> np.ndarray:
    w = np.asarray(words, dtype=np.float64)[..., None]
    return np.divide(counts, w, out=np.full(np.shape(counts), np.nan), where=w > 0)


def delta(a: np.ndarray, b: np.ndarray, sd: np.ndarray) -> np.ndarray:
    """Burrows' Delta between rate vectors (last axis = features)."""
    return np.mean(np.abs(a - b) / sd, axis=-1)


def permute_within(lab: np.ndarray, group: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """`lab` shuffled among the rows of each group (each group keeps its labels)."""
    by_group = np.argsort(group, kind="stable")
    shuffled = np.lexsort((rng.random(len(lab)), group))
    out = np.empty_like(lab)
    out[by_group] = lab[shuffled]
    return out


def distinctiveness(
    x: np.ndarray,
    nw: np.ndarray,
    book: np.ndarray,
    lab: np.ndarray,
    n_keep: int,
    sd: np.ndarray,
    reps: int,
    rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    """Delta of each kept speaker (lab 0..n_keep−1; n_keep = any other speaker) against the
    other speech of its books, with the within-book permutation null."""
    books, book_idx = np.unique(book, return_inverse=True)
    t, tw = group_sums(book_idx, len(books), x, nw)
    member = np.zeros((n_keep, len(books)))
    kept = lab < n_keep
    member[lab[kept], book_idx[kept]] = 1.0

    def stat(labels: np.ndarray) -> np.ndarray:
        s, w = group_sums(labels, n_keep + 1, x, nw)
        s, w = s[:n_keep], w[:n_keep]
        return delta(rates(s, w), rates(member @ t - s, member @ tw - w), sd)

    observed = stat(lab)
    null = np.stack([stat(permute_within(lab, book_idx, rng)) for _ in range(reps)])
    pseudo = stat(permute_within(lab, book_idx, rng))
    mean, sdn = null.mean(axis=0), null.std(axis=0)
    p = np.array([empirical_p(observed[i], null[:, i]) for i in range(n_keep)])
    p_cal = np.array([empirical_p(pseudo[i], null[:, i]) for i in range(n_keep)])
    return {
        "delta": observed,
        "null_mean": mean,
        "effect": np.divide(observed - mean, sdn, out=np.zeros(n_keep), where=sdn > 0),
        "p": p,
        "q": bh_q(p),
        "q_calibration": bh_q(p_cal),
    }


def author_check(
    x: np.ndarray,
    nw: np.ndarray,
    a: np.ndarray,
    b: np.ndarray,
    narr_a: np.ndarray,
    narr_b: np.ndarray,
    sd: np.ndarray,
    reps: int,
    rng: np.random.Generator,
) -> dict[str, float]:
    """`cross` and `d_ab` of one speaker's clauses in corpus A vs B (boolean row masks), with
    their narrators; null: the speaker's clauses re-split between A and B (sizes kept)."""
    ra = rates(x[narr_a].sum(axis=0), nw[narr_a].sum())
    rb = rates(x[narr_b].sum(axis=0), nw[narr_b].sum())
    rows = np.flatnonzero(a | b)
    side = a[rows].astype(np.int64)  # 1 = A, 0 = B

    def stat(s: np.ndarray) -> tuple[float, float]:
        sa = rates(x[rows[s == 1]].sum(axis=0), nw[rows[s == 1]].sum())
        sb = rates(x[rows[s == 0]].sum(axis=0), nw[rows[s == 0]].sum())
        cross = delta(sa, rb, sd) + delta(sb, ra, sd) - delta(sa, ra, sd) - delta(sb, rb, sd)
        return float(cross), float(delta(sa, sb, sd))

    cross, d_ab = stat(side)
    null = np.array([stat(rng.permutation(side)) for _ in range(reps)])
    return {
        "cross": round(cross, 4),
        "p_cross": round(empirical_p(cross, null[:, 0]), 4),
        "d_ab": round(d_ab, 4),
        "p_ab": round(empirical_p(d_ab, null[:, 1]), 4),
        "words_a": int(nw[a].sum()),
        "words_b": int(nw[b].sum()),
    }


def verdict(check: dict[str, float], min_words: int, alpha: float = 0.05) -> str:
    """underpowered | author (each side sounds like its narrator) | differs | same."""
    if min(check["words_a"], check["words_b"]) < min_words:
        return "underpowered"
    if check["cross"] > 0 and check["p_cross"] <= alpha:
        return "author"
    return "differs" if check["p_ab"] <= alpha else "same"


def _books(osis: list[str]) -> list[int]:
    for o in osis:
        if o not in BY_OSIS:
            raise RuntimeError(f"voices: unknown book {o!r}")
    return [BY_OSIS[o].book_id for o in osis]


def _write(out: Path, speakers: pd.DataFrame, features: pd.DataFrame, pairs: pd.DataFrame,
           meta: dict[str, Any]) -> None:  # fmt: skip
    out.mkdir(parents=True, exist_ok=True)
    speakers.to_parquet(out / "speakers.parquet", index=False)
    features.to_parquet(out / "features.parquet", index=False)
    pairs.to_parquet(out / "pairs.parquet", index=False)
    (out / "voices.meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def run_voices(cfg: dict[str, Any], log: Log = print) -> Path:
    from bsim.store.db import lemma_display_forms

    t0 = time.perf_counter()
    vc, st = cfg["voices"], cfg["stylometry"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "voices"
    meta: dict[str, Any] = {
        "config_hash": config_hash(cfg, "voices", "stylometry", "syntax"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    author_specs = [(c, _books(c["a"]), _books(c["b"])) for c in vc["checks"].get("author", [])]
    distinct_specs = [(c, _books([c["book"]])[0]) for c in vc["checks"].get("distinct", [])]
    clause_path = proc / "syntax_clauses.parquet"
    if not clause_path.exists():
        _write(
            out,
            pd.DataFrame(columns=SPEAKER_COLUMNS),
            pd.DataFrame(columns=FEATURE_COLUMNS),
            pd.DataFrame(columns=PAIR_COLUMNS),
            {**meta, "speakers": 0},
        )
        log(f"{clause_path} missing (run `bsim syntax` for speakers); empty voices written")
        return out

    clauses = pd.read_parquet(
        clause_path, columns=["verse_id", "words", "txt", "speaker", "speaker_source"]
    ).reset_index(drop=True)
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter"])
    words = pd.read_parquet(
        proc / "words.parquet",
        columns=["verse_id", "idx", "surface", "lemma", "content_lemmas", "morph"],
    )
    lemma_counts: Counter[str] = Counter(t for c in words.content_lemmas for t in c)
    mfw = [t for t, _ in lemma_counts.most_common(st["mfw"])]

    # feature spread over chapters (the scale of every Delta)
    chap = (verses.sort_values("verse_id").book_id * 1000 + verses.chapter).to_numpy()
    _, chap_of_verse = np.unique(chap, return_inverse=True)
    xc, nwc, names = feature_matrix(words, chap_of_verse, int(chap_of_verse.max()) + 1, mfw)
    sd = xc[nwc >= st["min_words"]].std(axis=0)
    keep_f = sd > 0
    names = [n for n, k in zip(names, keep_f, strict=True) if k]
    sd = sd[keep_f]

    # clause profiles
    wc = word_clauses(clauses)
    row_of = words[["verse_id", "idx"]].merge(wc, on=["verse_id", "idx"], how="left").row
    counts, nw, _ = feature_counts(
        words, row_of.fillna(-1).astype(np.int64).to_numpy(), len(clauses), mfw
    )
    x = counts[:, keep_f]
    book_of_verse = verses.set_index("verse_id").book_id
    info = pd.DataFrame(
        {
            "book": book_of_verse.reindex(clauses.verse_id).to_numpy(),
            "ttype": clauses.txt.str[-1].fillna("").to_numpy(),
            "key": [speaker_key(s, set(cfg["syntax"]["divine"])) for s in clauses.speaker],
            "explicit": (clauses.speaker_source == "explicit").to_numpy(),
            "nw": nw,
        }
    )
    exclude, names_np = set(vc["exclude"]), proper_names(words)
    excluded = info.key.map(
        lambda k: (
            isinstance(k, str)
            and k != DIVINE
            and (k.replace(" ", "") not in names_np or strong_key(k) in exclude)
        )
    )
    speech = (info.ttype == "Q") & (nw > 0)
    pool = speech & info.key.notna()
    totals = info[pool & ~excluded].groupby("key").nw.sum()
    keys = sorted(totals[totals >= vc["min_words"]].index, key=lambda k: -totals[k])
    n_keep = len(keys)
    key_idx = {k: i for i, k in enumerate(keys)}
    rng = np.random.default_rng(vc["seed"])

    rows = np.flatnonzero(pool.to_numpy())
    lab = np.array([key_idx.get(k, n_keep) for k in info.key.to_numpy()[rows]])
    book = info.book.to_numpy()[rows]
    res = distinctiveness(x[rows], nw[rows], book, lab, n_keep, sd, vc["shuffles"], rng)

    # explicitly introduced speech only
    ex_rows = np.flatnonzero((pool & info.explicit).to_numpy())
    ex_words = info.iloc[ex_rows].groupby("key").nw.sum()
    ex_keys = [k for k in keys if ex_words.get(k, 0) >= vc["min_words"]]
    ex_idx = {k: i for i, k in enumerate(ex_keys)}
    ex_lab = np.array([ex_idx.get(k, len(ex_keys)) for k in info.key.to_numpy()[ex_rows]])
    sensitivity: dict[str, Any] = {"speakers": len(ex_keys), "rho": None}
    if len(ex_keys) >= 3:
        from scipy.stats import spearmanr

        ex = distinctiveness(
            x[ex_rows], nw[ex_rows], info.book.to_numpy()[ex_rows], ex_lab, len(ex_keys), sd,
            vc["sensitivity_shuffles"], rng,
        )  # fmt: skip
        full = [res["effect"][key_idx[k]] for k in ex_keys]
        sensitivity["rho"] = round(float(spearmanr(full, ex["effect"]).statistic), 3)

    # speaker table and feature profiles
    gloss = dict(zip(*lemma_display_forms(words)[["lemma", "he_lemma"]].T.values, strict=True))

    def label(name: str) -> str:
        return gloss.get(name[6:], name[6:]) if name.startswith("lemma:") else MORPH_LABELS[name]

    s_sum, s_w = group_sums(lab, n_keep + 1, x[rows], nw[rows])
    books_all, book_idx = np.unique(book, return_inverse=True)
    t, tw = group_sums(book_idx, len(books_all), x[rows], nw[rows])
    spk_rows, feat_rows = [], []
    for k, i in key_idx.items():
        mine = info.iloc[rows[lab == i]]
        by_book = mine.groupby("book").nw.sum().sort_values(ascending=False)
        in_books = np.isin(books_all, by_book.index)
        r_s = rates(s_sum[i], s_w[i])
        r_ref = rates(t[in_books].sum(axis=0) - s_sum[i], tw[in_books].sum() - s_w[i])
        z = (r_s - r_ref) / sd
        spk_rows.append(
            (k, int(s_w[i]), int(mine[mine.explicit].nw.sum()), len(mine),
             int(by_book.index[0]), [int(b) for b in by_book.index],
             float(res["delta"][i]), float(res["null_mean"][i]), float(res["effect"][i]),
             float(res["p"][i]), float(res["q"][i]))
        )  # fmt: skip
        order = np.argsort(-z, kind="stable")
        picks = [(j, "over") for j in order[: vc["top_features"]]]
        picks += [(j, "under") for j in order[::-1][: vc["top_features"]]]
        for rank, (j, side) in enumerate(picks):
            feat_rows.append(
                (k, side, rank, names[j], label(names[j]), float(r_s[j]), float(r_ref[j]),
                 float(z[j]))
            )  # fmt: skip
    speakers = pd.DataFrame(spk_rows, columns=SPEAKER_COLUMNS).sort_values(
        "effect", ascending=False, ignore_index=True
    )
    features = pd.DataFrame(feat_rows, columns=FEATURE_COLUMNS)

    # pairs: the speakers, the narrator and unattributed speech
    narr = ((info.ttype == "N") & (nw > 0)).to_numpy()
    unattr = (speech & info.key.isna()).to_numpy()
    group_keys = [*keys, NARRATOR, UNATTRIBUTED]
    group_rates = np.vstack(
        [rates(s_sum[:n_keep], s_w[:n_keep])]
        + [rates(x[m].sum(axis=0), nw[m].sum())[None] for m in (narr, unattr)]
    )
    d = delta(group_rates[:, None, :], group_rates[None, :, :], sd)
    iu = np.triu_indices(len(group_keys), k=1)
    pairs = pd.DataFrame(
        {"a": np.array(group_keys)[iu[0]], "b": np.array(group_keys)[iu[1]], "delta": d[iu]}
    )
    from bsim.analysis.stylometry import cluster_order

    order = [group_keys[i] for i in cluster_order(d)] if len(group_keys) > 2 else group_keys

    # checks fixed in advance
    authors = []
    for spec, a_books, b_books in author_specs:
        mine = (speech & (info.key == spec["speaker"])).to_numpy()
        in_a, in_b = np.isin(info.book, a_books), np.isin(info.book, b_books)
        c = author_check(
            x, nw, mine & in_a, mine & in_b, narr & in_a, narr & in_b, sd, vc["shuffles"], rng
        )
        authors.append(
            {"speaker": spec["speaker"], "a": spec["a"], "b": spec["b"], **c,
             "verdict": verdict(c, vc["min_words"])}
        )  # fmt: skip
    distinct = []
    for spec, b in distinct_specs:
        in_book = speakers[speakers.main_book == b]
        ranking = in_book.key.tolist()
        distinct.append(
            {
                "book": spec["book"],
                "speaker": spec["speaker"],
                "rank": ranking.index(spec["speaker"]) + 1 if spec["speaker"] in ranking else None,
                "of": len(ranking),
                "ranking": [
                    {"key": k, "effect": round(e, 2), "q": round(q, 4)}
                    for k, e, q in zip(in_book.key, in_book.effect, in_book.q, strict=True)
                ],
            }
        )

    meta.update(
        {
            "speakers": n_keep,
            "features": len(names),
            "speech_clauses": len(rows),
            "words": {
                "attributed": int(nw[pool.to_numpy()].sum()),
                "profiled": int(s_w[:n_keep].sum()),
                "excluded": int(nw[(pool & excluded).to_numpy()].sum()),
                "narration": int(nw[narr].sum()),
                "unattributed": int(nw[unattr].sum()),
            },
            "significant": int((speakers.q <= 0.05).sum()),
            "calibration": {
                "significant": int((res["q_calibration"] <= 0.05).sum()),
                "of": n_keep,
            },
            "sensitivity": sensitivity,
            "order": order,
            "checks": {"author": authors, "distinct": distinct},
            "seconds": round(time.perf_counter() - t0, 1),
        }
    )
    _write(out, speakers, features, pairs, meta)
    log(
        f"{n_keep} speakers over {len(rows)} speech clauses; {meta['significant']} distinct at"
        f" q <= 0.05 (calibration shuffle: {meta['calibration']['significant']});"
        f" explicit-only rho {sensitivity['rho']}"
    )
    for c in authors:
        log(
            f"  author {c['speaker']} {'+'.join(c['a'])} / {'+'.join(c['b'])}:"
            f" cross {c['cross']} (p {c['p_cross']}), d_ab {c['d_ab']} (p {c['p_ab']}),"
            f" words {c['words_a']} / {c['words_b']} -> {c['verdict']}"
        )
    for c in distinct:
        log(f"  distinct in {c['book']}: {c['speaker']} rank {c['rank']} of {c['of']}")
    log(f"done in {meta['seconds']} s -> {out}")
    return out
