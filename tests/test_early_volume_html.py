"""
Created on 2026-10-18

@author: wf
"""

import json
import os

from ceursemantify.early_volume_html import EarlyVolumeHtml
from ceursemantify.volume_html import VolumeHtml
from tests.base_ceurtest import BaseCeurTest


class TestEarlyVolumeHtml(BaseCeurTest):
    """
    test the mapping of the early volume pages without CEUR marks
    see https://github.com/ceurws/semantify/issues/39
    """

    def test_selection(self) -> None:
        """
        test that a page without CEURVOLNR is read as early volume page
        """
        for volume, expected in [
            ("Vol-6", EarlyVolumeHtml),
            ("Vol-1", EarlyVolumeHtml),
            ("Vol-4280", VolumeHtml),
            ("Vol-1356", VolumeHtml),
        ]:
            with self.subTest(volume=volume):
                volume_html = VolumeHtml.of_file(os.path.join(self.examples_path, f"{volume}.html"))
                self.assertIs(expected, type(volume_html))

    def test_postscript_volumes(self) -> None:
        """
        test that the papers of early volume pages with PostScript only papers
        are the PostScript files converted for semantify issue 39,
        in table rows (Vol-6, Vol-12, Vol-27), paragraphs (Vol-22) and list items (Vol-86);
        known gap: the page lists V 098 of Vol-12 without a link, Vol-12/098.ps exists,
        the link based mapping does not find it
        """
        with open(os.path.join(self.examples_path, "early-paper-stems.json"), "r", encoding="utf-8") as json_file:
            early_stems = json.load(json_file)
        for volume, expected in early_stems.items():
            with self.subTest(volume=volume):
                result = VolumeHtml.of_file(os.path.join(self.examples_path, f"{volume}.html")).proceedings()
                proceedings = result.target
                self.assertEqual(int(volume[4:]), proceedings.volumeNumber)
                ids = [paper.id for paper in proceedings.papers]
                if self.debug:
                    print(f"{volume}: {len(ids)} papers, converted {len(expected)}")
                self.assertEqual(sorted(expected), sorted(ids))
                for paper in proceedings.papers:
                    # the official PDF to be generated from the PostScript file
                    self.assertEqual(f"https://ceur-ws.org/{volume}/{paper.id}.pdf", paper.pdfUrl)
                    self.assertIsNotNone(paper.title)
                postscript = [issue for issue in result.issues if issue.message == "PostScript only"]
                self.assertEqual(len(ids), len(postscript))
