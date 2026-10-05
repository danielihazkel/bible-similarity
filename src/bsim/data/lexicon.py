"""`bsim lexicon`: word senses and semantic domains from SDBH, name types from Strong's
(DESIGN.md §16.22).

Sources (`bsim download --only lexicon`, pinned in `sources.sdbh` / `sources.hebrew_lexicon`):
- the UBS Dictionary of Biblical Hebrew (SDBH, CC BY-SA 4.0): per lemma its meanings, each with
  lexical semantic domains (a code per level, 3 digits each: `002001001069`), Hebrew synonyms and
  antonyms, and every verse word it is attested in (`BBBCCCVVVSSWWW`, book in Protestant order,
  words counted 2, 4, 6, ... over the morphemes of the verse);
- OpenScriptures HebrewStrong.xml (CC BY 4.0): Strong's part of speech, whose `n-pr-m` / `n-pr-f`
  / `n-pr-loc` tell people from places.
Glosses and definitions are read but never stored: scripture is not translated (D5, D56).

Word tagging: an SDBH reference names a morpheme position in OSHB's verse. Positions are counted
over the lemma parts of each word (`c/d/776` = 3), plus one for the article hidden in a
preposition (`Rd`); pronominal suffixes do not count. The reference is matched to the nearest
morpheme within `lexicon.search_window` whose Strong number is one of the meaning's. A morpheme
with no matched reference takes its lemma's meanings: all of them, weights split, when
`lexicon.ambiguous` is `split`, or none when `skip` (a lemma with a single meaning is always
taken). A matched meaning without a domain leaves its morpheme untagged.

Writes to `paths.data_processed`:
    lexicon_domains.parquet     code, level, parent, label_en
    lexicon_senses.parquet      lex_id, lemma (consonantal), strongs, domains
    lexicon_relations.parquet   a, b (Strong numbers), kind: synonym | antonym (both directions)
    lexicon_lemmas.parquet      strong, pos (Strong's), name_kind: person | place | both | None
    word_senses.parquet         verse_id, idx, part, strong, lex_ids, domains, weights, source
                                (source: sdbh = matched reference, lemma = from the lemma)
    lexicon_meta.json           coverage and config hash
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from lxml import etree

from bsim.config import config_hash, resolve_path
from bsim.text.normalize import consonantal, fold_finals

Log = Callable[[str], None]

# SDBH numbers the books in the Protestant order of the Old Testament.
PROTESTANT_ORDER = [
    "Gen", "Exod", "Lev", "Num", "Deut", "Josh", "Judg", "Ruth", "1Sam", "2Sam", "1Kgs",
    "2Kgs", "1Chr", "2Chr", "Ezra", "Neh", "Esth", "Job", "Ps", "Prov", "Eccl", "Song", "Isa",
    "Jer", "Lam", "Ezek", "Dan", "Hos", "Joel", "Amos", "Obad", "Jonah", "Mic", "Nah", "Hab",
    "Zeph", "Hag", "Zech", "Mal",
]

NAME_POS = {"n-pr-m": "person", "n-pr-f": "person", "n-pr-loc": "place"}


def strong_key(code: str) -> str:
    """Strong number without language prefix, zero padding or OSHB's homograph letter:
    `H0430` / `A7308` / `1254 a` / `1254a` -> `430` / `7308` / `1254` / `1254`."""
    code = code.strip().lstrip("HA").replace(" ", "")
    return re.sub(r"[a-z+]+$", "", code).lstrip("0")


def lemma_key(lemma: str) -> str:
    """Consonantal, final forms folded: how SDBH synonyms and antonyms name a lemma."""
    return fold_finals(consonantal(lemma))


def parse_ref(ref: str) -> tuple[str, int, int, int] | None:
    """`02304002800030` -> (`Isa`, 40, 28, 15): OSIS book, chapter, verse, 1-based morpheme."""
    b, c, v, w = int(ref[0:3]), int(ref[3:6]), int(ref[6:9]), int(ref[11:14])
    if not 1 <= b <= len(PROTESTANT_ORDER) or w < 2:
        return None
    return PROTESTANT_ORDER[b - 1], c, v, w // 2


@dataclass
class Meaning:
    lex_id: str
    lemma: str
    strongs: list[str]
    domains: list[str]
    synonyms: list[str] = field(default_factory=list)
    antonyms: list[str] = field(default_factory=list)
    refs: list[str] = field(default_factory=list)


def read_sdbh(path: Path) -> list[Meaning]:
    entries = json.loads(path.read_text(encoding="utf-8-sig"))
    out = []
    for e in entries:
        strongs = sorted({k for c in e.get("StrongCodes") or [] if (k := strong_key(c))})
        for bf in e.get("BaseForms") or []:
            for m in bf.get("LEXMeanings") or []:
                out.append(
                    Meaning(
                        lex_id=m["LEXID"],
                        lemma=lemma_key(e["Lemma"]),
                        strongs=strongs,
                        domains=sorted(
                            {d["DomainCode"] for d in m.get("LEXDomains") or [] if d["DomainCode"]}
                        ),
                        synonyms=[lemma_key(s) for s in m.get("LEXSynonyms") or []],
                        antonyms=[lemma_key(s) for s in m.get("LEXAntonyms") or []],
                        refs=list(m.get("LEXReferences") or []),
                    )
                )
    return out


def read_domains(path: Path) -> pd.DataFrame:
    rows = []
    for d in json.loads(path.read_text(encoding="utf-8-sig")):
        code = d["Code"]
        label = next(
            (x["Label"] for x in d["SemanticDomainLocalizations"] if x["LanguageCode"] == "en"),
            "",
        )
        rows.append((code, len(code) // 3, code[:-3] or None, label))
    return pd.DataFrame(rows, columns=["code", "level", "parent", "label_en"])


def read_strong(path: Path) -> pd.DataFrame:
    root = etree.parse(str(path)).getroot()
    ns = {"x": root.nsmap[None]}
    rows = []
    for e in root.iterfind("x:entry", ns):
        w = e.find("x:w", ns)
        pos = (w.get("pos") or "") if w is not None else ""
        kinds = {NAME_POS[p] for p in pos.split() if p in NAME_POS}
        kind = "both" if len(kinds) > 1 else next(iter(kinds), None)
        rows.append((strong_key(e.get("id")), pos, kind))
    df = pd.DataFrame(rows, columns=["strong", "pos", "name_kind"])
    return df.drop_duplicates("strong").reset_index(drop=True)


def morpheme_positions(words: pd.DataFrame, verses: pd.DataFrame) -> dict[str, list[tuple]]:
    """OSHB verse (OSIS) -> per counted morpheme `(verse_id, idx, part, strong)`; `part` is the
    lemma part within the word and `strong` None for an article hidden in a preposition.
    Verses that MAM splits or joins (several OSHB verses) are left out."""
    single = verses[verses.oshb_osis.map(len) == 1]
    osis_of = dict(zip(single.verse_id, single.oshb_osis.map(lambda a: a[0]), strict=True))
    out: dict[str, list[tuple]] = defaultdict(list)
    w = words[words.verse_id.isin(osis_of)].sort_values(["verse_id", "idx"])
    for vid, idx, lemma, morph in zip(w.verse_id, w.idx, w.lemma, w.morph, strict=True):
        parts = str(lemma).split("/")
        codes = [m for m in str(morph)[1:].split("/") if not m.startswith("S")]
        pos = out[osis_of[vid]]
        for part, lem in enumerate(parts):
            pos.append((vid, idx, part, strong_key(lem) if lem[:1].isdigit() else None))
            if part < len(codes) and codes[part].startswith("Rd"):
                pos.append((vid, idx, part, None))
    return out


def match_refs(
    meanings: list[Meaning], positions: dict[str, list[tuple]], window: int
) -> tuple[dict[tuple[int, int, int], set[str]], dict[str, int]]:
    """(verse_id, idx, part) -> lex_ids of the SDBH references matched there, and counts."""
    offsets = sorted(range(-window, window + 1), key=lambda d: (abs(d), d))
    tagged: dict[tuple[int, int, int], set[str]] = defaultdict(set)
    stats = {"refs": 0, "matched": 0, "exact": 0, "no_verse": 0}
    for m in meanings:
        strongs = set(m.strongs)
        for ref in m.refs:
            parsed = parse_ref(ref)
            if parsed is None:
                continue
            stats["refs"] += 1
            osis, c, v, n = parsed
            pos = positions.get(f"{osis}.{c}.{v}")
            if pos is None:
                stats["no_verse"] += 1
                continue
            for d in offsets:
                i = n - 1 + d
                if 0 <= i < len(pos) and pos[i][3] in strongs:
                    vid, idx, part, _ = pos[i]
                    tagged[(vid, idx, part)].add(m.lex_id)
                    stats["matched"] += 1
                    stats["exact"] += d == 0
                    break
    return tagged, stats


def tag_words(
    positions: dict[str, list[tuple]],
    tagged: dict[tuple[int, int, int], set[str]],
    meanings: list[Meaning],
    ambiguous: str,
) -> pd.DataFrame:
    """One row per lemma morpheme with a sense: matched references first, else the lemma's."""
    by_id = {m.lex_id: m for m in meanings}
    by_strong: dict[str, list[str]] = defaultdict(list)
    for m in meanings:
        if m.domains:
            for s in m.strongs:
                by_strong[s].append(m.lex_id)
    rows = []
    for pos in positions.values():
        for vid, idx, part, strong in pos:
            if strong is None:
                continue
            matched = tagged.get((vid, idx, part))
            # a matched reference wins even when its meaning has no domain
            lex_ids = sorted(i for i in matched or () if by_id[i].domains)
            source = "sdbh"
            if not matched:
                cand = by_strong.get(strong, [])
                if len({tuple(by_id[i].domains) for i in cand}) > 1 and ambiguous == "skip":
                    continue
                lex_ids, source = cand, "lemma"
            if not lex_ids:
                continue
            weight: dict[str, float] = defaultdict(float)
            for i in lex_ids:
                ds = by_id[i].domains
                for d in ds:
                    weight[d] += 1 / (len(lex_ids) * len(ds))
            doms = sorted(weight)
            rows.append((vid, idx, part, strong, lex_ids, doms, [weight[d] for d in doms], source))
    cols = ["verse_id", "idx", "part", "strong", "lex_ids", "domains", "weights", "source"]
    df = pd.DataFrame(rows, columns=cols)
    return df.sort_values(["verse_id", "idx", "part"]).reset_index(drop=True)


def relations(meanings: list[Meaning]) -> pd.DataFrame:
    """Strong-level synonym / antonym pairs, both directions (a lemma name SDBH spells for
    several homographs links to each of them)."""
    strongs_of: dict[str, set[str]] = defaultdict(set)
    for m in meanings:
        strongs_of[m.lemma].update(m.strongs)
    pairs = set()
    for m in meanings:
        for kind, names in (("synonym", m.synonyms), ("antonym", m.antonyms)):
            for name in names:
                for a in m.strongs:
                    for b in strongs_of.get(name, ()):
                        if a != b:
                            pairs.add((a, b, kind))
                            pairs.add((b, a, kind))
    df = pd.DataFrame(sorted(pairs), columns=["a", "b", "kind"])
    # a pair listed as both keeps its antonym reading
    anti = set(zip(df.a[df.kind == "antonym"], df.b[df.kind == "antonym"], strict=True))
    keep = [
        k == "antonym" or (a, b) not in anti for a, b, k in zip(df.a, df.b, df.kind, strict=True)
    ]
    return df[keep].reset_index(drop=True)


def run_lexicon(cfg: dict[str, Any], log: Log = print) -> dict[str, Any]:
    raw = resolve_path(cfg, "data_raw") / "lexicon"
    proc = resolve_path(cfg, "data_processed")
    lc, src = cfg["lexicon"], cfg["sources"]
    dic, dom_file = src["sdbh"]["files"]
    for f in (dic, dom_file, *src["hebrew_lexicon"]["files"]):
        if not (raw / f).exists():
            raise RuntimeError(f"{raw / f} missing; run `bsim download --only lexicon` first")
    if not (proc / "words.parquet").exists():
        raise RuntimeError(f"{proc / 'words.parquet'} missing; run `bsim build-corpus` first")

    log("reading SDBH and Strong's")
    meanings = read_sdbh(raw / dic)
    domains = read_domains(raw / dom_file)
    lemmas = read_strong(raw / src["hebrew_lexicon"]["files"][0])

    words = pd.read_parquet(proc / "words.parquet", columns=["verse_id", "idx", "lemma", "morph"])
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "oshb_osis"])
    positions = morpheme_positions(words, verses)
    log("matching SDBH word references to OSHB morphemes")
    tagged, stats = match_refs(meanings, positions, lc["search_window"])
    senses = tag_words(positions, tagged, meanings, lc["ambiguous"])
    rel = relations(meanings)

    n_lemma_morphemes = sum(1 for p in positions.values() for t in p if t[3] is not None)
    stats.update(
        {
            "meanings": len(meanings),
            "meanings_with_domains": sum(bool(m.domains) for m in meanings),
            "domains": len(domains),
            "lemma_morphemes": n_lemma_morphemes,
            "tagged_sdbh": int((senses.source == "sdbh").sum()),
            "tagged_lemma": int((senses.source == "lemma").sum()),
            "synonym_pairs": int((rel.kind == "synonym").sum() // 2),
            "antonym_pairs": int((rel.kind == "antonym").sum() // 2),
            "name_lemmas": lemmas.name_kind.value_counts().to_dict(),
        }
    )
    log(
        f"  {stats['matched']:,} of {stats['refs']:,} references matched "
        f"({stats['matched'] / max(stats['refs'], 1):.1%}, "
        f"{stats['exact']:,} at the exact position)"
    )
    log(
        f"  {len(senses):,} of {n_lemma_morphemes:,} lemma morphemes tagged: "
        f"{stats['tagged_sdbh']:,} by reference, {stats['tagged_lemma']:,} from the lemma"
    )

    proc.mkdir(parents=True, exist_ok=True)
    domains.to_parquet(proc / "lexicon_domains.parquet", index=False)
    pd.DataFrame(
        [(m.lex_id, m.lemma, m.strongs, m.domains) for m in meanings],
        columns=["lex_id", "lemma", "strongs", "domains"],
    ).to_parquet(proc / "lexicon_senses.parquet", index=False)
    rel.to_parquet(proc / "lexicon_relations.parquet", index=False)
    lemmas.to_parquet(proc / "lexicon_lemmas.parquet", index=False)
    senses.to_parquet(proc / "word_senses.parquet", index=False)
    meta = {"config_hash": config_hash(cfg, "lexicon", "sources"), **stats}
    (proc / "lexicon_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta
