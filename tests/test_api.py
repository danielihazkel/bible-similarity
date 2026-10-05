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
    assert [u["unit_id"] for u in client.get("/api/units/verse?book=0").json()] == [
        f"v:{i}" for i in range(5)
    ]
    assert client.get("/api/units/verse").status_code == 422  # all 23k verses: per book only
    by_chapter = client.get("/api/units/verse?book=0&chapter=2").json()
    assert [u["unit_id"] for u in by_chapter] == ["v:3", "v:4"]
    assert client.get("/api/units/verse?chapter=2").status_code == 422
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


def test_compare_cap(built):
    cfg, _ = built
    cfg["serve"]["max_compare_verses"] = 2
    capped = TestClient(create_app(cfg, encoder=fake_encoder, log=lambda _: None))
    assert capped.get("/api/compare?a=c:0:2&b=c:1:1").status_code == 200
    assert capped.get("/api/compare?a=c:0:1&b=c:1:1").status_code == 422  # 3 verses


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
    assert r.headers["cache-control"] == "no-store"
    books = client.get("/api/books")
    assert books.headers["cache-control"] == "public, max-age=300"
    assert books.headers["content-encoding"] == "gzip"  # 39 books > gzip_min_bytes
    assert "cache-control" not in client.get("/api/unit/v:99").headers  # errors are not cached
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


def test_surface_index_cached(built):
    cfg, _ = built
    cache = Path(cfg["paths"]["artifacts"]) / "api" / "surface_bm25.pkl"
    create_app(cfg, encoder=fake_encoder, log=lambda _: None)
    assert cache.exists()
    stamp = cache.stat().st_mtime_ns
    client = TestClient(create_app(cfg, encoder=fake_encoder, log=lambda _: None))
    assert cache.stat().st_mtime_ns == stamp  # reused, not rebuilt
    assert client.get("/api/search?q=חָכְמָה&mode=lexical").json()["hits"][0]["verse"]["verse_id"] == 5
    cfg["serve"]["search"]["bigrams"] = False  # parameters are part of the key
    create_app(cfg, encoder=fake_encoder, log=lambda _: None)
    assert cache.stat().st_mtime_ns != stamp


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
    # lexical search does not need the encoder; semantic search fails fast while it loads
    assert client.get("/api/search?q=ראשית&mode=lexical").status_code == 200
    r = client.get("/api/search?q=דגן&mode=semantic")
    assert r.status_code == 503 and r.headers["Retry-After"] == "5"
    gate.set()
    assert enc.wait(5)
    sem = client.get("/api/search?q=דגן&mode=semantic").json()
    assert sem["hits"][0]["verse"]["verse_id"] == 3
    assert client.get("/api/meta").json()["runtime"]["encoder_ready"] is True


def test_failed_encoder_is_503(built):
    from bsim.api.search import BackgroundEncoder

    def broken():
        raise OSError("no model")

    cfg, _ = built
    enc = BackgroundEncoder(broken, log=lambda _: None)
    assert enc.wait(5)
    client = TestClient(create_app(cfg, encoder=enc, log=lambda _: None))
    r = client.get("/api/search?q=דגן&mode=fused")
    assert r.status_code == 503 and "no model" in r.json()["detail"]
    assert "Retry-After" not in r.headers
    assert client.get("/api/search?q=דגן&mode=lexical").status_code == 200
    runtime = client.get("/api/meta").json()["runtime"]
    assert runtime["encoder_ready"] is False and "no model" in runtime["encoder_error"]


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


def test_phrases(client):
    hits = client.get("/api/similar/v:0?mode=semantic").json()["hits"]
    phrase = {h["unit"]["unit_id"]: h["phrase"] for h in hits}
    assert phrase["v:5"] == {"score": 15.0, "n_tokens": 3}
    assert phrase["v:3"] is None
    assert all(h["phrase"] is None for h in client.get("/api/similar/c:0:1").json()["hits"])

    of5 = client.get("/api/phrases/5").json()
    assert len(of5) == 1
    p = of5[0]  # v:5 is put on the `a` side
    assert (p["a"]["unit_id"], p["b"]["unit_id"], p["a_display"], p["b_display"]) == (
        "v:5",
        "v:0",
        [0],
        [0, 1],
    )
    assert p["link"] == {"level": "verse", "types": ["quotation"]}
    assert client.get("/api/phrases/2").json() == []
    assert client.get("/api/phrases/99").status_code == 404

    board = client.get("/api/phrases").json()
    assert board["total"] == 1 and board["items"][0]["a"]["unit_id"] == "v:0"
    assert client.get("/api/phrases?min_tokens=4").json()["total"] == 0
    assert client.get("/api/phrases?max_spread=2").json()["total"] == 1
    assert board["items"][0]["spread"] == 2
    assert client.get("/api/phrases?cross_book=true").json()["total"] == 1
    assert client.get("/api/phrases?book=0").json()["total"] == 1
    assert client.get("/api/phrases?limit=0").status_code == 422


def test_structure(client):
    body = client.get("/api/structure/c:0:1").json()
    assert body["verse_ids"] == [0, 1, 2]
    sem = body["semantic"]
    assert sem["matrix"][0][1] == pytest.approx(0.8) and sem["matrix"][0][0] == pytest.approx(1)
    assert sem["inclusio"] is None and sem["chiasm"] is None  # 3 verses: too short
    assert sem["echoes"] == [{"a": 0, "b": 2, "sim": 0.0}]
    keys = {k["lemma"]: k for k in body["leitworte"]}
    assert set(keys) == {"430", "559", "3068"}  # 2 of 2 corpus occurrences each; 7225 is not
    assert keys["430"]["occurrences"] == {"0": [1], "1": [0]}
    assert client.get("/api/structure/c:0:1").json() == body  # served from the LRU
    assert client.app.state.serve.structure_cache.get("c:0:1") is not None
    assert client.get("/api/structure/v:0").status_code == 422
    assert client.get("/api/structure/c:9:9").status_code == 404


def test_structure_ranking(client):
    body = client.get("/api/structure?unit_type=chapter").json()
    assert (body["by"], body["total"], body["items"]) == ("semantic_chiasm", 0, [])
    assert client.get("/api/structure?unit_type=verse").status_code == 422
    assert client.get("/api/structure?by=nope").status_code == 422


def test_corpus_map(client):
    body = client.get("/api/map/chapter").json()
    assert [p["unit_id"] for p in body["points"]] == ["c:0:1", "c:0:2", "c:1:1"]
    assert all(0 <= p["x"] <= 1 and 0 <= p["y"] <= 1 for p in body["points"])
    assert sum(c["size"] for c in body["clusters"]) == 3
    assert client.get("/api/map/verse").status_code == 422


def test_affinity(client):
    body = client.get("/api/affinity").json()
    assert sorted(body["order"]) == [0, 1]
    assert [(c["a"], c["b"], c["n_pairs"]) for c in body["cells"]] == [(0, 1, 1)]
    pairs = client.get("/api/affinity/1/0").json()  # book 1 on the `a` side
    assert [(p["a"]["unit_id"], p["b"]["unit_id"]) for p in pairs] == [("v:5", "v:0")]
    assert pairs[0]["link"] == {"level": "verse", "types": ["quotation"]}
    assert client.get("/api/affinity/3/4").json() == []


def test_structural_mode(client):
    body = client.get("/api/similar/v:0?mode=structural").json()
    assert body["mode"] == "structural" and body["hits"][0]["unit"]["unit_id"] == "v:1"
    assert client.get("/api/search?q=רשית&mode=structural").status_code == 422


def test_stylometry(client):
    body = client.get("/api/stylometry").json()
    assert {p["unit_id"] for p in body["points"]} == {"c:0:1", "c:0:2", "c:1:1"}
    assert [a["pc"] for a in body["axes"]] == [1, 2]
    assert len(body["delta"]) == 39 * 38 // 2 and len(body["order"]) == 39
    book = client.get("/api/stylometry/book/0").json()
    assert book["n_words"] == 10 and book["over"] and book["under"]
    assert book["closest"][0]["a"] == 0
    assert client.get("/api/stylometry/book/99").status_code == 404


def test_sequences(client):
    body = client.get("/api/sequences").json()
    assert body["total"] == 2 and [s["seq_id"] for s in body["items"]] == [1, 2]
    first = body["items"][0]
    assert (first["a_label"], first["b_label"]) == ("v:0–1", "v:3–4")
    assert first["n_gold"] == 1  # (1, 4) lies inside the passage-level link v1-v2 <-> v3-v4
    ids = lambda q: [s["seq_id"] for s in client.get(f"/api/sequences?{q}").json()["items"]]  # noqa: E731
    assert ids("cross_book=true") == [2]
    assert ids("max_q=0.05") == [1]
    assert ids("unit=c:1:1") == [2]
    assert ids("unit=c:0:1") == [1, 2]
    assert ids("book=1") == [2]
    assert client.get("/api/sequences?unit=nope").status_code == 404
    assert client.get("/api/sequences?max_q=2").status_code == 422
    assert client.get("/api/sequences?limit=0").status_code == 422


def test_sequence_detail(client):
    d = client.get("/api/sequences/1").json()
    assert d["sequence"]["n_pairs"] == 2
    assert [(r["a"], r["b"], r["gold"]) for r in d["rows"]] == [(0, 3, False), (1, 4, True)]
    assert d["rows"][1]["cosine"] == pytest.approx(0.8 * 0.0 + 0.6 * 0.0)  # v1 . v4
    assert sorted(d["verses"]) == ["0", "1", "3", "4"]
    assert client.get("/api/sequences/99").status_code == 404


def test_verse_diff(client):
    d = client.get("/api/diff?a=0&b=3").json()
    # v0 בראשית אלהים ויאמר יהוה -> v3 ראשית: the shared lemma keeps its place, 3 words dropped
    assert d["counts"] == {"form": 1, "omitted": 3}
    assert (d["shared"], d["loose"]) == (1.0, False)
    assert d["a_marks"] == {"0": "form", "1": "omitted", "2": "omitted", "3": "omitted"}
    assert d["b_marks"] == {"0": "form"}
    # v1 אלהים ויאמר יהוה -> v4 ראשית share no lemma: too loose to mark
    loose = client.get("/api/diff?a=1&b=4").json()
    assert (loose["shared"], loose["loose"], loose["a_marks"]) == (0.0, True, {})
    assert client.get("/api/diff?a=0&b=99").status_code == 404


def test_changes(client):
    # only sequence 1 (q 0.01) is diffed, and only its (0 -> 3) pair: (1 -> 4) is too loose
    body = client.get("/api/changes?op=omitted").json()
    assert body["totals"] == {"form": 1, "omitted": 3}
    assert body["total"] == 3 and [g["count"] for g in body["items"]] == [1, 1, 1]
    g = next(g for g in body["items"] if g["a_key"] == "430")
    assert (g["a_he"], g["b_key"], g["b_he"]) == ("אלהים", None, None)
    assert g["examples"] == [{"seq_id": 1, "a": 0, "b": 3, "a_label": "v:0", "b_label": "v:3"}]
    # form changes are grouped by written form
    [f] = client.get("/api/changes?op=form").json()["items"]
    assert (f["a_he"], f["b_he"], f["a_key"]) == ("בראשית", "ראשית", None)
    assert f["examples"][0]["a"] == 0
    assert client.get("/api/changes").json()["items"] == []  # no substitutions
    assert client.get("/api/changes?op=omitted&a_book=1").json()["items"] == []
    assert client.get("/api/changes?op=same").status_code == 422


def test_sequence_ladder_marks(client):
    rows = client.get("/api/sequences/1").json()["rows"]
    assert rows[0]["b_marks"] == {"0": "form"} and rows[0]["loose"] is False
    assert rows[1]["b_marks"] == {} and rows[1]["loose"] is True


def test_unit_parallelism(client):
    body = client.get("/api/parallelism/c:0:1").json()
    assert [v["n_cola"] for v in body["verses"]] == [2, 1, 1]
    assert body["verses"][0]["cola"] == [[0, 1], [2, 3]]
    assert body["verses"][0]["pauses"] == ["etnahta"]
    assert (body["n_scored"], body["mean_prob"], body["share_parallel"]) == (1, 0.9, 1.0)
    assert body["verses"][1]["prob"] is None
    assert client.get("/api/parallelism/c:9:9").status_code == 404


def test_parallelism_ranking(client):
    body = client.get("/api/parallelism?min_verses=1").json()
    assert [(i["unit"]["unit_id"], i["mean_prob"]) for i in body["items"]] == [
        ("c:0:1", 0.9),
        ("c:0:2", 0.2),
    ]
    assert body["items"][1]["share_parallel"] == 0.0
    assert body["books"][0]["book_id"] == 0 and body["books"][0]["mean_prob"] == pytest.approx(0.55)
    assert body["coefficients"] == {"cos": 1.0}
    assert client.get("/api/parallelism").json()["total"] == 0  # min_chapter_verses = 6
    assert client.get("/api/parallelism?min_verses=1&book=1").json()["items"] == []
    assert client.get("/api/parallelism?unit_type=verse").status_code == 422


def test_wordplay(client):
    body = client.get("/api/wordplay").json()
    assert (body["total"], body["expected_by_chance"]) == (2, 1.5)
    first, second = body["items"]
    assert (first["a_he"], first["b_he"], first["a_display"], first["b_display"]) == (
        "אלהים",
        "יהוה",
        1,
        3,
    )
    assert [v["verse_id"] for v in first["verses"]] == [0]  # one verse
    assert [v["verse_id"] for v in second["verses"]] == [3, 4]  # crosses a verse boundary
    assert (second["a_label"], second["b_label"]) == ("v:3", "v:4")
    ids = lambda q: [i["a_vid"] for i in client.get(f"/api/wordplay?{q}").json()["items"]]  # noqa: E731
    assert ids("kind=extension") == [3]
    assert ids("unit=c:0:2") == [3]
    assert ids("unit=v:4") == [3]
    assert ids("book=1") == []
    assert client.get("/api/wordplay?kind=pun").status_code == 422
    assert client.get("/api/wordplay?unit=nope").status_code == 404


def test_entities(client):
    body = client.get("/api/entities").json()
    assert body["total"] == 3 and [e["lemma"] for e in body["items"]] == ["430", "559", "7225"]
    ids = lambda q: [e["lemma"] for e in client.get(f"/api/entities?{q}").json()["items"]]  # noqa: E731
    assert ids("kind=place") == ["559"]
    assert ids("book=1") == ["7225"]
    assert client.get("/api/entities?book=1").json()["items"][0]["n_here"] == 1
    assert ids("q=אֱלֹהִים") == ["430"]  # pointed query, consonantal match
    assert client.get("/api/entities?kind=god").status_code == 422


def test_entity_detail_and_unit(client):
    d = client.get("/api/entities/430").json()
    assert (d["entity"]["he"], d["first_label"], d["last_label"]) == ("אלהים", "v:0", "v:1")
    assert d["by_book"] == [{"book_id": 0, "n_verses": 2}]
    assert [(p["lemma"], p["n_verses"]) for p in d["partners"]] == [("559", 2)]
    assert d["links"] == []  # one partner: no links among partners
    assert client.get("/api/entities/9999").status_code == 404
    cast = client.get("/api/unit-entities/c:0:1").json()
    assert [(e["lemma"], e["n_here"]) for e in cast] == [("430", 2), ("559", 2)]
    assert client.get("/api/unit-entities/c:1:1").json()[0]["lemma"] == "7225"


def test_seams(client):
    body = client.get("/api/seams?book=0").json()
    assert (body["threshold"], body["block_words"]) == (0.6, 600)
    assert [(c["verse_id"], c["chapter"]) for c in body["curve"]] == [
        (1, 1),
        (2, 1),
        (3, 2),
        (4, 2),
    ]
    [seam] = body["seams"]
    assert (seam["verse_id"], seam["label"], seam["rank"]) == (3, "v:3", 1)
    assert seam["features"][0] == {"feature": "aramaic", "label": "ארמית", "z": -9.7}
    top = client.get("/api/seams").json()
    assert top["curve"] == [] and top["threshold"] is None and len(top["seams"]) == 1
    assert client.get("/api/seams?book=1").json()["seams"] == []
    assert client.get("/api/seams?limit=0").status_code == 422


def test_query_embedding_cache(built):
    cfg, _ = built
    calls = []

    def counting(texts):
        calls.append(texts)
        return fake_encoder(texts)

    client = TestClient(create_app(cfg, encoder=counting, log=lambda _: None))
    for _ in range(3):
        assert client.get("/api/search?q=דגן&mode=semantic").status_code == 200
    assert len(calls) == 1  # encoded once, then served from the LRU
    client.get("/api/search?q=חכמה&mode=fused")
    assert len(calls) == 2


def test_list_limits_and_offsets(client):
    assert len(client.get("/api/phrases/5?limit=1").json()) == 1
    assert client.get("/api/phrases/5?limit=0").status_code == 422
    for path in ("sequences?", "wordplay?", "entities?", "changes?op=omitted&"):
        body = client.get(f"/api/{path}offset=100").json()
        assert body["items"] == [] and body["total"] > 0, path
        assert client.get(f"/api/{path}limit=0").status_code == 422, path
        assert client.get(f"/api/{path}offset=-1").status_code == 422, path


def test_connection_settings(client):
    conn = client.app.state.serve.connect()
    try:
        assert conn.execute("PRAGMA query_only").fetchone()[0] == 1
        assert conn.execute("PRAGMA cache_size").fetchone()[0] < 0  # KiB budget
    finally:
        conn.close()


def test_connection_pool_reuses_connections(client):
    state = client.app.state.serve
    while not state._pool.empty():
        state._pool.get_nowait().close()
    assert client.get("/api/books").status_code == 200
    conn = state.acquire()
    assert client.get("/api/books").status_code == 200  # opened a second one meanwhile
    state.release(conn)
    assert state._pool.qsize() == 2
    for _ in range(state.cfg["serve"]["sqlite_pool"] + 2):
        state.release(state.connect())
    assert state._pool.qsize() == state.cfg["serve"]["sqlite_pool"]


def test_parameter_checks(client):
    for path in (
        "sequences?min_pairs=0",
        "phrases?min_tokens=0",
        "parallelism?min_verses=0",
        "structure?min_verses=0",
        "seams?offset=-1",
        "seams?limit=0",
    ):
        assert client.get(f"/api/{path}").status_code == 422, path
    assert client.get("/api/affinity/0/999").status_code == 404
    assert client.get("/api/affinity/0/1").status_code == 200
    detail = client.get("/api/compare?a=c:0:1&b=c:0:2").status_code
    assert detail == 200


def test_phrases_of_paging(client):
    r = client.get("/api/phrases/5?limit=1")
    assert r.status_code == 200 and r.headers["X-Total-Count"] == "1" and len(r.json()) == 1
    r = client.get("/api/phrases/5?offset=1")
    assert r.json() == [] and r.headers["X-Total-Count"] == "1"


def test_sequence_detail_cached(client):
    items = client.get("/api/sequences").json()["items"]
    if not items:
        pytest.skip("fixture has no sequences")
    sid = items[0]["seq_id"]
    first = client.get(f"/api/sequences/{sid}").json()
    assert client.app.state.serve.sequence_cache.get(sid) is not None
    assert client.get(f"/api/sequences/{sid}").json() == first


def test_eval(client, built):
    import json

    cfg, _ = built
    body = client.get("/api/eval").json()
    assert body["splits"] == {} and body["openbible"] is None
    assert body["final"]["verse"]["fused"] == cfg["final_systems"]["fused"]
    folder = Path(cfg["paths"]["artifacts"]) / "eval"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "metrics.json").write_text(json.dumps({"splits": {"dev": {"results": {}}}}))
    assert client.get("/api/eval").json()["splits"] == {"dev": {"results": {}}}


def test_acrostics(client):
    body = client.get("/api/acrostics?max_q=1").json()
    # the one-verse chapter c:1:1 has no chain (a chain needs two lines)
    assert body["total"] == 2 and len(body["items"]) == 2
    item = body["items"][0]
    assert item["unit"]["unit_type"] == "chapter" and 0 < item["p"] <= 1 and item["q"] >= item["p"]
    assert item["chain"] and {"verse_id", "display_idx", "letter"} <= set(item["chain"][0])
    assert client.get("/api/acrostics").json()["total"] == 0  # nothing significant in 6 verses
    one = client.get("/api/acrostics/c:0:1").json()
    assert one["unit"]["unit_id"] == "c:0:1"
    assert client.get("/api/acrostics/v:0").json() is None
    assert client.get("/api/acrostics/nope").status_code == 404
    assert client.get("/api/acrostics?max_q=2").status_code == 422


def test_rewrites(client):
    profiles = client.get("/api/rewrite-profiles").json()
    assert profiles and profiles[0]["verse_pairs"] >= 1 and profiles[0]["a_words"] > 0
    body = client.get("/api/rewrites?max_q=1").json()
    assert body["total"] == len(body["items"])
    for r in body["items"]:
        assert r["op"] in ("substitution", "omitted", "added") and r["n"] >= 2
    assert client.get("/api/rewrites?op=spelling").status_code == 422


def test_structure_ranking_has_q_and_leitwort_numbers(client):
    body = client.get("/api/structure?min_verses=1").json()
    assert "leitwort_numbers" in body and body["leitwort_numbers"]["leitworte"] >= 0
    assert all("semantic_inclusio_q" in r for r in body["items"])


def test_sequence_directions(client):
    # fixture chains predate reverse / mixed ones: build-db marks them forward
    items = client.get("/api/sequences").json()["items"]
    assert items and all(s["direction"] == "forward" for s in items)
    assert client.get("/api/sequences?direction=forward").json()["total"] == len(items)
    assert client.get("/api/sequences?direction=reverse").json()["total"] == 0
    assert client.get("/api/sequences?direction=sideways").status_code == 422


def test_network(client):
    body = client.get("/api/network/chapter").json()
    assert body["communities"] and body["central"]
    assert sum(c["size"] for c in body["communities"]) == 3  # the fixture's chapters
    k = body["communities"][0]["community"]
    one = client.get(f"/api/network/chapter/{k}").json()
    assert len(one["nodes"]) == body["communities"][0]["size"]
    ids = {n["unit"]["unit_id"] for n in one["nodes"]}
    assert all(e["a"] in ids and e["b"] in ids for e in one["edges"])
    u = client.get("/api/unit-network/c:0:1").json()
    assert 1 <= u["rank"] <= u["of"] == 3
    assert client.get("/api/unit-network/v:0").json() is None
    assert client.get("/api/network/verse").status_code == 422
    assert client.get("/api/network/chapter/99").status_code == 404


def test_word_pairs_and_clauses(client):
    body = client.get("/api/word-pairs").json()
    assert body["total"] == 1
    w = body["items"][0]
    assert (w["a"]["lemma"], w["b"]["lemma"], w["n"]) == ("430", "3068", 4)
    assert [e["verse_id"] for e in w["examples"]] == [0, 1]
    assert client.get("/api/word-pairs?lemma=999").json()["total"] == 0
    assert client.get("/api/word-pairs?max_q=5").status_code == 422
    halves = client.get("/api/parallelism/c:0:1").json()["verses"]
    # fixture artifacts predate clauses: the cola stand in for them
    assert halves[0]["clauses"] == halves[0]["cola"] and halves[0]["next_prob"] is None


def test_alliteration_and_rhymes(client):
    body = client.get("/api/alliteration").json()
    assert body["total"] == len(body["items"])
    for a in body["items"]:
        assert a["count"] >= 3 and a["verse"]["verse_id"] == int(a["verse"]["verse_id"])
    assert client.get("/api/alliteration?unit=nope").status_code == 404
    rh = client.get("/api/rhymes").json()
    assert rh["total"] == len(rh["items"])
    assert client.get("/api/rhymes?max_q=3").status_code == 422


def test_typescenes_endpoint(client):
    body = client.get("/api/typescenes?max_q=1&hide_textual=false").json()
    assert body["total"] == len(body["items"])
    for t in body["items"]:
        assert t["n_matches"] == len(t["aligned"]) and t["a"]["unit_type"] == "chapter"
    assert client.get("/api/typescenes?unit=nope").status_code == 404
    assert client.get("/api/typescenes?max_q=2").status_code == 422


def test_export_csv(client):
    r = client.get("/api/export/discoveries.csv?unit_type=verse&mode=fused")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert r.headers["content-disposition"] == 'attachment; filename="discoveries.csv"'
    lines = r.content.decode("utf-8-sig").strip().splitlines()
    total = client.get("/api/discoveries?unit_type=verse&mode=fused").json()["total"]
    assert len(lines) == total + 1
    header = lines[0].split(",")
    assert "a" in header and "score" in header and "a_verse" not in header  # units as labels
    # path-style parameters come from the query; missing ones are 422
    assert client.get("/api/export/concordance.csv?lemma=430").status_code == 200
    assert client.get("/api/export/concordance.csv").status_code == 422
    assert client.get("/api/export/discoveries.csv?book=abc").status_code == 422
    assert client.get("/api/export/nope.csv").status_code == 404
    for name in ("phrases", "sequences", "wordplay", "names", "acrostics", "structure", "poetry"):
        assert client.get(f"/api/export/{name}.csv").status_code == 200, name


def test_flatten_labels_nested_values():
    from bsim.api.routes.export import flatten

    row = flatten(
        {
            "a": {"unit_id": "v:1", "label_en": "Gen 1:1"},
            "lemmas": [{"lemma": "1", "he_lemma": "אב"}, {"lemma": "2", "he_lemma": "אם"}],
            "verse": {"text_display": "x"},
            "counts": {"same": 3},
            "q": 0.01,
        }
    )
    assert row == {"a": "Gen 1:1", "lemmas": "אב; אם", "counts.same": 3, "q": 0.01}


def test_search_book_filter_and_depth(client):
    all_hits = client.get("/api/search?q=ראשית&mode=lexical&k=50").json()["hits"]
    in_book1 = client.get("/api/search?q=ראשית&mode=lexical&book=1").json()
    assert in_book1["book"] == 1
    assert [h["verse"]["verse_id"] for h in in_book1["hits"]] == [5]  # book 1 = v5 only
    assert {h["verse"]["book_id"] for h in all_hits} == {0, 1}
    sem = client.get("/api/search?q=דגן&mode=semantic&book=1").json()["hits"]
    assert [h["verse"]["verse_id"] for h in sem] == [5]
    assert client.get("/api/search?q=ראשית&k=200").status_code == 200
    assert client.get("/api/search?q=ראשית&k=201").status_code == 422
    assert client.get("/api/search?q=ראשית&book=99").status_code == 404
