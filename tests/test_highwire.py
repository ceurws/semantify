"""
Created on 2026-10-27

@author: wf
"""

import os
import re
from typing import List, Tuple

from ceursemantify.pages import PageState, PaperPage
from ceursemantify.site import SiteConfig
from ceursemantify.volume_html import VolumeHtml
from tests.base_ceurtest import BaseCeurTest


class TestHighwire(BaseCeurTest):
    """
    issue 50: the landing page of a paper carries the Highwire tags that the
    walks from the paper node of the core entities reach, on the example of
    https://cr.bitplan.com/index.php/CoreEntities: paper7 of Vol-3262
    """

    tag_pattern = re.compile(r'<meta name="(citation_[a-z_]+)" content="([^"]*)">')

    def paper_page(self, number: int, paper_id: str) -> str:
        """
        get the landing page of the given paper generated from the chair page of the example volume

        Args:
            number: the volume number
            paper_id: the id of the paper

        Returns:
            str: the html of the landing page
        """
        config = SiteConfig.of_yaml()
        volume_html = VolumeHtml.of_file(os.path.join(self.examples_path, f"Vol-{number}", "index.html"))
        proceedings = volume_html.proceedings().target
        paper = next(paper for paper in proceedings.papers if paper.id == paper_id)
        page = PaperPage(paper, proceedings, config, self.jsonld, PageState(generated_on="2026-10-27")).as_html()
        return page

    def tags(self, page: str) -> List[Tuple[str, str]]:
        """
        get the Highwire tags of the head of the given page in document order

        Args:
            page: the html of the page

        Returns:
            List[Tuple[str, str]]: name and content per tag
        """
        head = page.split("</head>")[0]
        tags = self.tag_pattern.findall(head)
        return tags

    def test_vol_3262_paper7(self) -> None:
        """
        the example of the core entities: five authors, no pages, no doi
        """
        expected = [
            ("citation_title", "Property cardinality analysis to extract truly tabular query results from Wikidata"),
            ("citation_author", "Fahl, Wolfgang"),
            ("citation_author", "Holzheim, Tim"),
            ("citation_author", "Westerinen, Andrea"),
            ("citation_author", "Lange, Christoph"),
            ("citation_author", "Decker, Stefan"),
            ("citation_publication_date", "2022-11-03"),
            ("citation_publisher", "CEUR-WS.org"),
            ("citation_journal_title", "Proceedings of the 3rd Wikidata Workshop 2022"),
            ("citation_conference_title", "Wikidata Workshop 2022"),
            ("citation_issn", "1613-0073"),
            ("citation_pdf_url", "https://ceur-ws.org/Vol-3262/paper7.pdf"),
            ("citation_abstract_html_url", "https://ceur-ws.org/Vol-3262/paper7/"),
        ]
        self.assertEqual(expected, self.tags(self.paper_page(3262, "paper7")))

    def test_vol_4298_paper1(self) -> None:
        """
        a paper with pages and a doi, from the embedded example of Vol-4298
        """
        tags = dict(self.tags(self.paper_page(4298, "paper1")))
        self.assertEqual("1", tags["citation_firstpage"])
        self.assertEqual("12", tags["citation_lastpage"])
        self.assertEqual("10.83095/ceurws_04298_paper1", tags["citation_doi"])
        self.assertEqual("2026-10-19", tags["citation_publication_date"])
        self.assertNotIn("citation_keywords", tags)
        self.assertNotIn("citation_language", tags)
