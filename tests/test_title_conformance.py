"""
Created on 2026-10-27

@author: wf
"""

import shutil
import tempfile

from tests.base_ceurtest import BaseCeurTest


class TestTitleConformance(BaseCeurTest):
    """
    issue 22: --embed and --generate report a CEURFULLTITLE that names the
    edition neither by year nor by ordinal
    """

    # full titles that name the edition
    titles_named = [
        # Vol-4298
        "Proceedings of the Work-in-Progress in Hardware and Software for Location Computation Workshop (WIPHAL 2026)",
        # the Vol-XXX template
        "Proceedings of the 7th Workshop on Publishing Papers with CEUR-WS (NNNN YYYY)",
        "Proceedings of the 1st Workshop on Practical Aspects of Automated Reasoning",
        "Proceedings of the 22nd Workshop on Practical Aspects of Automated Reasoning",
        "Proceedings of the 23rd Workshop on Practical Aspects of Automated Reasoning",
        "Proceedings of the Workshop on Practical Aspects of Automated Reasoning 2026",
    ]
    # full titles without year and ordinal
    titles_unnamed = [
        # Vol-4241 and Vol-3201, the case of the ticket
        "Proceedings of the Workshop on Practical Aspects of Automated Reasoning",
        "Proceedings of the Workshop on Practical Aspects of Automated Reasoning (PAAR)",
    ]

    def setUp(self, debug: bool = False, profile: bool = True) -> None:
        BaseCeurTest.setUp(self, debug=debug, profile=profile)
        self.temp_dir = tempfile.mkdtemp(prefix="title-conformance-")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_title_reported(self) -> None:
        """
        a full title without year and ordinal is reported by embed and generate
        """
        for title in self.titles_unnamed:
            for report in self.chair_reports(self.temp_dir, {"CEURFULLTITLE": title}):
                with self.subTest(title=title, report=report.problems):
                    self.assertEqual(1, len(self.problems(report, "CEURFULLTITLE")))

    def test_title_named(self) -> None:
        """
        a full title with a year or an ordinal is not reported
        """
        for title in self.titles_named:
            for report in self.chair_reports(self.temp_dir, {"CEURFULLTITLE": title}):
                with self.subTest(title=title, report=report.problems):
                    self.assertEqual([], self.problems(report, "CEURFULLTITLE"))
