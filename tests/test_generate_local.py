"""
Created on 2026-10-20

@author: wf
"""

import json
import os
import shutil
import tempfile
from typing import Any

from ceursemantify.ceursemantify_cmd import main
from ceursemantify.embed import Embedder
from ceursemantify.pages import PageState
from tests.base_ceurtest import BaseCeurTest


class TestGenerateLocal(BaseCeurTest):
    """
    generate the volume and paper pages from the local volume page and its
    index.jsonld instead of ceur-spt, see issues 33 and 34; the DOIs of the
    JSON-LD are shown on the pages
    """

    def setUp(self, debug: bool = False, profile: bool = True) -> None:
        BaseCeurTest.setUp(self, debug=debug, profile=profile)
        # Vol-4298 as on ceur-ws.org on 2026-10-20: embedded with an empty fence, index.jsonld with the DOIs
        self.example_dir = os.path.join(self.examples_path, "Vol-4298")

    def copy_example(self, temp_dir: str) -> str:
        """
        copy the example volume directory into the given directory
        """
        volume_dir = os.path.join(temp_dir, "source", "Vol-4298")
        shutil.copytree(self.example_dir, volume_dir)
        return volume_dir

    def read(self, *path: str) -> str:
        with open(os.path.join(*path), "r", encoding="utf-8") as page_file:
            text = page_file.read()
        return text

    def test_generate_paths(self) -> None:
        """
        the volume of 2026 with its 8 papers is written from the local JSON-LD,
        the round trip holds and the DOIs are on the pages
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = self.copy_example(temp_dir)
            output_dir = os.path.join(temp_dir, "site")
            generator = self.get_generator(output_dir)
            report = generator.generate_paths([source_dir])
            self.assertEqual([], report.problems)
            # page and JSON-LD for the volume and its 8 papers
            self.assertEqual(2 + 2 * 8, len(report.written))
            volume_dir = os.path.join(output_dir, "2026", "Vol-4298")
            self.assertTrue(generator.round_trip(volume_dir))
            volume_page = self.read(volume_dir, "index.html")
            self.assertIn('<a href="https://doi.org/10.83095/ceurws_04298">10.83095/ceurws_04298</a>', volume_page)
            self.assertIn(
                '<a href="https://doi.org/10.83095/ceurws_04298_paper7">10.83095/ceurws_04298_paper7</a>', volume_page
            )
            paper_dir = os.path.join(volume_dir, "paper7")
            self.assertTrue(generator.round_trip(paper_dir))
            paper_page = self.read(paper_dir, "index.html")
            self.assertIn('<span class="CEURDOI"><a href="https://doi.org/10.83095/ceurws_04298_paper7">', paper_page)
            # the source is not touched
            self.assertEqual(self.read(self.example_dir, "index.html"), self.read(source_dir, "index.html"))

    def strip_dois(self, node: Any) -> Any:
        """
        remove the doi keys from the given JSON-LD node recursively
        """
        if isinstance(node, dict):
            node = {key: self.strip_dois(value) for key, value in node.items() if key != "doi"}
        elif isinstance(node, list):
            node = [self.strip_dois(item) for item in node]
        return node

    def test_index_jsonld_wins(self) -> None:
        """
        the fence of the embedded page holds the JSON-LD without DOIs, index.jsonld
        the one with the DOIs as register-dois writes it: the DOIs are on the pages, see issue 42
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = self.copy_example(temp_dir)
            with open(os.path.join(source_dir, "index.jsonld"), "r", encoding="utf-8") as jsonld_file:
                document = json.load(jsonld_file)
            without_dois = json.dumps(self.strip_dois(document), indent=2, ensure_ascii=False)
            embedder = Embedder(PageState(generated_on="2026-10-23"))
            page_path = os.path.join(source_dir, "index.html")
            self.assertNotIn("10.83095", without_dois)
            fenced = embedder.embed(self.read(page_path), without_dois, "https://ceur-ws.org/Vol-4298/")
            self.assertIn("```json-ld", fenced)
            with open(page_path, "w", encoding="utf-8") as page_file:
                page_file.write(fenced)
            output_dir = os.path.join(temp_dir, "site")
            generator = self.get_generator(output_dir)
            report = generator.generate_paths([source_dir])
            self.assertEqual([], report.problems)
            volume_page = self.read(output_dir, "2026", "Vol-4298", "index.html")
            self.assertIn('<a href="https://doi.org/10.83095/ceurws_04298_paper7">', volume_page)

    def test_generate_in_place(self) -> None:
        """
        the volume page and the paper pages are written into the volume directory itself, see issue 43
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = self.copy_example(temp_dir)
            output_dir = os.path.join(temp_dir, "site")
            generator = self.get_generator(output_dir)
            report = generator.generate_paths([source_dir], in_place=True)
            self.assertEqual([], report.problems)
            self.assertEqual(2 + 2 * 8, len(report.written))
            for path in report.written:
                self.assertTrue(path.startswith(source_dir), path)
            self.assertFalse(os.path.exists(output_dir))
            self.assertTrue(generator.round_trip(source_dir))
            volume_page = self.read(source_dir, "index.html")
            self.assertIn('<a href="https://doi.org/10.83095/ceurws_04298">10.83095/ceurws_04298</a>', volume_page)
            self.assertTrue(generator.round_trip(os.path.join(source_dir, "paper7")))
            # the command line
            config_path = os.path.join(temp_dir, "site.yaml")
            generator.config.save_to_yaml_file(config_path)
            exit_code = main(["--generate", source_dir, "--in-place", "--config", config_path, "--quiet"])
            self.assertEqual(0, exit_code)
            self.assertTrue(os.path.isfile(os.path.join(source_dir, "paper1", "index.html")))

    def test_generate_problem(self) -> None:
        """
        a path without a volume page is reported, nothing is written
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = self.get_generator(os.path.join(temp_dir, "site"))
            report = generator.generate_paths([os.path.join(temp_dir, "Vol-9999")])
            self.assertEqual([], report.written)
            self.assertEqual(1, len(report.problems))

    def test_cmd(self) -> None:
        """
        the command line: --generate with the volume directory, the year as separate call
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = self.copy_example(temp_dir)
            output_dir = os.path.join(temp_dir, "site")
            config_path = os.path.join(temp_dir, "site.yaml")
            self.get_generator(output_dir).config.save_to_yaml_file(config_path)
            exit_code = main(["--generate", source_dir, "-o", output_dir, "--config", config_path, "--quiet"])
            self.assertEqual(0, exit_code)
            self.assertTrue(os.path.isfile(os.path.join(output_dir, "2026", "Vol-4298", "paper1", "index.html")))
            exit_code = main(["--year", "2026", "-o", output_dir, "--config", config_path, "--quiet"])
            self.assertEqual(0, exit_code)
            self.assertIn("Vol-4298/", self.read(output_dir, "2026", "index.html"))
