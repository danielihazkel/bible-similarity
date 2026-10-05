import json

import numpy as np
import pandas as pd
import pytest

from bsim.data.lexicon import (
    Meaning,
    lemma_key,
    match_refs,
    morpheme_positions,
    parse_ref,
    read_domains,
    read_sdbh,
    read_strong,
    relations,
    strong_key,
    tag_words,
)
from bsim.lexical.domains import ancestors, domain_streams


def test_strong_key():
    assert strong_key("H0430") == "430"
    assert strong_key("A7308") == "7308"
    assert strong_key("1254 a") == "1254"
    assert strong_key("1254a") == "1254"
    assert strong_key("1126+") == "1126"


def test_parse_ref():
    # Protestant book 23 = Isaiah; words counted 2, 4, 6, ... -> morpheme 15
    assert parse_ref("02304002800030") == ("Isa", 40, 28, 15)
    assert parse_ref("00100100100002") == ("Gen", 1, 1, 1)
    assert parse_ref("04001001000002") is None  # past Malachi (New Testament)


def test_lemma_key_folds_points_and_finals():
    assert lemma_key("אֶרֶץ") == "ארצ"
    assert lemma_key("ארץ") == "ארצ"


# Gen 1:1 in miniature: בְּ/רֵאשִׁית בָּרָא, then לַ/אָרֶץ (preposition with a hidden article).
WORDS = pd.DataFrame(
    {
        "verse_id": [0, 0, 0],
        "idx": [0, 1, 2],
        "lemma": ["b/7225", "1254 a", "l/776"],
        "morph": ["HR/Ncfsa", "HVqp3ms", "HRd/Ncbsa"],
    }
)
VERSES = pd.DataFrame({"verse_id": [0], "oshb_osis": [np.array(["Gen.1.1"])]})


def test_morpheme_positions_count_the_hidden_article():
    pos = morpheme_positions(WORDS, VERSES)["Gen.1.1"]
    assert [p[3] for p in pos] == [None, "7225", "1254", None, None, "776"]
    assert pos[5][:3] == (0, 2, 1)  # verse 0, word 2, lemma part 1


def meaning(lex_id, strongs, domains, refs=(), lemma="x", synonyms=(), antonyms=()):
    return Meaning(
        lex_id, lemma, list(strongs), list(domains), list(synonyms), list(antonyms), list(refs)
    )


def test_match_and_tag():
    pos = morpheme_positions(WORDS, VERSES)
    meanings = [
        meaning("begin", ["7225"], ["002001"], refs=["00100100100004"]),  # exact: morpheme 2
        meaning("land", ["776"], ["001002"], refs=["00100100100010"]),  # 5 -> actual 6 (+1)
        meaning("create", ["1254"], ["002002"]),  # no reference: from the lemma
        meaning("make", ["1254"], ["002003"]),  # a second meaning: split
    ]
    tagged, stats = match_refs(meanings, pos, window=2)
    assert stats["matched"] == 2 and stats["exact"] == 1
    assert tagged[(0, 2, 1)] == {"land"}
    df = tag_words(pos, tagged, meanings, "split")
    rows = {(r.idx, r.part): r for r in df.itertuples()}
    assert rows[(0, 1)].source == "sdbh" and rows[(0, 1)].domains == ["002001"]
    assert rows[(1, 0)].source == "lemma" and rows[(1, 0)].domains == ["002002", "002003"]
    assert rows[(1, 0)].weights == pytest.approx([0.5, 0.5])
    skipped = tag_words(pos, tagged, meanings, "skip")
    assert (1, 0) not in {(r.idx, r.part) for r in skipped.itertuples()}


def test_matched_meaning_without_domain_is_not_replaced_by_the_lemma():
    pos = morpheme_positions(WORDS, VERSES)
    meanings = [
        meaning("heaven-sense", ["7225"], [], refs=["00100100100004"]),
        meaning("other", ["7225"], ["001001"]),
    ]
    tagged, _ = match_refs(meanings, pos, window=2)
    assert tag_words(pos, tagged, meanings, "split").empty


def test_relations_both_directions_and_antonyms_win():
    meanings = [
        meaning("a", ["1"], ["001"], lemma=lemma_key("טוב"), antonyms=[lemma_key("רע")]),
        meaning("b", ["2"], ["001"], lemma=lemma_key("רע"), synonyms=[lemma_key("טוב")]),
    ]
    rel = relations(meanings)
    assert set(zip(rel.a, rel.b, rel.kind, strict=True)) == {
        ("1", "2", "antonym"),
        ("2", "1", "antonym"),
    }


def test_readers(tmp_path):
    sdbh = [
        {
            "Lemma": "אָב",
            "StrongCodes": ["H0001"],
            "BaseForms": [
                {
                    "LEXMeanings": [
                        {
                            "LEXID": "000001001001000",
                            "LEXDomains": [{"DomainCode": "001001002"}],
                            "LEXSynonyms": None,
                            "LEXAntonyms": ["בֵּן"],
                            "LEXReferences": ["00100200400002"],
                            "LEXSenses": [{"Glosses": ["father"]}],
                        }
                    ]
                }
            ],
        }
    ]
    (tmp_path / "d.json").write_text(json.dumps(sdbh, ensure_ascii=False), encoding="utf-8-sig")
    (m,) = read_sdbh(tmp_path / "d.json")
    assert (m.lex_id, m.strongs, m.domains, m.antonyms) == (
        "000001001001000",
        ["1"],
        ["001001002"],
        [lemma_key("בן")],
    )
    assert not hasattr(m, "glosses")  # glosses are never kept (D56)
    doms = [
        {
            "Code": "001",
            "SemanticDomainLocalizations": [{"LanguageCode": "en", "Label": "Objects"}],
        },
        {
            "Code": "001001",
            "SemanticDomainLocalizations": [{"LanguageCode": "en", "Label": "Beings"}],
        },
    ]
    (tmp_path / "dom.json").write_text(json.dumps(doms), encoding="utf-8")
    d = read_domains(tmp_path / "dom.json")
    assert d.to_dict("records")[1] == {
        "code": "001001",
        "level": 2,
        "parent": "001",
        "label_en": "Beings",
    }
    ns = "http://openscriptures.github.com/morphhb/namespace"
    (tmp_path / "s.xml").write_text(
        f'<lexicon xmlns="{ns}"><entry id="H1"><w pos="n-m">אָב</w></entry>'
        f'<entry id="H85"><w pos="n-pr-m">אַבְרָהָם</w></entry>'
        f'<entry id="H1204"><w pos="n-pr-m n-pr-loc">x</w></entry></lexicon>',
        encoding="utf-8",
    )
    s = read_strong(tmp_path / "s.xml").set_index("strong").name_kind
    assert pd.isna(s["1"]) and s["85"] == "person" and s["1204"] == "both"


def test_domain_streams():
    assert ancestors("002001001069") == ["002001001", "002001", "002"]
    senses = pd.DataFrame(
        {
            "verse_id": [0, 0, 1],
            "idx": [0, 1, 0],
            "strong": ["7225", "853", "7225"],
            "domains": [["002001"], ["004003"], ["002001", "002002"]],
            "weights": [[1.0], [1.0], [0.5, 0.5]],
        }
    )
    words = pd.DataFrame(
        {"verse_id": [0, 0, 1], "idx": [0, 1, 0], "content_lemmas": [["7225"], [], ["7225a"]]}
    )
    tokens, weights = domain_streams(senses, words, 2, ancestor_weight=0.5, content_only=True)
    assert tokens[0] == ["002001", "002"]  # 853 (אֵת) is a function word
    assert weights[0] == pytest.approx([1.0, 0.5])
    assert tokens[1] == ["002001", "002", "002002", "002"]
    assert weights[1] == pytest.approx([0.5, 0.25, 0.5, 0.25])
    tokens, _ = domain_streams(senses, words, 2, ancestor_weight=0.0, content_only=False)
    assert tokens[0] == ["002001", "004003"]
