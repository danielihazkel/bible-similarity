import numpy as np
import pandas as pd
import pytest

from bsim.config import load_config
from bsim.retrieve.fusion import final_lists, final_systems, rrf, run_fuse, to_topk_frame
from bsim.retrieve.topk import Units


def _frame(rows: list[tuple[int, int, float]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["src", "tgt", "score"])
    df["rank"] = df.groupby("src").cumcount() + 1
    return df


def test_rrf_hand_computed():
    lex = _frame([(0, 1, 9.0), (0, 2, 8.0)])
    sem = _frame([(0, 3, 0.9), (0, 1, 0.8)])
    out = rrf(lex, sem, w_lex=0.5, w_sem=1.0, rrf_k=60, k=50)
    by_tgt = out.set_index("tgt")
    assert by_tgt.score[1] == pytest.approx(0.5 / 61 + 1 / 62)
    assert by_tgt.score[2] == pytest.approx(0.5 / 62)  # only in the lexical list
    assert by_tgt.score[3] == pytest.approx(1 / 61)  # only in the semantic list
    assert out.tgt.tolist() == [1, 3, 2] and out["rank"].tolist() == [1, 2, 3]
    row = by_tgt.loc[2]
    assert row.lex_rank == 2 and row.lex_score == 8.0
    assert pd.isna(row.sem_rank) and pd.isna(row.sem_score)
    assert by_tgt.loc[1].sem_rank == 2


def test_rrf_ties_by_target_and_truncates_per_source():
    lex = _frame([(0, 5, 1.0), (1, 2, 1.0), (1, 3, 0.5)])
    sem = _frame([(0, 4, 1.0), (1, 9, 1.0)])
    out = rrf(lex, sem, w_lex=1.0, w_sem=1.0, rrf_k=60, k=2)
    assert out[out.src == 0].tgt.tolist() == [4, 5]  # equal scores -> lower target first
    assert out[out.src == 1].tgt.tolist() == [2, 9]  # k=2 drops target 3
    assert out.groupby("src")["rank"].max().tolist() == [2, 2]


def test_to_topk_frame_ids():
    fused = rrf(_frame([(0, 2, 1.0)]), _frame([(0, 1, 1.0)]), 1.0, 1.0, 60, 50)
    v = to_topk_frame(fused, "verse", None)
    assert v.src_id.tolist() == ["v:0", "v:0"] and v.tgt_id.tolist() == ["v:1", "v:2"]
    units = Units(np.array(["c:a", "c:b", "c:c"], dtype=object), np.arange(3), np.arange(3))
    u = to_topk_frame(fused, "chapter", units)
    assert u.tgt_id.tolist() == ["c:b", "c:c"] and set(u.unit_type) == {"chapter"}
    assert list(u.columns[:4]) == ["unit_type", "src_id", "rank", "tgt_id"]


def test_final_lists():
    cfg = load_config()
    fs = cfg["final_systems"]
    assert final_lists(cfg, "verse") == (fs["lexical"], fs["semantic"])
    sem = f"{fs['semantic']}_{fs['unit_aggregation']}"
    assert final_lists(cfg, "chapter") == (fs["unit_lexical"], sem)
    assert final_systems(cfg, "pericope")["fused"] == fs["fused"]


def test_run_fuse_writes_all_unit_types(tmp_path):
    cfg = load_config()
    proc, art = tmp_path / "processed", tmp_path / "artifacts"
    cfg["paths"] = {**cfg["paths"], "data_processed": str(proc), "artifacts": str(art)}
    cfg["units"] = {**cfg["units"], "types": ["verse", "chapter"]}
    cfg["final_systems"] = {
        **cfg["final_systems"],
        "lexical": "lx",
        "semantic": "sm",
        "unit_lexical": "tfidf",
        "unit_aggregation": "bma",
    }
    proc.mkdir()
    pd.DataFrame(
        {
            "unit_id": ["c:0", "c:1"],
            "unit_type": "chapter",
            "start_verse_id": [0, 2],
            "end_verse_id": [1, 3],
        }
    ).to_parquet(proc / "units.parquet")

    def write(unit_type: str, name: str, rows: list[tuple[str, str, int]]) -> None:
        d = art / "topk" / unit_type
        d.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            {
                "unit_type": unit_type,
                "src_id": [r[0] for r in rows],
                "rank": [r[2] for r in rows],
                "tgt_id": [r[1] for r in rows],
                "score": np.float32(1.0),
            }
        ).to_parquet(d / f"{name}.parquet")

    write("verse", "lx", [("v:0", "v:3", 1)])
    write("verse", "sm", [("v:0", "v:2", 1), ("v:0", "v:3", 2)])
    write("chapter", "tfidf", [("c:0", "c:1", 1)])
    write("chapter", "sm_bma", [("c:1", "c:0", 1)])
    run_fuse(cfg, log=lambda _: None)

    v = pd.read_parquet(art / "topk" / "verse" / "fused.parquet")
    assert v.tgt_id.tolist() == ["v:3", "v:2"]  # in both lists beats semantic rank 1 alone
    assert v.lex_rank.tolist()[0] == 1 and pd.isna(v.lex_rank.tolist()[1])
    c = pd.read_parquet(art / "topk" / "chapter" / "fused.parquet")
    assert sorted(zip(c.src_id, c.tgt_id, strict=True)) == [("c:0", "c:1"), ("c:1", "c:0")]
    assert (art / "topk" / "chapter" / "fused.meta.json").exists()

    (art / "topk" / "chapter" / "sm_bma.parquet").unlink()
    with pytest.raises(RuntimeError, match="bsim units"):
        run_fuse(cfg, log=lambda _: None)
