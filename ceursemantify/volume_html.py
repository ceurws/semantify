"""
Created on 2026-10-13

Input mapping of a volume page as submitted by the proceedings chair
(https://ceur-ws.org/Vol-XXX/index.html template) to the research model, see
https://github.com/ceurws/semantify/issues/28

@author: wf
"""

import json
import os
import posixpath
import re
from datetime import date
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from ceursemantify.convert import Convert
from ceursemantify.jsonld import JsonLd
from ceursemantify.loctime import LocTime
from ceursemantify.mapper import MappingIssue, MappingResult
from ceursemantify.model import City, Country, Event, Paper, Proceedings, Publisher, Scholar


class VolumeHtml:
    """
    a volume page with the CEUR* marks of the volume template
    """

    publisher_name = "CEUR-WS.org"
    # no volume was published before, the plausible range of CEURPUBDATE starts here, see issue 58
    first_pub_date = "1995-01-01"
    # a year, an ordinal or the YYYY placeholder of the Vol-XXX template, see issue 22
    edition_pattern = re.compile(r"\b(?:(?:19|20)\d\d|\d+(?:st|nd|rd|th)|YYYY)\b")
    # tried after the declared charset; latin-1 decodes every byte
    fallback_encodings = ["utf-8", "cp1252", "latin-1"]
    # an embedded or generated page announces its state and carries its JSON-LD in a fence with a
    # marker line, see issues 28 and 49
    embedded_pattern = re.compile(r"<!-- CEURSTATE=(embedded|generated)[^\n]*-->")
    fence_pattern = re.compile(r"```json-ld\n(?:[^\n{\[]*\n)?(.*?)\n```", re.DOTALL)
    _jsonld: Optional[JsonLd] = None

    def __init__(self, text: str, base_url: str = "https://ceur-ws.org", volume_number: Optional[int] = None):
        """
        constructor

        Args:
            text: the html of the volume page
            base_url: the url of the site the volume is published on
            volume_number: the number of the volume for pages without CEURVOLNR
        """
        self.text = text
        self.base_url = base_url.rstrip("/")
        self.volume_number = volume_number
        self.soup = BeautifulSoup(text, "html.parser")
        self.issues: List[MappingIssue] = []
        self.embedded = False
        self.jsonld_document: Optional[dict] = None

    @classmethod
    def jsonld(cls) -> JsonLd:
        """
        the JSON-LD support of the research model, loaded once
        """
        if cls._jsonld is None:
            cls._jsonld = JsonLd.of_yaml()
        return cls._jsonld

    def read_embedded(self, path: str) -> None:
        """
        read the JSON-LD record of a page, the source of the mapping instead of the markup, see issue 28:
        index.jsonld beside the page is the record that the DOI registration writes, for every page
        whatever its state, see issues 42 and 49; the fence of an embedded or generated page is the
        copy and is read only when there is no index.jsonld

        Args:
            path: the path of the index.html
        """
        document = None
        jsonld_path = os.path.join(os.path.dirname(path), "index.jsonld")
        marked = self.embedded_pattern.search(self.text) is not None
        if os.path.isfile(jsonld_path):
            with open(jsonld_path, "r", encoding="utf-8") as jsonld_file:
                document = json.load(jsonld_file)
        elif marked:
            match = self.fence_pattern.search(self.text)
            if match and match.group(1).strip():
                document = json.loads(match.group(1))
        if document is None and not marked:
            return
        self.embedded = True
        if document is None:
            self.issues.append(
                MappingIssue(
                    "Proceedings", "CEURSTATE", "embedded, but neither the fence nor index.jsonld holds the JSON-LD"
                )
            )
        self.jsonld_document = document

    @classmethod
    def decode(cls, raw: bytes) -> Tuple[str, Optional[str], str]:
        """
        decode the bytes of a volume page with its declared charset,
        then with the fallback encodings, see https://github.com/ceurws/semantify/issues/38

        Args:
            raw: the bytes of the page

        Returns:
            Tuple[str, Optional[str], str]: the text, the declared charset or None and the encoding used
        """
        match = re.search(rb"charset\s*=\s*[\"']?([A-Za-z0-9_.:\-]+)", raw[:4096], re.IGNORECASE)
        declared = match.group(1).decode("ascii") if match else None
        encodings = ([declared] if declared else []) + cls.fallback_encodings
        text = None
        used = None
        for encoding in encodings:
            try:
                text = raw.decode(encoding)
                used = encoding
                break
            except (LookupError, UnicodeDecodeError):
                pass
        return text, declared, used

    @classmethod
    def of_file(cls, path: str, base_url: str = "https://ceur-ws.org") -> "VolumeHtml":
        """
        read the volume page from the given file

        Args:
            path: the path of the index.html, the volume number is taken from a Vol-N part of it
            base_url: the url of the site the volume is published on

        Returns:
            VolumeHtml: the volume page, an EarlyVolumeHtml for a page without CEURVOLNR
        """
        with open(path, "rb") as html_file:
            raw = html_file.read()
        text, declared, used = cls.decode(raw)
        numbers = re.findall(r"Vol-(\d+)", path)
        volume_number = int(numbers[-1]) if numbers else None
        volume_class = cls
        if "CEURVOLNR" not in text:
            # imported here since the early volume page is a subclass of this one
            from ceursemantify.early_volume_html import EarlyVolumeHtml

            volume_class = EarlyVolumeHtml
        volume_html = volume_class(text, base_url, volume_number)
        volume_html.read_embedded(path)
        expected = (declared or "utf-8").lower().replace("-", "")
        if used.lower().replace("-", "") != expected:
            volume_html.issues.append(MappingIssue("Proceedings", "charset", f"declared {declared}, decoded as {used}"))
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
        # NONE is the template's value for a volume that is not co-located, see issue 55
        if colocated and colocated.strip().upper() != "NONE":
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
            item: the li element of the paper, the id of the paper is the li id
                or the stem of the pdf link when the li has no id
                see https://github.com/ceurws/semantify/issues/36
            url: the url of the volume
            result: the mapping result to report issues to

        Returns:
            Optional[Paper]: the paper, None if the item has no link to a pdf,
                has no id and links to a pdf outside the volume,
                or links to a pdf outside the volume directory: a paper published elsewhere,
                see https://github.com/ceurws/semantify/issues/35
        """
        paper = None
        link = item.find("a", href=lambda href: href and href.lower().endswith(".pdf"))
        paper_id = item.get("id")
        if link is not None and not paper_id:
            href = link["href"]
            # without li id only a pdf of the volume itself is taken
            if not urlparse(href).scheme and "/" not in href.strip("./"):
                paper_id = posixpath.splitext(posixpath.basename(href))[0]
        if link is not None and paper_id:
            pdf_url = urljoin(url, link["href"])
            if not self.in_volume(pdf_url, url):
                result.issues.append(MappingIssue("Paper", paper_id, f"published elsewhere: {pdf_url}"))
            else:
                title = self.mark_text("CEURTITLE", item) or Convert.text(link.get_text()) or None
                if title is None:
                    result.issues.append(MappingIssue("Paper", paper_id, "no title"))
                paper = Paper(
                    id=paper_id,
                    title=title,
                    pdfUrl=pdf_url,
                    publishedIn=url,
                    authors=[self.scholar(element) for element in item.find_all(class_="CEURAUTHOR")],
                )
                paper.publish_in(url)
                pages = self.mark_text("CEURPAGES", item)
                if pages:
                    paper.pageStart = Convert.page_start(pages)
                    paper.pageEnd = Convert.page_end(pages)
                # the paper belongs to the CEURSESSION heading before it, see issue 54
                session = item.find_previous(class_="CEURSESSION")
                if session is not None:
                    paper.session = Convert.text(session.get_text()) or None
        return paper

    @classmethod
    def in_volume(cls, pdf_url: str, url: str) -> bool:
        """
        check whether the given pdf lies in the directory of the volume,
        the criterion for a paper of the volume, see https://github.com/ceurws/semantify/issues/35;
        the scheme is ignored so that http links to an https site still count

        Args:
            pdf_url: the absolute url of the pdf
            url: the url of the volume

        Returns:
            bool: True if the pdf is in the volume directory or one of its subdirectories
        """
        pdf_parts = urlparse(pdf_url)
        volume_parts = urlparse(url)
        in_volume = pdf_parts.netloc == volume_parts.netloc and pdf_parts.path.startswith(volume_parts.path)
        return in_volume

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
        pdf_urls = set()
        for item in toc.find_all("li"):
            paper = self.paper(item, url, result)
            # an li around a nested list finds the pdf of its first child again
            if paper is not None and paper.pdfUrl not in pdf_urls:
                pdf_urls.add(paper.pdfUrl)
                papers.append(paper)
        return papers

    def volume_number_of(self, result: MappingResult) -> Optional[int]:
        """
        get the volume number of the CEURVOLNR mark

        Args:
            result: the mapping result to report a missing or unparsed mark to

        Returns:
            Optional[int]: the volume number, None if the mark is missing or unparsed
        """
        volume_number = None
        volume_mark = self.required("CEURVOLNR", result)
        if volume_mark:
            try:
                volume_number = Convert.volume_number(volume_mark)
            except ValueError as error:
                result.issues.append(MappingIssue("Proceedings", "CEURVOLNR", str(error)))
        return volume_number

    def proceedings(self) -> MappingResult:
        """
        map the volume page to the proceedings of the research model

        Returns:
            MappingResult: the proceedings and the issues
        """
        result = MappingResult()
        result.issues.extend(self.issues)
        if self.jsonld_document is not None:
            result.target = self.jsonld().proceedings(self.jsonld_document)
            return result
        proceedings = Proceedings(publisher=Publisher(name=self.publisher_name))
        proceedings.volumeNumber = self.volume_number_of(result)
        if proceedings.volumeNumber is not None:
            proceedings.url = f"{self.base_url}/Vol-{proceedings.volumeNumber}/"
            proceedings.archive = f"{self.base_url}/ftp-dir/Vol-{proceedings.volumeNumber}.zip"
        proceedings.urn = self.required("CEURURN", result)
        proceedings.title = self.required("CEURFULLTITLE", result) or self.mark_text("CEURVOLTITLE")
        # the title names the edition by year or ordinal, see issue 22
        if proceedings.title and not self.edition_pattern.search(proceedings.title):
            result.issues.append(
                MappingIssue("Proceedings", "CEURFULLTITLE", f"neither year nor ordinal in {proceedings.title}")
            )
        pub_date = self.required("CEURPUBDATE", result)
        if pub_date:
            try:
                proceedings.pubDate = Convert.iso_date(pub_date)
                # the plausible range of a publication date, see issue 58
                today = date.today().isoformat()
                if not self.first_pub_date <= proceedings.pubDate <= today:
                    result.issues.append(
                        MappingIssue(
                            "Proceedings",
                            "CEURPUBDATE",
                            f"{proceedings.pubDate} is not between {self.first_pub_date} and {today}",
                        )
                    )
            except ValueError as error:
                result.issues.append(MappingIssue("Proceedings", "CEURPUBDATE", str(error)))
        pub_year = self.mark_text("CEURPUBYEAR")
        if pub_year:
            try:
                proceedings.pubYear = Convert.integer(pub_year)
            except ValueError as error:
                result.issues.append(MappingIssue("Proceedings", "CEURPUBYEAR", str(error)))
        # the numbers of the summary sentence of the Vol-XXX template, see issue 54
        for css_class, field_name in [
            ("CEURSUBMITTEDPAPERS", "submittedPapers"),
            ("CEURACCEPTEDPAPERS", "acceptedPapers"),
        ]:
            count = self.mark_text(css_class)
            if count:
                try:
                    setattr(proceedings, field_name, Convert.integer(count))
                except ValueError as error:
                    result.issues.append(MappingIssue("Proceedings", css_class, str(error)))
        license_element = self.mark("CEURLIC")
        if license_element is not None:
            proceedings.license = self.link_of(license_element) or self.mark_text("CEURLIC")
        proceedings.event = self.event(result)
        proceedings.editors = self.editors()
        if proceedings.url:
            proceedings.papers = self.papers(proceedings.url, result)
        result.target = proceedings
        return result
