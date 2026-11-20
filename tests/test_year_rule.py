"""
Created on 2026-11-20

@author: wf
"""

import json
import os
import tempfile
import time
from typing import Optional

from ceursemantify.model import Proceedings
from ceursemantify.year_rule import YearRule
from tests.base_ceurtest import BaseCeurTest


class TestYearRule(BaseCeurTest):
    """
    test the rule for the year of publication of a volume, see issue 78
    """

    def volume_dir(self, www: str, number: int, pub_date: Optional[str] = None) -> str:
        """
        create the directory of a volume with a page

        Args:
            www: the directory holding the volumes
            number: the volume number
            pub_date: the content of the CEURPUBDATE mark, no mark if None

        Returns:
            str: the volume directory
        """
        volume_dir = os.path.join(www, f"Vol-{number}")
        os.makedirs(volume_dir)
        mark = f"""<span class="CEURPUBDATE">{pub_date}</span>""" if pub_date else ""
        with open(os.path.join(volume_dir, "index.html"), "w", encoding="utf-8") as page_file:
            page_file.write(f"<html><body>{mark}</body></html>")
        return volume_dir

    def set_year(self, path: str, year: int) -> None:
        """
        set the modification time of the given file to the given year

        Args:
            path: the file
            year: the year
        """
        os.utime(path, (time.mktime((year, 6, 1, 0, 0, 0, 0, 0, -1)),) * 2)

    def test_order(self) -> None:
        """
        test the order of the sources: CEURPUBDATE, volume browser,
        index.html.orig, submitted by line, oldest file
        """
        with tempfile.TemporaryDirectory() as www:
            volumes_json = os.path.join(www, "volumes.json")
            with open(volumes_json, "w", encoding="utf-8") as json_file:
                json.dump([{"number": 7, "published": "1996-12-09"}, {"number": 8, "pubDate": None}], json_file)
            rule = YearRule(volumes_json)
            volume_dir = self.volume_dir(www, 7, "28-Nov-2012")
            orig = os.path.join(volume_dir, "index.html.orig")
            with open(orig, "w", encoding="utf-8") as orig_file:
                orig_file.write("<html></html>")
            self.set_year(os.path.join(volume_dir, "index.html"), 2003)
            self.set_year(orig, 2005)
            proceedings = Proceedings(volumeNumber=7, pubDate="2012-11-28", dateSubmitted="2004-05-01")
            self.assertEqual((2012, "CEURPUBDATE"), rule.decide(proceedings, volume_dir))
            # a publication date the mapping could not parse is read from the mark of the page
            proceedings.pubDate = None
            self.assertEqual((2012, "CEURPUBDATE"), rule.decide(proceedings, volume_dir))
            with open(os.path.join(volume_dir, "index.html"), "w", encoding="utf-8") as page_file:
                page_file.write("<html></html>")
            self.set_year(os.path.join(volume_dir, "index.html"), 2003)
            rule = YearRule(volumes_json)
            self.assertEqual((1996, "volume browser"), rule.decide(proceedings, volume_dir))
            proceedings.volumeNumber = 8
            self.assertEqual((2005, "index.html.orig mtime"), rule.decide(proceedings, volume_dir))
            os.remove(orig)
            self.assertEqual((2004, "submitted by"), rule.decide(proceedings, volume_dir))
            proceedings.dateSubmitted = None
            self.assertEqual((2003, "oldest file mtime"), rule.decide(proceedings, volume_dir))
            self.assertIsNone(YearRule().decide(Proceedings(volumeNumber=8), None))

    def test_gate(self) -> None:
        """
        test the gate: a year before 1995 or after the current year and a
        year more than one year off the median of the publication years of
        the 25 volumes on each side fall to the next source
        """
        with tempfile.TemporaryDirectory() as www:
            for number in range(100, 111):
                self.volume_dir(www, number, "2018-06-01")
            rule = YearRule()
            self.assertEqual(2018, rule.neighbour_median(os.path.join(www, "Vol-105")))
            cases = [("2104-10-15", 2018), ("2015-03-15", 2018), ("2017-06-18", 2017), ("2019-01-02", 2019)]
            volume_dir = os.path.join(www, "Vol-105")
            for pub_date, expected in cases:
                with self.subTest(pub_date=pub_date):
                    with open(os.path.join(volume_dir, "index.html"), "w", encoding="utf-8") as page_file:
                        page_file.write(f"""<html><span class="CEURPUBDATE">{pub_date}</span></html>""")
                    proceedings = Proceedings(volumeNumber=105, pubDate=pub_date, dateSubmitted="2018-05-30")
                    year, _source = YearRule().decide(proceedings, volume_dir)
                    self.assertEqual(expected, year)
