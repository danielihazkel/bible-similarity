import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from bsim.analysis.speech import speech_tables, word_types
from bsim.api.app import create_app
from bsim.api.routes.syntax import segments
from bsim.config import load_config
from bsim.data.bhsa import align_verse, cons, read_otype, read_tf, run_syntax
from bsim.fixture import fixture_encoder
from bsim.lexical.syntax import clause_tokens, syntax_streams

HEADER = "@{kind}\n@valueType=str\n@writtenBy=Text-Fabric\n\n"


def tf(path, body, kind="node"):
    path.write_text(HEADER.format(kind=kind) + body, encoding="utf-8")


def test_read_tf(tmp_path):
    tf(tmp_path / "f.tf", "2\ta\nb\n\n5-6\tc\n")  # 1 unset, 2 a, 3 b, 4 empty, 5-6 c
    assert read_tf(tmp_path / "f.tf") == {2: "a", 3: "b", 4: "", 5: "c", 6: "c"}
    tf(tmp_path / "e.tf", "3\t1-2\n4,6\n", kind="edge")  # 3 -> 1, 2; 4 -> 4, 6
    assert read_tf(tmp_path / "e.tf") == {3: [1, 2], 4: [4, 6]}
    (tmp_path / "otype.tf").write_text("@node\n\n1-5\tword\n6\tbook\n", encoding="utf-8")
    assert read_otype(tmp_path / "otype.tf") == {"word": (1, 5), "book": (6, 6)}


def test_align_verse():
    # BHSA splits ו and the article (no consonants after ל); OSHB keeps them with the word
    bhsa = [cons(w) for w in ["ו", "יאמר", "ל", "", "מלך"]]
    oshb = [cons(w) for w in ["וַיֹּאמֶר", "לַמֶּלֶךְ"]]
    assert align_verse(bhsa, oshb) == [0, 0, 1, 1, 1]
    # ketiv / qere: an unmatched word goes with its neighbour
    assert align_verse(["אהלה", "שם"], ["אהלו", "שם"]) == [0, 1]


def write_bhsa(raw):
    """Gen 1:1 ויאמר אלהים | יהי אור (God speaks); Gen 1:2 ותאמר להם | שבו (a feminine
    introduction without a subject: אלהים does not agree, so no speaker)."""
    raw.mkdir(parents=True)
    (raw / "otype.tf").write_text(
        "@node\n\n1-9\tword\n10\tbook\n11\tchapter\n12-15\tclause\n16-19\tclause_atom\n"
        "20-28\tphrase\n29-30\tverse\n",
        encoding="utf-8",
    )
    slots = (
        "10\t1-9\n1-9\n1-3\n4-5\n6-8\n9\n1-3\n4-5\n6-8\n9\n1\n2\n3\n4\n5\n6\n7\n8\n9\n1-5\n6-9\n"
    )
    tf(raw / "oslots.tf", slots, kind="edge")
    tf(raw / "mother.tf", "17\t16\n19\t18\n", kind="edge")
    words = ["ו", "יאמר", "אלהים", "יהי", "אור", "ו", "תאמר", "להם", "שבו"]
    tf(raw / "g_cons_utf8.tf", "\n".join(words) + "\n")
    tf(raw / "sp.tf", "conj\nverb\nsubs\nverb\nsubs\nconj\nverb\nprep\nverb\n")
    tf(raw / "lex.tf", "W\n>MR[\n>LHJM/\nHJH[\n>WR/\nW\n>MR[\nL\nJCB[\n")
    tf(raw / "ps.tf", "NA\np3\nNA\np3\nNA\nNA\np3\nNA\np2\n")
    tf(raw / "gn.tf", "NA\nm\nm\nm\nm\nNA\nf\nNA\nm\n")
    tf(raw / "vt.tf", "NA\nwayq\nNA\nimpf\nNA\nNA\nwayq\nNA\nimpv\n")
    tf(raw / "book.tf", "10\tGenesis\n29-30\tGenesis\n")
    tf(raw / "chapter.tf", "29-30\t1\n")
    tf(raw / "verse.tf", "29\t1\n2\n")
    tf(raw / "typ.tf", "12\tWayX\nZYqX\nWay0\nZIm0\n20\tCP\nVP\nNP\nVP\nNP\nCP\nVP\nPP\nVP\n")
    tf(raw / "kind.tf", "12-15\tVC\n")
    tf(raw / "domain.tf", "12\tN\nQ\nN\nQ\n")
    tf(raw / "txt.tf", "12\tN\nNQ\nN\nNQ\n")
    tf(raw / "rela.tf", "12-15\tNA\n")
    tf(raw / "function.tf", "20\tConj\nPred\nSubj\nPred\nSubj\nConj\nPred\nCmpl\nPred\n")


@pytest.fixture
def syntax_cfg(tmp_path):
    cfg = load_config()
    raw, proc = tmp_path / "raw", tmp_path / "processed"
    cfg["paths"] = {**cfg["paths"], "data_raw": str(raw), "data_processed": str(proc)}
    write_bhsa(raw / "bhsa")
    proc.mkdir()
    pd.DataFrame({"verse_id": [0, 1], "oshb_osis": [["Gen.1.1"], ["Gen.1.2"]]}).to_parquet(
        proc / "verses.parquet"
    )
    pd.DataFrame(
        {
            "verse_id": [0, 0, 0, 0, 1, 1, 1],
            "idx": [0, 1, 2, 3, 0, 1, 2],
            "surface": ["וַיֹּאמֶר", "אֱלֹהִים", "יְהִי", "אוֹר", "וַתֹּאמֶר", "לָהֶם", "שְׁבוּ"],
            "content_lemmas": [["559"], ["430"], ["1961"], ["216"], ["559"], [], ["3427"]],
        }
    ).to_parquet(proc / "words.parquet")
    return cfg


def test_run_syntax(syntax_cfg):
    meta = run_syntax(syntax_cfg, log=lambda _: None)
    assert meta["verses_same_consonants"] == 2 and meta["clauses"] == 4
    proc = syntax_cfg["paths"]["data_processed"]
    c = pd.read_parquet(f"{proc}/syntax_clauses.parquet")
    assert [list(w) for w in c.words] == [[0, 1], [2, 3], [0, 1], [2]]
    assert c.speech.tolist() == [False, True, False, True]
    assert (c.speaker[1], c.speaker_source[1]) == ("430", "explicit")
    assert pd.isna(c.speaker[3])  # ותאמר: אלהים is masculine
    p = pd.read_parquet(f"{proc}/syntax_phrases.parquet")
    assert p[p.clause == 12].function.tolist() == ["Conj", "Pred", "Subj"]
    assert [list(w) for w in p[p.clause == 12].words] == [[0], [0], [1]]


def test_syntax_tokens():
    assert clause_tokens("WayX", ["Conj", "Pred", "Subj"], "NA", "?NQ") == [
        "C:WayX",
        "P:WayX:Conj-Pred-Subj",
        "T:Q",
    ]
    clauses = pd.DataFrame(
        {"clause": [1, 2], "verse_id": [0, 0], "typ": ["WayX", "xQt0"], "rela": ["NA", "Objc"],
         "txt": ["N", "N"]}
    )  # fmt: skip
    phrases = pd.DataFrame({"clause": [1, 1, 2], "function": ["Pred", "Subj", "Conj"]})
    tokens, weights = syntax_streams(clauses, phrases, 2)
    assert tokens[0] == [
        "C:WayX", "P:WayX:Pred-Subj", "T:N", "C:xQt0", "P:xQt0:Conj", "R:Objc", "T:N",
        "S:WayX>xQt0",
    ]  # fmt: skip
    assert tokens[1] == [] and len(weights[0]) == 8


def test_speech_tables():
    clauses = pd.DataFrame(
        {
            "verse_id": [0, 0, 1],
            "words": [[0, 1], [2, 3], [0]],
            "txt": ["N", "NQ", "NQ"],
            "speaker": [None, "3068", "1732"],
            "speaker_source": [None, "explicit", "carried"],
        }
    )
    w = word_types(clauses)
    assert w.ttype.tolist() == ["N", "N", "Q", "Q", "Q"]
    verses = pd.DataFrame({"verse_id": [0, 1], "book_id": [0, 0], "chapter": [1, 2]})
    chapters, books, speakers = speech_tables(clauses, verses, ["3068"])
    assert chapters.unit_id.tolist() == ["c:0:1", "c:0:2"]
    b = books.iloc[0]
    assert (b.narration, b.speech, b.divine, b.attributed, b.n_words) == (0.4, 0.6, 0.4, 0.6, 5)
    assert speakers.values.tolist() == [[0, "3068", 2, 2], [0, "1732", 1, 0]]


def test_segments():
    phrases = [
        {"phrase": 1, "function": "Conj", "typ": "CP", "words": [0]},
        {"phrase": 2, "function": "Pred", "typ": "VP", "words": [0]},
        {"phrase": 3, "function": "Subj", "typ": "NP", "words": [1, 2]},
    ]
    seg = segments([0, 1, 2], phrases, {0: "וַיֹּאמֶר", 1: "מֹשֶׁה", 2: "רַבֵּנוּ"})
    assert [(s.function, s.text) for s in seg] == [("Pred", "וַיֹּאמֶר"), ("Subj", "מֹשֶׁה רַבֵּנוּ")]


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_syntax_api(client):
    v = client.get("/api/syntax/v:0").json()
    (verse,) = v["verses"]
    assert [c["typ"] for c in verse["clauses"]] == ["xQtX", "WayX"]
    assert [s["function"] for s in verse["clauses"][1]["segments"]] == ["Pred", "Subj"]
    assert [n["unit"]["unit_id"] for n in v["neighbors"]] == ["v:1", "v:3", "v:5", "v:2"]
    speech = client.get("/api/syntax/v:1").json()["verses"][0]["clauses"][0]
    assert speech["speech"] and speech["divine"] and speech["speaker_he"] == "יהוה"
    chapter = client.get("/api/syntax/c:0:1").json()
    assert [x["verse_id"] for x in chapter["verses"]] == [0, 1] and chapter["neighbors"] == []
    assert client.get("/api/syntax/v:99").status_code == 404

    s = client.get("/api/speech").json()
    assert s["meta"]["clauses"] == 5
    books = {b["book_id"]: b for b in s["books"]}
    assert books[0]["speakers"][0] == {
        "lemma": "3068", "he": "יהוה", "n_words": 3, "n_explicit": 3, "divine": True,
    }  # fmt: skip
    assert books[1]["speakers"][0]["n_explicit"] == 0  # carried
    b = client.get("/api/speech/book/0").json()
    assert [c["chapter"] for c in b["chapters"]] == [1, 2]
    assert client.get("/api/speech/book/9").status_code == 404


def test_syntax_meta_in_db(built):
    _, db = built
    import sqlite3

    conn = sqlite3.connect(db)
    meta = json.loads(conn.execute("SELECT value FROM meta WHERE key = 'syntax'").fetchone()[0])
    assert meta["speech_clauses"] == 3
