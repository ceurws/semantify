"""
Created on 2026-10-01

@author: wf
"""

import time
from dataclasses import dataclass

from lodstorage.npq_endpoint import NpqEndpoint
from rdflib import Graph

from ceursemantify.site import Site


@dataclass
class LoadReport:
    """
    what was loaded into the endpoint
    """

    files: int = 0
    triples: int = 0
    seconds: float = 0.0


class SptEndpoint:
    """
    single point of truth endpoint: the JSON-LD files of the site loaded
    into memory on startup and served by the NPQ endpoint of pyLoDStorage,
    see https://cr.bitplan.com/index.php/NPQ-FakeSparql
    """

    def __init__(self, site: Site, name: str = "ceur-ws"):
        """
        constructor

        Args:
            site: the directory tree with the JSON-LD files
            name: the name the graph is served under: /npq/<name>
        """
        self.site = site
        self.name = name
        self.graph = Graph()

    def load(self) -> LoadReport:
        """
        load all JSON-LD files of the site into the graph

        Returns:
            LoadReport: number of files and triples and the time used
        """
        report = LoadReport()
        start = time.perf_counter()
        for path in self.site.jsonld_paths():
            self.graph.parse(path, format="json-ld")
            report.files += 1
        report.triples = len(self.graph)
        report.seconds = time.perf_counter() - start
        return report

    def serve(self, host: str = "127.0.0.1", port: int = 9987) -> None:
        """
        serve the graph over the SPARQL protocol

        Args:
            host: the host to listen on
            port: the port to listen on
        """
        endpoint = NpqEndpoint()
        endpoint.add_graph(self.name, self.graph)
        endpoint.run(host=host, port=port)
