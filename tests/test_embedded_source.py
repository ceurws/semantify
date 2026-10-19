"""
Created on 2026-10-19

@author: wf
"""

import json
import os
import shutil
import tempfile

from ceursemantify.embed import Embedder
from ceursemantify.pages import PageState
from ceursemantify.volume_html import VolumeHtml
from tests.base_ceurtest import BaseCeurTest


class TestEmbeddedSource(BaseCeurTest):
    """
    an embedded volume page is read from its JSON-LD, not scraped, see issue 28:
    the fence of index.html when it holds the document, else index.jsonld beside the page
    """

    def setUp(self, debug: bool = False, profile: bool = True) -> None:
        BaseCeurTest.setUp(self, debug=debug, profile=profile)
        with open(os.path.join(self.examples_path, "Vol-4280.html"), "r", encoding="utf-8") as html_file:
            self.original = html_file.read()
        self.scraped = VolumeHtml(self.original).proceedings().target
        self.scraped.doi = "10.83095/ceurws_04280"
        for paper in self.scraped.papers:
            paper.doi = f"10.83095/ceurws_04280_{paper.id}"
        self.jsonld_text = self.jsonld.as_text(self.scraped)
        self.embedder = Embedder(PageState(generated_on="2026-10-19"))

    def volume_dir(self, temp_dir: str, html_text: str, with_file: bool) -> str:
        """
        write a volume directory with the given index.html and optionally index.jsonld
        """
        volume_dir = os.path.join(temp_dir, "Vol-4280")
        os.makedirs(volume_dir)
        with open(os.path.join(volume_dir, "index.html"), "w", encoding="utf-8") as html_file:
            html_file.write(html_text)
        if with_file:
            with open(os.path.join(volume_dir, "index.jsonld"), "w", encoding="utf-8") as jsonld_file:
                jsonld_file.write(self.jsonld_text + "\n")
        return volume_dir

    def test_fence(self) -> None:
        """
        the fence of the embedded page is the source and carries the DOIs
        """
        embedded = self.embedder.embed(self.original, self.jsonld_text, "https://ceur-ws.org/Vol-4280/")
        with tempfile.TemporaryDirectory() as temp_dir:
            volume_dir = self.volume_dir(temp_dir, embedded, with_file=False)
            volume_html = VolumeHtml.of_file(os.path.join(volume_dir, "index.html"))
            self.assertTrue(volume_html.embedded)
            proceedings = volume_html.proceedings().target
        self.assertEqual(self.scraped, proceedings)
        self.assertEqual("10.83095/ceurws_04280", proceedings.doi)
        self.assertEqual("10.83095/ceurws_04280_paper1", proceedings.papers[1].doi)

    def test_empty_fence_file(self) -> None:
        """
        an embedded page with an empty fence, as on ceur-ws.org for Vol-4294 to Vol-4298
        on 2026-10-19, is read from index.jsonld beside it
        """
        embedded = self.embedder.embed(self.original, self.jsonld_text, "https://ceur-ws.org/Vol-4280/")
        empty = self.embedder.fence_pattern.sub("<!--\n-->\n", embedded)
        self.assertNotIn("```json-ld", empty)
        self.assertIn("CEURSTATE=embedded", empty)
        with tempfile.TemporaryDirectory() as temp_dir:
            volume_dir = self.volume_dir(temp_dir, empty, with_file=True)
            volume_html = VolumeHtml.of_file(os.path.join(volume_dir, "index.html"))
            self.assertTrue(volume_html.embedded)
            proceedings = volume_html.proceedings().target
        self.assertEqual(self.scraped, proceedings)
        self.assertEqual("10.83095/ceurws_04280_paper1", proceedings.papers[1].doi)

    def test_embedded_without_source(self) -> None:
        """
        an embedded page with an empty fence and no index.jsonld is scraped with an issue
        """
        embedded = self.embedder.embed(self.original, self.jsonld_text, "https://ceur-ws.org/Vol-4280/")
        empty = self.embedder.fence_pattern.sub("<!--\n-->\n", embedded)
        with tempfile.TemporaryDirectory() as temp_dir:
            volume_dir = self.volume_dir(temp_dir, empty, with_file=False)
            result = VolumeHtml.of_file(os.path.join(volume_dir, "index.html")).proceedings()
        self.assertIsNone(result.target.doi)
        self.assertEqual(4280, result.target.volumeNumber)
        self.assertTrue(any("CEURSTATE" in issue.source_key for issue in result.issues))

    def test_plain_page(self) -> None:
        """
        a page of the chair without embedding is scraped as before
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            volume_dir = self.volume_dir(temp_dir, self.original, with_file=False)
            volume_html = VolumeHtml.of_file(os.path.join(volume_dir, "index.html"))
            self.assertFalse(volume_html.embedded)
            proceedings = volume_html.proceedings().target
        self.assertIsNone(proceedings.doi)
        self.assertEqual(4280, proceedings.volumeNumber)
