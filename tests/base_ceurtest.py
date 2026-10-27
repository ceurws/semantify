"""
Created on 2026-10-01

@author: wf
"""

import json
import os
import re
import tempfile
from typing import Any, Dict, List

from basemkit.basetest import Basetest

from ceursemantify.generator import Generator
from ceursemantify.jsonld import JsonLd
from ceursemantify.mapper import Mapper
from ceursemantify.model import Proceedings
from ceursemantify.pages import PageState
from ceursemantify.site import CeurSpt, Site, SiteConfig, SiteReport


class BaseCeurTest(Basetest):
    """
    base class for the tests: the example volumes of ceur-spt in the
    examples directory serve as the source, read via file urls
    """

    # volume number -> year of the event
    example_years = {3887: 2023, 3889: 2024, 4175: 2024, 4183: 2026, 4184: 2025}

    def setUp(self, debug: bool = False, profile: bool = True) -> None:
        Basetest.setUp(self, debug=debug, profile=profile)
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.examples_path = os.path.join(self.project_root, "examples")
        self.mapper = Mapper.of_yaml()
        self.jsonld = JsonLd.of_yaml()

    def example_record(self, number: int) -> Dict[str, Any]:
        """
        get the source record of the example volume with the given number

        Args:
            number: the volume number

        Returns:
            Dict[str, Any]: the JSON-LD as served by ceur-spt
        """
        with open(os.path.join(self.examples_path, f"Vol-{number}.jsonld"), "r", encoding="utf-8") as record_file:
            record = json.load(record_file)
        return record

    def example_proceedings(self, number: int) -> Proceedings:
        """
        get the proceedings of the example volume with the given number

        Args:
            number: the volume number

        Returns:
            Proceedings: the mapped proceedings
        """
        proceedings = self.mapper.map_record(self.example_record(number), "Proceedings").target
        return proceedings

    def chair_page(self, number: int = 4298) -> str:
        """
        get the chair page of the example volume with the given number: its
        index.html without the CEURSTATE line

        Args:
            number: the volume number

        Returns:
            str: the html of the chair page
        """
        with open(os.path.join(self.examples_path, f"Vol-{number}", "index.html"), "r", encoding="utf-8") as page_file:
            chair_page = re.sub(r"<!-- CEURSTATE=[^\n]*-->\n", "", page_file.read())
        return chair_page

    def chair_volume(self, volume_dir: str, marks: Dict[str, str], number: int = 4298) -> str:
        """
        write the chair page of the example volume with the given marks replaced
        into the given directory

        Args:
            volume_dir: the volume directory to create
            marks: CEUR mark -> text to put into its span
            number: the volume number

        Returns:
            str: the volume directory
        """
        page = self.chair_page(number)
        for mark, text in marks.items():
            page = re.sub(rf'(<span class="{mark}">)[^<]*(</span>)', rf"\g<1>{text}\g<2>", page)
        os.makedirs(volume_dir)
        with open(os.path.join(volume_dir, "index.html"), "w", encoding="utf-8") as page_file:
            page_file.write(page)
        return volume_dir

    def chair_reports(self, temp_dir: str, marks: Dict[str, str], number: int = 4298) -> List[SiteReport]:
        """
        embed and generate the chair page of the example volume with the given
        marks replaced, each from its own copy of the page

        Args:
            temp_dir: the directory for the copies and the site
            marks: CEUR mark -> text to put into its span
            number: the volume number

        Returns:
            List[SiteReport]: the reports of embed and generate
        """
        generator = self.get_generator(os.path.join(temp_dir, "site"))
        case_dir = tempfile.mkdtemp(prefix="case-", dir=temp_dir)
        embed_report = generator.embed_volumes([self.chair_volume(os.path.join(case_dir, "embed"), marks, number)])
        generate_report = generator.generate_paths(
            [self.chair_volume(os.path.join(case_dir, "generate"), marks, number)]
        )
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

    def get_generator(self, output_dir: str) -> Generator:
        """
        get a generator that reads the examples and writes to the given directory

        Args:
            output_dir: the directory to generate into

        Returns:
            Generator: the generator with a fixed page state
        """
        config = SiteConfig.of_yaml()
        config.spt_url = f"file://{self.examples_path}"
        generator = Generator(
            site=Site(output_dir, self.jsonld),
            config=config,
            mapper=self.mapper,
            jsonld=self.jsonld,
            spt=CeurSpt(config.spt_url),
            state=PageState(generated_on="2026-10-01"),
        )
        return generator
