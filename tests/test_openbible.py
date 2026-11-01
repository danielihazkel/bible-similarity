import pandas as pd
import pytest

from bsim.config import load_config
from bsim.data.canon import BY_OSIS
from bsim.eval.openbible import (
    english_of,
    gold_links,
    gold_of,
    overlap,
    parse_ref,
    read_refs,
    resolve,
)

# a tiny canon slice in the Hebrew numbering (each chapter from verse 1, as `English` anchors it):
# Gen 1:1-5, Ps 8:1-3 (verse 1 the title), Isa 45:1-3, Joel 4:1-2 (the English Joel 3)
OSIS = (
    [f"Gen.1.{i}" for i in range(1, 6)]
    + [f"Ps.8.{i}" for i in range(1, 4)]
    + [f"Isa.45.{i}" for i in (1, 2, 3)]
    + ["Joel.4.1", "Joel.4.2"]
)
VERSES = pd.DataFrame(
    {
        "verse_id": range(len(OSIS)),
        "book_id": [BY_OSIS[o.split(".")[0]].book_id for o in OSIS],
        "osis": OSIS,
    }
)
ENGLISH = english_of(VERSES)


def test_parse_and_resolve():
    assert parse_ref("1Sam.17.4") == ("1Sam", 17, 4)
    assert parse_ref("Gen.1") is None and parse_ref("Gen.x.1") is None
    assert resolve("Isa.45.1-Isa.45.2", ENGLISH, 10) == [8, 9]
    assert resolve("Isa.45.1-Isa.45.3", ENGLISH, 2) is None  # longer than max_range
    assert resolve("Ps.8.1", ENGLISH, 10) == [6]  # the English verse 1 is the Hebrew's 2
    assert resolve("Ps.8.0", ENGLISH, 10) is None  # the title has no English number
    assert resolve("Joel.3.1", ENGLISH, 10) == [11]  # English Joel 3 is the Hebrew's 4
    assert resolve("Rom.11.36", ENGLISH, 10) is None  # not Hebrew Bible
    assert resolve("Gen.2.9", ENGLISH, 10) is None  # no such verse


def test_gold_links_and_overlap():
    cfg = load_config()
    cfg["openbible"] = {**cfg["openbible"], "min_votes": 5}
    refs = pd.DataFrame(
        {
            "frm": ["Gen.1.1", "Gen.1.1", "Gen.1.1", "Gen.1.1", "Gen.1.2"],
            "to": ["Isa.45.1-Isa.45.2", "Ps.8.3", "Gen.1.2", "Isa.45.3", "Rom.1.1"],
            "votes": [20, 30, 50, 2, 9],
        }
    )
    splits = {"Gen": "train", "Isa": "dev", "Ps": "train", "Joel": "test"}
    split_of_book = {BY_OSIS[o].book_id: sp for o, sp in splits.items()}
    links, stats = gold_links(refs, VERSES, split_of_book, cfg)
    # kept: Gen 1:1 -> Isa 45:1, 45:2; dropped: Ps 8:3 (the Hebrew 8:4, past this slice), Gen 1:2
    # (neighbour), < 5 votes
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


def test_gold_files_round_trip(tmp_path):
    from bsim.eval.openbible import read_gold, write_gold

    with pytest.raises(RuntimeError, match="build-golds"):
        read_gold(tmp_path, "openbible_links")
    links = pd.DataFrame({"src_vid": [1, 2], "tgt_vid": [2, 1], "votes": [7, 7], "split": "train"})
    write_gold(tmp_path, "openbible_links", links, {"pairs": 1})
    back, stats = read_gold(tmp_path, "openbible_links")
    pd.testing.assert_frame_equal(back, links)
    assert stats == {"pairs": 1}
