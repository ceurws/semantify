"""
Created on 2026-10-01

@author: wf
"""

from basemkit.basetest import Basetest

from ceursemantify.convert import Convert


class TestConvert(Basetest):
    """
    test the conversions of source values
    """

    def setUp(self, debug: bool = False, profile: bool = True) -> None:
        Basetest.setUp(self, debug=debug, profile=profile)

    def test_conversions(self) -> None:
        """
        test each conversion with a value of the ceur-spt JSON-LD
        """
        cases = [
            ("volume_number", "Vol-3889", 3889),
            ("volume_number", "Vol.3264", 3264),
            ("text", "Dataless\n            Tables", "Dataless Tables"),
            ("integer", "23", 23),
            ("iso_date", "2024-11-13", "2024-11-13"),
            ("wikidata_id", "http://www.wikidata.org/entity/Q131677362", "Q131677362"),
            ("wikidata_id", "Q57966547", "Q57966547"),
            ("dblp_person_id", "https://dblp.org/pid/32/7870", "32/7870"),
            ("dblp_record_id", "https://dblp.org/rec/conf/semtab/X24", "conf/semtab/X24"),
            ("file_stem", "https://ceur-ws.org/Vol-3889/paper0.pdf", "paper0"),
            ("page_start", "1-11", "1"),
            ("page_end", "1-11", "11"),
            ("page_end", "7", "7"),
        ]
        for conversion, value, expected in cases:
            with self.subTest(conversion=conversion, value=value):
                self.assertEqual(expected, getattr(Convert, conversion)(value))

    def test_errors(self) -> None:
        """
        test that values that can not be converted raise a ValueError
        """
        cases = [
            ("volume_number", "3889 papers"),
            ("integer", "first"),
            ("iso_date", "November 13, 2024"),
            ("wikidata_id", "http://www.wikidata.org/entity/P50"),
            ("file_stem", "https://ceur-ws.org/Vol-3889/"),
        ]
        for conversion, value in cases:
            with self.subTest(conversion=conversion, value=value):
                with self.assertRaises(ValueError):
                    getattr(Convert, conversion)(value)
