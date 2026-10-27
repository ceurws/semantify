"""
Created on 2026-10-27

@author: wf
"""

import shutil
import tempfile

from tests.base_ceurtest import BaseCeurTest


class TestDateConformance(BaseCeurTest):
    """
    issue 58: --embed and --generate report a CEURLOCTIME without extractable
    dates and a CEURPUBDATE that is not ISO or out of the plausible range,
    on the cases of issue 12 and Vol-3904
    """

    # CEURLOCTIME texts of issue 12 and Vol-3904 that the parser extracts dates from
    loctime_parsed = [
        "Khmelnytskyi, Ukraine on July 4, 2025",
        "Paris, France December 11-13, 2024",
        "Bolzano, Italy, November 28—29, 2024",
        "Kyiv, Ukraine, Decembeer 20 - 21, 2023",
        "Lyon, France; August 29th-31st, 2023",
        "Havana, Cuba October 13-15, 2022",
        "Jaen, Spain, Septembre 26, 2023",
        "Macao, S.A.R. China; August 20, 2023",
        "Madrid, Spain November 21-23, 2022",
    ]
    # CEURLOCTIME texts of issue 12 without extractable dates
    loctime_unparsed = [
        "Rome, Italy, May 24th and 25th, 2024",
        "Kuala Lumpur, Malaysia, 06 29-30, 2024",
        "Hybrid Event, Honolulu, HI, USA, May 11--16, 2024",
        "Hildesheim (Germany), Oktober 5-7th, 2022",
        "Nantes, France, July 5--8, 2022",
        "New Delhi, India, November29, 2024",
        "Lille, France from 8 to 11 of July 2024",
        "Vaasa, Finland, June, 2024",
        "Washington DC, USA, 07 18, 2024",
        "Virtual event, Taipei, Taiwan, 12 8-9, 2021",
        "Naples, Italy, 10-12/09/2025",
        "Ioannina, Greece, March, 28, 2023",
        "Brasília, Brazil, August 28 - September 1,2023",
        "Bari, Italy",
    ]
    # CEURPUBDATE values of issue 12 that are not ISO dates
    pubdate_not_iso = ["2024-12-22'", "2025-May-06", "yyyy-mm-dd", "yyyy-04-10", "28-Nov-2012"]
    # CEURPUBDATE values of issue 12 that are ISO dates outside the range of CEUR-WS
    pubdate_out_of_range = ["2104-10-15", "3014-11-22", "1021-12-23", "1994-12-31"]

    def setUp(self, debug: bool = False, profile: bool = True) -> None:
        BaseCeurTest.setUp(self, debug=debug, profile=profile)
        self.temp_dir = tempfile.mkdtemp(prefix="date-conformance-")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_loctime_reported(self) -> None:
        """
        a CEURLOCTIME without extractable dates is reported by embed and generate
        """
        for loctime in self.loctime_unparsed:
            for report in self.chair_reports(self.temp_dir, {"CEURLOCTIME": loctime}):
                with self.subTest(loctime=loctime, report=report.problems):
                    self.assertEqual(1, len(self.problems(report, "CEURLOCTIME")))

    def test_loctime_parsed(self) -> None:
        """
        a CEURLOCTIME with extractable dates, e.g. the em-dash of Vol-3904, is not reported
        """
        for loctime in self.loctime_parsed:
            for report in self.chair_reports(self.temp_dir, {"CEURLOCTIME": loctime}):
                with self.subTest(loctime=loctime, report=report.problems):
                    self.assertEqual([], self.problems(report, "CEURLOCTIME"))

    def test_pubdate_reported(self) -> None:
        """
        a CEURPUBDATE that is not ISO or out of the plausible range is reported by embed and generate
        """
        for pubdate in self.pubdate_not_iso + self.pubdate_out_of_range:
            for report in self.chair_reports(self.temp_dir, {"CEURPUBDATE": pubdate}):
                with self.subTest(pubdate=pubdate, report=report.problems):
                    self.assertEqual(1, len(self.problems(report, "CEURPUBDATE")))

    def test_pubdate_plausible(self) -> None:
        """
        the CEURPUBDATE of the chair page of Vol-4298 is not reported
        """
        for report in self.chair_reports(self.temp_dir, {}):
            with self.subTest(report=report.problems):
                self.assertEqual([], self.problems(report, "CEURPUBDATE"))
                self.assertEqual([], self.problems(report, "CEURLOCTIME"))
