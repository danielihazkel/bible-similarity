import pytest
from lxml import etree

from bsim.data.oshb import content_lemmas, parse_verse

NS = "http://www.bibletechnologies.net/2003/OSIS/namespace"

# One synthetic verse covering: maqaf, multi-word ketiv with one qere, qere without ketiv,
# ketiv without qere, an alternative-accent note, an untyped note, a letter in a nested seg, x-pe.
VERSE = f"""<verse xmlns="{NS}" osisID="Ruth.3.5">
  <w lemma="c/559" morph="HC/Vqw3fs" id="a1">וַ/תֹּ֖אמֶר</w>
  <w lemma="5921 a" morph="HR" id="a2">עַל</w><seg type="x-maqqef">־</seg>
  <w lemma="c/d/776" morph="HC/Td/Ncbsa" id="a3">וְ/הָ/אָ֗רֶץ</w>
  <w type="x-ketiv" lemma="2755" morph="HNcmsc" id="k1">חרי</w>
  <w type="x-ketiv" lemma="3123" morph="HNcfpa" id="k2">יונים</w>
  <note type="variant"><catchWord>חרייונים</catchWord>
    <rdg type="x-qere"><w lemma="1686" morph="HNcmpa" id="q1">דִּבְיוֹנִ֖ים</w></rdg></note>
  <note type="variant"><rdg type="x-qere">
    <w lemma="413" morph="HR/Sp1cs" id="q2">אֵלַ֖/י</w></rdg></note>
  <w type="x-ketiv" lemma="518 a" morph="HC" id="k3">אם</w>
  <note type="variant"><catchWord>אם</catchWord><rdg type="x-qere"/></note>
  <note type="alternative"><rdg type="x-accent"><w lemma="1" id="x1">אַב</w></rdg></note>
  <note>Large letter(s). <w lemma="2" id="x2">בַּ</w></note>
  <w lemma="8085" morph="HVqv2ms" id="a4">שְׁמַ֖<seg type="x-large">ע</seg></w>
  <seg type="x-sof-pasuq">׃</seg>
  <seg type="x-pe">פ</seg>
</verse>"""


def _verse(kq="qere"):
    return parse_verse(etree.fromstring(VERSE), kq)


def test_qere_reading():
    v = _verse()
    assert (v.chapter, v.verse, v.osis) == (3, 5, "Ruth.3.5")
    assert [w.oshb_id for w in v.words] == ["a1", "a2", "a3", "q1", "q2", "a4"]
    assert [w.kq for w in v.words] == [None, None, None, "q", "q", None]
    assert v.words[0].surface == "וַתֹּ֖אמֶר"
    assert v.words[-1].surface == "שְׁמַ֖ע"
    assert v.breaks == ["pe"]


def test_ketiv_reading():
    v = _verse("ketiv")
    assert [w.oshb_id for w in v.words] == ["a1", "a2", "a3", "k1", "k2", "k3", "a4"]
    assert v.words[3].kq == "k"


def test_bad_kq():
    with pytest.raises(ValueError):
        _verse("both")


def test_content_lemmas():
    assert content_lemmas("c/d/776") == ("776",)
    assert content_lemmas("1121 a") == ("1121a",)
    assert content_lemmas("l/6213 a") == ("6213a",)
    assert content_lemmas("1961+") == ("1961",)
    assert content_lemmas("i/c") == ()
