"""
Created on 2026-10-01

@author: wf
"""

import glob
import json
import os
import urllib.request
from dataclasses import field
from typing import Any, Dict, List, Optional

import requests
from basemkit.yamlable import lod_storable

from ceursemantify.jsonld import JsonLd
from ceursemantify.model import Proceedings


@lod_storable
class SiteConfig:
    """
    configuration of the generated site, see resources/site.yaml
    """

    base_url: str = ""
    original_url: str = ""
    spt_url: str = ""
    stylesheet: str = ""
    header: str = ""
    series_title: str = ""
    series_issn: str = ""
    validator_url: str = ""

    @classmethod
    def default_path(cls) -> str:
        """
        get the path of the default site configuration

        Returns:
            str: the path of resources/site.yaml
        """
        path = os.path.join(os.path.dirname(__file__), "resources", "site.yaml")
        return path

    @classmethod
    def of_yaml(cls, path: Optional[str] = None) -> "SiteConfig":
        """
        load the site configuration

        Args:
            path: the path of the yaml file, the default configuration if None

        Returns:
            SiteConfig: the configuration, with the path of the header
                resolved against the directory of the yaml file
        """
        if path is None:
            path = cls.default_path()
        config = cls.load_from_yaml_file(path)
        if config.header and not os.path.isabs(config.header):
            config_dir = os.path.dirname(os.path.abspath(path))
            config.header = os.path.join(config_dir, config.header)
        return config


class CeurSpt:
    """
    access to the JSON-LD of volumes as served by ceur-spt
    """

    def __init__(self, spt_url: str, timeout: float = 60.0):
        """
        constructor

        Args:
            spt_url: the base url of the service, http, https or file
            timeout: the time in seconds to wait for an answer
        """
        self.spt_url = spt_url.rstrip("/")
        self.timeout = timeout
        # one session for all requests so that the connection is kept alive
        self.session = requests.Session()

    def volume_url(self, number: int) -> str:
        """
        get the url of the JSON-LD of the volume with the given number

        Args:
            number: the volume number

        Returns:
            str: the url
        """
        volume_url = f"{self.spt_url}/Vol-{number}.jsonld"
        return volume_url

    def volume_text(self, number: int) -> str:
        """
        fetch the text of the JSON-LD of the volume with the given number

        Args:
            number: the volume number

        Returns:
            str: the text

        Raises:
            OSError: if the service does not answer or answers with an error
        """
        volume_url = self.volume_url(number)
        if volume_url.startswith("file://"):
            with urllib.request.urlopen(volume_url, timeout=self.timeout) as response:
                text = response.read().decode("utf-8")
        else:
            response = self.session.get(volume_url, timeout=self.timeout)
            response.raise_for_status()
            text = response.text
        return text

    def volume_record(self, number: int) -> Dict[str, Any]:
        """
        fetch the JSON-LD of the volume with the given number

        Args:
            number: the volume number

        Returns:
            Dict[str, Any]: the JSON-LD document

        Raises:
            OSError: if the service does not answer or answers with an error
            ValueError: if the answer is not JSON
        """
        record = json.loads(self.volume_text(number))
        return record


class VolumeRanges:
    """
    volume numbers given as numbers and ranges e.g. 3889 3887-3912
    """

    @classmethod
    def numbers(cls, ranges: List[str]) -> List[int]:
        """
        get the volume numbers of the given numbers and ranges

        Args:
            ranges: numbers such as 3889 and ranges such as 3887-3912

        Returns:
            List[int]: the sorted volume numbers without duplicates

        Raises:
            ValueError: if a range is not a number or two numbers separated by a hyphen
        """
        numbers = set()
        for volume_range in ranges:
            parts = volume_range.split("-")
            if len(parts) > 2 or not all(part.isdigit() for part in parts):
                raise ValueError(f"not a volume number or range: {volume_range}")
            first = int(parts[0])
            last = int(parts[-1])
            if last < first:
                raise ValueError(f"range ends before it starts: {volume_range}")
            numbers.update(range(first, last + 1))
        sorted_numbers = sorted(numbers)
        return sorted_numbers


@lod_storable
class SiteReport:
    """
    what a run wrote and what it could not handle
    """

    written: List[str] = field(default_factory=list)
    problems: List[str] = field(default_factory=list)
    seconds: float = 0.0


class Site:
    """
    the directory tree of the generated pages:
    <year>/index.html and <year>/Vol-<number>/index.html with index.jsonld
    """

    def __init__(self, root: str, jsonld: JsonLd):
        """
        constructor

        Args:
            root: the directory that holds the year directories
            jsonld: the JSON-LD support of the research model
        """
        self.root = root
        self.jsonld = jsonld

    def year_dir(self, year: int) -> str:
        """
        get the directory of the given year

        Args:
            year: the year

        Returns:
            str: the path
        """
        year_dir = os.path.join(self.root, str(year))
        return year_dir

    def volume_dir(self, proceedings: Proceedings) -> str:
        """
        get the directory of the given proceedings

        Args:
            proceedings: the proceedings, with a year and a volume number

        Returns:
            str: the path
        """
        volume_dir = os.path.join(self.year_dir(proceedings.year()), f"Vol-{proceedings.volumeNumber}")
        return volume_dir

    def paper_dir(self, proceedings: Proceedings, paper_id: str) -> str:
        """
        get the directory of the paper with the given id

        Args:
            proceedings: the proceedings the paper is published in
            paper_id: the id of the paper e.g. paper1

        Returns:
            str: the path
        """
        paper_dir = os.path.join(self.volume_dir(proceedings), paper_id)
        return paper_dir

    def write(self, path: str, content: str, report: SiteReport) -> None:
        """
        write the given content to the given file

        Args:
            path: the path of the file
            content: the content
            report: the report to add the path to
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as out_file:
            out_file.write(content)
        report.written.append(path)

    def jsonld_paths(self, year: Optional[int] = None) -> List[str]:
        """
        get the paths of the JSON-LD files of the volumes

        Args:
            year: the year to get the files for, all years if None

        Returns:
            List[str]: the sorted paths of the index.jsonld files
        """
        year_pattern = str(year) if year is not None else "[0-9][0-9][0-9][0-9]"
        pattern = os.path.join(self.root, year_pattern, "Vol-*", "index.jsonld")
        paths = sorted(glob.glob(pattern))
        return paths

    def volume_numbers(self, year: int) -> List[int]:
        """
        get the numbers of the volumes that are present for the given year

        Args:
            year: the year

        Returns:
            List[int]: the sorted volume numbers
        """
        names = [os.path.basename(os.path.dirname(path)) for path in self.jsonld_paths(year)]
        numbers = sorted(int(name.split("-", 1)[1]) for name in names)
        return numbers

    def read_proceedings(self, path: str) -> Proceedings:
        """
        read the proceedings of the given JSON-LD file

        Args:
            path: the path of an index.jsonld file

        Returns:
            Proceedings: the proceedings
        """
        with open(path, "r", encoding="utf-8") as jsonld_file:
            document = json.load(jsonld_file)
        proceedings = self.jsonld.proceedings(document)
        return proceedings

    def proceedings_of_year(self, year: int) -> List[Proceedings]:
        """
        get the proceedings that are present for the given year

        Args:
            year: the year

        Returns:
            List[Proceedings]: the proceedings
        """
        proceedings_list = [self.read_proceedings(path) for path in self.jsonld_paths(year)]
        return proceedings_list

    def years(self) -> List[int]:
        """
        get the years that have a directory

        Returns:
            List[int]: the sorted years
        """
        years = []
        if os.path.isdir(self.root):
            years = sorted(int(name) for name in os.listdir(self.root) if name.isdigit() and len(name) == 4)
        return years
