"""
Created on 2026-10-01

@author: wf
"""

import html
import json
import os
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlparse

from sem3.extractor import Extractor

import ceursemantify


class Volume:
    """
    A CEUR-WS volume as described by its JSON-LD
    """

    def __init__(self, jsonld: Dict[str, Any], source: str = ""):
        """
        constructor

        Args:
            jsonld: the JSON-LD description of the volume
            source: the path or url the JSON-LD was read from
        """
        self.jsonld = jsonld
        self.source = source

    @classmethod
    def of_file(cls, path: str) -> "Volume":
        """
        read a volume from the given JSON-LD file

        Args:
            path: the path of the JSON-LD file

        Returns:
            Volume: the volume
        """
        with open(path, "r", encoding="utf-8") as jsonld_file:
            jsonld = json.load(jsonld_file)
        volume = cls(jsonld, source=path)
        return volume

    def get(self, key: str, default: Any = None) -> Any:
        """
        get the value of the given ceur term

        Args:
            key: the term without the ceur prefix
            default: the value to return if the term is not set

        Returns:
            Any: the value
        """
        value = self.jsonld.get(f"ceur:{key}", default)
        return value

    def event_get(self, key: str, default: Any = None) -> Any:
        """
        get the value of the given ceur term of the event

        Args:
            key: the term without the ceur prefix
            default: the value to return if the term is not set

        Returns:
            Any: the value
        """
        event = self.get("event", {}) or {}
        value = event.get(f"ceur:{key}", default)
        return value

    @property
    def number(self) -> Optional[int]:
        """
        the volume number
        """
        number = None
        match = re.search(r"(\d+)", str(self.get("volume_nr", "")))
        if match:
            number = int(match.group(1))
        return number

    @property
    def year(self) -> Optional[int]:
        """
        the year of the volume: the year of the start date of the event
        """
        year = None
        match = re.match(r"(\d{4})-\d{2}-\d{2}", str(self.event_get("conference_date_start", "")))
        if match:
            year = int(match.group(1))
        return year

    @property
    def acronym(self) -> str:
        """
        the acronym of the event
        """
        acronym = self.event_get("conference_acronym", "") or ""
        return acronym

    @property
    def title(self) -> str:
        """
        the title of the proceedings
        """
        title = self.get("proceedings_title", "") or ""
        return title

    @property
    def original_url(self) -> str:
        """
        the url of the volume at ceur-ws.org
        """
        original_url = f"https://ceur-ws.org/Vol-{self.number}/"
        return original_url

    @classmethod
    def person_name(cls, person: Dict[str, Any]) -> str:
        """
        get the name of the given person

        Args:
            person: the JSON-LD description of the person

        Returns:
            str: given name and family name
        """
        parts = [person.get("ceur:given_name", ""), person.get("ceur:family_name", "")]
        name = " ".join(part.strip() for part in parts if part and part.strip())
        return name


@dataclass
class GeneratorReport:
    """
    the result of a generator run
    """

    files: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    years: List[int] = field(default_factory=list)


class PageGenerator:
    """
    generate year and volume pages from the JSON-LD of volumes
    """

    marker = "🌐🕸"
    fence = "`" * 3

    def __init__(
        self,
        base_url: str = "https://ceur-ws.wikidata.dbis.rwth-aachen.de",
        generated_on: Optional[str] = None,
    ):
        """
        constructor

        Args:
            base_url: the url the generated pages are served from
            generated_on: the ISO date to state in the header comment, today if None
        """
        self.base_url = base_url.rstrip("/")
        if generated_on is None:
            generated_on = date.today().isoformat()
        self.generated_on = generated_on
        self.version = ceursemantify.__version__

    def text(self, value: Any) -> str:
        """
        normalize whitespace and escape the given value for html

        Args:
            value: the value to show

        Returns:
            str: the html text
        """
        normalized = " ".join(str(value or "").split())
        text = html.escape(normalized)
        return text

    def state_comment(self, source: str) -> str:
        """
        get the header comment announcing the state of a page

        Args:
            source: what the page was generated from

        Returns:
            str: the html comment
        """
        comment = (
            f"<!-- CEURSTATE=generated: on {self.generated_on} by pyCEURsemantify {self.version} from {source} -->"
        )
        return comment

    def pretty_jsonld(self, volume: Volume) -> str:
        """
        get the pretty printed JSON-LD of the given volume

        Args:
            volume: the volume

        Returns:
            str: the JSON-LD with an indent of two, safe to be embedded in an html comment
        """
        pretty = json.dumps(volume.jsonld, indent=2, ensure_ascii=False)
        # an html comment ends at the first "-->"
        pretty = pretty.replace("-->", "--\\u003e")
        return pretty

    def fenced_jsonld(self, volume: Volume) -> str:
        """
        get the JSON-LD of the given volume as a semantify³ fence in an html comment

        Args:
            volume: the volume

        Returns:
            str: the html comment with the json-ld fence
        """
        fenced = f"""<!--
{self.fence}json-ld
{self.marker}
{self.pretty_jsonld(volume)}
{self.fence}
-->"""
        return fenced

    def license_html(self, volume: Volume) -> str:
        """
        get the license link of the given volume

        Args:
            volume: the volume

        Returns:
            str: the html link to the license
        """
        license_url = volume.get("license", "") or ""
        license_name = license_url
        if "creativecommons.org/licenses/by/4.0" in license_url:
            license_name = "CC BY 4.0"
        license_html = (
            f"""<a href="{self.text(license_url)}">(<span class="CEURLIC">{self.text(license_name)}</span>)</a>"""
        )
        return license_html

    def editors_html(self, volume: Volume) -> str:
        """
        get the editors of the given volume

        Args:
            volume: the volume

        Returns:
            str: one line per editor
        """
        lines = []
        for editor in volume.get("editors", []) or []:
            name = Volume.person_name(editor)
            lines.append(f"""    <span class="CEURVOLEDITOR">{self.text(name)}</span><br>""")
        editors_html = "\n".join(lines)
        return editors_html

    def paper_html(self, paper: Dict[str, Any]) -> str:
        """
        get the table of contents entry of the given paper

        Args:
            paper: the JSON-LD description of the paper

        Returns:
            str: the html list item
        """
        path = urlparse(paper.get("@id", "")).path
        paper_id = os.path.splitext(os.path.basename(path))[0]
        authors = []
        for contributor in paper.get("ceur:contributors", []) or []:
            name = Volume.person_name(contributor)
            authors.append(f"""        <span class="CEURAUTHOR">{self.text(name)}</span>""")
        authors_html = ",\n".join(authors)
        pages_html = ""
        if paper.get("ceur:pages"):
            pages_html = f"""
        <span class="CEURPAGES">{self.text(paper.get("ceur:pages"))}</span>"""
        paper_html = f"""      <li id="{self.text(paper_id)}"><a href="{self.text(path)}">
          <span class="CEURTITLE">{self.text(paper.get("ceur:title"))}</span></a>{pages_html} <br>
{authors_html}
      </li>"""
        return paper_html

    def volume_page(self, volume: Volume) -> str:
        """
        generate the page of the given volume

        Args:
            volume: the volume

        Returns:
            str: the html page
        """
        number = volume.number
        year = volume.year
        acronym = self.text(volume.acronym)
        title = self.text(volume.title)
        pub_year = self.text(volume.get("publication_year"))
        homepage = volume.event_get("conference_homepage")
        acronym_html = f"""<span class="CEURVOLACRONYM">{acronym}</span>"""
        if homepage:
            acronym_html = f"""<a href="{self.text(homepage)}">{acronym_html}</a>"""
        colocated_html = ""
        if volume.event_get("conference_colocated_with"):
            colocated_html = f"""<br>
    co-located with <span class="CEURCOLOCATED">{self.text(volume.event_get("conference_colocated_with"))}</span>"""
        papers_html = "\n".join(self.paper_html(paper) for paper in volume.get("has_paper", []) or [])
        page_url = f"{self.base_url}/{year}/Vol-{number}/"
        validator_url = f"https://validator.w3.org/nu/?doc={quote(page_url, safe='')}"
        page = f"""<!DOCTYPE html>
<!-- CEURVERSION=2020-07-09 -->
{self.state_comment("the embedded JSON-LD")}
<html lang="en">

<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" type="text/css" href="/ceur-ws.css">
  <link rel="alternate" type="application/ld+json" href="index.jsonld">
  <title>CEUR-WS.org/Vol-{number} - {title} ({acronym})</title>
{self.fenced_jsonld(volume)}
</head>
<!--CEURLANG=eng -->

<body>
  <p class="unobtrusive">Original: <a href="{volume.original_url}">{volume.original_url}</a> |
    Mirror: <a href="/Vol-{number}/">{self.base_url}/Vol-{number}/</a> |
    Year: <a href="../">{year}</a></p>

  <table style="border: 0; border-spacing: 0; border-collapse: collapse; width: 95%">
    <tbody>
      <tr>
        <td style="text-align: left; vertical-align: middle">
          <a href="../">
            <div id="CEURWSLOGO"></div>
          </a>
        </td>
        <td style="text-align: right; vertical-align: middle">
          <div style="float:left" id="CEURCCBY"></div>
          <span class="CEURVOLNR">Vol-{number}</span> <br>
          <span class="CEURURN">{self.text(volume.get("urn"))}</span>
          <p class="unobtrusive copyright" style="text-align: justify">Copyright &copy; {pub_year} for
            the individual papers by the papers' authors.
            Copyright &copy; <span class="CEURPUBYEAR">{pub_year}</span> for the volume
            as a collection by its editors.
            This volume and its papers are published under the
            Creative Commons License Attribution 4.0 International
            {self.license_html(volume)}.
          </p>
        </td>
      </tr>
    </tbody>
  </table>

  <hr>

  <h1>{acronym_html}</h1>

  <h2>
    <span class="CEURFULLTITLE">{title}</span>{colocated_html}
  </h2>
  <h3><span class="CEURLOCTIME">{self.text(volume.event_get("conference_location"))}</span>.</h3>

  <p><b>Edited by</b></p>
  <h3>
{self.editors_html(volume)}
  </h3>

  <hr>

  <div class="CEURTOC">
    <h2>Table of Contents</h2>
    <ul>
{papers_html}
    </ul>
  </div>

  <hr>
  <span class="unobtrusive">
    <span class="CEURPUBDATE">{self.text(volume.get("publication_date"))}</span>: published on CEUR Workshop Proceedings (CEUR-WS.org, ISSN 1613-0073)
    |<a href="{validator_url}">valid HTML5</a>|
  </span>
</body>

</html>
"""
        return page

    def year_entry(self, volume: Volume) -> str:
        """
        generate the entry of the given volume on its year page

        Args:
            volume: the volume

        Returns:
            str: the html of the entry
        """
        number = volume.number
        editors = ", ".join(Volume.person_name(editor) for editor in volume.get("editors", []) or [])
        urn = volume.get("urn", "") or ""
        archive = volume.get("archive", "") or ""
        entry = f"""  <div class="CEURVOLUME" id="Vol-{number}">
    <h2><a href="Vol-{number}/">Vol-{number}</a> {self.text(volume.acronym)}</h2>
    <p>{self.text(volume.title)},
      {self.text(volume.event_get("conference_location"))}.<br>
      Edited by: {self.text(editors)}<br>
      Published on CEUR-WS: {self.text(volume.get("publication_date"))}<br>
      ONLINE: <a href="{volume.original_url}">{volume.original_url}</a><br>
      URN: <a href="https://nbn-resolving.org/{self.text(urn)}">{self.text(urn)}</a><br>
      ARCHIVE: <a href="{self.text(archive)}">{self.text(archive)}</a>
    </p>
  </div>"""
        return entry

    def year_navigation(self, year: int, years: List[int]) -> str:
        """
        generate the links to the previous and next year

        Args:
            year: the year of the page
            years: all years that have a page

        Returns:
            str: the html of the navigation
        """
        parts = []
        if year - 1 in years:
            parts.append(f"""<a href="../{year - 1}/" rel="prev">&laquo; {year - 1}</a>""")
        parts.append(f"{year}")
        if year + 1 in years:
            parts.append(f"""<a href="../{year + 1}/" rel="next">{year + 1} &raquo;</a>""")
        navigation = " | ".join(parts)
        return navigation

    def year_page(self, year: int, volumes: List[Volume], years: List[int]) -> str:
        """
        generate the page of the given year

        Args:
            year: the year
            volumes: the volumes of the year
            years: all years that have a page

        Returns:
            str: the html page
        """
        volumes = sorted(volumes, key=lambda volume: volume.number, reverse=True)
        entries_html = "\n".join(self.year_entry(volume) for volume in volumes)
        page = f"""<!DOCTYPE html>
{self.state_comment(f"the JSON-LD of {len(volumes)} volumes")}
<html lang="en">

<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" type="text/css" href="/ceur-ws.css">
  <link rel="shortcut icon" href="/ceur-ws.ico">
  <title>CEUR-WS.org - CEUR Workshop Proceedings of events in {year}</title>
</head>

<body>
  <h1>CEUR Workshop Proceedings of events in {year}</h1>
  <p>Year: {self.year_navigation(year, years)}</p>
  <p class="unobtrusive">Original: <a href="https://ceur-ws.org/">https://ceur-ws.org/</a> |
    Mirror: <a href="/">{self.base_url}/</a></p>

{entries_html}
</body>

</html>
"""
        return page

    def write(self, path: str, content: str, report: GeneratorReport) -> None:
        """
        write the given content to the given path

        Args:
            path: the path of the file
            content: the content to write
            report: the report to add the path to
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as out_file:
            out_file.write(content)
        report.files.append(path)

    def generate(self, volumes: List[Volume], output_dir: str) -> GeneratorReport:
        """
        generate the year and volume pages for the given volumes

        A volume without an event start date has no year and is skipped.

        Args:
            volumes: the volumes
            output_dir: the directory to write the year directories to

        Returns:
            GeneratorReport: the files written, the volumes skipped and the years
        """
        report = GeneratorReport()
        by_year: Dict[int, List[Volume]] = {}
        for volume in volumes:
            if volume.year is None or volume.number is None:
                report.skipped.append(volume.source or str(volume.get("volume_nr")))
            else:
                by_year.setdefault(volume.year, []).append(volume)
        report.years = sorted(by_year.keys())
        for year in report.years:
            year_dir = os.path.join(output_dir, str(year))
            for volume in by_year[year]:
                volume_dir = os.path.join(year_dir, f"Vol-{volume.number}")
                self.write(os.path.join(volume_dir, "index.html"), self.volume_page(volume), report)
                self.write(os.path.join(volume_dir, "index.jsonld"), self.pretty_jsonld(volume) + "\n", report)
            self.write(os.path.join(year_dir, "index.html"), self.year_page(year, by_year[year], report.years), report)
        return report

    def round_trip(self, html_path: str, volume: Volume) -> bool:
        """
        check the round trip: the JSON-LD extracted from the generated page
        equals the JSON-LD of the volume

        Args:
            html_path: the path of the generated volume page
            volume: the volume the page was generated from

        Returns:
            bool: True if exactly one json-ld fence is found and it equals the input
        """
        extractor = Extractor()
        markups = [markup for markup in extractor.extract_from_file(html_path) if markup.lang == "json-ld"]
        ok = False
        if len(markups) == 1:
            ok = json.loads(markups[0].code) == volume.jsonld
        return ok
