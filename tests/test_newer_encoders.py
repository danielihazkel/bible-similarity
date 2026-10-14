import pytest

from bsim.config import load_config
from bsim.eval.newer_encoders import adoption, candidate_config, noise_bar, report


def _g(mean, lo, hi):
    return {"mean": mean, "lo": lo, "hi": hi, "better": 1, "worse": 1, "queries": 2}


def _gains(sef, ob=(0.0, -0.01, 0.01), et=(0.0, -0.01, 0.01)):
    flat = _g(0.0, -0.01, 0.01)
    return {
        "sefaria": {"fused": _g(*sef), "semantic": flat},
        "openbible": {"fused": _g(*ob), "semantic": flat},
        "etcbc": {"fused": _g(*et), "semantic": flat},
    }


def test_candidate_config_starts_from_the_base():
    cfg = load_config()
    cfg["train"]["supervised"]["init_from"] = "berel-simcse"
    overrides = {"base": "dicta-il/dictabert-large", "mini_batch_size": 16}
    out = candidate_config(cfg, "dictabert_large", overrides)
    sup = out["train"]["supervised"]
    assert sup["base"] == "dicta-il/dictabert-large" and sup["mini_batch_size"] == 16
    assert sup["init_from"] == "base" and sup["output"] == "dictabert_large-sup"
    # the rest of the recipe is the model in use's, and cfg itself is untouched
    assert sup["extra_pairs"] == cfg["train"]["supervised"]["extra_pairs"]
    assert out["seed"] == cfg["seed"] and cfg["train"]["supervised"]["output"] == "berel-sup"


def test_noise_bar_is_the_largest_fused_gain_either_way():
    sup = {"results": {"seed14": {"gains": _gains((0.0001, -1, 1), ob=(-0.0009, -1, 1))}}}
    assert noise_bar(sup, "seed14", ["sefaria", "openbible", "etcbc"]) == pytest.approx(0.0009)
    with pytest.raises(RuntimeError, match="supervision-exp --only seed14"):
        noise_bar(None, "seed14", ["sefaria"])


def test_adoption_rule():
    gains = {
        "small": _gains((0.004, 0.001, 0.007)),  # above 0 but within the noise bar
        "good": _gains((0.02, 0.01, 0.03)),
        "better": _gains((0.03, 0.01, 0.05), ob=(-0.01, -0.02, -0.001)),  # loses on OpenBible
        "unsure": _gains((0.05, -0.001, 0.1)),  # CI reaches 0
    }
    ok, chosen = adoption(gains, bar=0.005)
    assert ok == {"small": False, "good": True, "better": False, "unsure": False}
    assert chosen == "good"
    assert adoption({"small": gains["small"]}, bar=0.005) == ({"small": False}, None)


def test_report_lists_every_candidate_and_the_zero_shot_comparison():
    zero = {"kind": "zero_shot", "model": "intfloat/multilingual-e5-large", "adopt": False,
            "gains": _gains((-0.05, -0.06, -0.04)),
            "vs_reference": {g: _g(0.01, 0.0, 0.02) for g in ("sefaria", "openbible", "etcbc")}}
    out = {
        "metric": "ndcg@10", "baseline": "berel_sup", "reference": "bge_m3",
        "baseline_scores": {li: {"sefaria": 0.19} for li in ("semantic", "fused")},
        "queries": {"sefaria": 884, "openbible": 2541, "etcbc": 179},
        "noise": "seed14", "noise_bar": 0.0009, "chosen": None,
        "results": {"e5_large": zero},
    }
    md = report(out)
    assert "| e5_large | zero_shot | intfloat/multilingual-e5-large | fused |" in md
    assert "Chosen: none." in md and "against `bge_m3`" in md and "0.0009" in md
