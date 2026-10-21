"""The family tree (TIPNR's family columns, `data/kjv.py`, `bsim genealogy`, DESIGN.md §16.63)."""

import json

import pandas as pd
import pytest

from bsim.analysis.genealogy import (
    UNATTACHED,
    CurationError,
    Link,
    Person,
    Word,
    cue,
    rank_proofs,
    run_genealogy,
    run_genealogy_review,
)
from bsim.config import load_config
from bsim.data.geo import TipnrRelative, read_tipnr, relatives
from bsim.data.kjv import English


def person(uid, strong, parents=" + ", partners="", offspring="", tribe=">", type_="Male",
           refs="Gen.1.1", name="Named", hebrew="שֵׁם"):  # fmt: skip
    fields = [parents, "", partners, offspring, tribe]
    head = "\t".join([f"{uid}={strong}", "desc", *fields, "#summary", type_])
    line = f"– {name}\t{uid}\t{strong}«{strong[:5]}={hebrew}\tX\t{refs}\t"
    return ["$========== PERSON(s)\t", head, line, "– Total\tX\tX\tH\tx;\t1"]


TIPNR = "\n".join(
    ["TIPNR header"]
    + person("Adam@Gen.1.1", "H0120", partners="Eve@Gen.1.1", offspring="Seth@Gen.1.1",
             hebrew="אָדָם")
    + person("Eve@Gen.1.1", "H2332", partners="Adam@Gen.1.1", offspring="Seth@Gen.1.1",
             type_="Female", hebrew="חַוָּה")
    + person("Seth@Gen.1.1", "H8352", parents="Adam@Gen.1.1 + Eve@Gen.1.1", hebrew="שֵׁת")
    + person("Abraham@Gen.1.2", "H0085", partners="Sarah@Gen.1.2",
             offspring="Isaac@Gen.1.2, Hebron@Gen.1.5(f)", refs="Gen.1.2; Gen.1.3a",
             hebrew="אַבְרָהָם")
    + person("Sarah@Gen.1.2", "H8283", partners="Abraham@Gen.1.2", offspring="Isaac@Gen.1.2",
             type_="Female", refs="Gen.1.2", hebrew="שָׂרָה")
    + person("Isaac@Gen.1.2", "H3327", parents="Abraham@Gen.1.2 + Sarah@Gen.1.2",
             offspring="Judah@Gen.1.4", refs="Gen.1.2; Gen.1.3; Gen.1.4", hebrew="יִצְחָק")
    + person("Judah@Gen.1.4", "H3063", parents="Isaac@Gen.1.2(?) + ", refs="Gen.1.4",
             hebrew="יְהוּדָה")
    + person("Hezron@Gen.1.5", "H2696", partners="a_wife_of_Hezron@Gen.1.5",
             tribe="Tribe of Judah", refs="Gen.1.5", hebrew="חֶצְרוֹן")
    + person("a_wife_of_Hezron@Gen.1.5", "H2696K", partners="Hezron@Gen.1.5",
             tribe="Tribe of Judah", type_="Female", refs="Gen.1.5", name="Mentioned",
             hebrew=".")
    + person("Abagtha@Exo.1.1", "H0005", refs="Exo.1.1", hebrew="אֲבַגְתָא")
    + person("Jesus@Mat.1.1", "G2424", refs="Mat.1.1")  # no Hebrew Bible name: left out
)  # fmt: skip

# Genesis 1:1-6, Exodus 1:1 (content lemmas per word)
WORDS = [
    ["3045", "120", "853", "2332", "802", "3205", "853", "8352"],  # וידע אדם את חוה אשתו ותלד את שת
    [
        "7121",
        "85",
        "853",
        "8034",
        "1121a",
        "3205",
        "8283",
        "3327",
    ],  # ויקרא אברהם ... בנו ילדה שרה יצחק
    ["3327", "1121a", "85"],  # יצחק בן אברהם
    ["1121a", "3327", "3063"],  # ובני יצחק יהודה
    ["2696"],  # חצרון
    ["1961"],
    ["5"],  # אבגתא
]


def corpus(tmp_path, curation=None):
    proc, art, raw, cur = (tmp_path / d for d in ("processed", "art", "raw", "cur"))
    for d in (proc, art, raw / "geo", cur / "genealogy"):
        d.mkdir(parents=True)
    rows = [(i, 0, 1, i + 1) for i in range(6)] + [(6, 1, 1, 1)]
    pd.DataFrame(
        [(*r, ref, words) for r, ref, words in zip(
            rows, [*(f"Genesis 1:{i}" for i in range(1, 7)), "Exodus 1:1"],
            [[f"w{j}" for j in range(len(w))] for w in WORDS], strict=True)],
        columns=["verse_id", "book_id", "chapter", "verse", "ref", "display_tokens"],
    ).to_parquet(proc / "verses.parquet")  # fmt: skip
    pd.DataFrame(
        [(v, i, [c], i) for v, ws in enumerate(WORDS) for i, c in enumerate(ws)],
        columns=["verse_id", "idx", "content_lemmas", "display_idx"],
    ).assign(morph=lambda d: d.content_lemmas.map(
        lambda c: "HNp" if c[0] in {"120", "2332", "8352", "85", "8283", "3327", "3063", "2696",
                                    "5"} else "HNcmsa"),
        display_idx=lambda d: d.display_idx.astype("Int32"),
    ).to_parquet(proc / "words.parquet")  # fmt: skip
    cfg = load_config()
    (raw / "geo" / cfg["sources"]["tipnr"]["files"][0].split("/")[-1]).write_text(TIPNR, "utf-8")
    if curation is not None:
        (cur / "genealogy" / "01-b1.yaml").write_text(curation, "utf-8")
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art),
                    "data_raw": str(raw), "curation": str(cur)}  # fmt: skip
    cfg["genealogy"] = {
        **cfg["genealogy"], "root": "Adam@Gen.1.1",
        "tribes": {"Tribe of Judah": "Judah@Gen.1.4"},
        "blocks": {"b1": ["Genesis 1:1", "Genesis 1:6"], "b2": ["Exodus 1:1", "Exodus 1:1"]},
    }  # fmt: skip
    return cfg


def test_read_family(tmp_path):
    path = tmp_path / "tipnr.txt"
    path.write_text(TIPNR, encoding="utf-8")
    recs = {r.uid: r for r in read_tipnr(path)}
    isaac, judah, abraham = recs["Isaac@Gen.1.2"], recs["Judah@Gen.1.4"], recs["Abraham@Gen.1.2"]
    assert (isaac.family.father.uid, isaac.family.mother.uid) == ("Abraham@Gen.1.2",
                                                                  "Sarah@Gen.1.2")  # fmt: skip
    assert judah.family.father == TipnrRelative("Isaac@Gen.1.2", "?") and not judah.family.mother
    assert [(o.uid, o.marker) for o in abraham.family.offspring] == [
        ("Isaac@Gen.1.2", ""), ("Hebron@Gen.1.5", "f"),
    ]  # fmt: skip
    assert recs["Hezron@Gen.1.5"].family.tribe == "Tribe of Judah"
    assert recs["Abagtha@Exo.1.1"].family.tribe == ""  # TIPNR's ">" is none
    assert recs["Eve@Gen.1.1"].family.type == "Female"
    # `Gen.1.3a` (an occurrence in the verse) is kept as written; `refs` stays as places read it
    name = abraham.names[0]
    assert (name.refs, name.eng_refs) == ([(0, 1, 2)], [(0, 1, 2), (0, 1, 3)])
    assert recs["a_wife_of_Hezron@Gen.1.5"].names[0].kind == "Mentioned"
    assert relatives("Zerah@Gen.38.30-Mat(a), Tehinnah@1Ch.4.12=H8468, >") == [
        TipnrRelative("Zerah@Gen.38.30-Mat", "a"), TipnrRelative("Tehinnah@1Ch.4.12", ""),
    ]  # fmt: skip


def test_english_numbering():
    # 1 Chronicles: Hebrew 5 has 41 verses, 6 has 66; English 6:1-15 is Hebrew 5:27-41
    vid_of, n = {}, 0
    for ch, last in ((5, 41), (6, 66)):
        for v in range(1, last + 1):
            vid_of[(37, ch, v)] = n
            n += 1
    vid_of[(38, 1, 1)] = n  # the next book
    eng = English(vid_of, {37: "1Chr", 38: "2Chr"})
    assert eng(37, 6, 1) == vid_of[(37, 5, 27)]
    assert eng(37, 6, 15) == vid_of[(37, 5, 41)]
    assert eng(37, 6, 16) == vid_of[(37, 6, 1)]
    assert eng(37, 5, 26) == vid_of[(37, 5, 26)]
    assert eng(37, 6, 81) == vid_of[(37, 6, 66)]
    assert eng(37, 6, 82) is None  # past the book's end
    assert eng(37, 7, 1) is None


def test_cues():
    def words(content):
        return [Word(i, i, frozenset([int(c.rstrip("a"))]), frozenset([c]))
                for i, c in enumerate(content)]  # fmt: skip

    ws = words(["3327", "1121a", "85"])  # יצחק בן אברהם
    assert cue(ws, [2], [0], "father", 3) == ("construct", 2)
    assert cue(words(["1121a", "3327", "3063"]), [1], [2], "father", 3)[0] == "sons_of"
    assert cue(words(["7121", "85", "3205", "3327"]), [1], [3], "father", 3)[0] == "begot"
    assert cue(words(["85", "1", "3327"]), [0], [2], "father", 3)[0] == "kin"
    assert cue(words(["85", "3327"]), [0], [1], "father", 3)[0] == "together"
    assert cue(words(["120", "802", "2332"]), [0], [2], "spouse", 3)[0] == "wife"

    # a list's heading: the parent named the verse before
    w = {"construct": 5, "sons_of": 4, "begot": 3, "kin": 2, "together": 1, "nearby": 0, "wife": 4}
    a = Person("P", "", "m", "person", verses={10: [1]})
    b = Person("C", "", "m", "person", verses={11: [0], 20: [0]})
    lk = Link("P", "C", "father")
    assert rank_proofs(lk, a, b, {}, w, 3, near=2) == [(11, "nearby", [0])]
    assert rank_proofs(lk, a, b, {}, w, 3, near=0) == []


def test_run_genealogy(tmp_path):
    cfg = corpus(tmp_path)
    out = run_genealogy(cfg, log=lambda _: None)
    p = pd.read_parquet(out / "persons.parquet")
    assert p[["person_id", "key", "he", "placement"]].values.tolist() == [
        [1, "Adam@Gen.1.1", "אדם", "root"],
        [2, "Eve@Gen.1.1", "חוה", "spouse"],  # married in: beside Adam
        [3, "Seth@Gen.1.1", "שת", "tree"],
        [4, "Abraham@Gen.1.2", "אברהם", "unattached"],  # no parent, no tribe
        [5, "Isaac@Gen.1.2", "יצחק", "tree"],
        [6, "Sarah@Gen.1.2", "שרה", "spouse"],
        [7, "Judah@Gen.1.4", "יהודה", "tree"],
        [8, "Hezron@Gen.1.5", "חצרון", "tribe"],  # under Judah, the eponym of his tribe
        [9, "a_wife_of_Hezron@Gen.1.5", "", "spouse"],
        [10, "Abagtha@Exo.1.1", "אבגתא", "unattached"],
        [11, UNATTACHED, "", "virtual"],
        [12, "virtual:book:0", "", "virtual"],
        [13, "virtual:book:1", "", "virtual"],
    ]  # fmt: skip
    assert p.set_index("key").kind["a_wife_of_Hezron@Gen.1.5"] == "anon"
    assert json.loads(p.set_index("key").founded["Abraham@Gen.1.2"]) == ["Hebron@Gen.1.5"]
    assert p.book_id.tolist()[-2:] == [0, 1]
    links = pd.read_parquet(out / "links.parquet")
    proofs = pd.read_parquet(out / "proofs.parquet")
    by = {(r.child_id, r.parent_id, r.role): r for r in links.itertuples()}

    def verses(child, parent, role):
        lk = by[(child, parent, role)]
        ps = proofs[proofs.link_id == lk.link_id].sort_values("rank")
        return list(zip(ps.verse_id, ps.cue, strict=True))

    # Isaac son of Abraham: the construct (Gen 1:3) before the verse of his birth (1:2)
    assert verses(5, 4, "father") == [(2, "construct"), (1, "begot")]
    assert verses(5, 6, "mother") == [(1, "begot")]
    assert verses(3, 1, "father") == [(0, "begot")]
    assert verses(7, 5, "father") == [(3, "sons_of")]
    assert verses(2, 1, "spouse") == [(0, "wife")]
    isaac = proofs[proofs.link_id == by[(5, 4, "father")].link_id].iloc[0]
    assert json.loads(isaac.tokens) == [0, 2]  # the display tokens of both names
    assert by[(7, 5, "father")].doubt and by[(7, 5, "father")].drawn
    assert not by[(5, 6, "mother")].drawn and by[(5, 4, "father")].drawn
    assert by[(8, 7, "unstated")].drawn and by[(8, 7, "unstated")].source == "tribe"
    assert by[(4, 12, "unstated")].drawn and by[(12, 11, "unstated")].drawn
    assert (8, 9, "spouse") not in by and by[(9, 8, "spouse")].role == "spouse"
    meta = json.loads((out / "genealogy.meta.json").read_text("utf-8"))
    assert meta["persons"] == 10 and meta["parent_links"] == 5 and meta["proved"] == 5
    assert meta["placement"] == {"root": 1, "tree": 3, "tribe": 1, "spouse": 3, "unattached": 2}
    assert meta["blocks"] == {"todo": 2, "draft": 0, "reviewed": 0}
    first = (out / "links.parquet").read_bytes()
    run_genealogy(cfg, log=lambda _: None)
    assert (out / "links.parquet").read_bytes() == first


REVIEW = """
block: b1
status: reviewed
people:
  - {key: "anon:daughter-of-seth", he: "בת שת", sex: f, kind: anon}
links:
  - "Seth@Gen.1.1 <- Adam@Gen.1.1"
  - {child: "anon:daughter-of-seth", parent: "Seth@Gen.1.1", status: added, proof: [Genesis 1:6]}
  - {child: "Isaac@Gen.1.2", parent: "Sarah@Gen.1.2", status: rejected}
conflicts:
  - kind: bible
    child: "Judah@Gen.1.4"
    readings:
      - {parent: "Abraham@Gen.1.2", proof: [Genesis 1:2]}
      - {parent: "Isaac@Gen.1.2", proof: [Genesis 1:4]}
    note: {en: "two fathers", he: "שני אבות"}
missed:
  - {ref: Genesis 1:5, reason: "a name alone"}
"""


def test_review_applied(tmp_path):
    cfg = corpus(tmp_path, REVIEW)
    out = run_genealogy(cfg, log=lambda _: None)
    p = pd.read_parquet(out / "persons.parquet").set_index("key")
    pid = p.person_id.to_dict()
    links = pd.read_parquet(out / "links.parquet")
    by = {(r.child_id, r.parent_id, r.role): r for r in links.itertuples()}
    seth = by[(pid["Seth@Gen.1.1"], pid["Adam@Gen.1.1"], "father")]
    assert (seth.status, seth.block) == ("confirmed", "b1")
    daughter = by[(pid["anon:daughter-of-seth"], pid["Seth@Gen.1.1"], "father")]
    assert (daughter.status, daughter.source, daughter.drawn) == ("added", "curated", True)
    assert p.he["anon:daughter-of-seth"] == "בת שת" and p.kind["anon:daughter-of-seth"] == "anon"
    proofs = pd.read_parquet(out / "proofs.parquet")
    assert proofs[proofs.link_id == daughter.link_id][["verse_id", "source"]].values.tolist() == [
        [5, "curated"]
    ]
    assert by[(pid["Isaac@Gen.1.2"], pid["Sarah@Gen.1.2"], "mother")].status == "rejected"
    # the conflict: Judah under the first reading, the other a cross-link of the same conflict
    first = by[(pid["Judah@Gen.1.4"], pid["Abraham@Gen.1.2"], "father")]
    other = by[(pid["Judah@Gen.1.4"], pid["Isaac@Gen.1.2"], "father")]
    assert (first.drawn, first.status, other.drawn, other.status) == (True, "reading", False,
                                                                     "confirmed")  # fmt: skip
    assert first.conflict_id == other.conflict_id == 1
    c = pd.read_parquet(out / "conflicts.parquet").iloc[0]
    assert json.loads(c.readings) == [first.link_id, other.link_id] and c.note_he == "שני אבות"
    b = pd.read_parquet(out / "blocks.parquet").set_index("block")
    assert b.loc["b1"][["status", "n_links", "n_conflicts", "n_missed"]].tolist() == [
        "reviewed",
        3,
        1,
        1,
    ]
    assert b.status["b2"] == "todo"
    # reviewed: every parent link checked (Seth's mother is not yet)
    assert p.reviewed["Judah@Gen.1.4"] and not p.reviewed["Seth@Gen.1.1"]
    sheet = run_genealogy_review(cfg, "b1", log=lambda _: None).read_text("utf-8")
    assert "## Links" in sheet and "`Seth@Gen.1.1 <- Adam@Gen.1.1`" in sheet
    assert "Genesis 1:5" not in sheet.split("## Cue verses")[1].split("## Conflicts")[0]
    with pytest.raises(RuntimeError, match="unknown block"):
        run_genealogy_review(cfg, "b9", log=lambda _: None)


BAD = """
block: b1
links:
  - {child: "Nobody@Gen.1.1", parent: "Adam@Gen.1.1"}
  - {child: "Isaac@Gen.1.2", parent: "Abraham@Gen.1.2", status: added}
  - {child: "Seth@Gen.1.1", parent: "Adam@Gen.1.1", proof: [Genesis 9:9]}
  - "Seth@Gen.1.1 Adam@Gen.1.1"
conflicts:
  - {kind: bible, child: "Judah@Gen.1.4", readings: [{parent: "Isaac@Gen.1.2"}]}
"""


def test_review_errors(tmp_path):
    cfg = corpus(tmp_path, BAD)
    with pytest.raises(CurationError) as e:
        run_genealogy(cfg, log=lambda _: None)
    msg = str(e.value)
    for want in ("unknown person 'Nobody@Gen.1.1'", "is in TIPNR: confirm or fix it",
                 "no verse 'Genesis 9:9'", "write `child <- parent`", "at least two"):  # fmt: skip
        assert want in msg


def test_cycle_is_an_error(tmp_path):
    cfg = corpus(tmp_path, 'block: b1\nlinks:\n  - {child: "Adam@Gen.1.1", parent: "Seth@Gen.1.1",'
                           ' status: added}\n')  # fmt: skip
    with pytest.raises(RuntimeError, match="cycles"):
        run_genealogy(cfg, log=lambda _: None)


def test_missing_tipnr_fails_fast(tmp_path):
    cfg = corpus(tmp_path)
    for f in (tmp_path / "raw" / "geo").iterdir():
        f.unlink()
    with pytest.raises(FileNotFoundError, match="--only geo"):
        run_genealogy(cfg, log=lambda _: None)
