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

from dataclasses import field
from typing import List, Optional

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
    title: Optional[str] = None
    pdfUrl: Optional[str] = None
    pageStart: Optional[str] = None
    pageEnd: Optional[str] = None
    dblpPublicationId: Optional[str] = None
    session: Optional[str] = None
    publishedIn: Optional[str] = None
    authors: List[Scholar] = field(default_factory=list)


@lod_storable
class Proceedings:
    """
    a collection of papers mostly documenting the results of an academic event
    """

    wikidataid: Optional[str] = None
    title: Optional[str] = None
    volumeNumber: Optional[int] = None
    urn: Optional[str] = None
    pubDate: Optional[str] = None
    pubYear: Optional[int] = None
    url: Optional[str] = None
    archive: Optional[str] = None
    license: Optional[str] = None
    publisher: Optional[Publisher] = None
    event: Optional[Event] = None
    editors: List[Scholar] = field(default_factory=list)
    papers: List[Paper] = field(default_factory=list)

    def year(self) -> Optional[int]:
        """
        get the year the proceedings belong to: the year of the event

        Returns:
            Optional[int]: the year, None if there is no event start date
        """
        year = None
        if self.event:
            year = self.event.year()
        return year
