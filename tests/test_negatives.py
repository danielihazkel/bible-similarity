import numpy as np
import pandas as pd
import pytest

from bsim.train.negatives import linked_sets, mine_hard_negatives
from bsim.train.supervised import with_overrides

# 15 verses: book 0 = vids 0..4, book 1 = vids 5..9 (train), book 2 = vids 10..14 (dev)
BOOK = np.repeat([0, 1, 2], 5)
TRAIN_BOOK = np.array([True, True, False])
WINDOW = 1


def _candidates(src, tgts):
    """A neighbour-filtered top-k frame for one query: ranks 1.. in the given order."""
    return pd.DataFrame({"src": src, "tgt": tgts, "rank": np.arange(1, len(tgts) + 1)})


def _mine(anchors, positives, cand, linked=None, text_key=None, rank_range=(2, 10), seed=0):
    return mine_hard_negatives(
        np.array(anchors),
        np.array(positives),
        cand,
        BOOK,
        TRAIN_BOOK,
        linked or {},
        np.arange(15) if text_key is None else np.asarray(text_key),
        rank_range,
        WINDOW,
        seed,
    )


def test_only_eligible_candidates_are_drawn():
    # anchor 0, positive 8. Candidate list (rank 1..9):
    #   9 rank 1: below the rank range
    #   10 dev book; 1 neighbour of the anchor; 7 neighbour of the positive;
    #   3 linked to the anchor; 4 linked to the positive; 2 same text as the positive
    #   5 and 6 eligible (ranks 8, 9)
    cand = _candidates(0, [9, 10, 1, 7, 3, 4, 2, 5, 6])
    linked = {0: {8, 3}, 8: {0, 4}}
    text_key = np.arange(15)
    text_key[2] = text_key[8]
    picks = {
        int(_mine([0], [8], cand, linked, text_key, seed=s).negative_vid[0]) for s in range(20)
    }
    assert picks == {5, 6}


def test_rank_and_fallback_columns():
    cand = _candidates(0, [6, 7])
    df = _mine([0, 1], [5, 5], cand)  # anchor 1 has no candidates -> fallback
    assert df.negative_vid[0] == 7 and df.negative_rank[0] == 2  # rank 1 is out of range
    assert not df.fallback[0]
    assert df.fallback[1] and df.negative_rank[1] == 0
    n = int(df.negative_vid[1])
    assert TRAIN_BOOK[BOOK[n]] and n not in (0, 1, 2, 4, 5, 6)  # not anchor/positive ±1


def test_deterministic_for_seed():
    cand = _candidates(0, list(range(5, 10)))
    a = _mine([0] * 10, [3] * 10, cand, seed=7)
    b = _mine([0] * 10, [3] * 10, cand, seed=7)
    pd.testing.assert_frame_equal(a, b)


def test_no_eligible_verse_raises():
    small_train = np.array([True, False, False])
    with pytest.raises(RuntimeError, match="no eligible negative"):
        mine_hard_negatives(
            np.array([0]),
            np.array([4]),
            _candidates(0, []),
            BOOK,
            small_train,
            {0: {2}},
            np.arange(15),
            (1, 10),
            WINDOW,
            0,
        )


def test_linked_sets_uses_verse_rows_of_every_split():
    links = pd.DataFrame(
        {
            "src_vid": [0, 7, 3, 10],
            "tgt_vid": [7, 0, 11, 3],
            "level": ["verse", "verse", "unit", "verse"],
        }
    )
    assert linked_sets(links) == {0: {7}, 7: {0}, 10: {3}}


def test_with_overrides_copies():
    cfg = {"train": {"supervised": {"init_from": "berel-simcse", "hard_negatives": True}}}
    out = with_overrides(cfg, init="base", hard_negatives=False)
    assert out["train"]["supervised"] == {"init_from": "base", "hard_negatives": False}
    assert cfg["train"]["supervised"]["init_from"] == "berel-simcse"


def test_run_hard_negatives_writes_under_its_name(tmp_path, monkeypatch):
    import json

    import bsim.train.negatives as neg
    from bsim.config import load_config

    cfg = load_config()
    proc, art = tmp_path / "processed", tmp_path / "artifacts"
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art)}
    (art / "topk" / "verse").mkdir(parents=True)
    (art / "topk" / "verse" / f"{neg.LEXICAL_SYSTEM}.parquet").touch()
    proc.mkdir()
    (proc / "links.parquet").touch()
    text = list("abcdefghijklmno")
    verses = {"verse_id": range(15), "book_id": BOOK, "chapter": 1, "text_model": text}
    pd.DataFrame(verses).to_parquet(proc / "verses.parquet")
    books = {"Genesis": "train", "Exodus": "train", "Leviticus": "dev"}
    (proc / "splits.json").write_text(json.dumps({"books": books}), "utf-8")
    pairs = pd.DataFrame({"src_vid": [0], "tgt_vid": [8], "source": ["etcbc"]})
    monkeypatch.setattr(neg, "training_pairs", lambda cfg: (pairs, pairs[["src_vid", "tgt_vid"]]))
    monkeypatch.setattr(neg, "read_topk", lambda path: _candidates(0, [5, 6]))
    monkeypatch.setattr(neg, "apply_filters", lambda df, *args: df)
    df = neg.run_hard_negatives(cfg, log=lambda s: None, name="hard_negatives_x")
    assert df.source.tolist() == ["etcbc"] and df.negative_vid[0] not in (0, 8)
    out = art / "train"
    assert sorted(p.name for p in out.iterdir()) == [
        "hard_negatives_x.meta.json",
        "hard_negatives_x.parquet",
    ]
    assert json.loads((out / "hard_negatives_x.meta.json").read_text("utf-8"))["by_source"] == {
        "etcbc": 1
    }


# --- negatives from the model's own list, screened by the cross-encoder (M143, §16.80) ---------


def test_a_refused_draw_is_drawn_again_and_asked_once():
    cand = _candidates(
        0, [9, 5, 6, 7]
    )  # ranks 2-4 in range: 5, 6, 7 (7 is the positive's neighbour)
    asked = []

    def accept(a, c):
        asked.extend(zip(a.tolist(), c.tolist(), strict=True))
        return c != 5  # 5 is a link no gold records

    redraws = []
    for seed in range(10):
        asked.clear()
        df = mine_hard_negatives(
            np.array([0, 0]), np.array([8, 8]), cand, BOOK, TRAIN_BOOK, {}, np.arange(15),
            (2, 10), WINDOW, seed, None, accept,
        )  # fmt: skip
        assert df.negative_vid.tolist() == [6, 6]
        assert len(asked) == len(set(asked))  # each pair asked once
        assert set(df.redrawn) <= {0, 1}
        redraws.append(int(df.redrawn.sum()))
    assert any(redraws)  # 5 was drawn first now and then, and drawn again
    # every candidate refused: a random train verse, not screened
    df = mine_hard_negatives(
        np.array([0]), np.array([8]), cand, BOOK, TRAIN_BOOK, {}, np.arange(15), (2, 10), WINDOW,
        0, None, lambda a, c: np.zeros(len(a), bool),
    )  # fmt: skip
    assert df.fallback[0] and df.negative_rank[0] == 0 and df.redrawn[0] == 2


def test_without_a_screen_the_draws_are_unchanged():
    cand = pd.concat([_candidates(0, [9, 5, 6, 3, 4]), _candidates(1, [6, 7, 8, 9])])
    args = (np.array([0, 1, 0]), np.array([8, 12, 9]), cand, BOOK, TRAIN_BOOK, {}, np.arange(15))
    plain = mine_hard_negatives(*args, (2, 10), WINDOW, 3)
    screened = mine_hard_negatives(*args, (2, 10), WINDOW, 3, None, lambda a, c: c >= 0)
    assert plain.negative_vid.tolist() == screened.negative_vid.tolist()
    assert not screened.redrawn.any()


def test_ce_accept_reuses_stored_scores(tmp_path, monkeypatch):
    import bsim.train.rerank as rr
    from bsim.config import load_config
    from bsim.train.negatives import ce_accept

    cfg = load_config()
    art = tmp_path / "artifacts"
    cfg["paths"] = {**cfg["paths"], "artifacts": str(art)}
    cfg["train"]["supervised"]["ce_max"] = 0.5
    (art / "topk" / "verse").mkdir(parents=True)
    stored = pd.DataFrame(
        {"unit_type": "verse", "src_id": ["v:0", "v:0"], "rank": [1, 2], "tgt_id": ["v:5", "v:6"],
         "score": 0.1, "ce_score": [0.9, 0.2]}
    )  # fmt: skip
    stored.to_parquet(art / "topk" / "verse" / f"{cfg['rerank']['system']}.parquet")
    loads, scored = [], []
    monkeypatch.setattr(rr, "load_reranker", lambda cfg: loads.append(1) or "model")

    def score_pairs(model, texts, a, b, batch):
        scored.extend(zip(a.tolist(), b.tolist(), strict=True))
        return np.full(len(a), 0.7, np.float32)

    monkeypatch.setattr(rr, "score_pairs", score_pairs)
    accept = ce_accept(cfg, list("abcdefghij"), log=lambda s: None)
    # (0, 5) stored 0.9: refused; (0, 6) stored 0.2: kept; (6, 0) the other direction: computed
    assert accept(np.array([0, 0]), np.array([5, 6])).tolist() == [False, True] and not loads
    assert accept(np.array([6]), np.array([0])).tolist() == [False]
    assert loads == [1] and scored == [(6, 0)]


def test_negatives_from_picks_the_list(tmp_path, monkeypatch):
    import json

    import bsim.train.negatives as neg
    from bsim.config import load_config

    cfg = load_config()
    proc, art = tmp_path / "processed", tmp_path / "artifacts"
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art)}
    (art / "topk" / "verse").mkdir(parents=True)
    proc.mkdir()
    (proc / "links.parquet").touch()
    verses = {
        "verse_id": range(15),
        "book_id": BOOK,
        "chapter": 1,
        "text_model": list("abcdefghijklmno"),
    }
    pd.DataFrame(verses).to_parquet(proc / "verses.parquet")
    books = {"Genesis": "train", "Exodus": "train", "Leviticus": "dev"}
    (proc / "splits.json").write_text(json.dumps({"books": books}), "utf-8")
    pairs = pd.DataFrame({"src_vid": [0], "tgt_vid": [8], "source": ["sefaria"]})
    monkeypatch.setattr(neg, "training_pairs", lambda cfg: (pairs, pairs[["src_vid", "tgt_vid"]]))
    read = []
    monkeypatch.setattr(
        neg, "read_topk", lambda path: read.append(path.name) or _candidates(0, [5, 6])
    )
    monkeypatch.setattr(neg, "apply_filters", lambda df, *args: df)
    sup = cfg["train"]["supervised"]
    sup["negatives_from"] = "self"
    with pytest.raises(RuntimeError, match=sup["self_system"]):
        neg.run_hard_negatives(cfg, log=lambda s: None, name="x")
    (art / "topk" / "verse" / f"{sup['self_system']}.parquet").touch()
    neg.run_hard_negatives(cfg, log=lambda s: None, name="x")
    assert read == [f"{sup['self_system']}.parquet"]
    meta = json.loads((art / "train" / "x.meta.json").read_text("utf-8"))
    assert (meta["source"], meta["negatives_from"], meta["redrawn"]) == (
        sup["self_system"],
        "self",
        0,
    )
    sup["negatives_from"] = "dense"
    with pytest.raises(RuntimeError, match="negatives_from must be one of"):
        neg.run_hard_negatives(cfg, log=lambda s: None, name="x")
