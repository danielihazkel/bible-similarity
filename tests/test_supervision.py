import pandas as pd
import pytest

from bsim.config import load_config
from bsim.eval.supervision import adoption, variant_config
from bsim.train.negatives import linked_sets
from bsim.train.pairs import extra_links, merge_pairs, training_pairs
from bsim.train.supervised import with_overrides


def _both(pairs, split, **extra):
    """Both directions of undirected pairs, as the gold files store them."""
    rows = [(a, b) for a, b in pairs] + [(b, a) for a, b in pairs]
    df = pd.DataFrame(rows, columns=["src_vid", "tgt_vid"]).assign(split=split)
    return df.assign(**extra)


SEFARIA = pd.concat([_both([(1, 2)], "train"), _both([(3, 4)], "dev")], ignore_index=True)


def test_merge_pairs_adds_only_new_train_pairs():
    ob = pd.concat(
        [
            _both([(2, 1), (5, 6), (7, 8)], "train"),  # (2, 1) is Sefaria's
            _both([(3, 4)], "train"),  # Sefaria links it in another split: still not added
            _both([(9, 10)], "dev"),  # dev never trains
        ],
        ignore_index=True,
    )
    etcbc = _both([(6, 5), (11, 12)], "train")  # (6, 5) came with OpenBible already
    out = merge_pairs(SEFARIA, {"openbible": ob, "etcbc": etcbc})
    assert out.source.value_counts().to_dict() == {"sefaria": 2, "openbible": 4, "etcbc": 2}
    got = {(s, a, b) for s, a, b in zip(out.source, out.src_vid, out.tgt_vid, strict=True)}
    assert ("openbible", 5, 6) in got and ("openbible", 6, 5) in got
    assert ("etcbc", 11, 12) in got and ("etcbc", 12, 11) in got
    assert not {(a, b) for _, a, b in got} & {(3, 4), (4, 3), (9, 10)}
    # without extras, Sefaria's train rows in their order (the pipeline's model is unchanged)
    alone = merge_pairs(SEFARIA, {})
    assert alone[["src_vid", "tgt_vid"]].values.tolist() == [[1, 2], [2, 1]]


def test_extra_links_reads_the_gold_files(tmp_path):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "data_processed": str(tmp_path)}
    cfg["train"]["supervised"]["extra_min_votes"] = 10
    with pytest.raises(RuntimeError, match="build-golds"):
        extra_links(cfg, "openbible")
    with pytest.raises(RuntimeError, match="unknown extra_pairs source"):
        extra_links(cfg, "kjv")
    ob = pd.concat([_both([(5, 6)], "train", votes=12), _both([(7, 8)], "train", votes=5)])
    ob.to_parquet(tmp_path / "openbible_links.parquet")
    assert extra_links(cfg, "openbible").src_vid.tolist() == [5, 6]  # under 10 votes dropped
    SEFARIA.assign(level="verse").to_parquet(tmp_path / "links.parquet")
    pairs, linked = training_pairs(with_overrides(cfg, extra_pairs=["openbible"]))
    assert pairs.source.tolist() == ["sefaria", "sefaria", "openbible", "openbible"]
    # a hard negative may be linked by neither source, in any split
    assert linked_sets(linked) == {1: {2}, 2: {1}, 3: {4}, 4: {3}, 5: {6}, 6: {5}}


def test_variant_config():
    cfg = load_config()
    out = variant_config(cfg, "both", {"extra_pairs": ["openbible", "etcbc"], "seed": 14})
    sup = out["train"]["supervised"]
    assert sup["output"] == f"{cfg['train']['supervised']['output']}-both"
    assert sup["extra_pairs"] == ["openbible", "etcbc"] and out["seed"] == 14
    assert cfg["train"]["supervised"]["extra_pairs"] == ["openbible", "etcbc"] and cfg["seed"] == 13


def _g(mean, lo, hi):
    return {"fused": {"mean": mean, "lo": lo, "hi": hi}}


def _v(sefaria, openbible, etcbc=(0, -0.1, 0.1)):
    """A variant's fused gains (mean, lo, hi) on the three golds."""
    return {"sefaria": _g(*sefaria), "openbible": _g(*openbible), "etcbc": _g(*etcbc)}


def test_adoption_rule():
    gains = {
        "seed14": _v((0, -1, 1), (-0.01, -0.02, 0)),
        # gains on OpenBible beyond the retrain noise, loses nothing significant: passes
        "a": _v((0.001, -0.01, 0.01), (0.03, 0.02, 0.04)),
        # the same, with a larger Sefaria gain: chosen
        "b": _v((0.004, -0.01, 0.02), (0.03, 0.02, 0.04)),
        # significant Sefaria loss
        "c": _v((-0.02, -0.03, -0.01), (0.05, 0.04, 0.06)),
        # OpenBible CI above 0, but within what a retrain moves (|-0.01|)
        "d": _v((0, -0.01, 0.01), (0.008, 0.001, 0.015)),
        # significant ETCBC loss
        "e": _v((0, -0.01, 0.01), (0.03, 0.02, 0.04), (-0.05, -0.08, -0.02)),
    }
    ok, chosen = adoption(gains, "seed14")
    assert ok == {"seed14": False, "a": True, "b": True, "c": False, "d": False, "e": False}
    assert chosen == "b"
    assert adoption({"seed14": gains["seed14"]}, "seed14") == ({"seed14": False}, None)
