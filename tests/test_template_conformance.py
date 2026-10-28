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
from unittest.mock import patch

from ceursemantify.ceursemantify_cmd import main
from ceursemantify.index_check import IndexCheck
from ceursemantify.model import Proceedings
from ceursemantify.pages import VolumePage
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
        co-located, gives no co-located event in index.jsonld and no visible co-located line;
        the page keeps the CEURCOLOCATED tag in the comment line of the Vol-XXX template,
        which check-index-errors A44 prescribes
        """
        pages = self.generate("Vol-4298", colocated="NONE")
        self.assertIn('<span class="CEURCOLOCATED">NONE</span>', pages["chair"])
        self.assertNotIn("colocated_with", self.event_of(pages["jsonld"]))
        visible = re.sub(r"<!--.*?-->", "", pages["generated"], flags=re.S)
        self.assertNotIn("co-located with", visible)
        self.assertIn('<!-- co-located with <span class="CEURCOLOCATED">NONE</span> -->', pages["generated"])

    def with_index_check(self) -> None:
        """
        put the check-index-errors of scripts on the PATH, skip where it can not run
        """
        scripts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
        env_patch = patch.dict(os.environ, {"PATH": scripts_dir + os.pathsep + os.environ.get("PATH", "")})
        env_patch.start()
        self.addCleanup(env_patch.stop)
        probe = IndexCheck("check-index-errors").run(os.path.join(self.examples_path, "Vol-4298"))
        if not probe.ran:
            self.skipTest(f"check-index-errors does not run here: {probe.output.strip()[:80]}")

    def test_gate_passes(self) -> None:
        """
        issue 62: the 0.0.6 page of the Vol-4298 chair page adds no report of
        check-index-errors to those of the chair page, so it replaces the chair page
        """
        self.with_index_check()
        pages = self.generate("Vol-4298")
        self.assertIn("CEURSTATE=generated", pages["generated"])
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, "Vol-4298", "index.html.rejected")))

    def test_gate_rejects(self) -> None:
        """
        issue 62: a page that loses CEURVOLTITLE as 0.0.4 did is reported by
        check-index-errors, the chair page is kept and the generated page set aside
        """
        self.with_index_check()
        title_as_html = VolumePage.title_as_html

        def without_voltitle(page: VolumePage) -> str:
            return re.sub(r'<br>\n    <span class="CEURVOLTITLE">[^<]*</span>', "", title_as_html(page))

        with patch.object(VolumePage, "title_as_html", without_voltitle):
            pages = self.generate("Vol-4298")
        volume_dir = os.path.join(self.temp_dir, "Vol-4298")
        # the page kept is the chair page as --embed left it
        self.assertIn("CEURSTATE=embedded", pages["generated"])
        self.assertIn('class="CEURVOLTITLE"', pages["generated"])
        self.assertNotIn("CEURVOLTITLE", self.read_page(os.path.join(volume_dir, "index.html.rejected")))
        self.assertIn("ERROR (A17)", self.read_page(os.path.join(volume_dir, "index.html.rejected.txt")))

    def test_no_blank_before_closing_span(self) -> None:
        """
        issue 61: no line of the generated page matches rule 27 of check-index-errors-after,
        A20 of check-index-errors, as the rule is written, line by line
        """
        rule_27 = re.compile(r'class="CEUR(?!TOC)[^"]*">\s+|\s+</span>')
        pages = self.generate("Vol-4298")
        hits = [line for line in pages["generated"].split("\n") if rule_27.search(line)]
        self.assertEqual([], hits)

    def test_version_and_submission(self) -> None:
        """
        issue 63: the generated page keeps the CEURVERSION comment and the submitted by
        footer of the chair page, check-index-errors A17 and A28; the record holds both
        """
        pages = self.generate("Vol-4298")
        self.assertIn("<!-- CEURVERSION=2026-02-04 -->", pages["chair"])
        self.assertIn("<!-- CEURVERSION=2026-02-04 -->", pages["generated"])
        self.assertIn("2026-10-18: submitted by Jari Nurmi,", pages["generated"])
        self.assertIn("Creative Commons CC0", pages["generated"])
        record = json.loads(pages["jsonld"])
        proceedings = record if "templateVersion" in record else record.get("@graph", [record])[0]
        self.assertEqual("2026-02-04", proceedings["templateVersion"])
        self.assertEqual("2026-10-18", proceedings["dateSubmitted"])
        self.assertEqual("Jari Nurmi", proceedings["submittedBy"])

    def test_colocated_kept(self) -> None:
        """
        a real CEURCOLOCATED acronym stays a co-located event on the page
        """
        pages = self.generate("Vol-4298")
        self.assertIn('<span class="CEURCOLOCATED">ICL-GNSS 2026</span>', pages["chair"])
        self.assertEqual("ICL-GNSS 2026", self.event_of(pages["jsonld"])["colocated_with"]["acronym"])
        self.assertIn('co-located with <span class="CEURCOLOCATED">ICL-GNSS 2026</span>', pages["generated"])

    def test_yaml_record(self) -> None:
        """
        issue 59: --embed --yaml writes index.yaml next to index.jsonld with the
        yamlable standard of the model, and --generate --yaml takes an edit of the
        yaml to the page and to index.jsonld
        """
        volume_dir = os.path.join(self.temp_dir, "Vol-4298")
        os.makedirs(volume_dir)
        example_page = self.read_page(os.path.join(self.examples_path, "Vol-4298", "index.html"))
        with open(os.path.join(volume_dir, "index.html"), "w", encoding="utf-8") as page_file:
            page_file.write(re.sub(r"<!-- CEURSTATE=[^\n]*-->\n", "", example_page))
        main(["--embed", volume_dir, "--yaml", "-q"])
        yaml_path = os.path.join(volume_dir, "index.yaml")
        self.assertTrue(os.path.isfile(yaml_path))
        from_yaml = Proceedings.load_from_yaml_file(yaml_path)
        from_jsonld = self.jsonld.proceedings(json.loads(self.read_page(os.path.join(volume_dir, "index.jsonld"))))
        self.assertEqual(from_jsonld, from_yaml)
        # the human's correction: the volume is co-located with another event
        from_yaml.event.colocated_with.acronym = "ICL-GNSS 2027"
        from_yaml.save_to_yaml_file(yaml_path)
        main(["--generate", volume_dir, "--yaml", "--in-place", "-q"])
        page = self.read_page(os.path.join(volume_dir, "index.html"))
        self.assertIn('co-located with <span class="CEURCOLOCATED">ICL-GNSS 2027</span>', page)
        event = self.event_of(self.read_page(os.path.join(volume_dir, "index.jsonld")))
        self.assertEqual("ICL-GNSS 2027", event["colocated_with"]["acronym"])

    def test_paper_url(self) -> None:
        """
        issue 32: every paper of the record has paperUrl, the landing page of the
        paper under the volume, as its identity next to pdfUrl, the file; in
        index.jsonld and in index.yaml
        """
        volume_dir = os.path.join(self.temp_dir, "Vol-4298")
        os.makedirs(volume_dir)
        with open(os.path.join(volume_dir, "index.html"), "w", encoding="utf-8") as page_file:
            page_file.write(self.chair_page())
        main(["--embed", volume_dir, "--yaml", "-q"])
        document = json.loads(self.read_page(os.path.join(volume_dir, "index.jsonld")))
        proceedings = document["@graph"][0] if "@graph" in document else document
        self.assertGreater(len(proceedings["papers"]), 0)
        for paper in proceedings["papers"]:
            with self.subTest(paper=paper["id"]):
                paper_url = f"https://ceur-ws.org/Vol-4298/{paper['id']}/"
                self.assertEqual(paper_url, paper["paperUrl"])
                self.assertEqual(paper_url, paper["@id"])
                self.assertEqual(f"https://ceur-ws.org/Vol-4298/{paper['id']}.pdf", paper["pdfUrl"])
        from_yaml = Proceedings.load_from_yaml_file(os.path.join(volume_dir, "index.yaml"))
        self.assertEqual(
            [paper["paperUrl"] for paper in proceedings["papers"]], [paper.paperUrl for paper in from_yaml.papers]
        )

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
