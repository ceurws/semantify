"""
Created on 2026-11-06

@author: wf
"""

from unittest.mock import patch

from ceursemantify.index_check import IndexCheck, IndexCheckRun
from tests.base_ceurtest import BaseCeurTest


class TestIndexCheck(BaseCeurTest):
    """
    the check-index-errors gate, see issues 62 and 68
    """

    def test_team_check_only(self) -> None:
        """
        issue 68: the gate runs the check once and without pre, so that a published
        volume gets the team check the script chooses for it, never the chair check
        """
        calls = []

        def record(check: IndexCheck, volume_dir: str, pre: bool = False) -> IndexCheckRun:
            calls.append(pre)
            run = IndexCheckRun(ran=True, errors={"42"}, output="Using check-index-errors-after")
            return run

        check = IndexCheck("check-index-errors")
        with patch.object(IndexCheck, "run", record):
            errors = check.errors("/nonexistent")
        self.assertEqual([False], calls)
        self.assertEqual({"42"}, errors)
