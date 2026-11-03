"""This week's parasha (DESIGN.md §11.1): a Shabbat's Torah reading, in Israel or abroad.

The Hebrew calendar and the reading cycle (the year's type, the portions read together, the
festivals that displace a Shabbat's reading, Israel's one-day festivals) come from `pyluach`
(MIT), computed locally. Its portions are numbered 0–53 in the Torah's order, the order of our
parasha units; `week.known` holds dates checked by the tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from pyluach import dates, parshios

SATURDAY = 5  # date.weekday()


@dataclass(frozen=True)
class Reading:
    shabbat: date  # the Shabbat on or after the date asked for
    festival: bool  # no weekly reading that Shabbat (a festival's)
    reading_shabbat: date | None  # the Shabbat whose portions are given (the next with a reading)
    portions: list[int]  # 0–53, one or two
    hebrew_he: str  # the Shabbat's Hebrew date
    hebrew_en: str


def next_shabbat(d: date) -> date:
    return d + timedelta(days=(SATURDAY - d.weekday()) % 7)


def portions(d: date, israel: bool) -> list[int]:
    got = parshios.getparsha(dates.GregorianDate(d.year, d.month, d.day), israel=israel)
    return [int(x) for x in got] if got else []


def reading(d: date, israel: bool, ahead: int) -> Reading:
    """The weekly reading of the Shabbat on or after `d`; on a festival's Shabbat, the next
    reading within `ahead` weeks."""
    shabbat = next_shabbat(d)
    got = portions(shabbat, israel)
    at: date | None = shabbat
    if not got:
        at = None
        for k in range(1, ahead + 1):
            nxt = shabbat + timedelta(weeks=k)
            got = portions(nxt, israel)
            if got:
                at = nxt
                break
    h = dates.GregorianDate(shabbat.year, shabbat.month, shabbat.day).to_heb()
    return Reading(
        shabbat=shabbat,
        festival=at != shabbat,
        reading_shabbat=at,
        portions=got,
        hebrew_he=h.hebrew_date_string(),
        hebrew_en=f"{h.day} {h.month_name()} {h.year}",
    )
