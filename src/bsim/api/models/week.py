"""Response models of `api/routes/week.py` (DESIGN.md §10, §11.1)."""

from __future__ import annotations

from bsim.api.models.common import ApiModel, UnitSummary


class WeekHaftarah(ApiModel):
    """The sages' haftarah for a parasha (`bsim haftarot`), and how the site ranks it."""

    haft: str  # the Ashkenazi haftarah, refs
    seph: str | None  # the Sephardi, where it differs
    theme: str | None  # admonition | consolation: fixed by the calendar
    chapters: list[str]  # chapter units holding it
    rank_fused: int  # its best rank among the Prophets' chapters for the parasha


class WeekParasha(ApiModel):
    unit: UnitSummary
    haftarah: WeekHaftarah | None  # None: `bsim haftarot` did not run


class WeekResponse(ApiModel):
    date: str  # the date asked for (ISO)
    israel: bool
    shabbat: str  # the Shabbat on or after it (ISO)
    hebrew_he: str  # its Hebrew date
    hebrew_en: str
    festival: bool  # a festival's Shabbat, with no weekly reading
    reading_shabbat: str | None  # the Shabbat whose parashot are given (the next with a reading)
    parashot: list[WeekParasha]  # one, or two read together
    prev: str  # the Shabbat before and after (ISO)
    next: str
