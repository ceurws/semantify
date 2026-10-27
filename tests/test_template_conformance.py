"""
Created on 2026-10-27

@author: wf
"""

import json
import os
import re
import shutil
import tempfile
from typing import Any, Dict, List, Optional

from ceursemantify.ceursemantify_cmd import main
from tests.base_ceurtest import BaseCeurTest


class TestTemplateConformance(BaseCeurTest):
    """
    issue 54: the volume page generated from a chair page carries every
    mark of the Vol-XXX template that the chair page carries
    """

    mark_pattern = re.compile(r'class="(CEUR[A-Z]+)"')

    def setUp(self, debug: bool = False, profile: bool = True) -> None:
        BaseCeurTest.setUp(self, debug=debug, profile=profile)
        self.temp_dir = tempfile.mkdtemp(prefix="template-conformance-")
        self.template_marks = sorted(set(self.marks(self.read_page(os.path.join(self.examples_path, "Vol-XXX.html")))))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def read_page(self, path: str) -> str:
        """
        read the html page at the given path

        Args:
            path: the path of the page

        Returns:
            str: the page content
        """
        with open(path, "r", encoding="utf-8") as page_file:
            page = page_file.read()
        return page

    def marks(self, page: str) -> List[str]:
        """
        get the CEUR marks of the given page in document order

        Args:
            page: the html of the page

        Returns:
            List[str]: the class names of the marks
        """
        marks = self.mark_pattern.findall(page)
        return marks

    def mark_values(self, page: str, mark: str) -> List[str]:
        """
        get the texts of the given mark on the given page

        Args:
            page: the html of the page
            mark: the class name of the mark

        Returns:
            List[str]: the stripped texts of the spans with this mark
        """
        values = [value.strip() for value in re.findall(rf'<span[^>]*class="{mark}"[^>]*>([^<]*)</span>', page)]
        return values

    def generate(self, volume: str, colocated: Optional[str] = None) -> Dict[str, str]:
        """
        embed and generate the volume page in place from the chair page of the
        example, the page without its CEURSTATE line and without index.jsonld

        Args:
            volume: the volume directory name in the examples, e.g. Vol-4298
            colocated: if given, the co-located line of the chair page is replaced by
                the template line with this CEURCOLOCATED text

        Returns:
            Dict[str, str]: the chair page, the generated page and its index.jsonld
        """
        volume_dir = os.path.join(self.temp_dir, volume)
        os.makedirs(volume_dir)
        example_page = self.read_page(os.path.join(self.examples_path, volume, "index.html"))
        chair_page = re.sub(r"<!-- CEURSTATE=[^\n]*-->\n", "", example_page)
        if colocated is not None:
            chair_page = re.sub(
                r'[^\n]*<span class="CEURCOLOCATED">[^<]*</span>\)?',
                f'co-located with <span class="CEURCOLOCATED">{colocated}</span>',
                chair_page,
            )
        page_path = os.path.join(volume_dir, "index.html")
        with open(page_path, "w", encoding="utf-8") as page_file:
            page_file.write(chair_page)
        main(["--embed", volume_dir, "-q"])
        main(["--generate", volume_dir, "--in-place", "-q"])
        pages = {
            "chair": chair_page,
            "generated": self.read_page(os.path.join(volume_dir, "index.html")),
            "jsonld": self.read_page(os.path.join(volume_dir, "index.jsonld")),
        }
        return pages

    def test_colocated_none(self) -> None:
        """
        issue 55: CEURCOLOCATED NONE, the template's value for a volume that is not
        co-located, gives no co-located event in index.jsonld and no co-located line on the page
        """
        pages = self.generate("Vol-4298", colocated="NONE")
        self.assertIn('<span class="CEURCOLOCATED">NONE</span>', pages["chair"])
        self.assertNotIn("colocated_with", self.event_of(pages["jsonld"]))
        self.assertNotIn("co-located with", pages["generated"])
        self.assertNotIn("CEURCOLOCATED", pages["generated"])

    def test_colocated_kept(self) -> None:
        """
        a real CEURCOLOCATED acronym stays a co-located event on the page
        """
        pages = self.generate("Vol-4298")
        self.assertIn('<span class="CEURCOLOCATED">ICL-GNSS 2026</span>', pages["chair"])
        self.assertEqual("ICL-GNSS 2026", self.event_of(pages["jsonld"])["colocated_with"]["acronym"])
        self.assertIn('co-located with <span class="CEURCOLOCATED">ICL-GNSS 2026</span>', pages["generated"])

    def event_of(self, jsonld_text: str) -> Dict[str, Any]:
        """
        get the event node of the given index.jsonld text

        Args:
            jsonld_text: the JSON-LD of the volume

        Returns:
            Dict[str, Any]: the event of the proceedings
        """
        document = json.loads(jsonld_text)
        proceedings = document["@graph"][0] if "@graph" in document else document
        event = proceedings["event"]
        return event

    def test_template_has_18_marks(self) -> None:
        """
        the Vol-XXX template of ceur-ws.org defines 18 marks
        """
        self.assertEqual(18, len(self.template_marks), self.template_marks)

    def test_marks_kept(self) -> None:
        """
        every template mark of the chair page of Vol-4298 is on the generated page
        """
        pages = self.generate("Vol-4298")
        chair_marks = set(self.marks(pages["chair"])) & set(self.template_marks)
        generated_marks = set(self.marks(pages["generated"]))
        missing = sorted(chair_marks - generated_marks)
        self.assertEqual([], missing)

    def test_mark_values_kept(self) -> None:
        """
        the single valued marks volume title and paper counts and the
        session names of the chair page of Vol-4298 keep their texts
        """
        pages = self.generate("Vol-4298")
        for mark in ["CEURVOLTITLE", "CEURSUBMITTEDPAPERS", "CEURACCEPTEDPAPERS", "CEURSESSION"]:
            with self.subTest(mark=mark):
                expected = self.mark_values(pages["chair"], mark)
                self.assertGreater(len(expected), 0, f"chair page of Vol-4298 has no {mark}")
                self.assertEqual(expected, self.mark_values(pages["generated"], mark))
