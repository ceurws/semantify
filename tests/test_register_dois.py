"""
Created on 2026-10-26

@author: wf
"""

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List

from tests.base_ceurtest import BaseCeurTest


class TestRegisterDois(BaseCeurTest):
    """
    register-dois.py run as a user in test mode on Vol-4298: the DataCite
    metadata it prints carries the ORCIDs of the record, see issue 52
    """

    def setUp(self, debug: bool = False, profile: bool = True) -> None:
        BaseCeurTest.setUp(self, debug=debug, profile=profile)
        self.script = os.path.join(os.path.dirname(__file__), "..", "ceursemantify", "register-dois.py")
        self.temp_dir = tempfile.mkdtemp(prefix="register-dois-")
        self.volume_dir = os.path.join(self.temp_dir, "Vol-4298")
        shutil.copytree(os.path.join(self.examples_path, "Vol-4298"), self.volume_dir)
        self.config_path = os.path.join(self.temp_dir, "register-dois.cfg")
        with open(self.config_path, "w", encoding="utf-8") as config_file:
            json.dump(
                {"apiUrl": "http://localhost:9", "apiUsername": "test", "apiPassword": "test", "doiPrefix": "10.83095"},
                config_file,
            )
        with open(os.path.join(self.volume_dir, "index.jsonld"), "r", encoding="utf-8") as record_file:
            self.record = json.load(record_file)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_script(self) -> List[Dict[str, Any]]:
        """
        run the script in test mode in the volume directory

        Returns:
            List[Dict[str, Any]]: the DataCite records it printed
        """
        result = subprocess.run(
            [sys.executable, self.script, "-t", "-c", self.config_path],
            cwd=self.volume_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        records = [ast.literal_eval(line) for line in result.stdout.splitlines() if line.startswith("{")]
        return records

    def test_orcids_reach_the_creators(self) -> None:
        """
        issue 52: every editor and author with an ORCID in index.jsonld is a
        creator with an ORCID nameIdentifier in the DataCite metadata
        """
        expected = [editor["orcid"] for editor in self.record["editors"] if editor.get("orcid")]
        for paper in self.record["papers"]:
            if paper.get("doi"):
                expected.extend(author["orcid"] for author in paper.get("authors", []) if author.get("orcid"))
        self.assertGreater(len(expected), 0, "Vol-4298 example carries no ORCIDs")
        records = self.run_script()
        # the volume and every paper with a doi and authors; the preface of Vol-4298
        # carries a doi from the test of 2026-10-15 and no authors
        papers_with_doi = sum(1 for paper in self.record["papers"] if paper.get("doi") and paper.get("authors"))
        self.assertEqual(1 + papers_with_doi, len(records))
        found = []
        for record in records:
            for creator in record["creators"]:
                for identifier in creator.get("nameIdentifiers", []):
                    if identifier.get("nameIdentifierScheme") == "ORCID":
                        # DataCite takes the ORCID as its url
                        found.append(identifier["nameIdentifier"].replace("https://orcid.org/", ""))
        self.assertEqual(sorted(expected), sorted(found))
