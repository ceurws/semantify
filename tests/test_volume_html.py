"""
Created on 2026-10-13

@author: wf
"""

import os

from ceursemantify.model import Scholar
from ceursemantify.volume_html import VolumeHtml
from tests.base_ceurtest import BaseCeurTest


class TestVolumeHtml(BaseCeurTest):
    """
    test the mapping of a volume page as submitted by the proceedings chair
    to the research model
    """

    def test_scholar_of_full_name(self) -> None:
        """
        test the split of a name into first name and family name
        """
        self.assertEqual(Scholar(name="Jans", firstName="Mieke"), Scholar.of_full_name("Mieke Jans"))
        self.assertEqual(
            Scholar(name="Reyes-Román", firstName="José Fabián"), Scholar.of_full_name("José Fabián Reyes-Román")
        )
        self.assertEqual(Scholar(name="Plato"), Scholar.of_full_name(" Plato "))

    def test_vol_4280(self) -> None:
        """
        test the proceedings of the volume page of Vol-4280
        """
        volume_html = VolumeHtml.of_file(os.path.join(self.examples_path, "Vol-4280.html"))
        result = volume_html.proceedings()
        self.assertEqual([], [str(issue) for issue in result.issues])
        proceedings = result.target
        self.assertEqual(4280, proceedings.volumeNumber)
        self.assertEqual("urn:nbn:de:0074-4280-x", proceedings.urn)
        self.assertEqual(2026, proceedings.pubYear)
        self.assertEqual("2026-10-02", proceedings.pubDate)
        self.assertEqual(
            "Proceedings of the CAiSE 2026 Research Projects Exhibition (CAiSE-RPE 2026)", proceedings.title
        )
        self.assertEqual("https://ceur-ws.org/Vol-4280/", proceedings.url)
        self.assertEqual("https://ceur-ws.org/ftp-dir/Vol-4280.zip", proceedings.archive)
        self.assertEqual("https://creativecommons.org/licenses/by/4.0/", proceedings.license)
        self.assertEqual("CEUR-WS.org", proceedings.publisher.name)
        event = proceedings.event
        self.assertEqual("CAiSE-RPE 2026", event.acronym)
        self.assertEqual("CAiSE Research Projects Exhibition 2026", event.title)
        self.assertEqual("https://caise26.polimi.it/", event.homepage)
        self.assertEqual("CAiSE 2026", event.colocated_with.acronym)
        self.assertEqual("Verona, Italy, June 8-12, 2026", event.location)
        self.assertEqual("Verona", event.city.name)
        self.assertEqual("Italy", event.country.name)
        self.assertEqual("2026-06-08", event.startDate)
        self.assertEqual("2026-06-12", event.endDate)
        self.assertEqual(2026, proceedings.year())
        self.assertEqual(1, len(proceedings.editors))
        editor = proceedings.editors[0]
        self.assertEqual(("Jans", "Mieke", "0000-0002-9171-2403"), (editor.name, editor.firstName, editor.orcid))
        self.assertEqual(7, len(proceedings.papers))
        preface = proceedings.papers[0]
        self.assertEqual("preface", preface.id)
        self.assertEqual("Preface", preface.title)
        self.assertEqual("https://ceur-ws.org/Vol-4280/preface.pdf", preface.pdfUrl)
        paper1 = proceedings.papers[1]
        self.assertEqual("paper1", paper1.id)
        self.assertEqual("UNICA: Unified Network for International Cancer Advancement", paper1.title)
        self.assertEqual("https://ceur-ws.org/Vol-4280/paper1.pdf", paper1.pdfUrl)
        self.assertEqual(proceedings.url, paper1.publishedIn)
        self.assertEqual(6, len(paper1.authors))
        self.assertEqual(("Reyes-Román", "José Fabián"), (paper1.authors[0].name, paper1.authors[0].firstName))
        self.assertEqual(19, len(proceedings.papers[6].authors))

    def test_issues(self) -> None:
        """
        test that missing marks and an unparsed date are reported as issues
        and that the proceedings are still returned
        """
        text = """<html><body>
<span class="CEURVOLNR">Vol-1</span>
<h1><span class="CEURVOLACRONYM">KRDB'94</span></h1>
<h2><span class="CEURLOCTIME">Saarbrücken, Germany, in the autumn</span></h2>
<div class="CEURTOC"><ul><li id="paper1"><a href="paper1.pdf">no title mark</a></li></ul></div>
</body></html>"""
        result = VolumeHtml(text).proceedings()
        proceedings = result.target
        self.assertEqual(1, proceedings.volumeNumber)
        self.assertEqual("Saarbrücken, Germany, in the autumn", proceedings.event.location)
        self.assertIsNone(proceedings.year())
        self.assertEqual("no title mark", proceedings.papers[0].title)
        keys = sorted(issue.source_key for issue in result.issues)
        self.assertEqual(["CEURFULLTITLE", "CEURLOCTIME", "CEURPUBDATE", "CEURURN"], keys)

    def test_round_trip_with_jsonld(self) -> None:
        """
        test that the proceedings survive the JSON-LD document unchanged
        """
        proceedings = VolumeHtml.of_file(os.path.join(self.examples_path, "Vol-4280.html")).proceedings().target
        document = self.jsonld.document(proceedings)
        self.assertEqual(proceedings, self.jsonld.proceedings(document))
