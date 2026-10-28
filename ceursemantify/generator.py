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

from ceursemantify.embed import Embedder
from ceursemantify.index_check import IndexCheck
from ceursemantify.jsonld import JsonLd
from ceursemantify.mapper import Mapper
from ceursemantify.model import Paper, Proceedings
from ceursemantify.pages import PageState, PaperPage, VolumePage, YearPage
from ceursemantify.site import CeurSpt, Site, SiteConfig, SiteReport
from ceursemantify.volume_html import VolumeHtml


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
                paper.publish_in(proceedings.url)
            for issue in result.issues:
                report.problems.append(f"Vol-{number}: {issue}")
        except (OSError, ValueError) as error:
            report.problems.append(f"Vol-{number}: {self.spt.volume_url(number)}: {error}")
        return proceedings

    def read_proceedings(self, path: str, report: SiteReport, yaml: bool = False) -> Optional[Proceedings]:
        """
        read the proceedings from the local volume page at the given path, an
        embedded page from its JSON-LD, see issues 33 and 34; with yaml from
        the index.yaml next to the page, the human-editable record, see issue 59

        Args:
            path: the index.html of the volume or its directory
            report: the report to add problems to
            yaml: if True read the index.yaml next to the page

        Returns:
            Optional[Proceedings]: the proceedings, None if the page could not be read
        """
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        proceedings = None
        try:
            if yaml:
                proceedings = Proceedings.load_from_yaml_file(self.yaml_path(path))
            else:
                volume_html = VolumeHtml.of_file(path, self.config.original_url)
                result = volume_html.proceedings()
                proceedings = result.target
                for issue in result.issues:
                    report.problems.append(f"{path}: {issue}")
            for paper in proceedings.papers:
                paper.publish_in(proceedings.url)
        except OSError as error:
            report.problems.append(f"{path}: {error}")
        return proceedings

    @classmethod
    def yaml_path(cls, path: str) -> str:
        """
        get the path of the index.yaml next to the given index.html

        Args:
            path: the path of the index.html

        Returns:
            str: the path of the index.yaml
        """
        yaml_path = os.path.join(os.path.dirname(path), "index.yaml")
        return yaml_path

    def write_volume(self, proceedings: Proceedings, report: SiteReport, volume_dir: Optional[str] = None) -> None:
        """
        write the page and the JSON-LD file of the given proceedings

        Args:
            proceedings: the proceedings, with a year
            report: the report to add the written files to
            volume_dir: the directory to write to, the year tree of the site if None
        """
        in_place = volume_dir is not None
        if volume_dir is None:
            volume_dir = self.site.volume_dir(proceedings)
        page_path = os.path.join(volume_dir, "index.html")
        # the check of the CEUR-WS team as gate of a page that replaces the chair page, see issue 62
        check = IndexCheck(self.config.index_check, self.config.index_check_ignore)
        chair_page = None
        chair_errors = None
        if in_place and check.available and os.path.isfile(page_path):
            with open(page_path, "r", encoding="utf-8") as page_file:
                chair_page = page_file.read()
            chair_errors = check.errors(volume_dir)
            if chair_errors is None:
                report.problems.append(f"{page_path}: {check.command} did not run, no gate")
        page = VolumePage(proceedings, self.config, self.jsonld, self.state, in_place=in_place)
        self.site.write(page_path, page.as_html(), report)
        self.site.write(os.path.join(volume_dir, "index.jsonld"), page.jsonld_text() + "\n", report)
        if chair_errors is not None:
            generated_errors = check.errors(volume_dir)
            added = sorted(generated_errors - chair_errors) if generated_errors is not None else ["no run"]
            if added:
                os.replace(page_path, page_path + ".rejected")
                with open(page_path + ".rejected.txt", "w", encoding="utf-8") as check_file:
                    check_file.write(check.last_output)
                with open(page_path, "w", encoding="utf-8") as page_file:
                    page_file.write(chair_page)
                report.problems.append(
                    f"{page_path}: {check.command} reports {', '.join(added)} beyond the chair page,"
                    f" the chair page is kept, the generated page is index.html.rejected"
                )
        for paper in proceedings.papers:
            if paper.id:
                self.write_paper(proceedings, paper, report, os.path.join(volume_dir, paper.id))

    def write_paper(self, proceedings: Proceedings, paper: Paper, report: SiteReport, paper_dir: str) -> None:
        """
        write the page and the JSON-LD file of the given paper

        Args:
            proceedings: the proceedings the paper is published in
            paper: the paper, with an id
            report: the report to add the written files to
            paper_dir: the directory to write to
        """
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

    def generate_paths(
        self, paths: List[str], progress: bool = False, in_place: bool = False, yaml: bool = False
    ) -> SiteReport:
        """
        generate the pages of the volumes from their local volume pages
        instead of ceur-spt, see issues 33 and 34; the volume pages are not
        touched unless in_place is set, see issue 43: then the volume page,
        its index.jsonld and the paper pages are written into the volume
        directory itself and the year tree of the site is not used

        A volume that can not be read or has no event start date is not
        written and reported as a problem. Year pages are not touched.

        Args:
            paths: the index.html files of the volumes or their directories
            progress: if True show a progress bar
            in_place: if True write into the volume directories of the given pages
            yaml: if True read each volume from its index.yaml, see issue 59

        Returns:
            SiteReport: the written files, the problems and the time used
        """
        report = SiteReport()
        start = time.perf_counter()
        for path in tqdm(paths, desc="volumes", unit="vol", disable=not progress):
            proceedings = self.read_proceedings(path, report, yaml=yaml)
            if proceedings is None:
                continue
            if proceedings.year() is None:
                report.problems.append(f"{path}: no event start date, the volume has no year")
                continue
            volume_dir = None
            if in_place:
                volume_dir = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
            self.write_volume(proceedings, report, volume_dir)
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

    def embed_volume(self, path: str, report: SiteReport, yaml: bool = False) -> None:
        """
        embed the JSON-LD into the volume page of the proceedings chair at
        the given path and write index.jsonld next to it, see issue 28

        The page is rewritten only if the round trip holds: the proceedings
        parsed from the embedded page equal the proceedings parsed from the
        original page.

        Args:
            path: the index.html of the volume or its directory
            report: the report to add the written files and problems to
            yaml: if True also write index.yaml, the human-editable record, see issue 59
        """
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        try:
            volume_html = VolumeHtml.of_file(path, self.config.original_url)
        except OSError as error:
            report.problems.append(f"{path}: {error}")
            return
        result = volume_html.proceedings()
        proceedings = result.target
        for issue in result.issues:
            report.problems.append(f"{path}: {issue}")
        jsonld_text = self.jsonld.as_text(proceedings)
        embedder = Embedder(self.state)
        try:
            embedded = embedder.embed(volume_html.text, jsonld_text, proceedings.url or path)
        except ValueError as error:
            report.problems.append(f"{path}: {error}")
            return
        from_embedded = VolumeHtml(embedded, self.config.original_url).proceedings().target
        if from_embedded != proceedings:
            report.problems.append(f"{path}: the embedded page does not parse to the same proceedings")
            return
        self.site.write(os.path.join(os.path.dirname(path), "index.jsonld"), jsonld_text + "\n", report)
        self.site.write(path, embedded, report)
        if yaml:
            yaml_path = self.yaml_path(path)
            proceedings.save_to_yaml_file(yaml_path)
            report.written.append(yaml_path)

    def embed_volumes(self, paths: List[str], progress: bool = False, yaml: bool = False) -> SiteReport:
        """
        embed the JSON-LD into the volume pages at the given paths

        Args:
            paths: the index.html files of the volumes or their directories
            progress: if True show a progress bar
            yaml: if True also write index.yaml per volume, see issue 59

        Returns:
            SiteReport: the written files, the problems and the time used
        """
        report = SiteReport()
        start = time.perf_counter()
        for path in tqdm(paths, desc="volumes", unit="vol", disable=not progress):
            self.embed_volume(path, report, yaml=yaml)
        report.seconds = time.perf_counter() - start
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
