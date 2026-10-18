"""
Created on 2026-10-18

Input mapping of the early volume pages without CEUR marks: free form html
with the papers as links in list items, table rows or paragraphs, partly as
PostScript only, see https://github.com/ceurws/semantify/issues/26
and https://github.com/ceurws/semantify/issues/39

@author: wf
"""

import posixpath
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import Tag

from ceursemantify.convert import Convert
from ceursemantify.mapper import MappingIssue, MappingResult
from ceursemantify.model import Paper
from ceursemantify.volume_html import VolumeHtml


class EarlyVolumeHtml(VolumeHtml):
    """
    an early volume page without the CEUR marks of the volume template
    """

    # longest first so that .ps.gz is not taken as .gz
    document_extensions = [".ps.gz", ".pdf", ".ps"]
    # the elements that hold one entry of the table of contents
    entry_elements = ["li", "tr", "p", "dd", "dt"]

    def document_of(self, href: Optional[str]) -> Optional[Tuple[str, str]]:
        """
        get the stem and extension of a link to a document of the volume itself

        Args:
            href: the href of the link

        Returns:
            Optional[Tuple[str, str]]: the stem and the extension, None for
                other links and for documents outside the volume
        """
        document = None
        if href:
            href = href.strip()
            if not urlparse(href).scheme and "/" not in href.strip("./"):
                name = posixpath.basename(href)
                for extension in self.document_extensions:
                    if name.lower().endswith(extension):
                        document = (name[: -len(extension)], extension)
                        break
        return document

    def title_of(self, link: Tag) -> Optional[str]:
        """
        get the title of the paper the given link belongs to

        Args:
            link: the link to the document of the paper

        Returns:
            Optional[str]: the text of the entry when it holds only this paper,
                the link text otherwise
        """
        entry = link.find_parent(self.entry_elements)
        title = None
        if entry is not None:
            stems = {self.document_of(a.get("href"))[0] for a in entry.find_all("a") if self.document_of(a.get("href"))}
            if len(stems) == 1:
                title = Convert.text(entry.get_text()) or None
        if title is None:
            title = Convert.text(link.get_text()) or None
        return title

    def papers(self, url: str, result: MappingResult) -> List[Paper]:
        """
        get the papers of the volume: every document of the volume itself
        the page links, one paper per file stem in the order of the page

        Args:
            url: the url of the volume
            result: the mapping result to report issues to

        Returns:
            List[Paper]: the papers, the pdfUrl is the official PDF also when
                only a PostScript file exists, see https://github.com/ceurws/semantify/issues/39
        """
        links: Dict[str, Tag] = {}
        extensions: Dict[str, set] = {}
        for link in self.soup.find_all("a"):
            document = self.document_of(link.get("href"))
            if document is not None:
                stem, extension = document
                links.setdefault(stem, link)
                extensions.setdefault(stem, set()).add(extension)
        papers = []
        for stem, link in links.items():
            title = self.title_of(link)
            if title is None:
                result.issues.append(MappingIssue("Paper", stem, "no title"))
            if ".pdf" not in extensions[stem]:
                result.issues.append(MappingIssue("Paper", stem, "PostScript only"))
            paper = Paper(id=stem, title=title, pdfUrl=urljoin(url, f"{stem}.pdf"), publishedIn=url, authors=[])
            papers.append(paper)
        return papers

    def volume_number_of(self, result: MappingResult) -> Optional[int]:
        """
        get the volume number from the Vol-N of the path, the page has no CEURVOLNR
        see https://github.com/ceurws/semantify/issues/37
        """
        return self.volume_number
