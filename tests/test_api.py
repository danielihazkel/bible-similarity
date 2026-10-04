from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.api.search import build_surface_index, search_tokens, top
from conftest import EMB, TEXTS, build_fixture_db


def fake_encoder(texts):
    """Every query lands exactly on verse 3."""
    return np.stack([EMB[3] for _ in texts])


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fake_encoder, log=lambda _: None))


def test_books(client):
    r = client.get("/api/books")
    assert r.status_code == 200
    books = r.json()
    assert len(books) == 39 and books[0]["book_id"] == 0 and books[0]["n_chapters"] > 0


def test_units(client):
    assert [u["unit_id"] for u in client.get("/api/units/verse").json()] == [
        f"v:{i}" for i in range(6)
    ]
    assert [u["unit_id"] for u in client.get("/api/units/chapter?book=0").json()] == [
        "c:0:1",
        "c:0:2",
    ]
    assert client.get("/api/units/nope").status_code == 422


def test_unit_detail(client):
    d = client.get("/api/unit/c:0:1").json()
    assert d["unit"]["n_verses"] == 3
    assert [v["verse_id"] for v in d["verses"]] == [0, 1, 2]
    assert d["verses"][0]["display_tokens"] == TEXTS[0].split()
    assert d["prev_id"] is None and d["next_id"] == "c:0:2"
    assert [p["unit_id"] for p in d["parents"]] == ["v:0"]
    v = client.get("/api/unit/v:3").json()
    assert [p["unit_id"] for p in v["parents"]] == ["c:0:2"]
    assert (v["prev_id"], v["next_id"]) == ("v:2", "v:4")
    assert client.get("/api/unit/v:5").json()["verses"][0]["ketiv_note"] == "כתיב"
    assert client.get("/api/unit/v:99").status_code == 404


def test_similar_verse(client):
    def tgts(query=""):
        r = client.get(f"/api/similar/v:0{query}")
        assert r.status_code == 200, r.text
        return [h["unit"]["unit_id"] for h in r.json()["hits"]]

    assert tgts() == ["v:1", "v:3", "v:5", "v:2"]
    assert tgts("?k=2") == ["v:1", "v:3"]
    assert tgts("?mode=lexical&exclude=neighbors") == ["v:3", "v:5"]
    assert tgts("?exclude=chapter") == ["v:3", "v:5"]
    assert tgts("?exclude=neighbors,book") == ["v:5"]
    body = client.get("/api/similar/v:0?k=1").json()
    assert body["mode"] == "fused" and body["k"] == 1 and body["exclude"] == []
    hit = body["hits"][0]
    assert hit["rank"] == 1 and hit["lex_rank"] == 1 and hit["sem_score"] is None
    assert hit["verse"]["text_display"] == TEXTS[1] and hit["preview"] is None
    semantic = client.get("/api/similar/v:0?mode=semantic&k=1").json()["hits"][0]
    assert semantic["lex_rank"] is None


def test_similar_chapter_and_errors(client):
    hits = client.get("/api/similar/c:0:1?mode=lexical").json()["hits"]
    assert [h["unit"]["unit_id"] for h in hits] == ["c:0:2", "c:1:1"]
    assert hits[0]["verse"] is None and hits[0]["preview"] == TEXTS[3]
    assert client.get("/api/similar/c:0:1?exclude=neighbors").status_code == 422
    assert client.get("/api/similar/v:0?exclude=nope").status_code == 422
    assert client.get("/api/similar/v:0?mode=nope").status_code == 422
    assert client.get("/api/similar/v:0?k=0").status_code == 422
    assert client.get("/api/similar/v:0?k=51").status_code == 422
    assert client.get("/api/similar/v:99").status_code == 404


def test_explain(client):
    shared = client.get("/api/explain?a=0&b=1").json()["shared"]
    assert [s["lemma"] for s in shared] == ["430", "559", "3068"]
    assert all(s["formula"] for s in shared)  # the repeated trigram is a formula
    yhwh = shared[2]
    assert yhwh["a_words"] == [{"idx": 3, "display_idx": 3, "in_formula": True}]
    assert yhwh["b_words"] == [{"idx": 2, "display_idx": None, "in_formula": True}]
    other = client.get("/api/explain?a=0&b=2").json()["shared"]
    assert [(s["lemma"], s["he_lemma"], s["formula"]) for s in other] == [("7225", "ראשית", False)]
    assert client.get("/api/explain?a=2&b=3").json()["shared"][0]["lemma"] == "7225"
    assert client.get("/api/explain?a=0&b=99").status_code == 404
    assert client.get("/api/explain?a=0").status_code == 422


def test_compare(client):
    d = client.get("/api/compare?a=c:0:2&b=c:1:1").json()
    assert [(p["src"], p["tgt"]) for p in d["a_to_b"]] == [(3, 5), (4, 5)]
    assert d["a_to_b"][1]["cosine"] == pytest.approx(0.8)
    assert [(p["src"], p["tgt"]) for p in d["b_to_a"]] == [(5, 4)]
    assert d["bma"] == pytest.approx(0.5 * (0.4 + 0.8))
    assert d["a_to_b"][0]["shared"] == [{"lemma": "7225", "he_lemma": "ראשית"}]
    assert sorted(d["verses"]) == ["3", "4", "5"]
    assert client.get("/api/compare?a=c:0:2&b=nope").status_code == 404


def test_search_modes(client):
    lex = client.get("/api/search?q=רֵאשִׁית חָכְמָה&mode=lexical").json()
    assert lex["normalized"] == "ראשית חכמה"
    assert lex["tokens"] == ["ראשית", "חכמה"]
    assert lex["hits"][0]["verse"]["verse_id"] == 5 and lex["hits"][0]["rank"] == 1
    assert lex["hits"][0]["label_en"] == "v:5"
    # every hit shares a term; v1 has no ראשית
    assert 1 not in [h["verse"]["verse_id"] for h in lex["hits"]]
    # prefix stripping on the query: וּבְרֵאשִׁית -> ראשית
    pre = client.get("/api/search?q=וּבְרֵאשִׁית&mode=lexical").json()
    assert pre["tokens"] == ["ראשית"] and len(pre["hits"]) == 5

    sem = client.get("/api/search?q=דגן&mode=semantic&k=2").json()
    assert [h["verse"]["verse_id"] for h in sem["hits"]] == [3, 4]
    assert sem["hits"][0]["score"] == pytest.approx(1.0)

    fused = client.get("/api/search?q=רֵאשִׁית חָכְמָה").json()
    assert fused["mode"] == "fused" and len(fused["hits"]) == 6
    top_hits = {h["verse"]["verse_id"]: h for h in fused["hits"]}
    assert top_hits[5]["lex_rank"] == 1 and top_hits[3]["sem_rank"] == 1
    assert top_hits[1]["lex_rank"] is None and top_hits[1]["sem_rank"] is not None


def test_search_errors(client):
    assert client.get("/api/search?q=").status_code == 422
    assert client.get("/api/search?q=ְֱ abc").status_code == 422  # no Hebrew letters
    assert client.get("/api/search?q=" + "א" * 501).status_code == 422
    assert client.get("/api/search?q=א&k=0").status_code == 422
    assert client.get("/api/search").status_code == 422


def test_meta_cors_timing(client):
    r = client.get("/api/meta")
    m = r.json()
    assert m["build"]["semantic_system"] == "sm"
    assert m["runtime"]["csls"] is False and m["runtime"]["embeddings_shape"] == [6, 4]
    assert r.headers["server-timing"].startswith("app;dur=")
    pre = client.options(
        "/api/books",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert pre.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_csls_hubness_cached(tmp_path):
    cfg, _ = build_fixture_db(tmp_path, semantic="sm_csls")
    client = TestClient(create_app(cfg, encoder=fake_encoder, log=lambda _: None))
    assert client.get("/api/meta").json()["runtime"]["csls"] is True
    cache = tmp_path / "artifacts" / "api" / "sm.hubness.npy"
    assert cache.exists()
    stamp = cache.stat().st_mtime_ns
    create_app(cfg, encoder=fake_encoder, log=lambda _: None)
    assert cache.stat().st_mtime_ns == stamp  # reused, not recomputed
    sem = client.get("/api/search?q=דגן&mode=semantic").json()["hits"]
    assert sem[0]["verse"]["verse_id"] == 3


def test_missing_db(tmp_path):
    cfg, db = build_fixture_db(tmp_path)
    db.unlink()
    with pytest.raises(RuntimeError, match="bsim build-db"):
        create_app(cfg, encoder=fake_encoder, log=lambda _: None)


def test_surface_index_and_top():
    assert search_tokens("וְהָאָרֶץ הָיְתָה", 2) == ["ארצ", "יתה"]
    idx = build_surface_index(["אבג דהו", "אבג", "זחט"], k1=1.2, b=0.75, min_root=2, bigrams=True)
    tokens, terms = idx.query_terms("אבג דהו")
    assert tokens == ["אבג", "דהו"] and "אבג_דהו" in terms
    scores = idx.scores(terms)
    assert scores[0] > scores[1] > 0 and scores[2] == 0
    assert idx.scores(["nope"]).tolist() == [0, 0, 0]
    t = top(np.array([0.5, 0.9, 0.5, 0.0], dtype=np.float32), 3, positive_only=True)
    assert t.tgt.tolist() == [1, 0, 2] and t["rank"].tolist() == [1, 2, 3]


def test_background_encoder(built):
    import threading

    from bsim.api.search import BackgroundEncoder

    cfg, _ = built
    gate = threading.Event()

    def slow_load():
        gate.wait(5)
        return fake_encoder

    enc = BackgroundEncoder(slow_load, log=lambda _: None)
    client = TestClient(create_app(cfg, encoder=enc, log=lambda _: None))
    assert client.get("/api/meta").json()["runtime"]["encoder_ready"] is False
    # lexical search does not need the encoder
    assert client.get("/api/search?q=ראשית&mode=lexical").status_code == 200
    gate.set()
    sem = client.get("/api/search?q=דגן&mode=semantic").json()
    assert sem["hits"][0]["verse"]["verse_id"] == 3
    assert client.get("/api/meta").json()["runtime"]["encoder_ready"] is True


def test_failed_encoder_is_503(built):
    from bsim.api.search import BackgroundEncoder

    def broken():
        raise OSError("no model")

    cfg, _ = built
    enc = BackgroundEncoder(broken, log=lambda _: None)
    client = TestClient(create_app(cfg, encoder=enc, log=lambda _: None))
    r = client.get("/api/search?q=דגן&mode=fused")
    assert r.status_code == 503 and "no model" in r.json()["detail"]
    assert client.get("/api/search?q=דגן&mode=lexical").status_code == 200


def test_web_dist_served(built):
    cfg, _ = built
    dist = Path(cfg["paths"]["web_dist"])
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>viewer</html>", encoding="utf-8")
    (dist / "assets" / "x.js").write_text("console.log(1)", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    client = TestClient(create_app(cfg, encoder=fake_encoder, log=lambda _: None))
    for path in ["/", "/unit/v:1", "/compare?a=c:0:1&b=c:0:2", "/../secret"]:
        r = client.get(path)
        assert r.status_code == 200 and r.text == "<html>viewer</html>", path
    assert client.get("/assets/x.js").text == "console.log(1)"
    assert client.get("/favicon.svg").text == "<svg/>"
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.json() == {"detail": "Not Found"}
    assert client.get("/api/books").status_code == 200


def test_web_dist_missing(client):
    assert client.get("/").status_code == 404
    assert client.get("/api/books").status_code == 200


def test_similar_gold_links(client):
    hits = client.get("/api/similar/v:0?mode=semantic").json()["hits"]
    links = {h["unit"]["unit_id"]: h["link"] for h in hits}
    assert links["v:5"] == {"level": "verse", "types": ["quotation"]}
    assert links["v:3"] is None
    known = client.get("/api/similar/v:0?mode=semantic&exclude=known").json()["hits"]
    assert "v:5" not in {h["unit"]["unit_id"] for h in known}
    chapter = client.get("/api/similar/c:0:1?mode=lexical").json()["hits"]
    assert chapter[0]["link"] == {"level": "unit", "types": []}


def test_discoveries(client):
    r = client.get("/api/discoveries")
    assert r.status_code == 200
    body = r.json()
    assert (body["unit_type"], body["mode"], body["total"]) == ("verse", "semantic", 1)
    item = body["items"][0]
    assert (item["a"]["unit_id"], item["b"]["unit_id"]) == ("v:0", "v:3")
    assert (item["rank_ab"], item["rank_ba"]) == (2, None)
    assert item["a_verse"]["text_display"] == TEXTS[0]
    assert client.get("/api/discoveries?cross_book=true").json()["total"] == 0
    assert client.get("/api/discoveries?book=1").json()["total"] == 0
    assert client.get("/api/discoveries?unit_type=chapter").json()["items"] == []
    assert client.get("/api/discoveries?offset=1").json()["items"] == []
    for bad in ("unit_type=book", "limit=0", "limit=100000", "offset=-1", "mode=x"):
        assert client.get(f"/api/discoveries?{bad}").status_code == 422


def test_resolve(client):
    unit = lambda q: client.get("/api/resolve", params={"q": q}).json()["unit"]  # noqa: E731
    assert unit("Gen 1:2")["unit_id"] == "v:1"
    assert unit("בראשית ב")["unit_id"] == "c:0:2"
    assert unit("Exod 1:1")["unit_id"] == "v:5"
    assert unit("Gen 1:9") is None  # no such verse in the fixture
    assert unit("בראשית ברא") is None


def test_words(client):
    words = client.get("/api/words/0").json()
    assert [w["surface"] for w in words] == TEXTS[0].split()
    assert words[0]["lemma"] == "b/7225"
    assert words[0]["lemmas"] == [{"lemma": "7225", "he_lemma": "ראשית", "n_verses": 5}]
    assert words[0]["morph_he"] == []  # the fixture's morph is just the language letter
    assert client.get("/api/words/99").status_code == 404


def test_lemma_concordance(client):
    body = client.get("/api/lemma/7225").json()
    assert (body["he_lemma"], body["n_words"], body["n_verses"], body["total"]) == (
        "ראשית",
        5,
        5,
        5,
    )
    assert body["by_book"] == [{"book_id": 0, "n_verses": 4}, {"book_id": 1, "n_verses": 1}]
    assert [i["verse"]["verse_id"] for i in body["items"]] == [0, 2, 3, 4, 5]
    assert body["items"][0]["display_idxs"] == [0]
    one = client.get("/api/lemma/7225?book=1").json()
    assert (one["total"], [i["label_en"] for i in one["items"]]) == (1, ["v:5"])
    page = client.get("/api/lemma/7225?limit=2&offset=2").json()
    assert [i["verse"]["verse_id"] for i in page["items"]] == [3, 4]
    assert client.get("/api/lemma/0000").status_code == 404
    assert client.get("/api/lemma/7225?limit=0").status_code == 422
