"""
Created on 2026-10-01

Research model of CEUR-WS: the core entities and CrSchema of
https://cr.bitplan.com/index.php/CoreEntities and
https://cr.bitplan.com/index.php/CrSchema

Field names follow CrSchema. Where CrSchema has no property the term of the
CEUR-WS proceedings ontology in the ontology directory is used. Fields that
have a term in neither are listed as provisional in resources/context.yaml.

@author: wf
"""

import os
import re
from dataclasses import field
from datetime import datetime
from typing import ClassVar, List, Optional
from urllib.parse import urljoin

from basemkit.yamlable import lod_storable


@lod_storable
class City:
    """
    large permanent human settlement
    """

    name: Optional[str] = None
    wikidataid: Optional[str] = None


@lod_storable
class Country:
    """
    distinct region in geography
    """

    name: Optional[str] = None
    wikidataid: Optional[str] = None


@lod_storable
class Publisher:
    """
    organization that publishes proceedings
    """

    name: Optional[str] = None
    wikidataid: Optional[str] = None


@lod_storable
class Scholar:
    """
    person who engages in research
    """

    name: Optional[str] = None
    firstName: Optional[str] = None
    orcid: Optional[str] = None
    dblpId: Optional[str] = None
    wikiDataId: Optional[str] = None
    gndId: Optional[str] = None

    @classmethod
    def of_full_name(cls, full_name: str) -> "Scholar":
        """
        get a scholar from a full name as written on a volume page

        The last word is taken as the family name, the words before it as
        the first name; a heuristic that fails e.g. for Spanish double surnames.

        Args:
            full_name: the name e.g. Mieke Jans

        Returns:
            Scholar: the scholar
        """
        parts = full_name.split()
        scholar = cls(name=parts[-1] if parts else None, firstName=" ".join(parts[:-1]) or None)
        return scholar

    def full_name(self) -> str:
        """
        get first name and last name of the scholar

        Returns:
            str: the name parts that are set, separated by a blank
        """
        parts = [part for part in [self.firstName, self.name] if part]
        full_name = " ".join(parts)
        return full_name


@lod_storable
class Event:
    """
    a meeting of researchers at a specific time and place
    """

    acronym: Optional[str] = None
    ordinal: Optional[int] = None
    title: Optional[str] = None
    homepage: Optional[str] = None
    wikidataid: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    location: Optional[str] = None
    virtual: Optional[bool] = None
    city: Optional[City] = None
    country: Optional[Country] = None
    colocated_with: Optional["Event"] = None

    def year(self) -> Optional[int]:
        """
        get the year of the event

        Returns:
            Optional[int]: the year of the start date, None if there is no start date
        """
        year = None
        if self.startDate:
            year = int(self.startDate[:4])
        return year


@lod_storable
class Paper:
    """
    a paper is e.g. a scholarly article
    """

    id: Optional[str] = None
    wikidataid: Optional[str] = None
    doi: Optional[str] = None
    title: Optional[str] = None
    # the landing page of the paper, the paper as a node with its metadata and links, see issue 32
    paperUrl: Optional[str] = None
    # the file
    pdfUrl: Optional[str] = None
    pageStart: Optional[str] = None
    pageEnd: Optional[str] = None
    dblpPublicationId: Optional[str] = None
    session: Optional[str] = None
    publishedIn: Optional[str] = None
    authors: List[Scholar] = field(default_factory=list)

    def publish_in(self, url: str) -> None:
        """
        set the volume the paper is published in and the landing page of the
        paper under it, the directory named by the paper id, see issue 32

        Args:
            url: the url of the volume e.g. https://ceur-ws.org/Vol-4298/
        """
        self.publishedIn = url
        if self.id:
            self.paperUrl = urljoin(url, f"{self.id}/")


@lod_storable
class Proceedings:
    """
    a collection of papers mostly documenting the results of an academic event
    """

    wikidataid: Optional[str] = None
    doi: Optional[str] = None
    title: Optional[str] = None
    volumeNumber: Optional[int] = None
    urn: Optional[str] = None
    pubDate: Optional[str] = None
    pubYear: Optional[int] = None
    url: Optional[str] = None
    archive: Optional[str] = None
    license: Optional[str] = None
    submittedPapers: Optional[int] = None
    acceptedPapers: Optional[int] = None
    # the CEURVERSION of the Vol-XXX template and the submitted by footer of the chair page, see issue 63
    templateVersion: Optional[str] = None
    dateSubmitted: Optional[str] = None
    submittedBy: Optional[str] = None
    # the year of a volume without usable publication date and where it is taken from, see issue 78
    inferredYear: Optional[int] = None
    inferredYearSource: Optional[str] = None
    publisher: Optional[Publisher] = None
    event: Optional[Event] = None
    editors: List[Scholar] = field(default_factory=list)
    papers: List[Paper] = field(default_factory=list)

    # the first year of CEUR-WS
    FIRST_YEAR: ClassVar[int] = 1995

    @classmethod
    def plausible_year(cls, year: Optional[int]) -> bool:
        """
        check that the given year lies in the range of CEUR-WS

        Args:
            year: the year

        Returns:
            bool: True if the year is from 1995 to the current year
        """
        plausible = year is not None and cls.FIRST_YEAR <= year <= datetime.now().year
        return plausible

    @classmethod
    def year_of(cls, date_text: Optional[str]) -> Optional[int]:
        """
        get the plausible four digit year of the given date text

        Args:
            date_text: the date, e.g. 2024-10-24 or 28-Nov-2012

        Returns:
            Optional[int]: the year, None if there is no plausible year
        """
        year = None
        if date_text:
            match = re.search(r"(?<!\d)(\d{4})(?!\d)", date_text)
            if match and cls.plausible_year(int(match.group(1))):
                year = int(match.group(1))
        return year

    def publication_year(self) -> Optional[int]:
        """
        get the year of the publication date, the CEURPUBDATE of the volume page

        Returns:
            Optional[int]: the year, None if there is no plausible publication date
        """
        year = self.year_of(self.pubDate)
        return year

    def year(self) -> Optional[int]:
        """
        get the year the proceedings belong to: the year of the publication on
        CEUR-WS, the inferred year where it is set, else the year of the
        publication date, see issue 78

        Returns:
            Optional[int]: the year, None if there is neither an inferred year nor a publication date
        """
        year = self.inferredYear if self.inferredYear is not None else self.publication_year()
        return year

    def infer_year(self, volume_dir: Optional[str] = None) -> Optional[int]:
        """
        infer the year of proceedings without plausible publication date, see
        issue 78: the year of the modification time of the index.html.orig of
        the volume directory, of the date of the submitted by line or of the
        modification time of the oldest file of the volume directory; the year
        and its source are kept in inferredYear and inferredYearSource

        Args:
            volume_dir: the directory of the local volume page, None if there is none

        Returns:
            Optional[int]: the inferred year, None if there is no source
        """
        candidates = []
        has_dir = volume_dir is not None and os.path.isdir(volume_dir)
        if has_dir:
            orig = os.path.join(volume_dir, "index.html.orig")
            if os.path.isfile(orig):
                candidates.append((datetime.fromtimestamp(os.path.getmtime(orig)).year, "index.html.orig mtime"))
        candidates.append((self.year_of(self.dateSubmitted), "submitted by"))
        if has_dir:
            files = [os.path.join(volume_dir, name) for name in os.listdir(volume_dir)]
            files = [path for path in files if os.path.isfile(path)]
            if files:
                oldest = min(os.path.getmtime(path) for path in files)
                candidates.append((datetime.fromtimestamp(oldest).year, "oldest file mtime"))
        year = None
        for candidate_year, source in candidates:
            if self.plausible_year(candidate_year):
                year = candidate_year
                self.inferredYear, self.inferredYearSource = year, source
                break
        return year
