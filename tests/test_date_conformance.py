"""
Created on 2026-10-27

@author: wf
"""

import os
import re
import shutil
import tempfile
from typing import List

from ceursemantify.site import SiteReport
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
        with open(os.path.join(self.examples_path, "Vol-4298", "index.html"), "r", encoding="utf-8") as page_file:
            self.chair_page = re.sub(r"<!-- CEURSTATE=[^\n]*-->\n", "", page_file.read())
        self.count = 0

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def chair_volume(self, loctime: str = None, pubdate: str = None) -> str:
        """
        write a chair page of Vol-4298 with the given marks replaced

        Args:
            loctime: the CEURLOCTIME text, the original if None
            pubdate: the CEURPUBDATE text, the original if None

        Returns:
            str: the volume directory
        """
        page = self.chair_page
        if loctime is not None:
            page = re.sub(r'(<span class="CEURLOCTIME">)[^<]*(</span>)', rf"\g<1>{loctime}\g<2>", page)
        if pubdate is not None:
            page = re.sub(r'(<span class="CEURPUBDATE">)[^<]*(</span>)', rf"\g<1>{pubdate}\g<2>", page)
        self.count += 1
        volume_dir = os.path.join(self.temp_dir, f"case{self.count}", "Vol-4298")
        os.makedirs(volume_dir)
        with open(os.path.join(volume_dir, "index.html"), "w", encoding="utf-8") as page_file:
            page_file.write(page)
        return volume_dir

    def reports(self, loctime: str = None, pubdate: str = None) -> List[SiteReport]:
        """
        embed and generate a chair page of Vol-4298 with the given marks replaced,
        each from its own copy of the chair page

        Args:
            loctime: the CEURLOCTIME text, the original if None
            pubdate: the CEURPUBDATE text, the original if None

        Returns:
            List[SiteReport]: the reports of embed and generate
        """
        generator = self.get_generator(os.path.join(self.temp_dir, "site"))
        embed_report = generator.embed_volumes([self.chair_volume(loctime, pubdate)])
        generate_report = generator.generate_paths([self.chair_volume(loctime, pubdate)])
        reports = [embed_report, generate_report]
        return reports

    def problems(self, report: SiteReport, mark: str) -> List[str]:
        """
        get the problems of the given report that name the given mark

        Args:
            report: the report
            mark: the CEUR mark

        Returns:
            List[str]: the problems
        """
        problems = [problem for problem in report.problems if f"{mark}:" in problem]
        return problems

    def test_loctime_reported(self) -> None:
        """
        a CEURLOCTIME without extractable dates is reported by embed and generate
        """
        for loctime in self.loctime_unparsed:
            for report in self.reports(loctime=loctime):
                with self.subTest(loctime=loctime, report=report.problems):
                    self.assertEqual(1, len(self.problems(report, "CEURLOCTIME")))

    def test_loctime_parsed(self) -> None:
        """
        a CEURLOCTIME with extractable dates, e.g. the em-dash of Vol-3904, is not reported
        """
        for loctime in self.loctime_parsed:
            for report in self.reports(loctime=loctime):
                with self.subTest(loctime=loctime, report=report.problems):
                    self.assertEqual([], self.problems(report, "CEURLOCTIME"))

    def test_pubdate_reported(self) -> None:
        """
        a CEURPUBDATE that is not ISO or out of the plausible range is reported by embed and generate
        """
        for pubdate in self.pubdate_not_iso + self.pubdate_out_of_range:
            for report in self.reports(pubdate=pubdate):
                with self.subTest(pubdate=pubdate, report=report.problems):
                    self.assertEqual(1, len(self.problems(report, "CEURPUBDATE")))

    def test_pubdate_plausible(self) -> None:
        """
        the CEURPUBDATE of the chair page of Vol-4298 is not reported
        """
        for report in self.reports():
            with self.subTest(report=report.problems):
                self.assertEqual([], self.problems(report, "CEURPUBDATE"))
                self.assertEqual([], self.problems(report, "CEURLOCTIME"))
