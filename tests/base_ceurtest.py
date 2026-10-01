"""
Created on 2026-10-01

@author: wf
"""

import json
import os
from typing import Any, Dict

from basemkit.basetest import Basetest

from ceursemantify.generator import Generator
from ceursemantify.jsonld import JsonLd
from ceursemantify.mapper import Mapper
from ceursemantify.model import Proceedings
from ceursemantify.pages import PageState
from ceursemantify.site import CeurSpt, Site, SiteConfig


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
