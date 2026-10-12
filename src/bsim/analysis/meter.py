"""`bsim meter`: stresses per line from the te'amim, and the falling line of the lament (DESIGN.md
§16.37).

Hebrew verse is usually counted by stresses: every accented word carries one, words joined by a
maqaf share one. The lament (*qinah*) line is said to fall, a longer member followed by a shorter
one (3:2, Budde), and Lamentations 1–4 to be written in it.

- **Stresses.** A display token carries a stress when it has a letter and does not end in a maqaf
  (paseq, sof pasuq and dashes carry none).
- **Lines.** The accents divide a verse by continuous dichotomy: a span splits at its strongest
  pause (`text.accents.token_levels`), the first of equal pauses being the greater (Wickes), and
  each part splits again. A verse is cut top-down into lines, the largest spans of at most
  `max_stresses` stresses; a line splits at its own strongest pause into two members of `a` and
  `b` stresses. Lines of `min_stresses`…`max_stresses` with both members stressed are measured.
- **Net fall** of a chapter: the share of its measured lines with `a > b` minus the share with
  `a < b`. The lament predicts both more falling and fewer rising lines; balanced lines are
  neutral.

The test, fixed in advance: the mean net fall of the `test` chapters (Lamentations 1–4) against
the same number of chapters drawn from the test chapters and a pool of other poetry, without
replacement (`shuffles`). Lamentations is accented with the prose system, which makes lines fall
by itself (a short last member before silluq or etnahta), so the pool is poetry under the same
accents: the prose-accented chapters (outside the test and control chapters) whose mean
probability of parallel halves (`bsim parallelism`) is in the top `pool_quantile`. The same test
is run against the chapters of the poetic accent books (Psalms, Proverbs, Job) and, for
robustness, over a `grid` of line lengths. Two more checks: the `control` chapter (Lamentations 5,
a lament not in the falling line) is placed among the pool chapters, and the chapters outside
Lamentations that use the noun קינה (`lament_lemma`) are tested against the pool like the test
chapters.

Writes `artifacts/meter/`: `lines.parquet` (every line of every verse: `verse_id, idx, first,
last` inclusive display-token span, `stresses`, `a`, `b`; `a` / `b` NULL when the line does not
split into two stressed members), `chapters.parquet` (`book_id, chapter, group` test | control |
pool | poetic | prose, `n_lines, fall, rise, net, share32, prob, pct` = share of pool chapters
with a lower net fall) and `meter.meta.json`.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.stats import empirical_p
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS, BY_OSIS
from bsim.text.accents import POETIC_BOOKS, poetic, token_levels

Log = Callable[[str], None]

MAQAF = "־"
LETTER = re.compile("[א-ת]")
LINE_COLUMNS = ["verse_id", "idx", "first", "last", "stresses", "a", "b"]
CHAPTER_COLUMNS = [
    "book_id",
    "chapter",
    "group",
    "n_lines",
    "fall",
    "rise",
    "net",
    "share32",
    "prob",
    "pct",
]


def stresses(tokens: Sequence[str]) -> list[int]:
    """1 for a display token that carries a stress: a word not joined to the next by a maqaf."""
    return [int(bool(LETTER.search(t)) and not t.endswith(MAQAF)) for t in tokens]


def main_pause(levels: Sequence[int], lo: int, hi: int) -> int | None:
    """The token after which the span lo..hi (inclusive) divides: its strongest pause, the first
    of equal ones; None when no pause falls inside it."""
    best = None
    for i in range(lo, hi):
        if levels[i] > 0 and (best is None or levels[i] < levels[best]):
            best = i
    return best


def lines(
    tokens: Sequence[str], is_poetic: bool, max_stresses: int
) -> list[tuple[int, int, int, int | None, int | None]]:
    """The verse cut top-down into lines of at most `max_stresses` stresses (or spans no pause
    divides): `(first, last, stresses, a, b)`, `a` / `b` the stresses of the line's two members
    (None when it does not split, or one member has no stress)."""
    if not tokens:
        return []
    st = stresses(tokens)
    lv = token_levels(list(tokens), is_poetic)
    out: list[tuple[int, int, int, int | None, int | None]] = []

    def cut(lo: int, hi: int) -> None:
        tot = sum(st[lo : hi + 1])
        mid = main_pause(lv, lo, hi)
        if tot > max_stresses and mid is not None:
            cut(lo, mid)
            cut(mid + 1, hi)
            return
        a = b = None
        if mid is not None:
            a, b = sum(st[lo : mid + 1]), sum(st[mid + 1 : hi + 1])
            if not a or not b:
                a = b = None
        out.append((lo, hi, tot, a, b))

    cut(0, len(tokens) - 1)
    return out


def verse_lines(verses: pd.DataFrame, max_stresses: int) -> pd.DataFrame:
    """`LINE_COLUMNS` for every verse (`verse_id, osis, chapter, verse, display_tokens`)."""
    rows = []
    for r in verses.itertuples(index=False):
        toks = list(r.display_tokens)
        for i, (lo, hi, tot, a, b) in enumerate(
            lines(toks, poetic(r.book, r.chapter, r.verse), max_stresses)
        ):
            rows.append((int(r.verse_id), i, lo, hi, tot, a, b))
    df = pd.DataFrame(rows, columns=LINE_COLUMNS)
    return df.astype({"a": "Int64", "b": "Int64"})


def chapter_rates(lines_df: pd.DataFrame, chapter_of: pd.Series, lo: int, hi: int) -> pd.DataFrame:
    """Per chapter key: measured lines (`lo`…`hi` stresses, both members stressed) and the shares
    falling, rising, net (fall - rise) and exactly 3:2."""
    m = lines_df[lines_df.a.notna() & lines_df.stresses.between(lo, hi)]
    a, b = m.a.astype(int), m.b.astype(int)
    d = pd.DataFrame(
        {
            "key": m.verse_id.map(chapter_of).to_numpy(),
            "fall": (a > b).astype(float).to_numpy(),
            "rise": (a < b).astype(float).to_numpy(),
            "share32": ((a == 3) & (b == 2)).astype(float).to_numpy(),
        }
    )
    g = d.groupby("key")
    out = g[["fall", "rise", "share32"]].mean()
    out["n_lines"] = g.size()
    out["net"] = out.fall - out.rise
    return out


def group_test(
    net: pd.Series, test: list[Any], pool: list[Any], reps: int, rng: np.random.Generator
) -> dict[str, Any]:
    """Mean net fall of the `test` keys against equally many keys drawn without replacement from
    test + pool (the group label permuted)."""
    t = net.reindex(test).dropna()
    p = net.reindex(pool).dropna()
    if not len(t) or not len(p):
        return {"n": int(len(t)), "pool_n": int(len(p)), "mean": None, "pool_mean": None, "p": None}
    both = np.r_[t.to_numpy(), p.to_numpy()]
    obs = float(t.mean())
    null = np.array([rng.choice(both, len(t), replace=False).mean() for _ in range(reps)])
    return {
        "n": int(len(t)),
        "pool_n": int(len(p)),
        "mean": obs,
        "pool_mean": float(p.mean()),
        "null_mean": float(null.mean()),
        "p": empirical_p(obs, null),
    }


def chapter_keys(spec: dict[str, list[int]]) -> list[tuple[int, int]]:
    """`{osis: [chapter, …]}` from the config as (book_id, chapter) keys."""
    return [(BY_OSIS[o].book_id, int(c)) for o, cs in spec.items() for c in cs]


def run_meter(cfg: dict[str, Any], log: Log = print) -> Path:
    mc = cfg["meter"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "meter"
    t0 = time.perf_counter()
    rng = np.random.default_rng(mc["seed"])
    osis = {b.book_id: b.osis for b in BOOKS}
    verses = pd.read_parquet(
        proc / "verses.parquet",
        columns=["verse_id", "book_id", "chapter", "verse", "display_tokens"],
    ).sort_values("verse_id")
    verses["book"] = verses.book_id.map(osis)
    chapter_of = pd.Series(
        list(zip(verses.book_id, verses.chapter, strict=True)), index=verses.verse_id
    )

    lo, hi = mc["min_stresses"], mc["max_stresses"]
    # each line limit of the grid cuts the verses its own way; the stored lines use `hi`
    by_limit = {h: verse_lines(verses, h) for h in sorted({hi, *(h for _, h in mc["grid"])})}
    lines_df = by_limit[hi]

    # chapter groups
    par_path = art / "parallelism" / "verses.parquet"
    if not par_path.exists():
        raise RuntimeError(f"{par_path} missing; run `bsim parallelism` first")
    par = pd.read_parquet(par_path, columns=["verse_id", "prob"])
    prob = par.assign(key=par.verse_id.map(chapter_of)).groupby("key").prob.mean()
    test, control = chapter_keys(mc["test"]), chapter_keys(mc["control"])
    emet_books = {BY_OSIS[o].book_id for o in POETIC_BOOKS}
    all_keys = list(dict.fromkeys(chapter_of.tolist()))
    prose_acc = [k for k in all_keys if k[0] not in emet_books and k not in test + control]
    cut = prob.reindex(prose_acc).quantile(mc["pool_quantile"])
    pool_set = {k for k in prose_acc if prob.get(k, np.nan) >= cut}

    def group(k: tuple[int, int]) -> str:
        if k in test:
            return "test"
        if k in control:
            return "control"
        if k in pool_set:
            return "pool"
        return "poetic" if k[0] in emet_books else "prose"

    def tests(rates: pd.DataFrame) -> dict[str, Any]:
        ok = rates[rates.n_lines >= mc["min_lines"]].net
        keys = [k for k in ok.index if k not in test + control]
        pool = [k for k in keys if k in pool_set]
        emet = [k for k in keys if k[0] in emet_books]
        return {
            "pool": group_test(ok, test, pool, mc["shuffles"], rng),
            "poetic": group_test(ok, test, emet, mc["shuffles"], rng),
        }

    rates = chapter_rates(lines_df, chapter_of, lo, hi)
    main = tests(rates)
    grid = []
    for g_lo, g_hi in mc["grid"]:
        t = tests(chapter_rates(by_limit[g_hi], chapter_of, g_lo, g_hi))
        grid.append({"min": g_lo, "max": g_hi, "mean": t["pool"]["mean"],
                     "pool_mean": t["pool"]["pool_mean"], "pool_p": t["pool"]["p"],
                     "poetic_p": t["poetic"]["p"]})  # fmt: skip

    measured = rates[rates.n_lines >= mc["min_lines"]]
    pool_net = measured.net.reindex(sorted(pool_set)).dropna().to_numpy()

    def pct(x: float) -> float | None:
        return float((pool_net < x).mean()) if len(pool_net) else None

    control_rows = [
        {"book_id": k[0], "chapter": k[1], "net": float(rates.net[k]), "pct": pct(rates.net[k]),
         "n_lines": int(rates.n_lines[k])}
        for k in control if k in rates.index
    ]  # fmt: skip
    test_rows = [
        {"book_id": k[0], "chapter": k[1], "net": float(rates.net[k]), "pct": pct(rates.net[k]),
         "n_lines": int(rates.n_lines[k])}
        for k in test if k in rates.index
    ]  # fmt: skip

    # chapters that name a lament (קינה), outside the test and control chapters
    words = pd.read_parquet(proc / "words.parquet", columns=["verse_id", "content_lemmas"])
    w = words.explode("content_lemmas").dropna()
    lemma = w.content_lemmas.str.replace(r"[a-z]+$", "", regex=True)
    named_keys = sorted(
        {chapter_of[v] for v in w.verse_id[lemma == str(mc["lament_lemma"])]} - set(test + control)
    )
    named_ok = [k for k in named_keys if k in measured.index]
    named = group_test(
        measured.net,
        named_ok,
        [k for k in measured.index if k in pool_set and k not in named_ok],
        mc["shuffles"],
        rng,
    )
    named["chapters"] = [
        {"book_id": k[0], "chapter": k[1], "net": float(rates.net[k]), "pct": pct(rates.net[k]),
         "n_lines": int(rates.n_lines[k])}
        for k in named_keys if k in rates.index
    ]  # fmt: skip

    ch = rates.reset_index()
    ch[["book_id", "chapter"]] = pd.DataFrame(ch.key.tolist(), index=ch.index)
    ch["group"] = ch.key.map(group)
    ch["prob"] = ch.key.map(prob)
    ch["pct"] = [pct(x) for x in ch.net]
    ch = ch.sort_values(["book_id", "chapter"])[CHAPTER_COLUMNS]
    stored = lines_df.copy()

    pattern_counts = lines_df[lines_df.a.notna() & lines_df.stresses.between(lo, hi)].assign(
        key=lambda d: d.verse_id.map(chapter_of)
    )
    by_group = {}
    for name in ("test", "control", "pool", "poetic", "prose"):
        keys = set(ch[ch.group == name].apply(lambda r: (r.book_id, r.chapter), axis=1))
        sub = pattern_counts[pattern_counts.key.isin(keys)]
        a, b = sub.a.astype(int), sub.b.astype(int)
        top = (a.astype(str) + ":" + b.astype(str)).value_counts().head(mc["top_patterns"])
        by_group[name] = {
            "chapters": len(keys),
            "lines": int(len(sub)),
            "fall": float((a > b).mean()) if len(sub) else None,
            "rise": float((a < b).mean()) if len(sub) else None,
            "patterns": [[p, int(n)] for p, n in top.items()],
        }

    out.mkdir(parents=True, exist_ok=True)
    stored.to_parquet(out / "lines.parquet")
    ch.to_parquet(out / "chapters.parquet")
    meta = {
        "config_hash": config_hash(cfg, "meter", "parallelism"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "min_stresses": lo,
        "max_stresses": hi,
        "min_lines": mc["min_lines"],
        "pool_quantile": mc["pool_quantile"],
        "pool_prob": float(cut),
        "lines": int(len(lines_df)),
        "split": int(lines_df.a.notna().sum()),
        "test": _round(main["pool"]),
        "test_poetic": _round(main["poetic"]),
        "test_chapters": _round(test_rows),
        "control": _round(control_rows),
        "named": _round(named),
        "grid": _round(grid),
        "groups": _round(by_group),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "meter.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    t = main["pool"]
    log(
        f"done: {len(lines_df)} lines, {meta['split']} split; test net fall {t['mean']}"
        f" vs pool {t['pool_mean']} (p {t['p']}), vs poetic books p {main['poetic']['p']};"
        f" named laments p {named['p']} ({meta['seconds']} s) -> {out}"
    )
    return out


def _round(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _round(v) for k, v in x.items()}
    if isinstance(x, list | tuple):
        return [_round(v) for v in x]
    if isinstance(x, float | np.floating):
        return float(f"{float(x):.6g}")
    if isinstance(x, np.integer):
        return int(x)
    return x
