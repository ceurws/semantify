"""
Created on 2026-10-01

@author: wf
"""

import os
import re
from datetime import date
from typing import Any, Optional
from urllib.parse import urlparse


class Convert:
    """
    conversions of source values to the values of the research model

    Each conversion is named in resources/ceurspt_mapping.yaml and raises a
    ValueError for a value it can not convert.
    """

    @classmethod
    def text(cls, value: Any) -> str:
        """
        normalize whitespace: line breaks and runs of blanks become one blank

        Args:
            value: the source text

        Returns:
            str: the single line text
        """
        text = " ".join(str(value).split())
        return text

    @classmethod
    def integer(cls, value: Any) -> int:
        """
        convert the given value to an integer

        Args:
            value: the source value

        Returns:
            int: the integer
        """
        integer = int(value)
        return integer

    @classmethod
    def volume_number(cls, value: Any) -> int:
        """
        get the volume number of a volume identifier such as Vol-3889

        Args:
            value: the volume identifier

        Returns:
            int: the volume number
        """
        match = re.fullmatch(r"Vol[-.]?(\d+)", str(value).strip())
        if not match:
            raise ValueError(f"not a volume identifier: {value}")
        volume_number = int(match.group(1))
        return volume_number

    @classmethod
    def iso_date(cls, value: Any) -> str:
        """
        check that the given value is an ISO date

        Args:
            value: the source date

        Returns:
            str: the date as YYYY-MM-DD
        """
        iso_date = date.fromisoformat(str(value).strip()).isoformat()
        return iso_date

    @classmethod
    def last_path_parts(cls, value: Any, marker: str) -> str:
        """
        get the part of the path of an url that follows the given marker

        Args:
            value: the url or an identifier without url
            marker: the path segment the identifier follows e.g. /pid/

        Returns:
            str: the identifier
        """
        identifier = str(value).strip()
        path = urlparse(identifier).path
        if marker in path:
            identifier = path.split(marker, 1)[1]
        return identifier

    @classmethod
    def wikidata_id(cls, value: Any) -> str:
        """
        get the Q-identifier of a Wikidata entity url or identifier

        Args:
            value: the entity url or Q-identifier

        Returns:
            str: the Q-identifier
        """
        wikidata_id = cls.last_path_parts(value, "/entity/")
        if not re.fullmatch(r"Q\d+", wikidata_id):
            raise ValueError(f"not a Wikidata identifier: {value}")
        return wikidata_id

    @classmethod
    def dblp_person_id(cls, value: Any) -> str:
        """
        get the dblp person identifier of a dblp person url

        Args:
            value: the url e.g. https://dblp.org/pid/32/7870

        Returns:
            str: the identifier e.g. 32/7870
        """
        dblp_person_id = cls.last_path_parts(value, "/pid/")
        return dblp_person_id

    @classmethod
    def dblp_record_id(cls, value: Any) -> str:
        """
        get the dblp publication identifier of a dblp record url

        Args:
            value: the url e.g. https://dblp.org/rec/conf/semtab/X24

        Returns:
            str: the identifier e.g. conf/semtab/X24
        """
        dblp_record_id = cls.last_path_parts(value, "/rec/")
        return dblp_record_id

    @classmethod
    def file_stem(cls, value: Any) -> str:
        """
        get the file name without extension of an url

        Args:
            value: the url e.g. https://ceur-ws.org/Vol-3889/paper0.pdf

        Returns:
            str: the stem e.g. paper0
        """
        path = urlparse(str(value)).path
        file_stem = os.path.splitext(os.path.basename(path))[0]
        if not file_stem:
            raise ValueError(f"no file name in: {value}")
        return file_stem

    @classmethod
    def page_part(cls, value: Any, index: int) -> Optional[str]:
        """
        get the first or last page of a page range such as 1-11

        Args:
            value: the page range or a single page
            index: 0 for the first page, -1 for the last page

        Returns:
            Optional[str]: the page
        """
        parts = [part.strip() for part in re.split(r"[-–—]+", str(value)) if part.strip()]
        if not parts:
            raise ValueError(f"no pages in: {value}")
        page_part = parts[index]
        return page_part

    @classmethod
    def page_start(cls, value: Any) -> Optional[str]:
        """
        get the first page of a page range

        Args:
            value: the page range

        Returns:
            Optional[str]: the first page
        """
        page_start = cls.page_part(value, 0)
        return page_start

    @classmethod
    def page_end(cls, value: Any) -> Optional[str]:
        """
        get the last page of a page range

        Args:
            value: the page range

        Returns:
            Optional[str]: the last page
        """
        page_end = cls.page_part(value, -1)
        return page_end
