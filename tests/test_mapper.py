"""
Created on 2026-10-01

@author: wf
"""

from tests.base_ceurtest import BaseCeurTest


class TestMapper(BaseCeurTest):
    """
    test the mapping of the ceur-spt JSON-LD to the research model
    """

    def test_examples(self) -> None:
        """
        test that the example volumes map without issues and get the year of their event
        """
        for number, year in self.example_years.items():
            with self.subTest(number=number):
                result = self.mapper.map_record(self.example_record(number), "Proceedings")
                issues = [str(issue) for issue in result.issues]
                self.assertEqual([], issues)
                self.assertEqual(number, result.target.volumeNumber)
                self.assertEqual(year, result.target.year())

    def test_vol3889(self) -> None:
        """
        test the mapped values of one volume
        """
        proceedings = self.example_proceedings(3889)
        if self.debug:
            print(proceedings.to_yaml())
        self.assertEqual("Q131677362", proceedings.wikidataid)
        self.assertEqual("2025-01-03", proceedings.pubDate)
        self.assertEqual(2024, proceedings.pubYear)
        self.assertEqual("CEUR-WS.org", proceedings.publisher.name)
        self.assertEqual("SemTab 2024", proceedings.event.acronym)
        self.assertEqual("Baltimore", proceedings.event.city.name)
        self.assertEqual("ISWC 2024", proceedings.event.colocated_with.acronym)
        self.assertEqual(8, len(proceedings.papers))
        paper = proceedings.papers[2]
        self.assertEqual("paper2", paper.id)
        self.assertEqual("Column Vocabulary Association (CVA): Semantic Interpretation of Dataless Tables", paper.title)
        self.assertEqual(("27", "42"), (paper.pageStart, paper.pageEnd))
        self.assertEqual("conf/semtab/MartoranaPKKO24", paper.dblpPublicationId)
        author = paper.authors[1]
        self.assertEqual("Tobias Kuhn", author.full_name())
        self.assertEqual("Q42027946", author.wikiDataId)
        self.assertEqual("68/6676", author.dblpId)

    def test_issues(self) -> None:
        """
        test that unknown source keys and values that can not be converted are reported
        """
        record = self.example_record(3889)
        record["ceur:new_key"] = "something"
        record["ceur:publication_date"] = "January 3rd, 2025"
        result = self.mapper.map_record(record, "Proceedings")
        issues = [str(issue) for issue in result.issues]
        self.assertEqual(2, len(issues), issues)
        self.assertTrue(any("ceur:new_key: not in the mapping table" in issue for issue in issues))
        self.assertTrue(any("ceur:publication_date" in issue for issue in issues))
        self.assertIsNone(result.target.pubDate)
