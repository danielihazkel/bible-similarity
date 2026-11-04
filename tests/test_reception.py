"""Rabbinic reception (`bsim reception`, `/reception`, DESIGN.md §16.77)."""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.reception import (
    cite_he,
    corpus_of,
    law_ratio,
    run_reception,
    sefaria_url,
    shifted,
)
from bsim.api.app import create_app
from bsim.config import load_config
from bsim.data.canon import BY_SEFARIA
from bsim.fixture import fixture_encoder

RC = load_config()["reception"]


def test_corpus_of_keeps_the_texts_and_leaves_their_commentaries():
    assert corpus_of("Mishnah", "Mishnah Berakhot", "Mishnah Berakhot 1:3", RC) == "mishnah"
    assert corpus_of("Mishnah", "Pirkei Avot", "Pirkei Avot 3:14", RC) == "mishnah"
    assert corpus_of("Mishnah", "English Explanation of Mishnah Sotah", "x 1:1", RC) is None
    assert corpus_of("Mishnah", "Yein Levanon on Avot", "Yein Levanon on Avot 1:1", RC) is None
    assert corpus_of("Tosefta", "Tosefta Sotah", "Tosefta Sotah 7:1", RC) == "tosefta"
    assert corpus_of("Tosefta", "Tosefta Sotah (Lieberman)", "Tosefta Sotah (Lieberman) 7:1",
                     RC) is None  # fmt: skip
    assert corpus_of("Talmud", "Sanhedrin", "Sanhedrin 90b:3", RC) == "bavli"
    assert corpus_of("Talmud", "Moed Katan", "Moed Katan 2a:1-4", RC) == "bavli"
    # cited by folio, but not the Talmud: Alfasi's code, the Daf Shevui
    assert corpus_of("Talmud", "Rif Berakhot", "Rif Berakhot 1a:2", RC) is None
    assert corpus_of("Talmud", "Daf Shevui to Sukkah", "Daf Shevui to Sukkah 2a:1", RC) is None
    # a title of the Talmud's category not cited by folio is not the Bavli
    assert corpus_of("Talmud", "Avot DeRabbi Natan", "Avot DeRabbi Natan 4:5", RC) is None
    j = "Jerusalem Talmud Berakhot"
    assert corpus_of("Talmud", j, f"{j} 1:1:2", RC) == "yerushalmi"
    assert corpus_of("Talmud", "Rashi on Berakhot", "Rashi on Berakhot 2a:1:1", RC) is None
    assert corpus_of("Midrash", "Bereshit Rabbah", "Bereshit Rabbah 1:1", RC) is None


def test_citations_in_hebrew_and_on_sefaria():
    assert cite_he("mishnah", "Mishnah Berakhot", "Mishnah Berakhot 1:3") == "משנה ברכות א:ג"
    assert cite_he("mishnah", "Pirkei Avot", "Pirkei Avot 3:14") == "פרקי אבות ג:יד"
    assert cite_he("bavli", "Sanhedrin", "Sanhedrin 90b:3") == "בבלי סנהדרין צ ע״ב"
    assert cite_he("bavli", "Berakhot", "Berakhot 2a:1-5") == "בבלי ברכות ב ע״א"
    assert cite_he("tosefta", "Tosefta Ta'anit", "Tosefta Ta'anit 2:4") == "תוספתא תענית ב:ד"
    j = "Jerusalem Talmud Bava Kamma"
    assert cite_he("yerushalmi", j, f"{j} 3:1:15") == "ירושלמי בבא קמא ג:א"
    assert sefaria_url("Berakhot 2a:1") == "https://www.sefaria.org/Berakhot.2a.1?lang=he"
    assert (
        sefaria_url("Jerusalem Talmud Berakhot 1:1:2")
        == "https://www.sefaria.org/Jerusalem_Talmud_Berakhot.1.1.2?lang=he"
    )


def test_the_law_shifted_round_each_book():
    legal = np.array([False, False, True, True, False, True, True, True])
    books = np.array([0, 0, 0, 0, 0, 1, 1, 1])
    rng = np.random.default_rng(0)
    for _ in range(20):
        s = shifted(legal, books, rng)
        # each book keeps its law's size, and a book all law stays so
        assert s[:5].sum() == 2 and s[5:].all()
        # the block stays whole (circularly)
        assert np.count_nonzero(np.diff(np.r_[s[:5], s[0]].astype(int))) == 2
    counts = np.array([0, 0, 4, 2, 0, 1, 1, 1], dtype=float)
    # no citation of the narrative: no ratio
    assert np.isnan(law_ratio(counts, legal))
    counts[0] = 3
    assert law_ratio(counts, legal) == pytest.approx((9 / 5) / 1.0)


def links_corpus(tmp_path):
    """Genesis 1:1-4 (narrative), Exodus 19:1-3 (narrative) and 20:1-3 (law), and links to them."""
    rows = [(0, 1, v) for v in range(1, 5)] + [(1, 19, v) for v in range(1, 4)]
    rows += [(1, 20, v) for v in range(1, 4)]
    gen, ex = BY_SEFARIA["Genesis"].book_id, BY_SEFARIA["Exodus"].book_id
    proc = tmp_path / "processed"
    proc.mkdir()
    pd.DataFrame(
        {
            "verse_id": range(len(rows)),
            "book_id": [gen if b == 0 else ex for b, _, _ in rows],
            "chapter": [c for _, c, _ in rows],
            "verse": [v for _, _, v in rows],
        }
    ).to_parquet(proc / "verses.parquet")
    links = tmp_path / "raw" / "sefaria" / "links"
    links.mkdir(parents=True)
    head = "Citation 1,Citation 2,Conection Type,Text 1,Text 2,Category 1,Category 2"
    lines = [
        head,
        "Mishnah Berakhot 1:3,Genesis 1:1,,Mishnah Berakhot,Genesis,Mishnah,Tanakh",
        "Genesis 1:1,Mishnah Berakhot 1:3,quotation,Genesis,Mishnah Berakhot,Tanakh,Mishnah",
        "Mishnah Bava Kamma 1:1,Exodus 20:1-2,,Mishnah Bava Kamma,Exodus,Mishnah,Tanakh",
        "Berakhot 2a:1,Genesis 1:2,,Berakhot,Genesis,Talmud,Tanakh",
        "Rif Berakhot 1a:1,Genesis 1:3,,Rif Berakhot,Genesis,Talmud,Tanakh",
        "Notes on Mishnah Peah 1:1,Genesis 1:3,,Notes on Mishnah Peah,Genesis,Mishnah,Tanakh",
        "Mishnah Sotah 7:1,Exodus 19:1-20:3,,Mishnah Sotah,Exodus,Mishnah,Tanakh",
        '"Abarbanel on Genesis 1:1:1",Mishnah Avot 1:1,,Abarbanel on Genesis,Mishnah Avot,'
        "Tanakh,Mishnah",
        "Jerusalem Talmud Berakhot 1:1:2,Exodus 19:2,,Jerusalem Talmud Berakhot,Exodus,Talmud,"
        "Tanakh",
        "Tosefta Berakhot 1:1,Genesis 1:4,,Tosefta Berakhot,Genesis,Tosefta,Tanakh",
        "Mishnah Peah 2:2,Genesis 9:1,,Mishnah Peah,Genesis,Mishnah,Tanakh",
    ]
    (links / "links0.csv").write_text("\n".join(lines) + "\n", "utf-8")
    cfg = load_config()
    cfg["paths"] = {
        **cfg["paths"],
        "data_raw": str(tmp_path / "raw"),
        "data_processed": str(proc),
        "artifacts": str(tmp_path / "artifacts"),
    }
    cfg["reception"] = {
        **cfg["reception"],
        "legal": ["Exodus 20:1-20:3"],
        "known": [["Mishnah Berakhot 1:3", "Genesis 1:1"], ["Mishnah Peah 1:1", "Genesis 1:3"]],
        "shifts": 19,
    }
    return cfg


def test_run_reception(tmp_path):
    cfg = links_corpus(tmp_path)
    run_reception(cfg, log=lambda _: None)
    out = tmp_path / "artifacts" / "reception"
    cit = pd.read_parquet(out / "citations.parquet")
    # one row per passage and verse (a link both ways counted once); a two-verse range counted
    # on each; Alfasi, the notes, the commentary's link and the long passage left out
    assert sorted(zip(cit.corpus, cit.cite, cit.verse_id, strict=True)) == sorted([
        ("mishnah", "Mishnah Berakhot 1:3", 0), ("mishnah", "Mishnah Bava Kamma 1:1", 7),
        ("mishnah", "Mishnah Bava Kamma 1:1", 8), ("bavli", "Berakhot 2a:1", 1),
        ("yerushalmi", "Jerusalem Talmud Berakhot 1:1:2", 5),
        ("tosefta", "Tosefta Berakhot 1:1", 3),
    ])  # fmt: skip
    assert cit.set_index("cite").cite_he["Berakhot 2a:1"] == "בבלי ברכות ב ע״א"
    verses = pd.read_parquet(out / "verses.parquet").set_index("verse_id")
    assert verses.loc[0, "mishnah"] == 1 and verses.loc[0, "total"] == 1
    assert len(verses) == 6
    ch = pd.read_parquet(out / "chapters.parquet").set_index("unit_id")
    assert ch.loc[f"c:{BY_SEFARIA['Exodus'].book_id}:20", "mishnah"] == 2
    assert ch.loc[f"c:{BY_SEFARIA['Genesis'].book_id}:1", "verses"] == 4
    meta = json.loads((out / "reception.meta.json").read_text("utf-8"))
    assert meta["dropped_long"] == 1 and meta["dropped_invalid"] == 1
    assert meta["by_corpus"] == {"mishnah": 3, "tosefta": 1, "bavli": 1, "yerushalmi": 1}
    # the Mishnah: law 2 / 3 verses, narrative 1 / 7
    assert meta["ratios"]["mishnah"] == pytest.approx((2 / 3) / (1 / 7), abs=1e-3)
    assert meta["legal_verses"] == 3 and meta["narrative_verses"] == 7
    assert [k["found"] for k in meta["known"]] == [True, False] and not meta["known_holds"]


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_reception_endpoint(client):
    r = client.get("/api/reception").json()
    assert r["law_holds"] and not r["gap_holds"] and not r["known_holds"]
    assert r["ratios"]["mishnah"] == 3.5 and r["citations"] == 5
    assert [k["found"] for k in r["known"]] == [True, False]
    assert r["known"][0]["verse"]["verse_id"] == 0
    assert [b["book_id"] for b in r["books"]] == [0, 1]
    assert r["books"][0]["total"] == 4 and r["books"][1]["yerushalmi"] == 1
    assert sum(c["total"] for c in r["chapters"]) == 5


def test_reception_verses(client):
    r = client.get("/api/reception/verses").json()
    assert r["total"] == 3
    assert [(v["verse"]["verse_id"], v["total"]) for v in r["items"]] == [(0, 3), (1, 1), (5, 1)]
    by = client.get("/api/reception/verses", params={"corpus": "bavli"}).json()
    assert [v["verse"]["verse_id"] for v in by["items"]] == [0, 1] and by["corpus"] == "bavli"
    assert client.get("/api/reception/verses", params={"book": 1}).json()["total"] == 1
    assert client.get("/api/reception/verses", params={"corpus": "midrash"}).status_code == 422
    assert client.get("/api/reception/verses", params={"book": 99}).status_code == 404


def test_reception_citations(client):
    r = client.get("/api/reception/citations", params={"unit": "v:0"}).json()
    assert r["counts"] == {"mishnah": 2, "tosefta": 0, "bavli": 1, "yerushalmi": 0, "total": 3}
    assert [c["corpus"] for c in r["items"]] == ["mishnah", "mishnah", "bavli"]
    first = r["items"][0]
    assert first["cite_he"] == "משנה ברכות א:ג" and first["url"].endswith("?lang=he")
    assert first["ref"] and first["ref_he"]
    one = client.get("/api/reception/citations", params={"unit": "v:0", "corpus": "bavli"}).json()
    assert one["total"] == 1 and one["items"][0]["cite"] == "Berakhot 2a:1"
    assert client.get("/api/reception/citations", params={"unit": "v:99"}).status_code == 404


def test_reception_in_the_reader_and_the_dossier(client):
    unit = client.get("/api/unit/v:0").json()["unit"]
    chapter = f"c:{unit['book_id']}:{client.get('/api/unit/v:0').json()['verses'][0]['chapter']}"
    r = client.get(f"/api/reader/{chapter}").json()
    assert r["computed"]["reception"]
    v0 = next(v for v in r["verses"] if v["verse_id"] == 0)
    assert v0["reception"]["total"] == 3 and v0["reception"]["mishnah"] == 2
    v2 = next(v for v in r["verses"] if v["verse_id"] == 2)
    assert v2["reception"] == {}
    d = client.get("/api/dossier/v:0").json()["entries"]
    e = next(x for x in d if x["kind"] == "reception")
    assert e["computed"] and e["count"] == 3 and e["key"] == "mishnah" and e["total"] == 1


def test_reception_findings(client):
    found = {f["key"]: f for f in client.get("/api/findings").json()["items"]}
    assert found["reception_law"]["verdict"] == "holds"
    assert found["reception_law"]["values"]["ratio"] == 3.5
    assert found["reception_bavli"]["verdict"] == "fails"
    assert found["reception_known"]["values"] == {"found": 1, "of": 2}
