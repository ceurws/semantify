"""
Created on 2026-10-26

@author: wf
"""

import json
import os
import re
import shutil
import tempfile

from ceursemantify.ceursemantify_cmd import main
from tests.base_ceurtest import BaseCeurTest


class TestBoardReview(BaseCeurTest):
    """
    page template defects found by the ceurws-board review of the DOI test
    volumes, milestone 0.0.4: the generated volume page keeps the ORCIDs of
    its record (issue 51), the copyright text and the line break after the
    title follow the Vol-XXX template (issue 44)
    """

    def setUp(self, debug: bool = False, profile: bool = True) -> None:
        BaseCeurTest.setUp(self, debug=debug, profile=profile)
        self.example_dir = os.path.join(self.examples_path, "Vol-4298")
        self.temp_dir = tempfile.mkdtemp(prefix="board-review-")
        self.volume_dir = os.path.join(self.temp_dir, "Vol-4298")
        shutil.copytree(self.example_dir, self.volume_dir)
        with open(os.path.join(self.volume_dir, "index.jsonld"), "r", encoding="utf-8") as record_file:
            self.record = json.load(record_file)
        main(["--generate", self.volume_dir, "--in-place", "-q"])
        with open(os.path.join(self.volume_dir, "index.html"), "r", encoding="utf-8") as page_file:
            self.page = page_file.read()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def record_orcids(self) -> list:
        """
        get the ORCIDs of the editors and authors of the record

        Returns:
            list: the ORCIDs in the order of the record
        """
        orcids = []
        proceedings = self.record["@graph"][0] if "@graph" in self.record else self.record
        scholars = list(proceedings.get("editors", []))
        for paper in proceedings.get("papers", []):
            scholars.extend(paper.get("authors", []))
        for scholar in scholars:
            orcid = scholar.get("orcid")
            if orcid:
                orcids.append(orcid)
        return orcids

    def test_orcids_on_the_volume_page(self) -> None:
        """
        issue 51: every ORCID of the record is on the generated page as the
        itemid of the CEURAUTHOR or CEURVOLEDITOR span, the markup of the
        Vol-XXX template that dblp reads
        """
        orcids = self.record_orcids()
        self.assertGreater(len(orcids), 0, "Vol-4298 example carries no ORCIDs")
        pattern = re.compile(
            r'<span class="(CEURAUTHOR|CEURVOLEDITOR)" itemscope itemtype="https://schema.org/Person" '
            r'itemid="https://orcid.org/([0-9X-]+)">'
        )
        page_orcids = [match.group(2) for match in pattern.finditer(self.page)]
        self.assertEqual(sorted(orcids), sorted(page_orcids))

    def test_copyright_text(self) -> None:
        """
        issue 44 S1: the copyright paragraph names the license as the template does
        """
        self.assertIn("published under the Creative Commons License Attribution 4.0 International", self.page)
        self.assertIn(
            '<a href="https://creativecommons.org/licenses/by/4.0/">(<span class="CEURLIC">CC BY 4.0</span>)</a>.',
            self.page,
        )
        self.assertNotIn('<span class="CEURLIC">https://', self.page)

    def test_line_break_after_title(self) -> None:
        """
        issue 44 S4: the table of contents entry breaks after the title and
        its pages as the template does, the PDF link and the DOI on their own line
        """
        titles = re.findall(r'<span class="CEURTITLE">[^<]*</span></a>', self.page)
        self.assertGreater(len(titles), 0)
        breaks = re.findall(
            r'<span class="CEURTITLE">[^<]*</span></a>( <span class="CEURPAGES">[^<]*</span>)?<br>', self.page
        )
        self.assertEqual(len(titles), len(breaks))
