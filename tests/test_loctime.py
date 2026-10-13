"""
Created on 2026-10-13

@author: wf
"""

from ceursemantify.loctime import LocTime
from tests.base_ceurtest import BaseCeurTest


class TestLocTime(BaseCeurTest):
    """
    test the parsing of the CEURLOCTIME text of a volume page
    """

    def test_parse(self) -> None:
        """
        test the location and date forms of the volume template and its variants
        """
        cases = {
            "Verona, Italy, June 8-12, 2026": ("Verona, Italy", "Verona", "Italy", "2026-06-08", "2026-06-12"),
            "Jena, Germany, Sept 23-24, 2025": ("Jena, Germany", "Jena", "Germany", "2025-09-23", "2025-09-24"),
            "Bolzano, Italy, September 29 - October 3, 2025": (
                "Bolzano, Italy",
                "Bolzano",
                "Italy",
                "2025-09-29",
                "2025-10-03",
            ),
            "Kyoto, Japan, December 30, 2025 - January 2, 2026": (
                "Kyoto, Japan",
                "Kyoto",
                "Japan",
                "2025-12-30",
                "2026-01-02",
            ),
            "Pretoria, South Africa, 1-3 December 2025": (
                "Pretoria, South Africa",
                "Pretoria",
                "South Africa",
                "2025-12-01",
                "2025-12-03",
            ),
            "Lisbon, Portugal, 30 June - 2 July 2026": (
                "Lisbon, Portugal",
                "Lisbon",
                "Portugal",
                "2026-06-30",
                "2026-07-02",
            ),
            "Aachen, Germany, March 1st, 2021": ("Aachen, Germany", "Aachen", "Germany", "2021-03-01", "2021-03-01"),
            "Hersonissos, Crete, Greece, May 30, 2022": (
                "Hersonissos, Crete, Greece",
                "Hersonissos",
                "Greece",
                "2022-05-30",
                "2022-05-30",
            ),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                loctime = LocTime.parse(text)
                self.assertIsNone(loctime.message, loctime)
                self.assertEqual(
                    expected, (loctime.location, loctime.city, loctime.country, loctime.startDate, loctime.endDate)
                )
                self.assertFalse(loctime.virtual)

    def test_virtual(self) -> None:
        """
        test that an online event has no city and no country
        """
        loctime = LocTime.parse("Online, March 1-2, 2021")
        self.assertTrue(loctime.virtual)
        self.assertIsNone(loctime.city)
        self.assertIsNone(loctime.country)
        self.assertEqual("2021-03-01", loctime.startDate)
        loctime = LocTime.parse("Virtual Event, June 14, 2021")
        self.assertTrue(loctime.virtual)
        self.assertEqual("Virtual Event", loctime.location)

    def test_not_parsed(self) -> None:
        """
        test that a text without a date keeps the location and reports a message
        """
        for text in ["Somewhere, Sometime", "Aachen, Germany, June 31, 2026", ""]:
            with self.subTest(text=text):
                loctime = LocTime.parse(text)
                self.assertIsNone(loctime.startDate)
                self.assertIsNotNone(loctime.message)
        self.assertEqual("Somewhere, Sometime", LocTime.parse("Somewhere, Sometime").location)
