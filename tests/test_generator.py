"""
Created on 2026-10-01

@author: wf
"""

import glob
import json
import os
import tempfile
from typing import List

from basemkit.basetest import Basetest

from ceursemantify.ceursemantify_cmd import main
from ceursemantify.generator import PageGenerator, Volume


class TestGenerator(Basetest):
    """
    test the generation of year and volume pages from JSON-LD
    """

    def setUp(self, debug: bool = False, profile: bool = True) -> None:
        Basetest.setUp(self, debug=debug, profile=profile)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.examples_path = os.path.join(project_root, "examples")
        self.expected_years = {3887: 2023, 3889: 2024, 4175: 2024, 4184: 2025, 4183: 2026}
        self.generator = PageGenerator(generated_on="2026-10-01")

    def get_volumes(self) -> List[Volume]:
        """
        get the example volumes

        Returns:
            List[Volume]: the volumes of the JSON-LD files in the examples directory
        """
        paths = sorted(glob.glob(os.path.join(self.examples_path, "Vol-*.jsonld")))
        volumes = [Volume.of_file(path) for path in paths]
        return volumes

    def read(self, *path_parts: str) -> str:
        """
        read the file with the given path parts

        Args:
            path_parts: the parts of the path

        Returns:
            str: the content of the file
        """
        with open(os.path.join(*path_parts), "r", encoding="utf-8") as text_file:
            content = text_file.read()
        return content

    def test_year(self) -> None:
        """
        test that the year of a volume is the year of the start date of its event
        """
        volumes = self.get_volumes()
        self.assertEqual(len(self.expected_years), len(volumes))
        for volume in volumes:
            with self.subTest(volume=volume.number):
                self.assertEqual(self.expected_years[volume.number], volume.year)

    def test_generate(self) -> None:
        """
        test the generated directory structure and the year pages
        """
        volumes = self.get_volumes()
        with tempfile.TemporaryDirectory() as output_dir:
            report = self.generator.generate(volumes, output_dir)
            self.assertEqual([2023, 2024, 2025, 2026], report.years)
            self.assertEqual([], report.skipped)
            # two files per volume and one page per year
            self.assertEqual(2 * len(volumes) + len(report.years), len(report.files))
            for number, year in self.expected_years.items():
                volume_dir = os.path.join(output_dir, str(year), f"Vol-{number}")
                self.assertTrue(os.path.isfile(os.path.join(volume_dir, "index.html")))
                self.assertTrue(os.path.isfile(os.path.join(volume_dir, "index.jsonld")))
            page_2024 = self.read(output_dir, "2024", "index.html")
            if self.debug:
                print(page_2024)
            self.assertIn("CEURSTATE=generated: on 2026-10-01 by pyCEURsemantify", page_2024)
            self.assertIn('<a href="../2023/" rel="prev">', page_2024)
            self.assertIn('<a href="../2025/" rel="next">', page_2024)
            # latest volume first
            self.assertLess(page_2024.index('id="Vol-4175"'), page_2024.index('id="Vol-3889"'))
            page_2023 = self.read(output_dir, "2023", "index.html")
            self.assertNotIn('rel="prev"', page_2023)
            page_2026 = self.read(output_dir, "2026", "index.html")
            self.assertNotIn('rel="next"', page_2026)

    def test_volume_page(self) -> None:
        """
        test the content of a generated volume page
        """
        volume = Volume.of_file(os.path.join(self.examples_path, "Vol-3889.jsonld"))
        page = self.generator.volume_page(volume)
        if self.debug:
            print(page)
        self.assertIn("CEURSTATE=generated: on 2026-10-01 by pyCEURsemantify", page)
        self.assertIn("<title>CEUR-WS.org/Vol-3889 - ", page)
        self.assertIn('<span class="CEURVOLNR">Vol-3889</span>', page)
        self.assertIn('<a href="/Vol-3889/paper0.pdf">', page)
        self.assertIn('Year: <a href="../">2024</a>', page)
        self.assertIn("%2F2024%2FVol-3889%2F", page)
        self.assertEqual(8, page.count('class="CEURTITLE"'))
        # titles are single line
        self.assertIn("Semantic Interpretation of Dataless Tables", page)

    def test_round_trip(self) -> None:
        """
        test that the JSON-LD extracted from each generated page equals its input
        """
        volumes = self.get_volumes()
        with tempfile.TemporaryDirectory() as output_dir:
            self.generator.generate(volumes, output_dir)
            for volume in volumes:
                with self.subTest(volume=volume.number):
                    volume_dir = os.path.join(output_dir, str(volume.year), f"Vol-{volume.number}")
                    self.assertTrue(self.generator.round_trip(os.path.join(volume_dir, "index.html"), volume))
                    jsonld = json.loads(self.read(volume_dir, "index.jsonld"))
                    self.assertEqual(volume.jsonld, jsonld)

    def test_comment_end_in_jsonld(self) -> None:
        """
        test that a comment end in the JSON-LD does not break the fence
        """
        volume = Volume.of_file(os.path.join(self.examples_path, "Vol-3889.jsonld"))
        volume.jsonld["ceur:proceedings_title"] = "arrow --> title"
        with tempfile.TemporaryDirectory() as output_dir:
            self.generator.generate([volume], output_dir)
            html_path = os.path.join(output_dir, "2024", "Vol-3889", "index.html")
            page = self.read(html_path)
            fence_start = page.index("<!--\n" + PageGenerator.fence)
            self.assertNotIn("-->", page[fence_start : page.index("\n" + PageGenerator.fence + "\n-->")])
            self.assertTrue(self.generator.round_trip(html_path, volume))

    def test_no_event_date(self) -> None:
        """
        test that a volume without an event start date is skipped and reported
        """
        volume = Volume.of_file(os.path.join(self.examples_path, "Vol-3889.jsonld"))
        del volume.jsonld["ceur:event"]["ceur:conference_date_start"]
        with tempfile.TemporaryDirectory() as output_dir:
            report = self.generator.generate([volume], output_dir)
            self.assertEqual([], report.files)
            self.assertEqual([], report.years)
            self.assertEqual(1, len(report.skipped))

    def test_cmd(self) -> None:
        """
        test the command line interface
        """
        pattern = os.path.join(self.examples_path, "Vol-*.jsonld")
        with tempfile.TemporaryDirectory() as output_dir:
            exit_code = main([pattern, "-o", output_dir, "--quiet"])
            self.assertEqual(0, exit_code)
            self.assertEqual(["2023", "2024", "2025", "2026"], sorted(os.listdir(output_dir)))
