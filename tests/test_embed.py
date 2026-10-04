import json

import numpy as np
import pandas as pd
import pytest

from bsim.config import load_config, resolve_path
from bsim.embed import encoders
from bsim.embed.encoders import run_embed, token_stats

# Consonantal text_model forms (§3.2): Gen 1:1, Ps 14:1, Ex 20:2, Gen 2:4 (finals), Esth 8:9 (long)
SAMPLE_VERSES = [
    "בראשית ברא אלהים את השמים ואת הארץ",
    "למנצח לדוד אמר נבל בלבו אין אלהים השחיתו התעיבו עלילה אין עשה טוב",
    "אנכי יהוה אלהיך אשר הוצאתיך מארץ מצרים מבית עבדים",
    "אלה תולדות השמים והארץ בהבראם ביום עשות יהוה אלהים ארץ ושמים",
    "ויקראו ספרי המלך בעת ההיא בחדש השלישי הוא חדש סיון בשלושה ועשרים בו ויכתב ככל אשר "
    "צוה מרדכי אל היהודים ואל האחשדרפנים והפחות ושרי המדינות אשר מהדו ועד כוש שבע ועשרים "
    "ומאה מדינה מדינה ומדינה ככתבה ועם ועם כלשנו ואל היהודים ככתבם וכלשונם",
]


@pytest.fixture(scope="module")
def berel_tokenizer():
    from transformers import AutoTokenizer

    try:
        return AutoTokenizer.from_pretrained(
            load_config()["encoders"]["berel"], local_files_only=True
        )
    except OSError:
        pytest.skip("BEREL tokenizer not in the HF cache")


def test_berel_tokenizer_is_fast_and_has_no_unk(berel_tokenizer):
    assert berel_tokenizer.is_fast
    stats = token_stats(berel_tokenizer, SAMPLE_VERSES, 128)
    assert stats["n_unk_tokens"] == 0
    assert stats["n_truncated"] == 0


def test_berel_no_unk_on_corpus(berel_tokenizer):
    path = resolve_path(load_config(), "data_processed") / "verses.parquet"
    if not path.exists():
        pytest.skip("corpus not built")
    texts = pd.read_parquet(path, columns=["text_model"]).text_model.tolist()
    stats = token_stats(berel_tokenizer, texts, 128)
    assert stats["n_unk_verses"] == 0
    assert stats["n_truncated"] == 0


class FakeTokenizer:
    """Whitespace tokenizer: id 1 = [UNK] for words containing 'x', [CLS]/[SEP] added."""

    is_fast = True
    unk_token, unk_token_id = "[UNK]", 1

    def __call__(self, texts, add_special_tokens=True, truncation=False):
        ids = [[0, *(1 if "x" in w else 2 for w in t.split()), 0] for t in texts]
        return {"input_ids": ids}


def test_token_stats_counts_unk_and_truncation():
    stats = token_stats(FakeTokenizer(), ["a b", "a x x", "a b c d"], 4)
    assert stats == {"n_unk_verses": 1, "n_unk_tokens": 2, "n_truncated": 2, "max_tokens": 6}


class FakeModel:
    tokenizer = FakeTokenizer()

    def encode(self, texts, batch_size, normalize_embeddings, convert_to_numpy, **_):
        e = np.array([[len(t), 1.0, 0.0] for t in texts], dtype=np.float32)
        return e / np.linalg.norm(e, axis=1, keepdims=True) if normalize_embeddings else e

    def __getitem__(self, i):
        raise IndexError(i)


def _cfg(tmp_path):
    cfg = load_config()
    cfg["paths"] = {**cfg["paths"], "artifacts": str(tmp_path), "data_processed": str(tmp_path)}
    cfg["encoders"] = {**cfg["encoders"], "device": "cpu"}
    return cfg


def test_run_embed_writes_rows_in_verse_order(tmp_path, monkeypatch):
    texts = ["a", "bbb", "cc"]
    pd.DataFrame({"verse_id": [2, 0, 1], "text_model": [texts[2], texts[0], texts[1]]}).to_parquet(
        tmp_path / "verses.parquet"
    )
    monkeypatch.setattr(encoders, "load_encoder", lambda *a: FakeModel())
    run_embed(_cfg(tmp_path), "berel_mean", log=lambda _: None)
    emb = np.load(tmp_path / "embeddings" / "berel_mean.npy")
    assert emb.dtype == np.float32 and emb.shape == (3, 3)
    assert np.linalg.norm(emb, axis=1) == pytest.approx(1.0)
    assert np.argsort(emb[:, 0]).tolist() == [0, 2, 1]  # row i = verse_id i (lengths 1, 3, 2)
    meta = json.loads((tmp_path / "embeddings" / "berel_mean.meta.json").read_text("utf-8"))
    assert meta["n"] == 3 and meta["dim"] == 3 and meta["n_unk_verses"] == 0
    assert meta["config_hash"]


def test_run_embed_rejects_unknown_system(tmp_path):
    with pytest.raises(RuntimeError, match="unknown encoder system"):
        run_embed(_cfg(tmp_path), "nope", log=lambda _: None)
