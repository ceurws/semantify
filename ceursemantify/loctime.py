"""
Created on 2026-10-13

@author: wf
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import ClassVar, Dict, Optional


@dataclass
class LocTime:
    """
    location and time of an event as given in the CEURLOCTIME text of a
    volume page e.g. Verona, Italy, June 8-12, 2026
    """

    text: str
    location: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    virtual: bool = False
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    # why the date could not be parsed, None if it was
    message: Optional[str] = None

    MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?"
    DAY = r"\d{1,2}(?:st|nd|rd|th)?"
    SEP = r"\s*(?:-|–|—|to|until)\s*"
    YEAR = r"\d{4}"
    # the date forms, the most specific first; m: month, d: day, y: year
    DATE_FORMS = [
        # December 30, 2025 - January 2, 2026
        rf"(?P<m1>{MONTH})\s+(?P<d1>{DAY}),?\s+(?P<y1>{YEAR}){SEP}(?P<m2>{MONTH})\s+(?P<d2>{DAY}),?\s+(?P<y2>{YEAR})",
        # September 29 - October 3, 2025
        rf"(?P<m1>{MONTH})\s+(?P<d1>{DAY}){SEP}(?P<m2>{MONTH})\s+(?P<d2>{DAY}),?\s+(?P<y1>{YEAR})",
        # June 8-12, 2026
        rf"(?P<m1>{MONTH})\s+(?P<d1>{DAY}){SEP}(?P<d2>{DAY}),?\s+(?P<y1>{YEAR})",
        # March 1st, 2021
        rf"(?P<m1>{MONTH})\s+(?P<d1>{DAY}),?\s+(?P<y1>{YEAR})",
        # 30 June - 2 July 2026
        rf"(?P<d1>{DAY})\s+(?P<m1>{MONTH}){SEP}(?P<d2>{DAY})\s+(?P<m2>{MONTH}),?\s+(?P<y1>{YEAR})",
        # 1-3 December 2025
        rf"(?P<d1>{DAY}){SEP}(?P<d2>{DAY})\s+(?P<m1>{MONTH}),?\s+(?P<y1>{YEAR})",
        # 3 December 2025
        rf"(?P<d1>{DAY})\s+(?P<m1>{MONTH}),?\s+(?P<y1>{YEAR})",
    ]
    date_patterns = [re.compile(date_form) for date_form in DATE_FORMS]
    virtual_pattern = re.compile(r"\b(online|virtual)\b", re.IGNORECASE)
    months: ClassVar[Dict[str, int]] = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    @classmethod
    def iso_date(cls, year: str, month: str, day: str) -> str:
        """
        get the ISO date of the given parts

        Args:
            year: the four digit year
            month: the month name, full or abbreviated
            day: the day, with an optional ordinal suffix

        Returns:
            str: the date as YYYY-MM-DD

        Raises:
            ValueError: if the parts are not a valid date
        """
        month_number = cls.months[month[:3].lower()]
        day_number = int(re.sub(r"\D", "", day))
        iso_date = date(int(year), month_number, day_number).isoformat()
        return iso_date

    @classmethod
    def parse(cls, text: str) -> "LocTime":
        """
        parse the given location and time text

        The date is the last part of the text; what is before it is the
        location, its first comma separated part the city and its last part
        the country. An online or virtual location has no city and no country.

        Args:
            text: the text e.g. Verona, Italy, June 8-12, 2026

        Returns:
            LocTime: the location and time, with a message if the date could not be parsed
        """
        text = " ".join(text.split())
        loctime = cls(text=text, location=text or None)
        match = None
        for pattern in cls.date_patterns:
            match = pattern.search(text)
            if match:
                break
        if match:
            parts = match.groupdict()
            try:
                loctime.startDate = cls.iso_date(parts["y1"], parts["m1"], parts["d1"])
                end_year = parts.get("y2") or parts["y1"]
                end_month = parts.get("m2") or parts["m1"]
                end_day = parts.get("d2") or parts["d1"]
                loctime.endDate = cls.iso_date(end_year, end_month, end_day)
            except ValueError as error:
                loctime.message = f"invalid date in {text}: {error}"
            loctime.location = text[: match.start()].rstrip(" ,.;") or None
        else:
            loctime.message = f"no date found in {text}" if text else "empty location and time"
        if loctime.location:
            if cls.virtual_pattern.search(loctime.location):
                loctime.virtual = True
            else:
                parts = [part.strip() for part in loctime.location.split(",") if part.strip()]
                loctime.city = parts[0]
                if len(parts) > 1:
                    loctime.country = parts[-1]
        return loctime
