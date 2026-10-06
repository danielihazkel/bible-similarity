"""ETCBC BHSA clauses and phrases, aligned to OSHB words (DESIGN.md §16.26).

The BHSA (Biblia Hebraica Stuttgartensia Amstelodamensis, ETCBC; CC BY-NC 4.0) is a syntactic
database of the WLC: every word belongs to a phrase with a function (Pred, Subj, Objc, Cmpl,
Adju, Time, Loca, ...), every phrase to a clause with a type (Way0, WXQt, NmCl, InfC, ...), a
kind (verbal / nominal / without predication) and a text type (`domain`: narrative N, discursive
D, quotation Q; `txt`: the embedding, e.g. `NQ` for a quotation inside narrative). `bsim
download --only syntax` fetches the needed Text-Fabric feature files at a pinned commit;
glosses are not fetched (D5).

Text-Fabric files (`read_tf`): a header of `@` lines, a blank line, then one line per node,
`[nodes<TAB>]value` for node features and `[nodes<TAB>]targets` for edges; omitted nodes are the
previous node + 1, and `nodes` / `targets` may be ranges (`5-9`) and lists (`1,3-4`).

Alignment (`align_verse`): BHSA words follow the ketiv and split off prefixes (ב, ו, ה) as words
of their own, the article after a preposition with no consonants; OSHB words keep prefixes and
read the qere. Per verse, the two consonant strings (finals folded) are aligned with difflib,
each BHSA word goes to the OSHB word that most of its consonants fall in, and a word with none
matched (the hidden article, a ketiv / qere difference) to its neighbour's.

`bsim syntax` writes, under `paths.data_processed`:
    syntax_clauses.parquet   clause, verse_id, words (OSHB idx list), typ, kind, domain, txt,
                             rela, mother (clause or -1), speech (txt has Q), speaker
    syntax_phrases.parquet   phrase, clause, verse_id, words, typ, function
    syntax_meta.json         counts, alignment check, the speaker rule's coverage
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from collections.abc import Callable, Iterable
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import resolve_path
from bsim.data.lexicon import strong_key
from bsim.text.normalize import consonantal, fold_finals

Log = Callable[[str], None]

# BHSA (Latin) book names -> OSIS
BOOKS = {
    "Genesis": "Gen", "Exodus": "Exod", "Leviticus": "Lev", "Numeri": "Num",
    "Deuteronomium": "Deut", "Josua": "Josh", "Judices": "Judg", "Samuel_I": "1Sam",
    "Samuel_II": "2Sam", "Reges_I": "1Kgs", "Reges_II": "2Kgs", "Jesaia": "Isa",
    "Jeremia": "Jer", "Ezechiel": "Ezek", "Hosea": "Hos", "Joel": "Joel", "Amos": "Amos",
    "Obadia": "Obad", "Jona": "Jonah", "Micha": "Mic", "Nahum": "Nah", "Habakuk": "Hab",
    "Zephania": "Zeph", "Haggai": "Hag", "Sacharia": "Zech", "Maleachi": "Mal",
    "Psalmi": "Ps", "Iob": "Job", "Proverbia": "Prov", "Ruth": "Ruth", "Canticum": "Song",
    "Ecclesiastes": "Eccl", "Threni": "Lam", "Esther": "Esth", "Daniel": "Dan",
    "Esra": "Ezra", "Nehemia": "Neh", "Chronica_I": "1Chr", "Chronica_II": "2Chr",
}  # fmt: skip


def _nodes(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out.extend(range(int(a), int(b or a) + 1))
    return out


def _unescape(v: str) -> str:
    return v.replace("\\t", "\t").replace("\\n", "\n").replace("\\\\", "\\")


def read_tf(path: Path) -> dict[int, Any]:
    """A Text-Fabric feature: node -> value (node feature) or node -> target list (edge)."""
    lines = path.read_text("utf-8").split("\n")
    edge = lines[0].strip() == "@edge"
    i = next(k for k, line in enumerate(lines) if not line.startswith("@")) + 1  # skip blank
    out: dict[int, Any] = {}
    node = 0
    if lines and lines[-1] == "":
        lines.pop()  # the file's final newline
    for line in lines[i:]:
        fields = line.split("\t")
        if edge:
            if line == "":
                continue
            nodes, targets = (
                ([node + 1], fields[0])
                if len(fields) == 1
                else (
                    _nodes(fields[0]),
                    fields[1],
                )
            )
            for n in nodes:
                out[n] = _nodes(targets)
        else:
            nodes, value = (
                ([node + 1], fields[0])
                if len(fields) == 1
                else (
                    _nodes(fields[0]),
                    fields[1],
                )
            )
            for n in nodes:
                out[n] = _unescape(value)
        node = nodes[-1]
    return out


def read_otype(path: Path) -> dict[str, tuple[int, int]]:
    """Node type -> (first, last) node."""
    out = {}
    for line in path.read_text("utf-8").split("\n"):
        if line and not line.startswith("@") and "\t" in line:
            span, typ = line.split("\t")
            a, _, b = span.partition("-")
            out[typ] = (int(a), int(b or a))
    return out


def cons(word: str) -> str:
    """Consonants of a word, finals folded (both BHSA and OSHB spellings)."""
    return fold_finals(re.sub(r"[^א-ת]", "", consonantal(word)))


def align_verse(bhsa: list[str], oshb: list[str]) -> list[int]:
    """OSHB word index of every BHSA word of a verse (both given as consonant strings)."""
    a = "".join(bhsa)
    b = "".join(oshb)
    a_word = np.repeat(np.arange(len(bhsa)), [len(w) for w in bhsa])
    b_word = np.repeat(np.arange(len(oshb)), [len(w) for w in oshb])
    votes: list[Counter] = [Counter() for _ in bhsa]
    for m in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(m.size):
            votes[a_word[m.a + k]][b_word[m.b + k]] += 1
    out = [v.most_common(1)[0][0] if v else -1 for v in votes]
    # unmatched words (no consonants, ketiv / qere): the next matched word's, else the previous
    nxt = -1
    for i in range(len(out) - 1, -1, -1):
        if out[i] == -1:
            out[i] = nxt
        else:
            nxt = out[i]
    prev = 0
    for i, o in enumerate(out):
        if o == -1:
            out[i] = prev
        prev = out[i]
    return out


def load_bhsa(raw: Path, features: Iterable[str]) -> tuple[dict[str, tuple[int, int]], dict]:
    """(otype ranges, feature -> node map) of the downloaded BHSA files."""
    otype = read_otype(raw / "otype.tf")
    return otype, {f: read_tf(raw / f"{f}.tf") for f in features}


FEATURES = (
    "oslots", "book", "chapter", "verse", "g_cons_utf8", "lex", "sp",
    "typ", "kind", "domain", "txt", "rela", "function", "mother", "ps", "gn", "vt",
)  # fmt: skip


def verse_words(
    otype: dict[str, tuple[int, int]], F: dict[str, dict], verse_of_osis: dict[str, int]
) -> tuple[dict[int, list[int]], int]:
    """verse_id -> its BHSA words in order (a verse_id may join several WLC verses), and how many
    BHSA verses have no verse_id."""
    v0, v1 = otype["verse"]
    out: dict[int, list[int]] = {}
    missing = 0
    for v in range(v0, v1 + 1):
        osis = f"{BOOKS[F['book'][v]]}.{F['chapter'][v]}.{F['verse'][v]}"
        vid = verse_of_osis.get(osis)
        if vid is None:
            missing += 1
            continue
        out.setdefault(vid, []).extend(F["oslots"][v])
    return out, missing


def run_syntax(cfg: dict[str, Any], log: Log = print) -> dict[str, Any]:
    t0 = time.perf_counter()
    sc = cfg["syntax"]
    raw, proc = resolve_path(cfg, "data_raw") / "bhsa", resolve_path(cfg, "data_processed")
    if not (raw / "otype.tf").exists():
        raise RuntimeError(f"{raw} missing; run `bsim download --only syntax` first")
    otype, F = load_bhsa(raw, FEATURES)
    log(f"BHSA: {otype['word'][1]} words, {otype['clause'][1] - otype['clause'][0] + 1} clauses")
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "oshb_osis"])
    verse_of_osis: dict[str, int] = {}
    for vid, refs in zip(verses.verse_id, verses.oshb_osis, strict=True):
        for r in refs:
            verse_of_osis.setdefault(r, int(vid))
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "idx", "surface", "content_lemmas"]
    )
    oshb = dict(iter(words.groupby("verse_id", sort=False)))
    by_verse, missing = verse_words(otype, F, verse_of_osis)

    # every BHSA word -> (verse_id, OSHB word idx)
    w_verse = np.full(otype["word"][1] + 1, -1, dtype=np.int64)
    w_idx = np.full(otype["word"][1] + 1, -1, dtype=np.int64)
    exact = total = 0
    for vid, ws in by_verse.items():
        g = oshb.get(vid)
        if g is None:
            continue
        b = [cons(F["g_cons_utf8"].get(w, "")) for w in ws]
        o = [cons(s) for s in g.surface]
        exact += "".join(b) == "".join(o)
        total += 1
        idx = g.idx.to_numpy()
        for w, k in zip(ws, align_verse(b, o), strict=True):
            w_verse[w], w_idx[w] = vid, idx[k]
    log(
        f"aligned {total} verses ({exact} with the same consonants; {missing} BHSA verses unmapped)"
    )

    content = {
        (int(v), int(i)): list(cl)
        for v, i, cl in zip(words.verse_id, words.idx, words.content_lemmas, strict=True)
    }

    def lemma(w: int) -> str | None:
        cl = content.get((int(w_verse[w]), int(w_idx[w])))
        return cl[0] if cl else None

    # who can speak: a name, a participle used as a noun (והנגשים), or a noun whose SDBH sense
    # here is a being (people, groups, leaders, deities, animals) or a name of a person or deity;
    # without `bsim lexicon`, any noun
    being = _beings(proc, sc["speaker_domains"])

    def can_speak(w: int) -> bool:
        if F["sp"].get(w) == "nmpr" or F["vt"].get(w) == "ptca":
            return True
        if F["sp"].get(w) != "subs":
            return False
        return being is None or (int(w_verse[w]), int(w_idx[w])) in being

    clauses, phrases, atom_clause = _units(otype, F, w_verse, w_idx)
    _speakers(clauses, phrases, atom_clause, F, lemma, can_speak, sc)

    cdf = pd.DataFrame(clauses).drop(columns=["slots", "atoms"])
    cdf = cdf[cdf.verse_id >= 0].reset_index(drop=True)
    pdf = pd.DataFrame(phrases).drop(columns=["slots"])
    pdf = pdf[pdf.verse_id >= 0].reset_index(drop=True)
    cdf.to_parquet(proc / "syntax_clauses.parquet")
    pdf.to_parquet(proc / "syntax_phrases.parquet")
    q = cdf[cdf.speech]
    meta = {
        "bhsa_commit": cfg["sources"]["bhsa"]["commit"],
        "verses_aligned": total,
        "verses_same_consonants": exact,
        "bhsa_verses_unmapped": missing,
        "clauses": len(cdf),
        "phrases": len(pdf),
        "speech_clauses": len(q),
        "speaker": {
            "explicit": int((q.speaker_source == "explicit").sum()),
            "carried": int((q.speaker_source == "carried").sum()),
            "enclosing": int((q.speaker_source == "enclosing").sum()),
            "unknown": int(q.speaker.isna().sum()),
        },
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (proc / "syntax_meta.json").write_text(json.dumps(meta, indent=2) + "\n", "utf-8")
    s = meta["speaker"]
    log(
        f"{len(cdf)} clauses, {len(pdf)} phrases; {len(q)} in direct speech, speaker explicit"
        f" {s['explicit']}, carried {s['carried']}, enclosing {s['enclosing']}, unknown"
        f" {s['unknown']}"
    )
    return meta


def _units(otype, F, w_verse, w_idx):
    """Clause and phrase records over OSHB words (a unit crossing verses keeps its first verse's
    words), and clause_atom -> clause."""
    S = F["oslots"]
    word_clause: dict[int, int] = {}
    clauses = []
    c0, c1 = otype["clause"]
    for c in range(c0, c1 + 1):
        slots = S[c]
        for w in slots:
            word_clause[w] = c
        vid = int(w_verse[slots[0]])
        clauses.append(
            {
                "clause": c,
                "verse_id": vid,
                "words": sorted({int(w_idx[w]) for w in slots if w_verse[w] == vid}),
                "typ": F["typ"].get(c, ""),
                "kind": F["kind"].get(c, ""),
                "domain": F["domain"].get(c, ""),
                "txt": F["txt"].get(c, ""),
                "rela": F["rela"].get(c, ""),
                "slots": slots,
                "atoms": [],
            }
        )
    by_clause = {r["clause"]: r for r in clauses}
    atom_clause: dict[int, int] = {}
    a0, a1 = otype["clause_atom"]
    for a in range(a0, a1 + 1):
        c = word_clause[S[a][0]]
        atom_clause[a] = c
        by_clause[c]["atoms"].append(a)
    phrases = []
    p0, p1 = otype["phrase"]
    for p in range(p0, p1 + 1):
        slots = S[p]
        vid = int(w_verse[slots[0]])
        phrases.append(
            {
                "phrase": p,
                "clause": word_clause[slots[0]],
                "verse_id": vid,
                "words": sorted({int(w_idx[w]) for w in slots if w_verse[w] == vid}),
                "typ": F["typ"].get(p, ""),
                "function": F["function"].get(p, ""),
                "slots": slots,
            }
        )
    return clauses, phrases, atom_clause


def _beings(proc: Path, prefixes: list[str]) -> set[tuple[int, int]] | None:
    """(verse_id, idx) of OSHB words with a sense in one of the `prefixes` domains (None without
    `word_senses.parquet`)."""
    path = proc / "word_senses.parquet"
    if not path.exists():
        return None
    s = pd.read_parquet(path, columns=["verse_id", "idx", "domains"])
    pre = tuple(prefixes)
    return {
        (int(v), int(i))
        for v, i, ds in zip(s.verse_id, s.idx, s.domains, strict=True)
        if any(d.startswith(pre) for d in ds)
    }


def _subject_head(slots: list[int], can_speak, lemma, pass_through: set[str]) -> int | None:
    """The word of a subject phrase that names its speaker: the first that can speak, moving on
    past a `pass_through` head to a later one (בני ישראל -> ישראל)."""
    heads = [w for w in slots if can_speak(w)]
    if not heads:
        return None
    if strong_key(lemma(heads[0]) or "") in pass_through and len(heads) > 1:
        return heads[1]
    return heads[0]


def _speakers(clauses, phrases, atom_clause, F, lemma, can_speak, sc) -> None:
    """Mark direct speech (`txt` ending in Q) and who speaks it.

    A quotation starts at a clause whose first clause atom's mother lies in a clause of a shallower
    text level: that clause introduces it (through an infinitive such as לאמר, `infinitive_hop`,
    to the clause the infinitive depends on). The speaker is the head noun or name of the
    introduction's subject phrase (`explicit`); an introduction without one whose verb is in the
    third person (ויאמר) takes the subject of the nearest of the `speaker_lookback` clauses before
    it at its level that has one and agrees with the verb in gender (`carried`; number is left
    out: collectives such as העם take plural verbs). A quotation with no speaker of its own (a
    first or second person introduction, ואמרת; no introduction found) is inside the nearest
    enclosing quotation that has one (`enclosing`). The speaker holds for the clauses of the
    quotation at its level.
    """
    by_clause = {r["clause"]: r for r in clauses}
    pos = {r["clause"]: i for i, r in enumerate(clauses)}
    sp, lex, ps, gn = F["sp"], F["lex"], F["ps"], F["gn"]
    subj: dict[int, int] = {}  # clause -> head word (BHSA) of its subject phrase
    pred_lex: dict[int, str] = {}
    pred_ps: dict[int, str] = {}
    pred_verb: dict[int, int] = {}
    for p in phrases:
        c = p["clause"]
        if p["function"] == "Subj" and c not in subj:
            head = _subject_head(p["slots"], can_speak, lemma, set(sc["pass_through"]))
            if head is not None:
                subj[c] = head
        if p["function"] in ("Pred", "PreO", "PreS") and c not in pred_lex:
            verb = next((w for w in p["slots"] if sp.get(w) == "verb"), None)
            if verb is not None:
                pred_lex[c] = lex.get(verb, "")
                pred_ps[c] = ps.get(verb, "")
                pred_verb[c] = verb

    def agrees(verb: int | None, noun: int) -> bool:
        """Gender agrees where both are marked (a name is often unmarked)."""
        if verb is None:
            return True
        a, b = gn.get(verb, ""), gn.get(noun, "")
        return not (a in ("m", "f") and b in ("m", "f") and a != b)
    mother = F["mother"]

    def intro_of(r) -> int | None:
        m = mother.get(r["atoms"][0]) if r["atoms"] else None
        intro = atom_clause.get(m[0]) if m else None
        if intro is None or len(by_clause[intro]["txt"]) >= len(r["txt"]):
            return None
        ir = by_clause[intro]
        if ir["typ"] == "InfC" and pred_lex.get(intro) in sc["infinitive_hop"] and ir["atoms"]:
            m2 = mother.get(ir["atoms"][0])
            if m2 and m2[0] in atom_clause:
                intro = atom_clause[m2[0]]
        return intro

    def carried(intro: int) -> int | None:
        if pred_ps.get(intro) in ("p1", "p2"):
            return None
        depth, seen = len(by_clause[intro]["txt"]), 0
        for i in range(pos[intro] - 1, max(pos[intro] - 200, -1), -1):
            c = clauses[i]
            if len(c["txt"]) != depth:
                continue
            if c["clause"] in subj:
                head = subj[c["clause"]]
                return head if agrees(pred_verb.get(intro), head) else None
            seen += 1
            if seen >= sc["speaker_lookback"]:
                return None
        return None

    def enclosing(levels: dict, depth: int) -> tuple[str | None, str | None]:
        """The speaker of the nearest enclosing quotation, for one without its own (the words
        God gives Moses to say, ואמרת אלהם)."""
        outer = [d for d, (s, _) in levels.items() if d < depth and s]
        return (levels[max(outer)][0], "enclosing") if outer else (None, None)

    level_speaker: dict[int, tuple[str | None, str | None]] = {}
    book = None
    for r in clauses:
        b = F["book"].get(r["slots"][0])
        if b != book:
            book, level_speaker = b, {}
        depth = len(r["txt"])
        r["speech"] = r["txt"].endswith("Q")
        # a quotation ends when the text is back at a shallower level
        level_speaker = {d: s for d, s in level_speaker.items() if d <= depth}
        r["speaker"], r["speaker_source"] = None, None
        if r["speech"]:
            intro = intro_of(r)
            if intro is not None:
                head, source = subj.get(intro), "explicit"
                if head is None:
                    head, source = carried(intro), "carried"
                spk = lemma(head) if head is not None else None
                level_speaker = {d: s for d, s in level_speaker.items() if d < depth}
                level_speaker[depth] = (spk, source) if spk else enclosing(level_speaker, depth)
            elif depth not in level_speaker:
                level_speaker[depth] = enclosing(level_speaker, depth)
            r["speaker"], r["speaker_source"] = level_speaker[depth]
