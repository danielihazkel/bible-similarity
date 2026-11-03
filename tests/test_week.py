"""This week's parasha (`/week`, DESIGN.md §11.1): the reading cycle, in Israel and abroad."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from bsim.api import queries
from bsim.api.app import create_app
from bsim.api.week import next_shabbat, portions, reading
from bsim.config import load_config
from bsim.fixture import fixture_encoder

CFG = load_config()
# the parasha units of the real build, in order, as `week.known` names them
NAMES = [
    "Bereshit", "Noach", "Lech Lecha", "Vayera", "Chayei Sara", "Toldot", "Vayetzei", "Vayishlach",
    "Vayeshev", "Miketz", "Vayigash", "Vayechi", "Shemot", "Vaera", "Bo", "Beshalach", "Yitro",
    "Mishpatim", "Terumah", "Tetzaveh", "Ki Tisa", "Vayakhel", "Pekudei", "Vayikra", "Tzav",
    "Shmini", "Tazria", "Metzora", "Achrei Mot", "Kedoshim", "Emor", "Behar", "Bechukotai",
    "Bamidbar", "Nasso", "Beha'alotcha", "Sh'lach", "Korach", "Chukat", "Balak", "Pinchas",
    "Matot", "Masei", "Devarim", "Vaetchanan", "Eikev", "Re'eh", "Shoftim", "Ki Teitzei",
    "Ki Tavo", "Nitzavim", "Vayeilech", "Ha'Azinu", "V'Zot HaBerachah",
]  # fmt: skip


def test_next_shabbat():
    assert next_shabbat(date(2026, 11, 3)) == date(2026, 11, 7)  # a Tuesday
    assert next_shabbat(date(2026, 11, 7)) == date(2026, 11, 7)  # a Shabbat is its own
    assert next_shabbat(date(2026, 11, 8)) == date(2026, 11, 14)


@pytest.mark.parametrize(("day", "israel", "expected"), CFG["week"]["known"])
def test_known_readings(day, israel, expected):
    assert [f"p:{NAMES[i]}" for i in portions(date.fromisoformat(day), israel)] == expected


def test_a_festival_shabbat_gives_the_next_reading():
    # Pesach's eighth day on Shabbat abroad, 2019: the next Shabbat's Achrei Mot
    r = reading(date(2019, 4, 24), israel=False, ahead=6)
    assert r.shabbat == date(2019, 4, 27) and r.festival
    assert r.reading_shabbat == date(2019, 5, 4) and r.portions == [NAMES.index("Achrei Mot")]
    assert (r.hebrew_en, r.hebrew_he) == ("22 Nissan 5779", "כ״ב ניסן תשע״ט")
    israel = reading(date(2019, 4, 24), israel=True, ahead=6)
    assert not israel.festival and israel.reading_shabbat == date(2019, 4, 27)


def units():
    return [
        {"unit_id": f"p:{n}", "unit_type": "parasha", "label_en": n, "label_he": n, "book_id": 0,
         "start_verse_id": i, "end_verse_id": i, "n_verses": 1, "marker": None}
        for i, n in enumerate(NAMES)
    ]  # fmt: skip


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_week_endpoint(client, monkeypatch):
    monkeypatch.setattr(queries, "parasha_units", lambda conn: units())
    r = client.get("/api/week", params={"date": "2025-10-14"}).json()
    assert r["shabbat"] == "2025-10-18" and not r["festival"]
    assert [p["unit"]["unit_id"] for p in r["parashot"]] == ["p:Bereshit"]
    h = r["parashot"][0]["haftarah"]  # the fixture's haftarah for Bereshit
    assert h is not None and h["rank_fused"] >= 1 and isinstance(h["chapters"], list)
    assert (r["prev"], r["next"]) == ("2025-10-11", "2025-10-25")
    joined = client.get("/api/week", params={"date": "2019-08-03"}).json()
    assert [p["unit"]["unit_id"] for p in joined["parashot"]] == ["p:Matot", "p:Masei"]
    assert joined["parashot"][0]["haftarah"] is None  # no fixture haftarah for Matot
    israel = client.get("/api/week", params={"date": "2019-08-03", "israel": True}).json()
    assert [p["unit"]["unit_id"] for p in israel["parashot"]] == ["p:Masei"] and israel["israel"]
    fest = client.get("/api/week", params={"date": "2019-04-27"}).json()
    assert fest["festival"] and fest["reading_shabbat"] == "2019-05-04"


def test_week_without_parasha_units(client):
    assert client.get("/api/week", params={"date": "2025-10-14"}).status_code == 503
    assert client.get("/api/week", params={"date": "not a date"}).status_code == 422
