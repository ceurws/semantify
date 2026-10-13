"""
Created on 2026-10-13

Input mapping of a volume page as submitted by the proceedings chair
(https://ceur-ws.org/Vol-XXX/index.html template) to the research model, see
https://github.com/ceurws/semantify/issues/28

@author: wf
"""

from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from ceursemantify.convert import Convert
from ceursemantify.loctime import LocTime
from ceursemantify.mapper import MappingIssue, MappingResult
from ceursemantify.model import City, Country, Event, Paper, Proceedings, Publisher, Scholar


class VolumeHtml:
    """
    a volume page with the CEUR* marks of the volume template
    """

    publisher_name = "CEUR-WS.org"

    def __init__(self, text: str, base_url: str = "https://ceur-ws.org"):
        """
        constructor

        Args:
            text: the html of the volume page
            base_url: the url of the site the volume is published on
        """
        self.text = text
        self.base_url = base_url.rstrip("/")
        self.soup = BeautifulSoup(text, "html.parser")

    @classmethod
    def of_file(cls, path: str, base_url: str = "https://ceur-ws.org") -> "VolumeHtml":
        """
        read the volume page from the given file

        Args:
            path: the path of the index.html
            base_url: the url of the site the volume is published on

        Returns:
            VolumeHtml: the volume page
        """
        with open(path, "r", encoding="utf-8") as html_file:
            text = html_file.read()
        volume_html = cls(text, base_url)
        return volume_html

    def mark(self, css_class: str, root: Optional[Tag] = None) -> Optional[Tag]:
        """
        get the first element with the given CEUR mark

        Args:
            css_class: the mark e.g. CEURVOLNR
            root: the element to search in, the whole page if None

        Returns:
            Optional[Tag]: the element, None if there is none
        """
        root = root if root is not None else self.soup
        element = root.find(class_=css_class)
        return element

    def mark_text(self, css_class: str, root: Optional[Tag] = None) -> Optional[str]:
        """
        get the text of the first element with the given CEUR mark

        Args:
            css_class: the mark e.g. CEURVOLNR
            root: the element to search in, the whole page if None

        Returns:
            Optional[str]: the single line text, None if there is no element or no text
        """
        text = None
        element = self.mark(css_class, root)
        if element is not None:
            text = Convert.text(element.get_text()) or None
        return text

    def link_of(self, element: Optional[Tag]) -> Optional[str]:
        """
        get the href of the link the given element is or is wrapped in

        Args:
            element: the element

        Returns:
            Optional[str]: the href, None if the element is not linked
        """
        href = None
        if element is not None:
            link = element if element.name == "a" else element.find_parent("a")
            if link is not None:
                href = link.get("href")
        return href

    def required(self, css_class: str, result: MappingResult) -> Optional[str]:
        """
        get the text of a mark that every volume page must have

        Args:
            css_class: the mark
            result: the mapping result to report a missing mark to

        Returns:
            Optional[str]: the text, None if the mark is missing
        """
        text = self.mark_text(css_class)
        if text is None:
            result.issues.append(MappingIssue("Proceedings", css_class, "mark missing"))
        return text

    def event(self, result: MappingResult) -> Event:
        """
        get the event of the volume

        Args:
            result: the mapping result to report issues to

        Returns:
            Event: the event
        """
        acronym_element = self.mark("CEURVOLACRONYM")
        event = Event(
            acronym=self.mark_text("CEURVOLACRONYM"),
            title=self.mark_text("CEURVOLTITLE"),
            homepage=self.link_of(acronym_element),
        )
        colocated = self.mark_text("CEURCOLOCATED")
        if colocated:
            event.colocated_with = Event(acronym=colocated)
        loctime_text = self.required("CEURLOCTIME", result)
        if loctime_text:
            loctime = LocTime.parse(loctime_text)
            # the full text as ceur-spt has it; place, city and country are derived
            event.location = loctime.text
            event.startDate = loctime.startDate
            event.endDate = loctime.endDate
            if loctime.virtual:
                event.virtual = True
            if loctime.city:
                event.city = City(name=loctime.city)
            if loctime.country:
                event.country = Country(name=loctime.country)
            if loctime.message:
                result.issues.append(MappingIssue("Event", "CEURLOCTIME", loctime.message))
        return event

    def scholar(self, element: Tag) -> Scholar:
        """
        get the scholar of the given CEURVOLEDITOR or CEURAUTHOR element

        Args:
            element: the element with the name, optionally linked to an ORCID

        Returns:
            Scholar: the scholar
        """
        scholar = Scholar.of_full_name(element.get_text())
        for url in [element.get("itemid"), self.link_of(element)]:
            if url and "orcid.org/" in url:
                scholar.orcid = url.rstrip("/").rsplit("/", 1)[1]
                break
        return scholar

    def editors(self) -> List[Scholar]:
        """
        get the editors of the volume

        Returns:
            List[Scholar]: the editors in the order of the page
        """
        editors = [self.scholar(element) for element in self.soup.find_all(class_="CEURVOLEDITOR")]
        return editors

    def paper(self, item: Tag, url: str, result: MappingResult) -> Optional[Paper]:
        """
        get the paper of the given table of contents item

        Args:
            item: the li element with the id of the paper
            url: the url of the volume
            result: the mapping result to report issues to

        Returns:
            Optional[Paper]: the paper, None if the item has no link to a pdf
        """
        paper = None
        link = item.find("a", href=lambda href: href and href.lower().endswith(".pdf"))
        if link is not None:
            title = self.mark_text("CEURTITLE", item) or Convert.text(link.get_text()) or None
            if title is None:
                result.issues.append(MappingIssue("Paper", item["id"], "no title"))
            paper = Paper(
                id=item["id"],
                title=title,
                pdfUrl=urljoin(url, link["href"]),
                publishedIn=url,
                authors=[self.scholar(element) for element in item.find_all(class_="CEURAUTHOR")],
            )
            pages = self.mark_text("CEURPAGES", item)
            if pages:
                paper.pageStart = Convert.page_start(pages)
                paper.pageEnd = Convert.page_end(pages)
        return paper

    def papers(self, url: str, result: MappingResult) -> List[Paper]:
        """
        get the papers of the volume

        Args:
            url: the url of the volume
            result: the mapping result to report issues to

        Returns:
            List[Paper]: the papers in the order of the table of contents
        """
        toc = self.mark("CEURTOC") or self.soup
        papers = []
        for item in toc.find_all("li", id=True):
            paper = self.paper(item, url, result)
            if paper is not None:
                papers.append(paper)
        return papers

    def proceedings(self) -> MappingResult:
        """
        map the volume page to the proceedings of the research model

        Returns:
            MappingResult: the proceedings and the issues
        """
        result = MappingResult()
        proceedings = Proceedings(publisher=Publisher(name=self.publisher_name))
        volume_mark = self.required("CEURVOLNR", result)
        if volume_mark:
            try:
                proceedings.volumeNumber = Convert.volume_number(volume_mark)
                proceedings.url = f"{self.base_url}/Vol-{proceedings.volumeNumber}/"
                proceedings.archive = f"{self.base_url}/ftp-dir/Vol-{proceedings.volumeNumber}.zip"
            except ValueError as error:
                result.issues.append(MappingIssue("Proceedings", "CEURVOLNR", str(error)))
        proceedings.urn = self.required("CEURURN", result)
        proceedings.title = self.required("CEURFULLTITLE", result) or self.mark_text("CEURVOLTITLE")
        pub_date = self.required("CEURPUBDATE", result)
        if pub_date:
            try:
                proceedings.pubDate = Convert.iso_date(pub_date)
            except ValueError as error:
                result.issues.append(MappingIssue("Proceedings", "CEURPUBDATE", str(error)))
        pub_year = self.mark_text("CEURPUBYEAR")
        if pub_year:
            try:
                proceedings.pubYear = Convert.integer(pub_year)
            except ValueError as error:
                result.issues.append(MappingIssue("Proceedings", "CEURPUBYEAR", str(error)))
        license_element = self.mark("CEURLIC")
        if license_element is not None:
            proceedings.license = self.link_of(license_element) or self.mark_text("CEURLIC")
        proceedings.event = self.event(result)
        proceedings.editors = self.editors()
        if proceedings.url:
            proceedings.papers = self.papers(proceedings.url, result)
        result.target = proceedings
        return result
