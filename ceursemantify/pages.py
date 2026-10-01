"""
Created on 2026-10-01

HTML pages of the generated site: each view has an as_html method that
escapes its values first and then fills a multiline f-string.

@author: wf
"""

import html
from dataclasses import dataclass
from datetime import date
from typing import Any, List
from urllib.parse import quote

import ceursemantify
from ceursemantify.jsonld import JsonLd
from ceursemantify.model import Paper, Proceedings, Scholar
from ceursemantify.site import SiteConfig


def esc(value: Any) -> str:
    """
    escape the given value for use in html text and attributes

    Args:
        value: the value, None gives the empty string

    Returns:
        str: the escaped text
    """
    text = "" if value is None else str(value)
    escaped = html.escape(text, quote=True)
    return escaped


class Fence:
    """
    JSON-LD as semantify³ fence in an html comment
    """

    marker = "🌐🕸"
    fence = "`" * 3

    @classmethod
    def as_html(cls, jsonld_text: str) -> str:
        """
        get the html comment with the json-ld fence

        An html comment ends at the first -->; the JSON string escape
        \\u003e for > keeps the JSON equal and the comment intact.

        Args:
            jsonld_text: the JSON-LD

        Returns:
            str: the html comment
        """
        safe_text = jsonld_text.replace("-->", "--\\u003e")
        comment = f"""<!--
{cls.fence}json-ld
{cls.marker}
{safe_text}
{cls.fence}
-->"""
        return comment


@dataclass
class PageState:
    """
    the state a page announces in its header comment
    """

    generated_on: str
    version: str = ceursemantify.__version__

    @classmethod
    def today(cls) -> "PageState":
        """
        get the state for a page generated today

        Returns:
            PageState: the state
        """
        state = cls(generated_on=date.today().isoformat())
        return state

    def as_html(self, source: str) -> str:
        """
        get the header comment

        Args:
            source: what the page was generated from

        Returns:
            str: the html comment
        """
        comment = (
            f"<!-- CEURSTATE=generated: on {self.generated_on} by pyCEURsemantify {self.version} from {source} -->"
        )
        return comment


class ScholarView:
    """
    html view of a scholar
    """

    # label, field of the scholar and formatter URI as in CrSchema
    identifier_formatters = [
        ("ORCID", "orcid", "https://orcid.org/$1"),
        ("dblp", "dblpId", "https://dblp.org/pid/$1"),
        ("Wikidata", "wikiDataId", "https://www.wikidata.org/wiki/$1"),
        ("GND", "gndId", "https://d-nb.info/gnd/$1"),
    ]

    def __init__(self, scholar: Scholar):
        """
        constructor

        Args:
            scholar: the scholar
        """
        self.scholar = scholar

    def as_html(self, css_class: str) -> str:
        """
        get the name of the scholar as a span

        Args:
            css_class: the CEUR-WS class of the span e.g. CEURAUTHOR

        Returns:
            str: the html span
        """
        name = esc(self.scholar.full_name())
        span = f"""<span class="{css_class}">{name}</span>"""
        return span

    def identifiers_as_html(self) -> str:
        """
        get the links to the identifiers of the scholar

        Returns:
            str: the html links, empty if the scholar has no identifiers
        """
        links = []
        for label, field_name, formatter in self.identifier_formatters:
            identifier = getattr(self.scholar, field_name)
            if identifier:
                url = esc(formatter.replace("$1", identifier))
                links.append(f"""<a href="{url}">{label}</a>""")
        identifiers = " ".join(links)
        return identifiers


class PaperView:
    """
    html view of a paper in the table of contents
    """

    def __init__(self, paper: Paper):
        """
        constructor

        Args:
            paper: the paper
        """
        self.paper = paper

    def pages_as_html(self) -> str:
        """
        get the page range of the paper

        Returns:
            str: the html span, empty if the paper has no pages
        """
        pages_html = ""
        if self.paper.pageStart:
            page_start = esc(self.paper.pageStart)
            page_end = esc(self.paper.pageEnd)
            pages_html = f"""<span class="CEURPAGES">{page_start}-{page_end}</span>"""
        return pages_html

    def as_html(self) -> str:
        """
        get the table of contents entry of the paper

        Returns:
            str: the html list item
        """
        paper_id = esc(self.paper.id)
        pdf_url = esc(self.paper.pdfUrl)
        title = esc(self.paper.title)
        pages = self.pages_as_html()
        authors = ",\n        ".join(ScholarView(author).as_html("CEURAUTHOR") for author in self.paper.authors)
        if self.paper.id:
            item = f"""      <li id="{paper_id}"><a href="{paper_id}/">
          <span class="CEURTITLE">{title}</span></a> {pages} <a href="{pdf_url}">PDF</a><br>
        {authors}
      </li>"""
        else:
            item = f"""      <li><a href="{pdf_url}">
          <span class="CEURTITLE">{title}</span></a> {pages}<br>
        {authors}
      </li>"""
        return item


class VolumePage:
    """
    the page of the proceedings of one volume
    """

    def __init__(self, proceedings: Proceedings, config: SiteConfig, jsonld: JsonLd, state: PageState):
        """
        constructor

        Args:
            proceedings: the proceedings
            config: the site configuration
            jsonld: the JSON-LD support of the research model
            state: the state to announce
        """
        self.proceedings = proceedings
        self.config = config
        self.jsonld = jsonld
        self.state = state

    def original_url(self) -> str:
        """
        get the url of the volume at the original site

        Returns:
            str: the url
        """
        original_url = f"{self.config.original_url}/Vol-{self.proceedings.volumeNumber}/"
        return original_url

    def page_url(self) -> str:
        """
        get the url the page is served from

        Returns:
            str: the url
        """
        page_url = f"{self.config.base_url}/{self.proceedings.year()}/Vol-{self.proceedings.volumeNumber}/"
        return page_url

    def jsonld_text(self) -> str:
        """
        get the pretty printed JSON-LD of the proceedings

        Returns:
            str: the JSON-LD
        """
        text = self.jsonld.as_text(self.proceedings)
        return text

    def head_as_html(self) -> str:
        """
        get the head of the page

        Returns:
            str: the html head element
        """
        number = esc(self.proceedings.volumeNumber)
        title = esc(self.proceedings.title)
        stylesheet = esc(self.config.stylesheet)
        fence = Fence.as_html(self.jsonld_text())
        head = f"""<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" type="text/css" href="{stylesheet}">
  <link rel="alternate" type="application/ld+json" href="index.jsonld">
  <title>CEUR-WS.org/Vol-{number} - {title}</title>
{fence}
</head>"""
        return head

    def links_as_html(self) -> str:
        """
        get the links to the original volume, its copy and the year

        Returns:
            str: the html paragraph
        """
        number = esc(self.proceedings.volumeNumber)
        year = esc(self.proceedings.year())
        original_url = esc(self.original_url())
        base_url = esc(self.config.base_url)
        links = f"""  <p class="unobtrusive">Original: <a href="{original_url}">{original_url}</a> |
    Mirror: <a href="/Vol-{number}/">{base_url}/Vol-{number}/</a> |
    Year: <a href="../">{year}</a></p>"""
        return links

    def header_as_html(self) -> str:
        """
        get the header with volume number, URN and copyright

        Returns:
            str: the html table
        """
        number = esc(self.proceedings.volumeNumber)
        urn = esc(self.proceedings.urn)
        pub_year = esc(self.proceedings.pubYear)
        license_url = esc(self.proceedings.license)
        header = f"""  <table style="border: 0; border-spacing: 0; border-collapse: collapse; width: 95%">
    <tbody>
      <tr>
        <td style="text-align: left; vertical-align: middle">
          <a href="../"><div id="CEURWSLOGO"></div></a>
        </td>
        <td style="text-align: right; vertical-align: middle">
          <span class="CEURVOLNR">Vol-{number}</span> <br>
          <span class="CEURURN">{urn}</span>
          <p class="unobtrusive copyright" style="text-align: justify">Copyright &copy; {pub_year} for
            the individual papers by the papers' authors.
            Copyright &copy; <span class="CEURPUBYEAR">{pub_year}</span> for the volume
            as a collection by its editors.
            This volume and its papers are published under
            <a href="{license_url}"><span class="CEURLIC">{license_url}</span></a>.
          </p>
        </td>
      </tr>
    </tbody>
  </table>"""
        return header

    def acronym_as_html(self) -> str:
        """
        get the acronym of the event, linked to its homepage if there is one

        Returns:
            str: the html span or link
        """
        event = self.proceedings.event
        acronym = esc(event.acronym)
        acronym_html = f"""<span class="CEURVOLACRONYM">{acronym}</span>"""
        if event.homepage:
            homepage = esc(event.homepage)
            acronym_html = f"""<a href="{homepage}">{acronym_html}</a>"""
        return acronym_html

    def colocated_as_html(self) -> str:
        """
        get the event the event of the proceedings is co-located with

        Returns:
            str: the html text, empty if the event is not co-located
        """
        colocated_html = ""
        colocated_with = self.proceedings.event.colocated_with
        if colocated_with:
            acronym = esc(colocated_with.acronym)
            colocated_html = f"""<br>
    co-located with <span class="CEURCOLOCATED">{acronym}</span>"""
        return colocated_html

    def title_as_html(self) -> str:
        """
        get the headings with acronym, title, location and time

        Returns:
            str: the html headings
        """
        acronym = self.acronym_as_html()
        title = esc(self.proceedings.title)
        colocated = self.colocated_as_html()
        location = esc(self.proceedings.event.location)
        title_html = f"""  <h1>{acronym}</h1>

  <h2>
    <span class="CEURFULLTITLE">{title}</span>{colocated}
  </h2>
  <h3><span class="CEURLOCTIME">{location}</span>.</h3>"""
        return title_html

    def editors_as_html(self) -> str:
        """
        get the editors of the proceedings

        Returns:
            str: the html paragraph and heading
        """
        editors = "<br>\n    ".join(ScholarView(editor).as_html("CEURVOLEDITOR") for editor in self.proceedings.editors)
        editors_html = f"""  <p><b>Edited by</b></p>
  <h3>
    {editors}
  </h3>"""
        return editors_html

    def toc_as_html(self) -> str:
        """
        get the table of contents

        Returns:
            str: the html division
        """
        papers = "\n".join(PaperView(paper).as_html() for paper in self.proceedings.papers)
        toc = f"""  <div class="CEURTOC">
    <h2>Table of Contents</h2>
    <ul>
{papers}
    </ul>
  </div>"""
        return toc

    def footer_as_html(self) -> str:
        """
        get the footer with publication date, series and checker link

        Returns:
            str: the html span
        """
        pub_date = esc(self.proceedings.pubDate)
        series_title = esc(self.config.series_title)
        series_issn = esc(self.config.series_issn)
        checked_url = quote(self.page_url(), safe="")
        validator_url = esc(f"{self.config.validator_url}?doc={checked_url}")
        footer = f"""  <span class="unobtrusive">
    <span class="CEURPUBDATE">{pub_date}</span>: published on {series_title} (CEUR-WS.org, ISSN {series_issn})
    |<a href="{validator_url}">valid HTML5</a>|
  </span>"""
        return footer

    def as_html(self) -> str:
        """
        get the complete page

        Returns:
            str: the html document
        """
        state = self.state.as_html("the embedded JSON-LD")
        head = self.head_as_html()
        links = self.links_as_html()
        header = self.header_as_html()
        title = self.title_as_html()
        editors = self.editors_as_html()
        toc = self.toc_as_html()
        footer = self.footer_as_html()
        page = f"""<!DOCTYPE html>
{state}
<html lang="en">

{head}

<body>
{links}

{header}

  <hr>

{title}

{editors}

  <hr>

{toc}

  <hr>
{footer}
</body>

</html>
"""
        return page


class PaperPage:
    """
    the landing page of one paper
    """

    def __init__(self, paper: Paper, proceedings: Proceedings, config: SiteConfig, jsonld: JsonLd, state: PageState):
        """
        constructor

        Args:
            paper: the paper
            proceedings: the proceedings the paper is published in
            config: the site configuration
            jsonld: the JSON-LD support of the research model
            state: the state to announce
        """
        self.paper = paper
        self.proceedings = proceedings
        self.config = config
        self.jsonld = jsonld
        self.state = state

    def jsonld_text(self) -> str:
        """
        get the pretty printed JSON-LD of the paper

        Returns:
            str: the JSON-LD
        """
        text = self.jsonld.as_text(self.paper)
        return text

    def navigation_as_html(self) -> str:
        """
        get the links to the previous and the next paper of the volume

        Returns:
            str: the html paragraph
        """
        paper_ids = [paper.id for paper in self.proceedings.papers if paper.id]
        position = paper_ids.index(self.paper.id)
        parts = []
        if position > 0:
            previous_id = esc(paper_ids[position - 1])
            parts.append(f"""<a href="../{previous_id}/" rel="prev">&laquo; {previous_id}</a>""")
        parts.append(esc(self.paper.id))
        if position < len(paper_ids) - 1:
            next_id = esc(paper_ids[position + 1])
            parts.append(f"""<a href="../{next_id}/" rel="next">{next_id} &raquo;</a>""")
        links = " | ".join(parts)
        navigation = f"""  <p>Paper: {links}</p>"""
        return navigation

    def author_as_html(self, author: Scholar) -> str:
        """
        get one author with the links to the identifiers

        Args:
            author: the author

        Returns:
            str: the html list item
        """
        view = ScholarView(author)
        name = view.as_html("CEURAUTHOR")
        identifiers = view.identifiers_as_html()
        item = f"""    <li>{name} {identifiers}</li>"""
        return item

    def as_html(self) -> str:
        """
        get the complete page

        Returns:
            str: the html document
        """
        state = self.state.as_html("the embedded JSON-LD")
        number = esc(self.proceedings.volumeNumber)
        year = esc(self.proceedings.year())
        acronym = esc(self.proceedings.event.acronym)
        paper_id = esc(self.paper.id)
        title = esc(self.paper.title)
        pdf_url = esc(self.paper.pdfUrl)
        stylesheet = esc(self.config.stylesheet)
        fence = Fence.as_html(self.jsonld_text())
        navigation = self.navigation_as_html()
        pages = PaperView(self.paper).pages_as_html()
        authors = "\n".join(self.author_as_html(author) for author in self.paper.authors)
        page = f"""<!DOCTYPE html>
{state}
<html lang="en">

<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" type="text/css" href="{stylesheet}">
  <link rel="alternate" type="application/ld+json" href="index.jsonld">
  <title>CEUR-WS.org/Vol-{number}/{paper_id} - {title}</title>
{fence}
</head>

<body>
  <p class="unobtrusive">Volume: <a href="../">Vol-{number}</a> {acronym} |
    Year: <a href="../../">{year}</a></p>
{navigation}

  <hr>

  <h1><span class="CEURTITLE">{title}</span></h1>
  <ul>
{authors}
  </ul>
  <p>{pages} <a href="{pdf_url}">PDF</a></p>

  <hr>

  <embed src="{pdf_url}" style="width:100%;height:100vh" type="application/pdf">
</body>

</html>
"""
        return page


class YearEntry:
    """
    the entry of one volume on the page of its year
    """

    def __init__(self, proceedings: Proceedings, config: SiteConfig):
        """
        constructor

        Args:
            proceedings: the proceedings
            config: the site configuration
        """
        self.proceedings = proceedings
        self.config = config

    def as_html(self) -> str:
        """
        get the entry

        Returns:
            str: the html division
        """
        number = esc(self.proceedings.volumeNumber)
        acronym = esc(self.proceedings.event.acronym)
        title = esc(self.proceedings.title)
        location = esc(self.proceedings.event.location)
        editors = esc(", ".join(editor.full_name() for editor in self.proceedings.editors))
        pub_date = esc(self.proceedings.pubDate)
        original_url = esc(f"{self.config.original_url}/Vol-{self.proceedings.volumeNumber}/")
        urn = esc(self.proceedings.urn)
        archive = esc(self.proceedings.archive)
        entry = f"""  <div class="CEURVOLUME" id="Vol-{number}">
    <h2><a href="Vol-{number}/">Vol-{number}</a> {acronym}</h2>
    <p>{title},
      {location}.<br>
      Edited by: {editors}<br>
      Published on CEUR-WS: {pub_date}<br>
      ONLINE: <a href="{original_url}">{original_url}</a><br>
      URN: <a href="https://nbn-resolving.org/{urn}">{urn}</a><br>
      ARCHIVE: <a href="{archive}">{archive}</a>
    </p>
  </div>"""
        return entry


class YearPage:
    """
    the page of one year with the volumes whose event started in that year
    """

    def __init__(
        self, year: int, proceedings_list: List[Proceedings], years: List[int], config: SiteConfig, state: PageState
    ):
        """
        constructor

        Args:
            year: the year
            proceedings_list: the proceedings of the year
            years: all years that have a page
            config: the site configuration
            state: the state to announce
        """
        self.year = year
        self.proceedings_list = proceedings_list
        self.years = years
        self.config = config
        self.state = state

    def navigation_as_html(self) -> str:
        """
        get the links to the previous and the next year, where those exist

        Returns:
            str: the html paragraph
        """
        parts = []
        previous_year = self.year - 1
        next_year = self.year + 1
        if previous_year in self.years:
            parts.append(f"""<a href="../{previous_year}/" rel="prev">&laquo; {previous_year}</a>""")
        parts.append(str(self.year))
        if next_year in self.years:
            parts.append(f"""<a href="../{next_year}/" rel="next">{next_year} &raquo;</a>""")
        links = " | ".join(parts)
        navigation = f"""  <p>Year: {links}</p>"""
        return navigation

    def entries_as_html(self) -> str:
        """
        get the entries of the volumes, the highest volume number first

        Returns:
            str: the html divisions
        """
        by_number = {proceedings.volumeNumber: proceedings for proceedings in self.proceedings_list}
        numbers = sorted(by_number.keys(), reverse=True)
        entries = "\n".join(YearEntry(by_number[number], self.config).as_html() for number in numbers)
        return entries

    def as_html(self) -> str:
        """
        get the complete page

        Returns:
            str: the html document
        """
        year = esc(self.year)
        count = len(self.proceedings_list)
        state = self.state.as_html(f"the JSON-LD of {count} volumes")
        stylesheet = esc(self.config.stylesheet)
        series_title = esc(self.config.series_title)
        original_url = esc(self.config.original_url)
        base_url = esc(self.config.base_url)
        navigation = self.navigation_as_html()
        entries = self.entries_as_html()
        page = f"""<!DOCTYPE html>
{state}
<html lang="en">

<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" type="text/css" href="{stylesheet}">
  <title>CEUR-WS.org - {series_title} of events in {year}</title>
</head>

<body>
  <h1>{series_title} of events in {year}</h1>
{navigation}
  <p class="unobtrusive">Original: <a href="{original_url}/">{original_url}/</a> |
    Mirror: <a href="/">{base_url}/</a></p>

{entries}
</body>

</html>
"""
        return page
