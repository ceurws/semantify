"""
Created on 2026-10-13

@author: wf
"""

import json
import os
import shutil
import tempfile

from ceursemantify.ceursemantify_cmd import main
from ceursemantify.embed import Embedder
from ceursemantify.pages import PageState
from ceursemantify.volume_html import VolumeHtml
from tests.base_ceurtest import BaseCeurTest


class TestEmbed(BaseCeurTest):
    """
    test the embedding of the JSON-LD into the volume page of the
    proceedings chair, see issue 28
    """

    def setUp(self, debug: bool = False, profile: bool = True) -> None:
        BaseCeurTest.setUp(self, debug=debug, profile=profile)
        self.state = PageState(generated_on="2026-10-13")
        self.embedder = Embedder(self.state)
        with open(os.path.join(self.examples_path, "Vol-4280.html"), "r", encoding="utf-8") as html_file:
            self.original = html_file.read()

    def embedded(self) -> str:
        """
        get the volume page of Vol-4280 with its JSON-LD embedded

        Returns:
            str: the html
        """
        proceedings = VolumeHtml(self.original).proceedings().target
        jsonld_text = self.jsonld.as_text(proceedings)
        html_text = self.embedder.embed(self.original, jsonld_text, proceedings.url)
        return html_text

    def test_embed(self) -> None:
        """
        test that the state comment, the alternate link and the fence are
        inserted and that the markup of the chair is otherwise untouched
        """
        embedded = self.embedded()
        self.assertIn("<!-- CEURSTATE=embedded: on 2026-10-13 by pyCEURsemantify", embedded.split("\n")[1])
        self.assertIn("from https://ceur-ws.org/Vol-4280/ -->", embedded)
        self.assertIn('<link rel="alternate" type="application/ld+json" href="index.jsonld">', embedded)
        self.assertLess(embedded.index("<head>"), embedded.index("```json-ld"))
        self.assertLess(embedded.index("```json-ld"), embedded.index("</head>"))
        self.assertEqual(self.original, self.embedder.strip(embedded))

    def test_idempotent(self) -> None:
        """
        test that embedding again replaces the embedded parts
        """
        embedded = self.embedded()
        again = self.embedder.embed(embedded, '{"@type": "Proceedings"}', "test")
        self.assertEqual(1, again.count("CEURSTATE="))
        self.assertEqual(1, again.count("```json-ld"))
        self.assertEqual(1, again.count('rel="alternate"'))
        self.assertIn("from test -->", again)
        self.assertEqual(self.original, self.embedder.strip(again))

    def test_embed_volume(self) -> None:
        """
        test the embedding of a volume directory: index.jsonld is written,
        index.html is rewritten and the round trip holds: the fence equals
        index.jsonld and a fresh parse of the embedded page
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            volume_dir = os.path.join(temp_dir, "Vol-4280")
            os.makedirs(volume_dir)
            shutil.copy(os.path.join(self.examples_path, "Vol-4280.html"), os.path.join(volume_dir, "index.html"))
            generator = self.get_generator(temp_dir)
            report = generator.embed_volumes([volume_dir])
            self.assertEqual([], report.problems)
            self.assertEqual(2, len(report.written))
            self.assertTrue(generator.round_trip(volume_dir))
            with open(os.path.join(volume_dir, "index.jsonld"), "r", encoding="utf-8") as jsonld_file:
                from_file = self.jsonld.proceedings(json.load(jsonld_file))
            with open(os.path.join(volume_dir, "index.html"), "r", encoding="utf-8") as html_file:
                from_html = VolumeHtml(html_file.read()).proceedings().target
            self.assertEqual(from_file, from_html)
            self.assertEqual(4280, from_html.volumeNumber)
            # embedding again gives the same files
            report = generator.embed_volumes([os.path.join(volume_dir, "index.html")])
            self.assertEqual([], report.problems)
            self.assertTrue(generator.round_trip(volume_dir))

    def test_embed_problems(self) -> None:
        """
        test that a missing page is reported and nothing is written
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = self.get_generator(temp_dir)
            report = generator.embed_volumes([os.path.join(temp_dir, "Vol-0")])
            self.assertEqual([], report.written)
            self.assertEqual(1, len(report.problems))

    def test_cmd(self) -> None:
        """
        test the command line option --embed
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            volume_dir = os.path.join(temp_dir, "Vol-4280")
            os.makedirs(volume_dir)
            shutil.copy(os.path.join(self.examples_path, "Vol-4280.html"), os.path.join(volume_dir, "index.html"))
            exit_code = main(["--embed", volume_dir, "--quiet"])
            self.assertEqual(0, exit_code)
            self.assertTrue(os.path.isfile(os.path.join(volume_dir, "index.jsonld")))
