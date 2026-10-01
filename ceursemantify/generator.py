"""
Created on 2026-10-01

@author: wf
"""

import json
import os
import time
from typing import List, Optional

from sem3.extractor import Extractor
from tqdm import tqdm

from ceursemantify.jsonld import JsonLd
from ceursemantify.mapper import Mapper
from ceursemantify.model import Paper, Proceedings
from ceursemantify.pages import PageState, PaperPage, VolumePage, YearPage
from ceursemantify.site import CeurSpt, Site, SiteConfig, SiteReport


class Generator:
    """
    generate the pages of volumes and years of the site
    """

    def __init__(
        self,
        site: Site,
        config: SiteConfig,
        mapper: Mapper,
        jsonld: JsonLd,
        spt: CeurSpt,
        state: Optional[PageState] = None,
    ):
        """
        constructor

        Args:
            site: the directory tree to generate into
            config: the site configuration
            mapper: the mapper of the source records to the research model
            jsonld: the JSON-LD support of the research model
            spt: the service that provides the source records
            state: the state the pages announce, generated today if None
        """
        self.site = site
        self.config = config
        self.mapper = mapper
        self.jsonld = jsonld
        self.spt = spt
        self.state = state if state is not None else PageState.today()

    @classmethod
    def of_output(cls, output_dir: str, config: Optional[SiteConfig] = None) -> "Generator":
        """
        create a generator for the given output directory

        Args:
            output_dir: the directory that holds the year directories
            config: the site configuration, the default configuration if None

        Returns:
            Generator: the generator
        """
        if config is None:
            config = SiteConfig.of_yaml()
        jsonld = JsonLd.of_yaml()
        generator = cls(
            site=Site(output_dir, jsonld),
            config=config,
            mapper=Mapper.of_yaml(),
            jsonld=jsonld,
            spt=CeurSpt(config.spt_url),
        )
        return generator

    def fetch_proceedings(self, number: int, report: SiteReport) -> Optional[Proceedings]:
        """
        fetch the source record of the volume with the given number and map
        it to the research model

        Args:
            number: the volume number
            report: the report to add problems to

        Returns:
            Optional[Proceedings]: the proceedings, None if the record could not be fetched
        """
        proceedings = None
        try:
            record = self.spt.volume_record(number)
            result = self.mapper.map_record(record, "Proceedings")
            proceedings = result.target
            for paper in proceedings.papers:
                paper.publishedIn = proceedings.url
            for issue in result.issues:
                report.problems.append(f"Vol-{number}: {issue}")
        except (OSError, ValueError) as error:
            report.problems.append(f"Vol-{number}: {self.spt.volume_url(number)}: {error}")
        return proceedings

    def write_volume(self, proceedings: Proceedings, report: SiteReport) -> None:
        """
        write the page and the JSON-LD file of the given proceedings

        Args:
            proceedings: the proceedings, with a year
            report: the report to add the written files to
        """
        volume_dir = self.site.volume_dir(proceedings)
        page = VolumePage(proceedings, self.config, self.jsonld, self.state)
        self.site.write(os.path.join(volume_dir, "index.html"), page.as_html(), report)
        self.site.write(os.path.join(volume_dir, "index.jsonld"), page.jsonld_text() + "\n", report)
        for paper in proceedings.papers:
            if paper.id:
                self.write_paper(proceedings, paper, report)

    def write_paper(self, proceedings: Proceedings, paper: Paper, report: SiteReport) -> None:
        """
        write the page and the JSON-LD file of the given paper

        Args:
            proceedings: the proceedings the paper is published in
            paper: the paper, with an id
            report: the report to add the written files to
        """
        paper_dir = self.site.paper_dir(proceedings, paper.id)
        page = PaperPage(paper, proceedings, self.config, self.jsonld, self.state)
        self.site.write(os.path.join(paper_dir, "index.html"), page.as_html(), report)
        self.site.write(os.path.join(paper_dir, "index.jsonld"), page.jsonld_text() + "\n", report)

    def generate_volumes(self, numbers: List[int], progress: bool = False) -> SiteReport:
        """
        generate the pages of the volumes with the given numbers

        A volume that can not be fetched or has no event start date is not
        written and reported as a problem. Year pages are not touched.

        Args:
            numbers: the volume numbers
            progress: if True show a progress bar

        Returns:
            SiteReport: the written files, the problems and the time used
        """
        report = SiteReport()
        start = time.perf_counter()
        for number in tqdm(numbers, desc="volumes", unit="vol", disable=not progress):
            proceedings = self.fetch_proceedings(number, report)
            if proceedings is None:
                continue
            if proceedings.year() is None:
                report.problems.append(f"Vol-{number}: no event start date, the volume has no year")
                continue
            self.write_volume(proceedings, report)
        report.seconds = time.perf_counter() - start
        return report

    def rebuild_year(self, year: int) -> SiteReport:
        """
        rebuild the page of the given year from the volumes present for it

        Args:
            year: the year

        Returns:
            SiteReport: the written file, the problems and the time used
        """
        report = SiteReport()
        start = time.perf_counter()
        proceedings_list = self.site.proceedings_of_year(year)
        if proceedings_list:
            page = YearPage(year, proceedings_list, self.site.years(), self.config, self.state)
            self.site.write(os.path.join(self.site.year_dir(year), "index.html"), page.as_html(), report)
        else:
            report.problems.append(f"{year}: no volumes in {self.site.year_dir(year)}")
        report.seconds = time.perf_counter() - start
        return report

    def regenerate_year(self, year: int, progress: bool = False) -> SiteReport:
        """
        regenerate the given year: fetch and write the volumes present for
        the year again and rebuild the page of the year

        Args:
            year: the year
            progress: if True show a progress bar

        Returns:
            SiteReport: the written files, the problems and the time used
        """
        numbers = self.site.volume_numbers(year)
        report = self.generate_volumes(numbers, progress=progress)
        year_report = self.rebuild_year(year)
        report.written.extend(year_report.written)
        report.problems.extend(year_report.problems)
        report.seconds += year_report.seconds
        return report

    def round_trip(self, page_dir: str) -> bool:
        """
        check the round trip of a generated volume or paper: the JSON-LD
        extracted from the fence of index.html equals index.jsonld

        Args:
            page_dir: the directory of the volume or paper

        Returns:
            bool: True if the page has exactly one json-ld fence and the documents are equal
        """
        extractor = Extractor()
        markups = extractor.extract_from_file(os.path.join(page_dir, "index.html"))
        fences = [markup for markup in markups if markup.lang == "json-ld"]
        equal = False
        if len(fences) == 1:
            with open(os.path.join(page_dir, "index.jsonld"), "r", encoding="utf-8") as jsonld_file:
                from_file = json.load(jsonld_file)
            equal = json.loads(fences[0].code) == from_file
        return equal
