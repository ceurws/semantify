"""
Created on 2026-10-01

@author: wf
"""

import re

from basemkit.basetest import Basetest

import ceursemantify


class TestVersion(Basetest):
    """
    test the package version
    """

    def setUp(self, debug: bool = False, profile: bool = True) -> None:
        Basetest.setUp(self, debug=debug, profile=profile)

    def test_version(self) -> None:
        """
        test that the package version is a semantic version
        """
        version = ceursemantify.__version__
        if self.debug:
            print(version)
        self.assertIsNotNone(re.fullmatch(r"\d+\.\d+\.\d+", version))
