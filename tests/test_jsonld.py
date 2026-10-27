"""
Created on 2026-10-01

@author: wf
"""

import dataclasses
import json
import os

from rdflib import Graph, URIRef
from rdflib.namespace import XSD

from ceursemantify import model
from tests.base_ceurtest import BaseCeurTest


class TestJsonLd(BaseCeurTest):
    """
    test the JSON-LD of the research model and its context table
    """

    def test_fields_and_terms(self) -> None:
        """
        test that the context table has exactly one term per field of each class of the model
        """
        for class_name, class_row in self.jsonld.classes.items():
            with self.subTest(class_name=class_name):
                model_class = getattr(model, class_name)
                field_names = [field.name for field in dataclasses.fields(model_class)]
                self.assertEqual(sorted(field_names), sorted(class_row["terms"].keys()))

    def test_ontology(self) -> None:
        """
        test the ceur terms of the context table against the ontology:
        a term is in the ontology unless it is listed as provisional
        """
        ontology = Graph()
        ontology.parse(os.path.join(self.project_root, "ontology", "ceur-ws.ttl"), format="turtle")
        ceur = self.jsonld.table["namespaces"]["ceur"]
        provisional = self.jsonld.table["provisional"]
        ceur_terms = set()
        for class_row in self.jsonld.classes.values():
            ceur_terms.add(class_row["type"])
            for term in class_row["terms"].values():
                ceur_terms.add(term.get("id") or term.get("reverse"))
        ceur_terms = sorted(term for term in ceur_terms if term.startswith("ceur:"))
        for term in ceur_terms:
            with self.subTest(term=term):
                iri = URIRef(ceur + term.split(":", 1)[1])
                in_ontology = (iri, None, None) in ontology
                self.assertEqual(term not in provisional, in_ontology)
        for term in provisional:
            self.assertIn(term, ceur_terms, "provisional term that the context does not use")

    def test_round_trip(self) -> None:
        """
        test that the JSON-LD of each example gives back the same proceedings
        """
        for number in self.example_years:
            with self.subTest(number=number):
                proceedings = self.example_proceedings(number)
                document = json.loads(self.jsonld.as_text(proceedings))
                self.assertEqual(proceedings, self.jsonld.proceedings(document))

    def test_doi(self) -> None:
        """
        test the DOI of a volume and a paper as decided in issue 14:
        10.83095/ceurws_xxxxx and 10.83095/ceurws_xxxxx_yyy, term ceur:doi
        """
        proceedings = self.example_proceedings(3889)
        proceedings.doi = "10.83095/ceurws_03889"
        proceedings.papers[1].doi = "10.83095/ceurws_03889_001"
        document = json.loads(self.jsonld.as_text(proceedings))
        self.assertEqual(proceedings, self.jsonld.proceedings(document))
        graph = Graph()
        graph.parse(data=self.jsonld.as_text(proceedings), format="json-ld")
        query = """
PREFIX ceur: <https://ceur-ws.org/rdf/schema#>
SELECT ?subject ?doi WHERE { ?subject ceur:doi ?doi . } ORDER BY ?doi"""
        rows = [(str(row.subject), str(row.doi)) for row in graph.query(query)]
        self.assertEqual(
            [
                ("http://ceur-ws.org/Vol-3889/", "10.83095/ceurws_03889"),
                (proceedings.papers[1].paperUrl, "10.83095/ceurws_03889_001"),
            ],
            rows,
        )

    def test_triples(self) -> None:
        """
        test the triples of the JSON-LD of one volume: types, typed values, author order
        """
        proceedings = self.example_proceedings(3889)
        graph = Graph()
        graph.parse(data=self.jsonld.as_text(proceedings), format="json-ld")
        query = """
PREFIX ceur: <https://ceur-ws.org/rdf/schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX schema: <https://schema.org/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?number ?start (COUNT(DISTINCT ?paper) AS ?papers) WHERE {
  ?volume a ceur:ProceedingsVolume ;
    ceur:volumeNumber ?number ;
    ceur:associatedEvent ?event .
  ?event a ceur:AcademicEvent ;
    schema:startDate ?start .
  ?paper a ceur:Paper ;
    dcterms:isPartOf ?volume .
} GROUP BY ?number ?start"""
        rows = list(graph.query(query))
        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual(3889, int(row.number))
        self.assertEqual(XSD.positiveInteger, row.number.datatype)
        self.assertEqual(XSD.date, row.start.datatype)
        self.assertEqual(8, int(row.papers))
        # the paper node is its landing page, see issue 32
        paper1 = next(paper for paper in proceedings.papers if paper.id == "paper1")
        author_query = f"""
PREFIX ceur: <https://ceur-ws.org/rdf/schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?family WHERE {{
  <{paper1.paperUrl}> ceur:author/rdf:rest*/rdf:first ?author .
  ?author ceur:familyName ?family .
}}"""
        families = [str(author_row.family) for author_row in graph.query(author_query)]
        self.assertEqual(["Kachroudi", "Faïz", "Baazouzi"], families)
