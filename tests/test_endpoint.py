"""
Created on 2026-10-01

@author: wf
"""

import tempfile

from ceursemantify.endpoint import SptEndpoint
from tests.base_ceurtest import BaseCeurTest


class TestEndpoint(BaseCeurTest):
    """
    test loading the JSON-LD files of a site into the endpoint graph
    """

    def test_load(self) -> None:
        """
        test that all volumes are loaded and can be queried by the year of their event
        """
        with tempfile.TemporaryDirectory() as output_dir:
            generator = self.get_generator(output_dir)
            generator.generate_volumes(list(self.example_years.keys()))
            endpoint = SptEndpoint(generator.site)
            report = endpoint.load()
            if self.debug:
                print(report)
            self.assertEqual(5, report.files)
            self.assertGreater(report.triples, 1000)
            query = """
PREFIX ceur: <https://ceur-ws.org/rdf/schema#>
PREFIX schema: <https://schema.org/>
SELECT ?number WHERE {
  ?volume a ceur:ProceedingsVolume ;
    ceur:volumeNumber ?number ;
    ceur:associatedEvent/schema:startDate ?start .
  FILTER(YEAR(?start) = 2024)
} ORDER BY ?number"""
            numbers = [int(row.number) for row in endpoint.graph.query(query)]
            self.assertEqual([3889, 4175], numbers)
