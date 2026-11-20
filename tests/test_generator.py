"""
Created on 2026-10-01

@author: wf
"""

import json
import os
import tempfile
from typing import Any, Dict

from ceursemantify.ceursemantify_cmd import main
from ceursemantify.pages import YearPage
from ceursemantify.site import CeurSpt, VolumeRanges
from ceursemantify.year_rule import YearRule
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
        test that volumes are written into the year of their publication, that a
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
            self.assertFalse(os.path.exists(os.path.join(output_dir, "2025", "index.html")))

    def test_paper_pages(self) -> None:
        """
        test the landing pages of the papers of a volume: one per paper,
        linked from the table of contents with the anchor kept, round trip,
        links to the neighbouring papers
        """
        with tempfile.TemporaryDirectory() as output_dir:
            generator = self.get_generator(output_dir)
            generator.generate_volumes([3889])
            volume_dir = os.path.join(output_dir, str(self.example_years[3889]), "Vol-3889")
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

    def test_publication_year(self) -> None:
        """
        test that a volume is written into the year of its publication date,
        not of its event, see issue 78; that a publication date outside the
        range of CEUR-WS falls to the next source of the year rule and the year
        is marked inferred with its source; that the copy of the volume in
        another year is removed and that a volume without any year is not
        written but reported
        """
        record = self.example_record(3889)
        event_year = int(record["ceur:event"]["ceur:conference_date_start"][:4])
        year = int(record["ceur:publication_date"][:4])
        self.assertNotEqual(event_year, year)
        with tempfile.TemporaryDirectory() as output_dir:
            generator = self.get_generator(output_dir)
            generator.spt = FixedRecordSpt(record)
            report = generator.generate_volumes([3889])
            self.assertTrue(report.written)
            self.assertEqual([], report.problems)
            self.assertTrue(os.path.isfile(os.path.join(output_dir, str(year), "Vol-3889", "index.jsonld")))
            self.assertFalse(os.path.exists(os.path.join(output_dir, str(event_year))))
            generator.rebuild_year(year)
            record["ceur:publication_date"] = "2104-10-15"
            record.pop("ceur:publication_year", None)
            volumes_json = os.path.join(output_dir, "volumes.json")
            with open(volumes_json, "w", encoding="utf-8") as json_file:
                json.dump([{"number": 3889, "published": "2023-12-30"}], json_file)
            generator.year_rule = YearRule(volumes_json)
            report = generator.generate_volumes([3889])
            self.assertEqual(["Vol-3889: year 2023 inferred from volume browser"], report.problems)
            jsonld_path = os.path.join(output_dir, "2023", "Vol-3889", "index.jsonld")
            with open(jsonld_path, "r", encoding="utf-8") as jsonld_file:
                proceedings = self.jsonld.proceedings(json.load(jsonld_file))
            self.assertEqual(2023, proceedings.inferredYear)
            self.assertEqual("volume browser", proceedings.inferredYearSource)
            self.assertEqual(2023, proceedings.year())
            # the volume is in one year only, a year without volumes has no directory
            self.assertFalse(os.path.exists(os.path.join(output_dir, str(year))))
            self.assertEqual([2023], generator.site.years())
        proceedings = self.mapper.map_record(record, "Proceedings").target
        self.assertIsNone(proceedings.year())
        with tempfile.TemporaryDirectory() as output_dir:
            generator = self.get_generator(output_dir)
            generator.spt = FixedRecordSpt(record)
            report = generator.generate_volumes([3889])
            self.assertEqual([], report.written)
            self.assertEqual(["Vol-3889: no publication year, the volume has no year"], report.problems)

    def test_rebuild_year(self) -> None:
        """
        test that the year page lists the volumes present, the highest number
        first, and links to the neighbouring years that exist
        """
        with tempfile.TemporaryDirectory() as output_dir:
            generator = self.get_generator(output_dir)
            generator.generate_volumes(list(self.example_years.keys()))
            years = generator.site.years()
            self.assertEqual([2024, 2025, 2026], years)
            pages = {}
            for year in years:
                report = generator.rebuild_year(year)
                self.assertEqual([], report.problems)
                with open(report.written[0], "r", encoding="utf-8") as page_file:
                    pages[year] = page_file.read()
            self.assertLess(pages[2026].index("Vol-4184/"), pages[2026].index("Vol-4175/"))
            self.assertIn("../2024/", pages[2025])
            self.assertIn("../2026/", pages[2025])
            self.assertNotIn("../2023/", pages[2024])
            self.assertNotIn("../2027/", pages[2026])
            # the neighbours are the previous and next year that have a page, also across a gap
            year_page = YearPage(2024, [], [2020, 2024, 2026], generator.config, generator.state)
            navigation = year_page.navigation_as_html()
            self.assertIn('href="../2020/" rel="prev"', navigation)
            self.assertIn('href="../2026/" rel="next"', navigation)
            self.assertNotIn("../2023/", navigation)
            regenerate_report = generator.regenerate_year(2025)
            self.assertEqual([], regenerate_report.problems)
            # one volume with 8 papers and the year page
            self.assertEqual(2 * 1 + 2 * 8 + 1, len(regenerate_report.written))
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
        test the command line: volumes first, the year as a separate call that
        also writes the overview of the years
        """
        with tempfile.TemporaryDirectory() as output_dir:
            config_path = os.path.join(output_dir, "site.yaml")
            config = self.get_generator(output_dir).config
            config.save_to_yaml_file(config_path)
            exit_code = main(["3889", "4175", "-o", output_dir, "--config", config_path, "--quiet"])
            self.assertEqual(0, exit_code)
            self.assertFalse(os.path.exists(os.path.join(output_dir, "2025", "index.html")))
            exit_code = main(["--year", "2025", "-o", output_dir, "--config", config_path, "--quiet"])
            self.assertEqual(0, exit_code)
            self.assertTrue(os.path.isfile(os.path.join(output_dir, "2025", "index.html")))
            # every --year call rewrites the overview of the years, see issue 81
            with open(os.path.join(output_dir, "years", "index.html"), "r", encoding="utf-8") as page_file:
                overview = page_file.read()
            self.assertIn('<a href="../2025/">2025</a>', overview)
            self.assertIn('<a href="../2026/">2026</a>', overview)
            self.assertLess(overview.index("../2026/"), overview.index("../2025/"))
            self.assertIn("Vol-3889", overview)
            self.assertIn("2 volumes in 2 years", overview)
            with open(os.path.join(output_dir, "2025", "index.html"), "r", encoding="utf-8") as page_file:
                self.assertIn('<a href="../years/">all years</a>', page_file.read())
