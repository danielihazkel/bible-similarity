import pandas as pd

from bsim.config import load_config
from bsim.eval.openbible import gold_links, gold_of, overlap, parse_ref, read_refs, resolve

# a tiny canon slice: Gen 1:1-5 (book 0), Ps 8:1-3 (book 26), Isa 45:18-20 (book 22), Joel 2:1
VERSES = pd.DataFrame(
    {
        "verse_id": range(12),
        "book_id": [0] * 5 + [26] * 3 + [22] * 3 + [28],
        "osis": [f"Gen.1.{i}" for i in range(1, 6)]
        + [f"Ps.8.{i}" for i in range(1, 4)]
        + [f"Isa.45.{i}" for i in (18, 19, 20)]
        + ["Joel.2.1"],
    }
)
VERSE_OF = {parse_ref(o): i for i, o in enumerate(VERSES.osis)}
UNSAFE = {"Ps": "all", "Joel": [2, 3, 4]}


def test_parse_and_resolve():
    assert parse_ref("1Sam.17.4") == ("1Sam", 17, 4)
    assert parse_ref("Gen.1") is None and parse_ref("Gen.x.1") is None
    assert resolve("Isa.45.18-Isa.45.19", VERSE_OF, UNSAFE, 10) == [8, 9]
    assert resolve("Isa.45.18-Isa.45.20", VERSE_OF, UNSAFE, 2) is None  # longer than max_range
    assert resolve("Ps.8.1", VERSE_OF, UNSAFE, 10) is None  # psalm titles: unsafe
    assert resolve("Joel.2.1", VERSE_OF, UNSAFE, 10) is None
    assert resolve("Rom.11.36", VERSE_OF, UNSAFE, 10) is None  # not Hebrew Bible
    assert resolve("Gen.1.9", VERSE_OF, UNSAFE, 10) is None  # no such verse


def test_gold_links_and_overlap():
    cfg = load_config()
    cfg["openbible"] = {**cfg["openbible"], "unsafe_chapters": UNSAFE, "min_votes": 5}
    refs = pd.DataFrame(
        {
            "frm": ["Gen.1.1", "Gen.1.1", "Gen.1.1", "Gen.1.1", "Gen.1.2"],
            "to": ["Isa.45.18-Isa.45.19", "Ps.8.3", "Gen.1.2", "Isa.45.20", "Rom.1.1"],
            "votes": [20, 30, 50, 2, 9],
        }
    )
    split_of_book = {0: "train", 22: "dev", 26: "train", 28: "test"}
    links, stats = gold_links(refs, VERSES, split_of_book, cfg)
    # kept: Gen 1:1 -> Isa 45:18, 45:19; dropped: psalm (unsafe), Gen 1:2 (neighbour), < 5 votes
    assert stats["pairs"] == 2 and stats["votes"] == 1 and stats["unresolved"] == 1
    assert sorted(zip(links.src_vid, links.tgt_vid, strict=True)) == [
        (0, 8),
        (0, 9),
        (8, 0),
        (9, 0),
    ]
    assert set(links.split) == {"dev"}
    gold = gold_of(links, "dev")
    assert gold[0] == {8, 9} and overlap(gold, {0: {9, 3}}) == 1


def test_read_refs(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("From Verse\tTo Verse\tVotes\t#licence note\nGen.1.1\tPs.8.3\t12\n", "utf-8")
    df = read_refs(f)
    assert df.values.tolist() == [["Gen.1.1", "Ps.8.3", 12]]
