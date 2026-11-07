"""
Created on 2026-10-01

@author: wf
"""

import os
import shutil
import tempfile

from ceursemantify.endpoint import SptEndpoint
from ceursemantify.site import Site
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

    def test_load_flat_layout(self) -> None:
        """
        issue 18: on ceur-ws.org the volumes lie directly under www as Vol-N/index.jsonld,
        without the year level of the generated tree; --serve on that directory loads them
        """
        with tempfile.TemporaryDirectory() as www_dir:
            sources = {
                "Vol-4298": os.path.join(self.examples_path, "Vol-4298", "index.jsonld"),
                "Vol-3889": os.path.join(self.examples_path, "Vol-3889.jsonld"),
            }
            for volume, source in sources.items():
                volume_dir = os.path.join(www_dir, volume)
                os.makedirs(volume_dir)
                shutil.copy(source, os.path.join(volume_dir, "index.jsonld"))
            site = Site(www_dir, self.jsonld)
            self.assertEqual(2, len(site.jsonld_paths()))
            report = SptEndpoint(site).load()
            self.assertEqual(2, report.files)
            self.assertGreater(report.triples, 100)
