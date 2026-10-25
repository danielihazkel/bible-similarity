"""Words linked through the encoder's token vectors (`/align`, DESIGN.md §16.73)."""

import threading

import numpy as np
import pytest
from fastapi.testclient import TestClient

from bsim.api.align import align_verses, mutual_links, verse_words, word_vectors
from bsim.api.app import create_app
from bsim.api.search import BackgroundEncoder, EncoderLoading, EncoderUnavailable, token_encoder
from bsim.fixture import fixture_encoder, fixture_tokens


def row(surface, lemmas, display):
    return {"surface": surface, "content_lemmas": lemmas, "display_idx": display}


def test_verse_words():
    vw = verse_words([row("בְּרֵאשִׁית", "7225", 0), row("׃", "", None), row("בָּרָא", "1254a", 1)])
    # a word with no letters is left out, so the spans follow the text
    assert vw.text == "בראשית ברא" and vw.spans == [(0, 6), (7, 10)]
    assert vw.display == [0, 1] and vw.lemmas == [frozenset({"7225"}), frozenset({"1254a"})]


def test_word_vectors():
    vw = verse_words([row("אב", "1", 0), row("אם", "517", 1), row("בן", "1121", 2)])
    # three tokens: two in the first word, one in the second; the third word cut off
    tokens = np.array([[1.0, 0], [0, 1.0], [1.0, 0]], np.float32)
    offsets = np.array([[0, 1], [1, 2], [3, 5]])
    v, has = word_vectors(vw, tokens, offsets)
    assert has.tolist() == [True, True, False]
    assert v[0] == pytest.approx([2**-0.5, 2**-0.5]) and v[1] == pytest.approx([1, 0])


def test_mutual_links():
    a = np.array([[1, 0], [0.6, 0.8], [0, 1]], np.float32)
    b = np.array([[0.8, 0.6], [0, 1]], np.float32)
    ok_a, ok_b = np.ones(3, bool), np.ones(2, bool)
    links = mutual_links(a, b, ok_a, ok_b, 0.0)
    # a2 ~ b1 (1.0) and a1 ~ b0 (0.96) are each other's best; a0's best, b0, prefers a1
    assert [(i, j) for i, j, _ in links] == [(2, 1), (1, 0)]
    assert links[1][2] == pytest.approx(0.96)
    assert [(i, j) for i, j, _ in mutual_links(a, b, ok_a, ok_b, 0.97)] == [(2, 1)]
    # without a1, a0 and b0 are each other's best
    assert mutual_links(a, b, np.array([True, False, True]), ok_b, 0.0)[1][:2] == (0, 0)
    assert mutual_links(a, b, np.zeros(3, bool), ok_b, 0.0) == []


def test_align_verses():
    va = [row("אלהים", "430", 0), row("את", "853", 1), row("השמים", "8064", 2)]
    vb = [row("את", "853", 0), row("השמים", "8064", 1), row("אלהים", "430", 2)]
    links = align_verses(va, vb, fixture_tokens, 0.5, {"853"})
    # את is in the stop list: linked words are אלהים and השמים, both shared lemmas
    assert sorted((x["a_display"], x["b_display"]) for x in links) == [(0, 2), (2, 1)]
    assert all(x["same_lemma"] and x["cos"] == 1.0 for x in links)


def test_token_encoder():
    assert token_encoder(fixture_encoder) is fixture_tokens
    with pytest.raises(EncoderUnavailable):
        token_encoder(lambda texts: np.zeros((len(texts), 4)))
    gate = threading.Event()
    bg = BackgroundEncoder(lambda: gate.wait() and fixture_encoder, log=lambda _: None)
    with pytest.raises(EncoderLoading):
        bg.tokens(["אב"])
    gate.set()
    bg._done.wait(5)
    assert len(bg.tokens(["אב אם"])[0][0]) == 2


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_align_endpoint(client):
    r = client.get("/api/align", params={"a": 0, "b": 1}).json()
    assert r["min_cos"] == 0.4 and r["links"]
    first = r["links"][0]
    assert first["cos"] == 1.0 and first["same_lemma"] and first["a_form"] == first["b_form"]
    assert client.get("/api/align", params={"a": 0, "b": 999}).status_code == 404


def test_align_without_token_vectors(built):
    cfg, _ = built
    plain = lambda texts: fixture_encoder(texts)  # noqa: E731 (no token vectors)
    c = TestClient(create_app(cfg, encoder=plain, log=lambda _: None))
    assert c.get("/api/align", params={"a": 0, "b": 1}).status_code == 503
