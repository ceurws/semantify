"""
Created on 2026-10-01

@author: wf
"""

import json
import os
import tempfile
import time
from typing import Any, Dict

from ceursemantify.ceursemantify_cmd import main
from ceursemantify.model import Proceedings
from ceursemantify.site import CeurSpt, VolumeRanges
from tests.base_ceurtest import BaseCeurTest


class FixedRecordSpt(CeurSpt):
    """
    a source that serves the same given record for every volume number
    """

    def __init__(self, record: Dict[str, Any]):
        """
        constructor

        Args:
            record: the record to serve
        """
        super().__init__("file:///fixed")
        self.record = record

    def volume_record(self, number: int) -> Dict[str, Any]:
        """
        get the fixed record

        Args:
            number: the volume number, not used

        Returns:
            Dict[str, Any]: the record
        """
        record = self.record
        return record


class TestGenerator(BaseCeurTest):
    """
    test the generation of volume pages and the rebuild of year pages
    """

    def test_volume_ranges(self) -> None:
        """
        test numbers and ranges of volumes
        """
        self.assertEqual([3889], VolumeRanges.numbers(["3889"]))
        self.assertEqual([3887, 3888, 3889, 4175], VolumeRanges.numbers(["3887-3889", "4175", "3888"]))
        for wrong in ["Vol-3889", "3889-3887", "1-2-3", ""]:
            with self.subTest(wrong=wrong):
                with self.assertRaises(ValueError):
                    VolumeRanges.numbers([wrong])

    def test_generate_volumes(self) -> None:
        """
        test that volumes are written into the year of their event, that a
        volume that is not available is reported and that no year page is written
        """
        with tempfile.TemporaryDirectory() as output_dir:
            generator = self.get_generator(output_dir)
            report = generator.generate_volumes([3887, 3888, 3889, 4175])
            # page and JSON-LD for 3 volumes and their 24, 8 and 7 papers
            self.assertEqual(2 * 3 + 2 * (24 + 8 + 7), len(report.written))
            self.assertEqual(1, len(report.problems), report.problems)
            self.assertTrue(report.problems[0].startswith("Vol-3888:"))
            for number in [3887, 3889, 4175]:
                volume_dir = os.path.join(output_dir, str(self.example_years[number]), f"Vol-{number}")
                self.assertTrue(os.path.isfile(os.path.join(volume_dir, "index.html")))
                self.assertTrue(os.path.isfile(os.path.join(volume_dir, "index.jsonld")))
                self.assertTrue(generator.round_trip(volume_dir))
            self.assertFalse(os.path.exists(os.path.join(output_dir, "2024", "index.html")))

    def test_paper_pages(self) -> None:
        """
        test the landing pages of the papers of a volume: one per paper,
        linked from the table of contents with the anchor kept, round trip,
        links to the neighbouring papers
        """
        with tempfile.TemporaryDirectory() as output_dir:
            generator = self.get_generator(output_dir)
            generator.generate_volumes([3889])
            volume_dir = os.path.join(output_dir, "2024", "Vol-3889")
            with open(os.path.join(volume_dir, "index.html"), "r", encoding="utf-8") as page_file:
                volume_page = page_file.read()
            for index in range(8):
                paper_dir = os.path.join(volume_dir, f"paper{index}")
                self.assertTrue(generator.round_trip(paper_dir), paper_dir)
                self.assertIn(f'<li id="paper{index}"><a href="paper{index}/">', volume_page)
            with open(os.path.join(volume_dir, "paper1", "index.html"), "r", encoding="utf-8") as page_file:
                paper_page = page_file.read()
            self.assertIn("../paper0/", paper_page)
            self.assertIn("../paper2/", paper_page)
            self.assertIn("https://dblp.org/pid/32/7870", paper_page)
            with open(os.path.join(volume_dir, "paper1", "index.jsonld"), "r", encoding="utf-8") as jsonld_file:
                paper = self.jsonld.paper(json.load(jsonld_file))
            self.assertEqual("Kepler-aSI : Semantic Annotation for Tabular Data", paper.title)
            self.assertEqual("http://ceur-ws.org/Vol-3889/", paper.publishedIn)

    def test_no_event_date(self) -> None:
        """
        test that a volume without event start date is written into the year
        of its publication date, marked as inferred, see issue 78, and that a
        volume without any date is not written but reported
        """
        record = self.example_record(3889)
        del record["ceur:event"]["ceur:conference_date_start"]
        with tempfile.TemporaryDirectory() as output_dir:
            generator = self.get_generator(output_dir)
            generator.spt = FixedRecordSpt(record)
            report = generator.generate_volumes([3889])
            self.assertTrue(report.written)
            self.assertEqual(1, len(report.problems))
            self.assertIn("Vol-3889: no event start date, year", report.problems[0])
            self.assertIn("inferred from pubDate", report.problems[0])
            year = int(record["ceur:publication_date"][:4])
            jsonld_path = os.path.join(output_dir, str(year), "Vol-3889", "index.jsonld")
            with open(jsonld_path, "r", encoding="utf-8") as jsonld_file:
                proceedings = self.jsonld.proceedings(json.load(jsonld_file))
            self.assertEqual(year, proceedings.inferredYear)
            self.assertEqual("pubDate", proceedings.inferredYearSource)
            self.assertEqual(year, proceedings.year())
        for key in ("ceur:publication_date", "ceur:publication_year"):
            record.pop(key, None)
        with tempfile.TemporaryDirectory() as output_dir:
            generator = self.get_generator(output_dir)
            generator.spt = FixedRecordSpt(record)
            report = generator.generate_volumes([3889])
            self.assertEqual([], report.written)
            self.assertEqual(["Vol-3889: no event start date, the volume has no year"], report.problems)

    def test_infer_year_from_files(self) -> None:
        """
        test that the year of a volume without any date is taken from the
        modification time of index.html.orig, else of the oldest file of the
        volume directory, see issue 78
        """
        with tempfile.TemporaryDirectory() as volume_dir:
            page = os.path.join(volume_dir, "index.html")
            orig = os.path.join(volume_dir, "index.html.orig")
            for path in (page, orig):
                with open(path, "w", encoding="utf-8") as file:
                    file.write("<html></html>")
            os.utime(page, (time.mktime((2003, 6, 1, 0, 0, 0, 0, 0, -1)),) * 2)
            os.utime(orig, (time.mktime((2005, 6, 1, 0, 0, 0, 0, 0, -1)),) * 2)
            proceedings = Proceedings()
            self.assertEqual(2005, proceedings.infer_year(volume_dir))
            self.assertEqual("index.html.orig mtime", proceedings.inferredYearSource)
            os.remove(orig)
            proceedings = Proceedings()
            self.assertEqual(2003, proceedings.infer_year(volume_dir))
            self.assertEqual("oldest file mtime", proceedings.inferredYearSource)
            self.assertIsNone(Proceedings().infer_year(None))

    def test_rebuild_year(self) -> None:
        """
        test that the year page lists the volumes present, the highest number
        first, and links to the neighbouring years that exist
        """
        with tempfile.TemporaryDirectory() as output_dir:
            generator = self.get_generator(output_dir)
            generator.generate_volumes(list(self.example_years.keys()))
            years = generator.site.years()
            self.assertEqual([2023, 2024, 2025, 2026], years)
            pages = {}
            for year in years:
                report = generator.rebuild_year(year)
                self.assertEqual([], report.problems)
                with open(report.written[0], "r", encoding="utf-8") as page_file:
                    pages[year] = page_file.read()
            self.assertLess(pages[2024].index("Vol-4175/"), pages[2024].index("Vol-3889/"))
            self.assertIn("../2023/", pages[2024])
            self.assertIn("../2025/", pages[2024])
            self.assertNotIn("../2022/", pages[2023])
            self.assertNotIn("../2027/", pages[2026])
            regenerate_report = generator.regenerate_year(2024)
            self.assertEqual([], regenerate_report.problems)
            # two volumes with 8 and 7 papers and the year page
            self.assertEqual(2 * 2 + 2 * (8 + 7) + 1, len(regenerate_report.written))
            empty_report = generator.rebuild_year(2020)
            self.assertEqual([], empty_report.written)
            self.assertEqual(1, len(empty_report.problems))

    def test_comment_end(self) -> None:
        """
        test that a comment end in a title does not break the fence
        """
        with tempfile.TemporaryDirectory() as output_dir:
            generator = self.get_generator(output_dir)
            proceedings = self.example_proceedings(3889)
            proceedings.title = "arrow --> title"
            report = generator.generate_volumes([])
            generator.write_volume(proceedings, report)
            volume_dir = generator.site.volume_dir(proceedings)
            self.assertTrue(generator.round_trip(volume_dir))
            from_file = generator.site.read_proceedings(os.path.join(volume_dir, "index.jsonld"))
            self.assertEqual("arrow --> title", from_file.title)

    def test_cmd(self) -> None:
        """
        test the command line: volumes first, the year as a separate call
        """
        with tempfile.TemporaryDirectory() as output_dir:
            config_path = os.path.join(output_dir, "site.yaml")
            config = self.get_generator(output_dir).config
            config.save_to_yaml_file(config_path)
            exit_code = main(["3889", "4175", "-o", output_dir, "--config", config_path, "--quiet"])
            self.assertEqual(0, exit_code)
            self.assertFalse(os.path.exists(os.path.join(output_dir, "2024", "index.html")))
            exit_code = main(["--year", "2024", "-o", output_dir, "--config", config_path, "--quiet"])
            self.assertEqual(0, exit_code)
            self.assertTrue(os.path.isfile(os.path.join(output_dir, "2024", "index.html")))
