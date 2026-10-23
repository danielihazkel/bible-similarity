"""The workbench (DESIGN.md §16.64): your own sets of words, contrasted and tested.

A *set* is written as items separated by `;`, their verses joined:

    book:1            a book (canon id); book:1-5 a run of books
    chapters:27:42-83 chapters of a book (here Psalms 42–83); chapters:0:1 one chapter
    section:torah     torah | prophets | writings
    unit:p:Noach      any unit of the results DB (verse, chapter, pericope, parasha)
    collection:3      a collection of your notebook (§16.47)
    pattern:[lemma=430] ..2 [lemma=3068]   the verses where a pattern query (§16.46) matches
    only:speech       a filter, not a part: of those verses' words, only direct speech
                      (or only:narration)

**Contrast** counts a feature of the words (lemma, root, SDBH domain, part of speech, stem, verb
form, person, phrase function, clause type) in set A and in set B — by default every other word —
and scores each value by Dunning's G² over the 2 × 2 table (its words against the rest, A against
B), with its p from χ²(1) and Benjamini–Hochberg q over the values tested. Words in both sets
count for A only. Rates are per 1,000 words that have the feature (verbs for a stem, a form or a
person).

**Check** asks whether a pattern is denser in one set than elsewhere: the matches per word in the
set's verses, against the set's verses drawn again at random in the same book, the same chapter
or anywhere (`within`), so a set is compared with its own surroundings. Verses whose group lies
wholly inside or outside the set do not move and are reported as such.

Errors are returned, not raised to the client: `SetError(code, item, token)`, `item` the index of
the item at fault.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import chi2

from bsim.analysis.stats import bh_q, empirical_p, g2_table
from bsim.api.patterns import PatternError, WordTable

SET_ERRORS = (
    "empty",               # no item
    "too_long",            # more items or characters than allowed
    "bad_item",            # an item that is not kind:value
    "unknown_kind",
    "unknown_book",
    "bad_range",           # a range or number that does not read, or runs backwards
    "unknown_unit",
    "unknown_collection",
    "pattern",             # the pattern of a pattern: item cannot run (`pattern` holds why)
    "no_words",            # the set has no words
    "filter_in_check",     # only: in a check, which counts verses
)  # fmt: skip
KINDS = ("book", "chapters", "section", "unit", "collection", "pattern", "only")
SECTIONS = {"torah": "Torah", "prophets": "Prophets", "writings": "Writings"}
ONLY = ("speech", "narration")
FEATURES = ("lemma", "root", "domain", "pos", "stem", "form", "person", "function", "clause")
WITHIN = ("corpus", "book", "chapter")
RANGE = re.compile(r"(\d+)(?:-(\d+))?")


class SetError(Exception):
    def __init__(self, code: str, item: int, token: str = "", pattern: PatternError | None = None):
        super().__init__(f"{code} at item {item}: {token}")
        self.code, self.item, self.token, self.pattern = code, item, token, pattern

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "item": self.item, "token": self.token,
                "pattern": self.pattern.as_dict() if self.pattern else None}  # fmt: skip


@dataclass
class Item:
    kind: str
    value: str
    at: int  # index among the items


def parse_set(spec: str, max_items: int, max_chars: int) -> list[Item]:
    """The items of a set; `SetError` on a malformed one (values are looked up later)."""
    if len(spec) > max_chars:
        raise SetError("too_long", 0, "")
    parts = [p.strip() for p in spec.split(";")]
    parts = [p for p in parts if p]
    if not parts:
        raise SetError("empty", 0, "")
    if len(parts) > max_items:
        raise SetError("too_long", max_items, parts[max_items])
    items = []
    for at, part in enumerate(parts):
        kind, sep, value = part.partition(":")
        kind, value = kind.strip().lower(), value.strip()
        if not sep or not value:
            raise SetError("bad_item", at, part)
        if kind not in KINDS:
            raise SetError("unknown_kind", at, kind)
        if kind == "section" and value.lower() not in SECTIONS:
            raise SetError("bad_item", at, part)
        if kind == "only" and value.lower() not in ONLY:
            raise SetError("bad_item", at, part)
        if kind in ("book", "collection") and not RANGE.fullmatch(value):
            raise SetError("bad_range", at, value)
        if kind == "collection" and "-" in value:
            raise SetError("bad_range", at, value)
        if kind == "chapters":
            book, sep2, rng = value.partition(":")
            if not sep2 or not book.isdigit() or not RANGE.fullmatch(rng):
                raise SetError("bad_range", at, value)
        items.append(Item(kind, value if kind in ("unit", "pattern") else value.lower(), at))
    return items


def _span(value: str, at: int) -> tuple[int, int]:
    m = RANGE.fullmatch(value)
    assert m is not None
    lo = int(m.group(1))
    hi = int(m.group(2)) if m.group(2) else lo
    if hi < lo:
        raise SetError("bad_range", at, value)
    return lo, hi


@dataclass
class Corpus:
    """What a set is resolved against: each verse's book and chapter, each book's section, and
    look-ups of units, collections and pattern matches (None: unknown)."""

    verse_book: np.ndarray
    verse_chapter: np.ndarray
    sections: dict[int, str]  # book_id -> Torah | Prophets | Writings
    unit_span: Callable[[str], tuple[int, int] | None]
    collection_spans: Callable[[int], list[tuple[int, int]] | None]
    pattern_rows: Callable[[str], np.ndarray]  # raises PatternError

    @property
    def n_verses(self) -> int:
        return len(self.verse_book)


@dataclass
class Resolved:
    verses: np.ndarray  # bool per verse: the set's verses
    words: np.ndarray  # bool per word: its words (after only: filters)
    filtered: bool  # an only: filter applied


def resolve(items: list[Item], corpus: Corpus, table: WordTable) -> Resolved:
    """The verses and words of a set."""
    n = corpus.n_verses
    verses = np.zeros(n, dtype=bool)
    only: set[str] = set()
    parts = 0
    for it in items:
        if it.kind == "only":
            only.add(it.value)
            continue
        parts += 1
        if it.kind == "book":
            lo, hi = _span(it.value, it.at)
            if hi >= len(corpus.sections) or lo not in corpus.sections:
                raise SetError("unknown_book", it.at, it.value)
            verses |= (corpus.verse_book >= lo) & (corpus.verse_book <= hi)
        elif it.kind == "section":
            books = [b for b, s in corpus.sections.items() if s == SECTIONS[it.value]]
            verses |= np.isin(corpus.verse_book, books)
        elif it.kind == "chapters":
            book, _, rng = it.value.partition(":")
            if int(book) not in corpus.sections:
                raise SetError("unknown_book", it.at, book)
            lo, hi = _span(rng, it.at)
            in_book = corpus.verse_book == int(book)
            if lo < 1 or hi > int(corpus.verse_chapter[in_book].max(initial=0)):
                raise SetError("bad_range", it.at, it.value)
            verses |= in_book & (corpus.verse_chapter >= lo) & (corpus.verse_chapter <= hi)
        elif it.kind == "unit":
            span = corpus.unit_span(it.value)
            if span is None:
                raise SetError("unknown_unit", it.at, it.value)
            verses[span[0] : span[1] + 1] = True
        elif it.kind == "collection":
            spans = corpus.collection_spans(int(it.value))
            if spans is None:
                raise SetError("unknown_collection", it.at, it.value)
            for s, e in spans:
                verses[s : e + 1] = True
        else:  # pattern
            try:
                rows = corpus.pattern_rows(it.value)
            except PatternError as e:
                raise SetError("pattern", it.at, it.value, e) from e
            if len(rows):
                verses[table.verse[rows[:, 0]]] = True
    if parts == 0:
        raise SetError("empty", 0, "")
    words = verses[table.verse]
    if only and only != set(ONLY):  # both kinds together: every word
        words &= table.speech if "speech" in only else ~table.speech
    if not words.any():
        raise SetError("no_words", 0, "")
    return Resolved(verses, words, bool(only))


# features


@dataclass
class DomainTable:
    """Each word's SDBH domains (`words.domains`, §16.22), a word split over k domains counting
    1/k in each, in the word table's order."""

    word: np.ndarray  # the word of each (word, domain) entry
    code: np.ndarray  # the domain (index into `keys`)
    weight: np.ndarray
    keys: list[str]

    @classmethod
    def load(cls, conn: sqlite3.Connection) -> DomainTable:
        word, code, weight = [], [], []
        vocab: dict[str, int] = {}
        rows = conn.execute("SELECT domains FROM words ORDER BY verse_id, idx")
        for i, (doms,) in enumerate(rows):
            if not doms:
                continue
            ds = doms.split()
            for d in ds:
                word.append(i)
                code.append(vocab.setdefault(d, len(vocab)))
                weight.append(1 / len(ds))
        return cls(
            np.array(word, dtype=np.int64),
            np.array(code, dtype=np.int64),
            np.array(weight, dtype=np.float64),
            list(vocab),
        )


def feature_keys(table: WordTable, domains: DomainTable, feature: str) -> list[str]:
    if feature == "domain":
        return domains.keys
    if feature in ("function", "clause"):
        return list(table.bit_vocab[feature])
    return list(table.vocab[feature])


def feature_counts(
    table: WordTable, domains: DomainTable, feature: str, words: np.ndarray
) -> tuple[np.ndarray, float]:
    """Each value's count among the given words, and the words that have the feature at all."""
    keys = feature_keys(table, domains, feature)
    if feature == "domain":
        sel = words[domains.word]
        counts = np.bincount(domains.code[sel], weights=domains.weight[sel], minlength=len(keys))
        return counts, float(counts.sum())
    if feature in ("function", "clause"):
        bits = table.bits[feature][words]
        voc = table.bit_vocab[feature]
        counts = np.array([np.count_nonzero(bits & np.uint64(voc[k])) for k in keys], dtype=float)
        return counts, float(np.count_nonzero(bits))
    arr = table.codes[feature][words]
    arr = arr[arr >= 0]
    return np.bincount(arr, minlength=len(keys)).astype(float), float(len(arr))


def feature_words(
    table: WordTable, domains: DomainTable, feature: str, key: str, words: np.ndarray
) -> np.ndarray:
    """Positions (in the word table) of the given words with a value."""
    if feature == "domain":
        c = domains.keys.index(key)
        hit = domains.word[(domains.code == c) & words[domains.word]]
        return np.unique(hit)
    if feature in ("function", "clause"):
        b = np.uint64(table.bit_vocab[feature][key])
        return np.flatnonzero(words & ((table.bits[feature] & b) != 0))
    return np.flatnonzero(words & (table.codes[feature] == table.vocab[feature][key]))


@dataclass
class Contrast:
    keys: list[str]
    a: np.ndarray
    b: np.ndarray
    total_a: float
    total_b: float
    tested: np.ndarray  # indexes into keys, those with at least min_count words in A and B
    g2: np.ndarray  # per tested value
    p: np.ndarray
    q: np.ndarray
    log_ratio: np.ndarray  # log2 of A's rate over B's, half a word added to each count
    side: np.ndarray  # "a" | "b": where the value is commoner


def contrast(
    table: WordTable,
    domains: DomainTable,
    feature: str,
    words_a: np.ndarray,
    words_b: np.ndarray,
    min_count: float,
) -> Contrast:
    keys = feature_keys(table, domains, feature)
    a, ta = feature_counts(table, domains, feature, words_a)
    b, tb = feature_counts(table, domains, feature, words_b)
    tested = np.flatnonzero(a + b >= min_count) if ta > 0 and tb > 0 else np.empty(0, dtype=int)
    g2 = np.array([g2_table(a[i], ta, a[i] + b[i], ta + tb) for i in tested], dtype=float)
    p = chi2.sf(g2, 1) if len(g2) else np.empty(0)
    lr = np.log2(((a[tested] + 0.5) / (ta + 0.5)) / ((b[tested] + 0.5) / (tb + 0.5)))
    side = np.where(a[tested] * tb >= b[tested] * ta, "a", "b")
    return Contrast(keys, a, b, ta, tb, tested, g2, p, bh_q(p), lr, side)


# check


@dataclass
class Check:
    matches: int  # in the set's verses
    words: int
    rate: float  # matches per 1,000 words
    rest_matches: int  # in the other verses of the groups the set touches
    rest_words: int
    null_mean: float
    null_low: float  # 2.5 % and 97.5 % of the shuffled rates
    null_high: float
    p_high: float  # denser than the shuffles
    p_low: float  # sparser
    groups: int  # groups holding verses of the set and others
    fixed_verses: int  # set verses in groups wholly inside the set (they never move)
    testable: bool


def check(
    matches: np.ndarray,
    words: np.ndarray,
    in_set: np.ndarray,
    groups: np.ndarray,
    draws: int,
    seed: int,
    batch_cells: int = 2_000_000,
) -> Check:
    """`matches` and `words` per verse; the set's verses drawn again at random among the verses
    of their own group (`groups`, one id per verse), `draws` times."""
    touched = np.unique(groups[in_set])
    mixed, whole = [], []
    for g in touched:
        ids = np.flatnonzero(groups == g)
        k = int(in_set[ids].sum())
        if k < len(ids):
            mixed.append((ids, k))
        else:
            whole.append(g)
    base = np.isin(groups, whole)  # groups wholly inside the set: the same in every draw
    fixed = int(base.sum())
    m_obs, w_obs = int(matches[in_set].sum()), int(words[in_set].sum())
    rate = 1000 * m_obs / w_obs if w_obs else 0.0
    around = np.isin(groups, touched) & ~in_set
    rest_m, rest_w = int(matches[around].sum()), int(words[around].sum())
    if not mixed or w_obs == 0:
        return Check(m_obs, w_obs, rate, rest_m, rest_w, rate, rate, rate, 1.0, 1.0, 0, fixed,
                     False)  # fmt: skip
    rng = np.random.default_rng(seed)
    m_null = np.full(draws, float(matches[base].sum()))
    w_null = np.full(draws, float(words[base].sum()))
    for ids, k in mixed:
        mg, wg = matches[ids].astype(float), words[ids].astype(float)
        step = max(1, batch_cells // len(ids))
        for start in range(0, draws, step):
            nb = min(step, draws - start)
            pick = np.argpartition(rng.random((nb, len(ids))), k - 1, axis=1)[:, :k]
            m_null[start : start + nb] += mg[pick].sum(axis=1)
            w_null[start : start + nb] += wg[pick].sum(axis=1)
    null = 1000 * m_null / np.maximum(w_null, 1)
    return Check(
        m_obs,
        w_obs,
        rate,
        rest_m,
        rest_w,
        float(null.mean()),
        float(np.quantile(null, 0.025)),
        float(np.quantile(null, 0.975)),
        empirical_p(rate, null),
        empirical_p(-rate, -null),
        len(mixed),
        fixed,
        True,
    )
