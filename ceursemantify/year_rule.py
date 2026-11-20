"""
Created on 2026-11-20

The rule for the year of a volume: its year of publication on CEUR-WS, see
issue 78. The order of the sources follows their measured agreement with
CEURPUBDATE on the volume pages of 2026-11-18, see SemanticLongTail issue 1.

@author: wf
"""

import json
import os
import re
import statistics
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ceursemantify.model import Proceedings


class YearRule:
    """
    decide the year of publication of a volume from its sources in order:
    the CEURPUBDATE mark, the publication date of the volume browser data,
    the modification time of index.html.orig, the date of the submitted by
    line, the modification time of the oldest file of the volume directory

    A year counts only if it lies in the range of CEUR-WS and within
    MAX_DISTANCE years of the median of the publication years of the
    NEIGHBOURS volumes on each side; else the next source is asked.
    """

    NEIGHBOURS = 25
    MAX_DISTANCE = 1
    YEAR_PATTERN = re.compile(r"(?<!\d)(\d{4})(?!\d)")
    MARK_PATTERN = re.compile(r'class="CEURPUBDATE"[^>]*>(.*?)</', re.S)

    def __init__(self, volumes_json: Optional[str] = None):
        """
        constructor

        Args:
            volumes_json: the volumes.json of the volume browser, no volume browser source if None or missing
        """
        self.volumes_json = os.path.expanduser(volumes_json) if volumes_json else None
        self.browser_years: Optional[Dict[int, Optional[int]]] = None
        self.mark_years: Dict[str, Optional[int]] = {}

    @classmethod
    def first_year(cls, text: Optional[str]) -> Optional[int]:
        """
        get the first four digit number of the given text

        Args:
            text: the text, e.g. 2024-10-24 or 28-Nov-2012

        Returns:
            Optional[int]: the number, None if there is none
        """
        year = None
        if text:
            match = cls.YEAR_PATTERN.search(text)
            if match:
                year = int(match.group(1))
        return year

    def browser_year(self, number: Optional[int]) -> Optional[int]:
        """
        get the year of the publication date of the volume browser data

        Args:
            number: the volume number

        Returns:
            Optional[int]: the year, None if the data or the date is missing
        """
        if self.browser_years is None:
            self.browser_years = {}
            if self.volumes_json and os.path.isfile(self.volumes_json):
                with open(self.volumes_json, "r", encoding="utf-8") as json_file:
                    records = json.load(json_file)
                for record in records:
                    published = record.get("published") or record.get("pubDate")
                    self.browser_years[record.get("number")] = self.first_year(published)
        year = self.browser_years.get(number)
        return year

    def mark_year(self, volume_dir: str) -> Optional[int]:
        """
        get the year of the CEURPUBDATE mark of the page of the given volume directory

        Args:
            volume_dir: the volume directory

        Returns:
            Optional[int]: the year as written, None if there is no page or no mark
        """
        if volume_dir not in self.mark_years:
            year = None
            page_path = os.path.join(volume_dir, "index.html")
            if os.path.isfile(page_path):
                with open(page_path, "rb") as page_file:
                    html = page_file.read().decode("utf-8", errors="replace")
                match = self.MARK_PATTERN.search(html)
                if match:
                    year = self.first_year(match.group(1))
            self.mark_years[volume_dir] = year
        year = self.mark_years[volume_dir]
        return year

    def neighbour_median(self, volume_dir: Optional[str]) -> Optional[int]:
        """
        get the median of the CEURPUBDATE years of the NEIGHBOURS volume
        directories on each side of the given one

        Args:
            volume_dir: the volume directory Vol-N, its neighbours lie beside it

        Returns:
            Optional[int]: the median, None if no neighbour has a publication date
        """
        median = None
        match = re.fullmatch(r"Vol-(\d+)", os.path.basename(os.path.abspath(volume_dir))) if volume_dir else None
        if match:
            number = int(match.group(1))
            www = os.path.dirname(os.path.abspath(volume_dir))
            numbers = [n for n in range(number - self.NEIGHBOURS, number + self.NEIGHBOURS + 1) if n != number]
            years = [self.mark_year(os.path.join(www, f"Vol-{n}")) for n in numbers]
            years = [year for year in years if year is not None]
            if years:
                median = int(statistics.median_low(years))
        return median

    def file_candidates(self, volume_dir: str) -> Tuple[Optional[int], Optional[int]]:
        """
        get the years of the modification times of index.html.orig and of the
        oldest file of the given volume directory

        Args:
            volume_dir: the volume directory

        Returns:
            Tuple[Optional[int], Optional[int]]: the year of index.html.orig and of the oldest file
        """
        orig_year, oldest_year = None, None
        orig = os.path.join(volume_dir, "index.html.orig")
        if os.path.isfile(orig):
            orig_year = datetime.fromtimestamp(os.path.getmtime(orig)).year
        files = [os.path.join(volume_dir, name) for name in os.listdir(volume_dir)]
        times = [os.path.getmtime(path) for path in files if os.path.isfile(path)]
        if times:
            oldest_year = datetime.fromtimestamp(min(times)).year
        return orig_year, oldest_year

    def candidates(self, proceedings: Proceedings, volume_dir: Optional[str] = None) -> List[Tuple[Optional[int], str]]:
        """
        get the year each source gives for the given proceedings, in the order of the rule

        Args:
            proceedings: the proceedings
            volume_dir: the directory of the local volume page, None if there is none

        Returns:
            List[Tuple[Optional[int], str]]: year and name of each source
        """
        has_dir = volume_dir is not None and os.path.isdir(volume_dir)
        pub_year = self.first_year(proceedings.pubDate)
        if pub_year is None and has_dir:
            pub_year = self.mark_year(volume_dir)
        orig_year, oldest_year = self.file_candidates(volume_dir) if has_dir else (None, None)
        candidates = [
            (pub_year, "CEURPUBDATE"),
            (self.browser_year(proceedings.volumeNumber), "volume browser"),
            (orig_year, "index.html.orig mtime"),
            (self.first_year(proceedings.dateSubmitted), "submitted by"),
            (oldest_year, "oldest file mtime"),
        ]
        return candidates

    def decide(self, proceedings: Proceedings, volume_dir: Optional[str] = None) -> Optional[Tuple[int, str]]:
        """
        decide the year of publication of the given proceedings: the first
        source whose year passes the gate

        Args:
            proceedings: the proceedings
            volume_dir: the directory of the local volume page, None if there is none

        Returns:
            Optional[Tuple[int, str]]: the year and its source, None if no source passes
        """
        decision = None
        median = self.neighbour_median(volume_dir)
        for year, source in self.candidates(proceedings, volume_dir):
            plausible = Proceedings.plausible_year(year)
            if plausible and (median is None or abs(year - median) <= self.MAX_DISTANCE):
                decision = (year, source)
                break
        return decision
