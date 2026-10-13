"""Pattern search (DESIGN.md §16.46): a small query language over the words, compiled to a scan.

A query is a row of word patterns, each in brackets, matched in order inside one verse:

    [root=@r form=infabs] [root=@r form=finite]       מות יומת: an infinitive absolute, then a
                                                      finite verb of the same root
    [form=imperative] ..4 [function=Voct pos=name]    a command, then within 4 words a name called

- **A word pattern** `[...]` holds conditions separated by spaces, all of which must hold; `[]`
  is any word. A condition is `key=value` or `key!=value`; `value|value` is any of them.
- **Between patterns:** nothing = the next word; `..N` = at most N words on; `..` = anywhere
  later in the verse.
- **Variables:** `@name` as the value of `lemma`, `root` or `word` stands for the value the first
  pattern using it matched; `!=@name` is any other.

Keys (`KEYS`): `lemma` (Strong's number, or a Hebrew form), `root` (the family of §16.38, by
Strong's number or Hebrew), `word` (the consonants of the word, prefixes included), `pos`, `type`,
`stem`, `form`, `person`, `gender`, `number`, `state`, `suffix`, `prefix`, `lang`, and from the
BHSA syntax (§16.26) `function` (the phrase's), `clause` (its type), `speech` and `speaker`.
Each word is described by its main morpheme: the first that is neither a prefix (ו, ה, ב, כ, ל,
מ, ש) nor a suffix; prefixes and the pronominal suffix are keys of their own.

The word table (`WordTable.load`) is read from the results DB once per server; a query compiles
to boolean masks over it, and the patterns are chained one word offset at a time. Errors are
returned, not raised to the client: `PatternError(code, at, token)`, `at` a character offset.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Any

import numpy as np

ERROR_CODES = (
    "empty",            # no pattern
    "expected_pattern", # something other than a pattern or a gap
    "unclosed",         # `[` without `]`
    "bad_condition",    # no `=` / `!=`, or no value
    "unknown_key",
    "bad_value",        # a value the key does not take
    "unknown_value",    # a Hebrew lemma or root that is not in the text
    "bad_gap",          # `..N` with N not between 1 and the limit
    "too_many",         # more patterns than allowed
    "variable",         # a variable on a key that takes none, or used with != before it is bound
    "too_broad",        # more partial matches than the limit
)

POS = {"V": "verb", "C": "conjunction", "R": "preposition", "D": "adverb", "P": "pronoun",
       "T": "particle", "S": "suffix"}  # fmt: skip
TYPES = {
    "N": {"c": "common", "g": "gentilic", "p": "proper"},
    "A": {"a": "adjective", "c": "cardinal", "g": "gentilic", "o": "ordinal"},
    "P": {"d": "demonstrative", "f": "indefinite", "i": "interrogative", "p": "personal",
          "r": "relative"},
    "T": {"a": "affirmation", "d": "article", "e": "exhortation", "i": "interrogative",
          "j": "interjection", "m": "demonstrative", "n": "negative", "o": "object",
          "r": "relative"},
}  # fmt: skip
STEMS = {
    "H": {"q": "qal", "N": "niphal", "p": "piel", "P": "pual", "h": "hiphil", "H": "hophal",
          "t": "hithpael", "o": "polel", "O": "polal", "r": "hithpolel", "m": "poel", "M": "poal",
          "k": "palel", "K": "pulal", "Q": "qal-passive", "l": "pilpel", "L": "polpal",
          "f": "hithpalpel", "D": "nithpael", "j": "pealal", "i": "pilel", "u": "hothpaal",
          "c": "tiphil", "v": "hishtaphel", "w": "nithpalel", "y": "nithpoel", "z": "hithpoel"},
    "A": {"q": "peal", "Q": "peil", "u": "hithpeel", "p": "pael", "P": "ithpaal", "M": "hithpaal",
          "a": "aphel", "h": "haphel", "s": "saphel", "e": "shaphel", "H": "hophal",
          "i": "ithpeel", "t": "hishtaphel", "v": "ishtaphel", "w": "hithaphel", "o": "polel",
          "z": "ithpoel", "r": "hithpolel", "f": "hithpalpel", "b": "hephal", "c": "tiphel",
          "m": "poel", "l": "palpel", "L": "ithpalpel", "O": "ithpolel", "G": "ittaphal"},
}  # fmt: skip
FORMS = {"p": "perfect", "q": "weqatal", "i": "imperfect", "w": "wayyiqtol", "h": "cohortative",
         "j": "jussive", "v": "imperative", "r": "participle", "s": "passive-participle",
         "a": "infabs", "c": "infcon"}  # fmt: skip
FORM_GROUPS = {
    "finite": ["perfect", "weqatal", "imperfect", "wayyiqtol", "cohortative", "jussive",
               "imperative"],
    "infinitive": ["infabs", "infcon"],
    "participles": ["participle", "passive-participle"],
}  # fmt: skip
GENDERS = {"m": "m", "f": "f", "c": "c", "b": "b"}
NUMBERS = {"s": "s", "p": "p", "d": "d"}
STATES = {"a": "a", "c": "c", "d": "d"}
PREFIXES = {"b": "ב", "c": "ו", "d": "ה", "i": "ה", "k": "כ", "l": "ל", "m": "מ", "s": "ש"}
PREFIX_BITS = {letter: 1 << i for i, letter in enumerate(dict.fromkeys(PREFIXES.values()))}
LANGS = {"H": "hebrew", "A": "aramaic"}
FINALS = str.maketrans("ךםןףץ", "כמנפצ")
LETTERS = re.compile("[א-ת]")
YES_NO = {"yes": True, "no": False}

# key -> how it is matched: "code" (one value per word), "bits" (a set per word), "bool"
KEYS = {
    "lemma": "code", "root": "code", "word": "code", "pos": "code", "type": "code",
    "stem": "code", "form": "code", "person": "code", "gender": "code", "number": "code",
    "state": "code", "suffix": "code", "lang": "code", "speaker": "code",
    "prefix": "bits", "function": "bits", "clause": "bits", "speech": "bool",
}  # fmt: skip
VARIABLE_KEYS = {"lemma", "root", "word"}


def consonants(text: str) -> str:
    """The Hebrew letters of a text, final forms as medial ones."""
    return "".join(LETTERS.findall(text)).translate(FINALS)


class PatternError(Exception):
    def __init__(self, code: str, at: int, token: str = ""):
        super().__init__(f"{code} at {at}: {token}")
        self.code, self.at, self.token = code, at, token

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "at": self.at, "token": self.token}


@dataclass
class Cond:
    key: str
    negate: bool
    values: list[str]
    at: int
    variable: str | None = None


@dataclass
class Term:
    conds: list[Cond]
    at: int
    gap: int = 1  # how far after the previous pattern's word this one may be (1 = next word)


TOKEN = re.compile(r"\s*(\[[^\[\]]*\]?|\.\.\d*|\S+)")
COND = re.compile(r"([A-Za-z_]+)\s*(!=|=)\s*(\S*)")


def parse(query: str, max_terms: int, max_gap: int) -> list[Term]:
    """The patterns of a query; `PatternError` on a malformed one."""
    terms: list[Term] = []
    gap: int | None = None
    pos = 0
    while pos < len(query):
        m = TOKEN.match(query, pos)
        if not m or not m.group(1):
            break
        tok, at = m.group(1), m.start(1)
        pos = m.end()
        if tok.startswith(".."):
            if not terms or gap is not None:
                raise PatternError("expected_pattern", at, tok)
            n = tok[2:]
            gap = max_gap if not n else int(n)
            if not 1 <= gap <= max_gap:
                raise PatternError("bad_gap", at, tok)
            continue
        if not tok.startswith("["):
            raise PatternError("expected_pattern", at, tok)
        if not tok.endswith("]"):
            raise PatternError("unclosed", at, tok)
        terms.append(Term(_conditions(tok[1:-1], at + 1), at, gap or 1))
        gap = None
        if len(terms) > max_terms:
            raise PatternError("too_many", at, tok)
    if gap is not None:
        raise PatternError("expected_pattern", len(query), "")
    if not terms:
        raise PatternError("empty", 0, "")
    return terms


def _conditions(body: str, offset: int) -> list[Cond]:
    out = []
    for part in re.finditer(r"\S+", body):
        at = offset + part.start()
        m = COND.fullmatch(part.group())
        if not m or not m.group(3):
            raise PatternError("bad_condition", at, part.group())
        key, op, raw = m.group(1).lower(), m.group(2), m.group(3)
        if key not in KEYS:
            raise PatternError("unknown_key", at, m.group(1))
        values = [v for v in raw.split("|") if v]
        if not values:
            raise PatternError("bad_condition", at, part.group())
        variable = None
        if values[0].startswith("@"):
            if key not in VARIABLE_KEYS or len(values) > 1 or len(values[0]) < 2:
                raise PatternError("variable", at, part.group())
            variable = values[0][1:]
        out.append(Cond(key, op == "!=", values, at, variable))
    return out


@dataclass
class WordTable:
    """Every word with its features as integer codes (-1 = none), in canon and word order."""

    verse: np.ndarray
    idx: np.ndarray
    display: np.ndarray
    codes: dict[str, np.ndarray]
    vocab: dict[str, dict[str, int]]
    bits: dict[str, np.ndarray]
    bit_vocab: dict[str, dict[str, int]]
    speech: np.ndarray
    he_lemmas: dict[str, set[str]] = field(default_factory=dict)  # consonants -> lemma keys
    he_roots: dict[str, set[str]] = field(default_factory=dict)
    surfaces: list[str] = field(default_factory=list)
    max_words: int = 1

    def __len__(self) -> int:
        return len(self.verse)

    @classmethod
    def load(cls, conn: sqlite3.Connection) -> WordTable:
        rows = conn.execute(
            "SELECT verse_id, idx, display_idx, surface, lemma, morph FROM words"
            " ORDER BY verse_id, idx"
        ).fetchall()
        root_of: dict[str, str] = {}
        he_roots: dict[str, set[str]] = {}
        he_lemmas: dict[str, set[str]] = {}
        for lemma, root, root_he, link in conn.execute(
            "SELECT lemma, root, root_he, link FROM lemma_roots"
        ):
            root_of[lemma] = root
            he_roots.setdefault(consonants(root_he), set()).add(root)
            if link is None:  # a root: its headword is its own
                he_lemmas.setdefault(consonants(root_he), set()).add(lemma)
        for lemma, he in conn.execute("SELECT lemma, he_lemma FROM lemma_gloss"):
            he_lemmas.setdefault(consonants(he), set()).add(lemma)
        n = len(rows)
        cols = ["lemma", "root", "word", "pos", "type", "stem", "form", "person", "gender",
                "number", "state", "suffix", "lang", "speaker"]  # fmt: skip
        vocab: dict[str, dict[str, int]] = {c: {} for c in cols}
        codes = {c: np.full(n, -1, dtype=np.int32) for c in cols}
        prefix = np.zeros(n, dtype=np.uint64)

        def put(col: str, i: int, value: str | None) -> None:
            if value:
                codes[col][i] = vocab[col].setdefault(value, len(vocab[col]))

        verse = np.empty(n, dtype=np.int32)
        idx = np.empty(n, dtype=np.int32)
        display = np.full(n, -1, dtype=np.int32)
        surfaces = []
        for i, (vid, wi, d, surface, lemma, morph) in enumerate(rows):
            verse[i], idx[i] = vid, wi
            if d is not None:
                display[i] = d
            surfaces.append(surface)
            put("word", i, consonants(surface))
            feats = describe(lemma, morph)
            for col in ("pos", "type", "stem", "form", "person", "gender", "number", "state",
                        "suffix", "lang"):  # fmt: skip
                put(col, i, feats.get(col))
            lem = feats.get("lemma")
            put("lemma", i, lem)
            put("root", i, root_of.get(lem) if lem else None)
            prefix[i] = feats.get("prefix_bits", 0)
        pos_of = {(int(v), int(w)): i for i, (v, w) in enumerate(zip(verse, idx, strict=True))}
        function = np.zeros(n, dtype=np.uint64)
        clause = np.zeros(n, dtype=np.uint64)
        speech = np.zeros(n, dtype=bool)
        bit_vocab: dict[str, dict[str, int]] = {"function": {}, "clause": {},
                                                "prefix": dict(PREFIX_BITS)}  # fmt: skip

        def bit(name: str, value: str) -> np.uint64:
            v = bit_vocab[name]
            if value not in v:
                if len(v) >= 64:
                    return np.uint64(0)
                v[value] = 1 << len(v)
            return np.uint64(v[value])

        for vid, words, fn in conn.execute("SELECT verse_id, words, function FROM syntax_phrases"):
            b = bit("function", fn.lower())
            for w in json.loads(words):
                if (vid, w) in pos_of:
                    function[pos_of[vid, w]] |= b
        for vid, words, typ, txt, speaker in conn.execute(
            "SELECT verse_id, words, typ, txt, speaker FROM clauses"
        ):
            b = bit("clause", typ.lower())
            for w in json.loads(words):
                if (vid, w) in pos_of:
                    i = pos_of[vid, w]
                    clause[i] |= b
                    speech[i] |= txt.endswith("Q")
                    put("speaker", i, speaker)
        sizes = np.bincount(verse) if n else np.array([1])
        return cls(
            verse=verse,
            idx=idx,
            display=display,
            codes=codes,
            vocab=vocab,
            bits={"prefix": prefix, "function": function, "clause": clause},
            bit_vocab=bit_vocab,
            speech=speech,
            he_lemmas=he_lemmas,
            he_roots=he_roots,
            surfaces=surfaces,
            max_words=int(sizes.max()) if n else 1,
        )

    # matching

    def mask(self, cond: Cond) -> np.ndarray:
        """The words a condition (without a variable) holds for."""
        kind = KEYS[cond.key]
        if kind == "bool":
            want = [YES_NO.get(v.lower()) for v in cond.values]
            if None in want:
                raise PatternError("bad_value", cond.at, cond.values[want.index(None)])
            m = np.isin(self.speech, want)
        elif kind == "bits":
            b = np.uint64(0)
            for v in cond.values:
                key = v if cond.key == "prefix" else v.lower()
                if cond.key == "prefix" and key == "none":
                    continue
                if key not in self.bit_vocab[cond.key]:
                    if cond.key == "prefix":
                        raise PatternError("bad_value", cond.at, v)
                    continue  # a function or clause type the text does not have: nothing
                b |= np.uint64(self.bit_vocab[cond.key][key])
            m = (self.bits[cond.key] & b) != 0
            if cond.key == "prefix" and "none" in cond.values:
                m |= self.bits["prefix"] == 0
        else:
            ids = self._codes(cond)
            arr = self.codes[cond.key]
            m = np.isin(arr, ids)
            if cond.key == "suffix" and "yes" in (v.lower() for v in cond.values):
                m |= arr >= 0
            if cond.key == "suffix" and "no" in (v.lower() for v in cond.values):
                m |= arr < 0
        return ~m if cond.negate else m

    def _codes(self, cond: Cond) -> list[int]:
        voc = self.vocab[cond.key]
        out: list[int] = []
        for v in cond.values:
            keys = self._resolve(cond, v)
            out += [voc[k] for k in keys if k in voc]
        return out

    def _resolve(self, cond: Cond, v: str) -> list[str]:
        key = cond.key
        low = v.lower()
        if key in ("lemma", "speaker"):
            if v[0].isdigit():
                k = v.replace(" ", "")
                return [k] + [k + c for c in "abcdefg"] if k.isdigit() else [k]
            he = consonants(v)
            if not he or he not in self.he_lemmas:
                raise PatternError("unknown_value", cond.at, v)
            return sorted(self.he_lemmas[he])
        if key == "root":
            if v[0].isdigit():
                return [v.replace(" ", "")]
            he = consonants(v)
            if not he or he not in self.he_roots:
                raise PatternError("unknown_value", cond.at, v)
            return sorted(self.he_roots[he])
        if key == "word":
            he = consonants(v)
            if not he:
                raise PatternError("bad_value", cond.at, v)
            return [he]
        if key == "suffix":
            if low in YES_NO:
                return []
            if not re.fullmatch(r"[123][mfcb][spd]", low):
                raise PatternError("bad_value", cond.at, v)
            return [low]
        allowed = ALLOWED[key]
        if key == "form" and low in FORM_GROUPS:
            return FORM_GROUPS[low]
        if low not in allowed:
            raise PatternError("bad_value", cond.at, v)
        return [low]

    def match(self, terms: list[Term], limit: int) -> np.ndarray:
        """Matches as rows of word positions (one column per pattern), in text order."""
        n = len(self)
        masks = []
        for t in terms:
            m = np.ones(n, dtype=bool)
            for c in t.conds:
                if c.variable is None:
                    m &= self.mask(c)
            masks.append(m)
        bound: dict[str, tuple[int, str]] = {}  # variable -> (pattern, key)
        checks: list[list[tuple[Cond, int]]] = []
        for k, t in enumerate(terms):
            mine = []
            for c in t.conds:
                if c.variable is None:
                    continue
                if c.variable in bound:
                    pk, pkey = bound[c.variable]
                    if pkey != c.key:
                        raise PatternError("variable", c.at, f"{c.key}=@{c.variable}")
                    mine.append((c, pk))
                elif c.negate:
                    raise PatternError("variable", c.at, f"{c.key}!=@{c.variable}")
                else:
                    bound[c.variable] = (k, c.key)
                    masks[k] &= self.codes[c.key] >= 0
            checks.append(mine)
        rows = np.flatnonzero(masks[0])[:, None]
        if len(rows) > limit:
            raise PatternError("too_broad", terms[0].at, "")
        for k in range(1, len(terms)):
            last = rows[:, -1]
            parts = []
            size = 0
            for d in range(1, min(terms[k].gap, self.max_words) + 1):
                j = last + d
                ok = j < n
                jj = np.where(ok, j, 0)
                ok &= self.verse[jj] == self.verse[last]
                if not ok.any():
                    break
                ok &= masks[k][jj]
                for c, pk in checks[k]:
                    arr = self.codes[c.key]
                    same = arr[jj] == arr[rows[:, pk]]
                    ok &= ~same if c.negate else same
                if ok.any():
                    parts.append(np.hstack([rows[ok], jj[ok][:, None]]))
                    size += int(ok.sum())
                    if size > limit:
                        raise PatternError("too_broad", terms[k].at, "")
            rows = np.vstack(parts) if parts else np.empty((0, k + 1), dtype=np.int64)
            if len(rows) == 0:
                break
        if len(rows) > 1:
            rows = rows[np.lexsort(rows.T[::-1])]
        return rows


ALLOWED = {
    "pos": {"noun", "name", "verb", "adjective", "number", *POS.values()},
    "type": {t for d in TYPES.values() for t in d.values()},
    "stem": {s for d in STEMS.values() for s in d.values()},
    "form": set(FORMS.values()),
    "person": {"1", "2", "3"},
    "gender": set(GENDERS),
    "number": set(NUMBERS),
    "state": set(STATES),
    "lang": set(LANGS.values()),
}


def describe(lemma: str | None, morph: str | None) -> dict[str, Any]:
    """A word's features from its OSHB lemma and morphology: the main morpheme's lemma, part of
    speech and inflection, its prefixes and its pronominal suffix."""
    out: dict[str, Any] = {}
    if not isinstance(morph, str) or len(morph) < 2:  # no morphology: the lemma alone
        parts = [x.replace(" ", "") for x in str(lemma or "").split("/") if x]
        main = [x for x in parts if x not in PREFIXES] or parts
        if main:
            out["lemma"] = main[0]
        return out
    lang = morph[0]
    out["lang"] = LANGS.get(lang)
    codes = morph[1:].split("/")
    parts = str(lemma or "").split("/")
    li = 0
    main: tuple[str, str] | None = None
    prefix_bits = 0
    for k, code in enumerate(codes):
        if code.startswith("S"):
            if code[1:2] == "p" and len(code) >= 5:
                out["suffix"] = code[2:5].lower()
            continue
        part = parts[li].replace(" ", "") if li < len(parts) else ""
        li += 1
        is_prefix = part in PREFIXES and any(not c.startswith("S") for c in codes[k + 1 :])
        if is_prefix and main is None:
            prefix_bits |= PREFIX_BITS[PREFIXES[part]]
            continue
        if main is None:
            main = (code, part)
    out["prefix_bits"] = prefix_bits
    if main is None:
        return out
    code, part = main
    out["lemma"] = part or None
    p = code[:1]
    rest = code[1:]
    if p == "V":
        out["pos"] = "verb"
        out["stem"] = STEMS.get(lang, {}).get(rest[:1])
        form = rest[1:2]
        out["form"] = FORMS.get(form)
        tail = rest[2:]
        if form in "pqiwhjv" and tail:
            _pgn(out, tail)
        elif form in "rs" and tail:
            _gns(out, tail)
    elif p == "N":
        out["pos"] = "name" if rest[:1] == "p" else "noun"
        out["type"] = TYPES["N"].get(rest[:1])
        _gns(out, rest[1:])
    elif p == "A":
        out["pos"] = "number" if rest[:1] == "c" else "adjective"
        out["type"] = TYPES["A"].get(rest[:1])
        _gns(out, rest[1:])
    elif p == "P":
        out["pos"] = "pronoun"
        out["type"] = TYPES["P"].get(rest[:1])
        _pgn(out, rest[1:])
    elif p == "T":
        out["pos"] = "particle"
        out["type"] = TYPES["T"].get(rest[:1])
    else:
        out["pos"] = POS.get(p)
    return out


def _pgn(out: dict[str, Any], s: str) -> None:
    if s[:1] in "123":
        out["person"] = s[:1]
    if len(s) > 1:
        out["gender"] = GENDERS.get(s[1])
    if len(s) > 2:
        out["number"] = NUMBERS.get(s[2])


def _gns(out: dict[str, Any], s: str) -> None:
    if s[:1]:
        out["gender"] = GENDERS.get(s[0])
    if len(s) > 1:
        out["number"] = NUMBERS.get(s[1])
    if len(s) > 2:
        out["state"] = STATES.get(s[2])


def normalize(query: str) -> str:
    """A query with its whitespace collapsed (the cache key)."""
    return " ".join(query.split())
