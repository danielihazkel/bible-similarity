"""`bsim roots`: root families, words of one root side by side, and Leitworte counted by root
(DESIGN.md §16.38).

A Hebrew root (ב־ר־ך) gives a verb (ברך, to bless), nouns (ברכה, a blessing) and more; Buber's
Leitwort is a root repeated through a passage, and the figure *etymologica* sets two words of one
root side by side (ויחלם חלום, he dreamt a dream). The concordance and the Leitworte of §16.2 key
on lemmas, which splits a root into its words.

- **Families.** OpenScriptures HebrewStrong.xml derives most entries from another (`from 1288`,
  `the same as`, `feminine of`, ...); each derivation chain is followed to its top. Strong's
  etymologies are often guesses (בית and אבן "from" בנה), so a word joins its top root only when
  it is the root's strong radicals in a Hebrew shape (`holds`: one prefix letter, vowel letters
  between, a common ending): ה ו י may drop out anywhere and נ as the first radical; a root
  with fewer than `min_radicals` strong radicals (היה, נוה) keeps no family.
  Aramaic entries, links "corresponding to" or "compare", and proper names (OSHB `Np`) stay
  outside the families.
- **Words of one root side by side** (Hebrew words of one verse at most `window` words apart):
  `cognate` = a verb and a common noun of one family (different lemmas); `other` = two other
  words of one family (different lemmas); `inf_abs` = an infinitive absolute with a finite verb of
  the same lemma (מות יומת). The cognate and other counts are set against the content words
  permuted within each chapter (`shuffles`); infinitive absolutes are counted only (a grammatical
  construction, not a choice of words).
  The derivations that still pass and are wrong (the numerals "from" שעה) are listed in
  `exclude`.
- **Leitworte by root.** Each chapter's content words are counted by family (names and the
  `structure.leitwort_skip_pos` parts of speech left out) and ranked by Dunning's G² against the
  corpus, as §16.2 ranks lemmas. Checks fixed in advance (`known`): Leitworte scholarship names,
  whose rank by root is compared with the best rank of any of their lemmas. *Hidden* Leitworte:
  roots in a chapter's top `structure.leitwort_top` that gather two or more words (Strong's
  numbers) there, none of which is in the top by lemma.

Writes `artifacts/roots/`: `lemmas.parquet` (`lemma, strong, root, root_he, link`: every content
lemma of the corpus, its family and the root's Strong's headword), `pairs.parquet` (`verse_id,
a_idx, b_idx, root, kind, a_lemma, b_lemma`), `books.parquet` (per book: cognate pairs observed
and expected, infinitive absolutes), `leitworte.parquet` (per chapter its top roots: `unit_id,
rank, root, count, g2, n_words, lemma_rank, hidden`) and `roots.meta.json`.
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from lxml import etree

from bsim.analysis.stats import empirical_p, shuffle_within
from bsim.analysis.structure import leitworte
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BY_OSIS
from bsim.data.lexicon import strong_key
from bsim.text.normalize import consonantal, fold_finals

Log = Callable[[str], None]

WEAK = set("הוי")  # א is kept: it stays written where it is a radical
LINK = re.compile(
    r"(from|the same as|feminine of|plural of|dual of|form of|variation of|participle of|for)$"
)
BLOCK = re.compile(r"(corresponding to|compare|see|with|and)$")
FINITE = set("pqiwhjv")  # OSHB conjugations perfect … imperative (no participle, infinitive)
KINDS = ("cognate", "other", "inf_abs")
PAIR_COLUMNS = ["verse_id", "a_idx", "b_idx", "root", "kind", "a_lemma", "b_lemma"]


def consonants(word: str) -> str:
    return fold_finals(consonantal(word)).replace(" ", "")


def radicals(root: str) -> list[str]:
    """The strong radicals of a root, in order: weak letters (ה ו י, a first נ) and a doubled
    letter left out."""
    out: list[str] = []
    for i, ch in enumerate(consonants(root)):
        if ch in WEAK or (ch == "נ" and i == 0) or (out and out[-1] == ch):
            continue
        out.append(ch)
    return out


PREFIX = "[מתאינה]?"
SUFFIX = "(ה|ת|ית|ות|ימ|ינ|נ|ונ|י|ני|נה|מ)?"  # finals folded, as `consonants` writes them


def holds(word: str, rads: list[str]) -> bool:
    """Whether a word is the root in the shape of a Hebrew noun or verb: at most one prefix
    letter (מ ת א י נ ה), the radicals in order with only weak letters (א ה ו י) or a doubled
    radical between them, the radicals twice over (pilpel: גלגל) or once, and a common ending."""
    core = "[אהוי]*".join(f"{re.escape(r)}{re.escape(r)}?" for r in rads)
    pattern = f"^{PREFIX}[אהוי]*({core})([אהוי]*{core})?[אהוי]*{SUFFIX}$"
    return re.match(pattern, consonants(word)) is not None


def read_derivations(path: Path) -> pd.DataFrame:
    """Every HebrewStrong.xml entry: `strong, word` (the Hebrew headword), `pos`, `aramaic`, and the
    entry it is derived from (`parent`, `link`: the phrase before it), or None."""
    root = etree.parse(str(path)).getroot()
    ns = root.nsmap[None]
    w_tag = f"{{{ns}}}w"
    rows = []
    for e in root.iterfind(f"{{{ns}}}entry"):
        w = e.find(w_tag)
        head = (w.text or "") if w is not None else ""
        pos = (w.get("pos") or "") if w is not None else ""
        src = e.find(f"{{{ns}}}source")
        text = (src.text or "") if src is not None else ""
        aramaic = text.strip().lower().startswith("(aramaic)")
        parent = link = None
        if src is not None and not aramaic:
            for ch in src:
                if ch.tag == w_tag and ch.get("src"):
                    before = re.sub(r"\s+", " ", text.lower()).strip(" ;,")
                    m = LINK.search(before)
                    if m and not BLOCK.search(before):
                        parent, link = strong_key(ch.get("src")), m.group(1)
                    break
                text += (ch.text or "") + (ch.tail or "")
        if link and re.search(r"patronym|patrial|gentilic", text.lower()):
            parent = link = None  # a gentilic or a family name, not a word of the root
        rows.append((strong_key(e.get("id")), head, pos, aramaic, parent, link))
    df = pd.DataFrame(rows, columns=["strong", "word", "pos", "aramaic", "parent", "link"])
    return df.drop_duplicates("strong").reset_index(drop=True)


def families(
    der: pd.DataFrame,
    min_radicals: int,
    max_depth: int = 2,
    exclude: frozenset[str] = frozenset(),
) -> dict[str, str]:
    """Strong number -> its root's, for the entries whose chain ends at a root they agree with
    (the others, and roots themselves, are left out: they are their own family). A chain of more
    than `max_depth` links is not followed (Strong's longest chains are its guesses: אלהים →
    אלוה → אל → איל → אול). Proper names neither join a family nor head one; `exclude` lists
    entries kept out by hand."""
    parent = dict(zip(der.strong, der.parent, strict=True))
    head = dict(zip(der.strong, der.word, strict=True))
    # a name only when every part of speech Strong gives is one (גדול is `a n-pr-m`)
    name = {
        k for k, p in zip(der.strong, der.pos, strict=True)
        if p and all("pr" in t for t in p.split())
    }
    out = {}
    for k in der.strong:
        if k in name or k in exclude:
            continue
        seen, r = {k}, k
        while parent.get(r) and parent[r] not in seen and parent[r] in head:
            r = parent[r]
            seen.add(r)
        if r == k or r in name or len(seen) - 1 > max_depth:
            continue
        rads = radicals(head[r])
        if len(rads) >= min_radicals and holds(head[k], rads):
            out[k] = r
    return out


def tokens(words: pd.DataFrame, family: dict[str, str]) -> pd.DataFrame:
    """One row per Hebrew content morpheme: `verse_id, idx, lemma, root, pos` (first morph
    letter; `p` for a proper name), `conj` (verb conjugation letter or '')."""
    rows = []
    for vid, idx, lemma, morph in zip(
        words.verse_id, words.idx, words.lemma, words.morph, strict=True
    ):
        if not isinstance(morph, str) or not morph.startswith("H"):
            continue  # Aramaic, or no morphology
        for part, m in zip(str(lemma).split("/"), morph[1:].split("/"), strict=False):
            lem = part.replace(" ", "")
            if not lem[:1].isdigit() or not m:
                continue
            pos = "p" if m.startswith("Np") else m[0]
            conj = m[2] if m[0] == "V" and len(m) > 2 else ""
            sk = strong_key(lem)
            root = sk if pos == "p" else family.get(sk, sk)
            rows.append((int(vid), int(idx), lem, root, pos, conj))
    return pd.DataFrame(rows, columns=["verse_id", "idx", "lemma", "root", "pos", "conj"])


def pair_mask(
    vid: np.ndarray, idx: np.ndarray, d: int, window: int
) -> tuple[np.ndarray, np.ndarray]:
    """Index pairs (i, i + d) of tokens in one verse at most `window` words apart."""
    a = np.arange(len(vid) - d)
    b = a + d
    gap = idx[b] - idx[a]
    ok = (vid[a] == vid[b]) & (gap >= 1) & (gap <= window)
    return a[ok], b[ok]


def find_pairs(t: pd.DataFrame, window: int) -> pd.DataFrame:
    """`PAIR_COLUMNS` of every same-root pair (tokens in verse order)."""
    vid, idx = t.verse_id.to_numpy(), t.idx.to_numpy()
    root, lemma = t.root.to_numpy(), t.lemma.to_numpy()
    pos, conj = t.pos.to_numpy(), t.conj.to_numpy()
    rows = []
    for d in range(1, window + 2):
        a, b = pair_mask(vid, idx, d, window)
        for i, j in zip(a, b, strict=True):
            if root[i] != root[j] or pos[i] == "p":
                continue
            kind = _kind(pos[i], pos[j], conj[i], conj[j], lemma[i] == lemma[j])
            if kind:
                rows.append(
                    (int(vid[i]), int(idx[i]), int(idx[j]), root[i], kind, lemma[i], lemma[j])
                )
    df = pd.DataFrame(rows, columns=PAIR_COLUMNS)
    return df.sort_values(["verse_id", "a_idx", "b_idx"]).reset_index(drop=True)


def _kind(pa: str, pb: str, ca: str, cb: str, same: bool) -> str | None:
    if same:
        if pa == pb == "V" and {ca, cb} & {"a"} and ({ca, cb} - {"a"}) <= FINITE and ca != cb:
            return "inf_abs"
        return None
    if {pa, pb} == {"V", "N"}:
        return "cognate"
    if pa in "VNA" and pb in "VNA":
        return "other"
    return None


def count_pairs(
    vid: np.ndarray,
    idx: np.ndarray,
    root: np.ndarray,
    lemma: np.ndarray,
    pos: np.ndarray,
    window: int,
    book: np.ndarray,
    n_books: int,
) -> dict[str, np.ndarray]:
    """Cognate and other pairs per book (vectorised; the shuffles use it)."""
    out = {k: np.zeros(n_books, dtype=np.int64) for k in ("cognate", "other")}
    content = np.isin(pos, ["V", "N", "A"])
    for d in range(1, window + 2):
        a, b = pair_mask(vid, idx, d, window)
        ok = (root[a] == root[b]) & (lemma[a] != lemma[b]) & content[a] & content[b]
        a, b = a[ok], b[ok]
        cog = ((pos[a] == "V") & (pos[b] == "N")) | ((pos[a] == "N") & (pos[b] == "V"))
        out["cognate"] += np.bincount(book[a[cog]], minlength=n_books)
        out["other"] += np.bincount(book[a[~cog]], minlength=n_books)
    return out


def chapter_key(ref: str) -> tuple[int, int]:
    """`Gen 27` -> (book_id, 27)."""
    osis, chapter = ref.rsplit(" ", 1)
    if osis not in BY_OSIS:
        raise RuntimeError(f"roots.known: unknown book {osis!r}")
    return BY_OSIS[osis].book_id, int(chapter)


def run_roots(cfg: dict[str, Any], log: Log = print) -> Path:
    rc, sc = cfg["roots"], cfg["structure"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    raw = resolve_path(cfg, "data_raw")
    out = art / "roots"
    t0 = time.perf_counter()
    rng = np.random.default_rng(rc["seed"])
    path = raw / "lexicon" / "HebrewStrong.xml"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim download --only lexicon` first")
    der = read_derivations(path)
    family = families(
        der, rc["min_radicals"], rc["max_depth"], frozenset(str(x) for x in rc["exclude"])
    )
    head = dict(zip(der.strong, der.word, strict=True))

    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter"])
    words = pd.read_parquet(proc / "words.parquet", columns=["verse_id", "idx", "lemma", "morph"])
    t = tokens(words.sort_values(["verse_id", "idx"]), family)
    book_of = dict(zip(verses.verse_id, verses.book_id, strict=True))
    chap_of = dict(zip(verses.verse_id, verses.book_id * 1000 + verses.chapter, strict=True))

    lemmas = (
        t[t.pos != "p"][["lemma", "root"]].drop_duplicates("lemma").assign(
            strong=lambda d: d.lemma.map(strong_key),
        )
    )
    der_link = dict(zip(der.strong, der.link, strict=True))
    lemmas["link"] = [der_link.get(s) if s in family else None for s in lemmas.strong]
    lemmas["root_he"] = lemmas.root.map(head).fillna("")
    lemmas = lemmas.sort_values("lemma")[["lemma", "strong", "root", "root_he", "link"]]

    # words of one root side by side, against the content words permuted within chapters
    pairs = find_pairs(t, rc["window"])
    n_books = int(verses.book_id.max()) + 1
    vid, idx = t.verse_id.to_numpy(), t.idx.to_numpy()
    book = t.verse_id.map(book_of).to_numpy()
    codes = {c: pd.factorize(t[c])[0] for c in ("root", "lemma", "pos")}
    pos_letters = np.array(["V", "N", "A"])
    pos_codes = {p: (t.pos == p).to_numpy() for p in pos_letters}
    pos_arr = np.select([pos_codes[p] for p in pos_letters], pos_letters, default="x")
    observed = count_pairs(
        vid, idx, codes["root"], codes["lemma"], pos_arr, rc["window"], book, n_books
    )
    groups = t.verse_id.map(chap_of).to_numpy()
    null = {k: [] for k in observed}
    for _ in range(rc["shuffles"]):
        perm = shuffle_within(groups, rng)
        c = count_pairs(vid, idx, codes["root"][perm], codes["lemma"][perm], pos_arr[perm],
                        rc["window"], book, n_books)  # fmt: skip
        for k in null:
            null[k].append(c[k])
    tests = {}
    for k in observed:
        tot = np.array([n.sum() for n in null[k]])
        tests[k] = {
            "observed": int(observed[k].sum()),
            "expected": float(tot.mean()),
            "ratio": float(observed[k].sum() / max(tot.mean(), 1e-9)),
            "p": empirical_p(observed[k].sum(), tot),
        }
    expected_book = np.mean(null["cognate"], axis=0)
    inf_abs = np.bincount(pairs[pairs.kind == "inf_abs"].verse_id.map(book_of), minlength=n_books)
    hebrew_words = np.bincount(t.drop_duplicates(["verse_id", "idx"]).verse_id.map(book_of),
                               minlength=n_books)  # fmt: skip
    books = pd.DataFrame(
        {
            "book_id": range(n_books),
            "words": hebrew_words,
            "cognate": observed["cognate"],
            "expected": expected_book,
            "inf_abs": inf_abs,
        }
    )

    # Leitworte by root
    units = pd.read_parquet(proc / "units.parquet")
    chapters = units[units.unit_type == "chapter"]
    skip = set(sc["leitwort_skip_pos"])
    keep = t[~t.pos.isin(skip)]
    lemma_corpus = Counter(keep.lemma)
    root_key = np.where(keep.pos == "p", keep.lemma, keep.root)
    keep = keep.assign(rkey=root_key)
    root_corpus = Counter(keep.rkey)
    total = len(keep)
    by_verse = {v: g for v, g in keep.groupby("verse_id")}
    lw_rows = []
    known_keys = {chapter_key(c): None for c, _ in rc["known"]}
    ranks: dict[tuple[int, int], tuple[list, list]] = {}
    for u in chapters.itertuples(index=False):
        parts = [by_verse[v] for v in range(u.start_verse_id, u.end_verse_id + 1) if v in by_verse]
        if not parts:
            continue
        g = pd.concat(parts)
        lem_rank = leitworte(Counter(g.lemma), lemma_corpus, total, sc["leitwort_min_count"], 10**6)
        root_rank = leitworte(Counter(g.rkey), root_corpus, total, sc["leitwort_min_count"], 10**6)
        key = (int(u.book_id), int(u.unit_id.rsplit(":", 1)[1]))
        if key in known_keys:
            ranks[key] = (lem_rank, root_rank)
        lem_pos = {k.lemma: i + 1 for i, k in enumerate(lem_rank)}
        members = g.groupby("rkey").lemma.agg(lambda s: sorted(set(s)))
        for r, kw in enumerate(root_rank[: sc["leitwort_top"]], start=1):
            best = min((lem_pos[m] for m in members[kw.lemma] if m in lem_pos), default=None)
            n_words = len({strong_key(m) for m in members[kw.lemma]})  # a word's senses: once
            hidden = n_words > 1 and (best is None or best > sc["leitwort_top"])
            lw_rows.append((u.unit_id, r, kw.lemma, kw.count, kw.g2, n_words, best, hidden))
    lw = pd.DataFrame(
        lw_rows,
        columns=["unit_id", "rank", "root", "count", "g2", "n_words", "lemma_rank", "hidden"],
    ).astype({"lemma_rank": "Int64"})

    known = []
    for ref, root in rc["known"]:
        key, root = chapter_key(ref), str(root)
        lem_rank, root_rank = ranks.get(key, ([], []))
        fam = {lem for lem, r in zip(lemmas.lemma, lemmas.root, strict=True) if r == root}
        lem_best = min(
            (i + 1 for i, k in enumerate(lem_rank) if k.lemma in fam), default=None
        )
        r_rank = next((i + 1 for i, k in enumerate(root_rank) if k.lemma == root), None)
        known.append({"chapter": ref, "book_id": key[0], "chapter_no": key[1], "root": root,
                      "he": head.get(root, ""), "lemma_rank": lem_best,
                      "root_rank": r_rank})  # fmt: skip
    top = sc["leitwort_top"]

    def in_top(r: int | None) -> bool:
        return r is not None and r <= top

    out.mkdir(parents=True, exist_ok=True)
    lemmas.to_parquet(out / "lemmas.parquet")
    pairs.to_parquet(out / "pairs.parquet")
    books.to_parquet(out / "books.parquet")
    lw.to_parquet(out / "leitworte.parquet")
    fam_sizes = lemmas.groupby("root").size()
    meta = {
        "config_hash": config_hash(cfg, "roots", "structure"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "entries": int(len(der)),
        "derived": int(der.parent.notna().sum()),
        "joined": int(len(family)),
        "lemmas": int(len(lemmas)),
        "families": int((fam_sizes > 1).sum()),
        "family_lemmas": int(fam_sizes[fam_sizes > 1].sum()),
        "window": rc["window"],
        "shuffles": rc["shuffles"],
        "pairs": {k: int((pairs.kind == k).sum()) for k in KINDS},
        "tests": _round(tests),
        "known": known,
        "known_top_lemma": sum(in_top(k["lemma_rank"]) for k in known),
        "known_top_root": sum(in_top(k["root_rank"]) for k in known),
        "known_better": sum(
            (k["root_rank"] or 10**6) < (k["lemma_rank"] or 10**6) for k in known
        ),
        "top": top,
        "hidden": int(lw.hidden.sum()),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "roots.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
    c = tests["cognate"]
    log(
        f"done: {meta['families']} families over {meta['family_lemmas']} lemmas; cognate pairs"
        f" {c['observed']} vs {c['expected']:.0f} by chance (p {c['p']}); known Leitworte in the"
        f" top {top}: {meta['known_top_root']} by root vs {meta['known_top_lemma']} by lemma;"
        f" {meta['hidden']} hidden ({meta['seconds']} s) -> {out}"
    )
    return out


def _round(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _round(v) for k, v in x.items()}
    if isinstance(x, float):
        return float(f"{x:.6g}")
    return x
