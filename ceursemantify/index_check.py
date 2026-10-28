"""
Created on 2026-10-28

@author: wf
"""

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class IndexCheckRun:
    """
    the result of one run of the check on a volume directory
    """

    ran: bool = False
    errors: Set[str] = field(default_factory=set)
    output: str = ""


class IndexCheck:
    """
    check-index-errors of the CEUR-WS team as gate of a generated volume page, see issue 62

    The check reports by ERROR (rule) lines and gives no exit status, so the
    rule ids are read from its output. A run counts only when the check
    announced itself, either as the chair check or as the team check.
    """

    error_pattern = re.compile(r"ERROR \(([A-Za-z0-9]+)\)")
    banner_pattern = re.compile(r"check-index-errors V|Using check-index-errors-after")

    def __init__(self, command: str, ignore: Optional[List[str]] = None, timeout: int = 300):
        """
        constructor

        Args:
            command: the name or path of the check
            ignore: the rule ids the gate does not count
            timeout: the seconds one run may take
        """
        self.command = command
        self.ignore = set(ignore or [])
        self.timeout = timeout
        self.path = shutil.which(command) if command else None
        self.last_output = ""

    @property
    def available(self) -> bool:
        """
        Returns:
            bool: True if the check is on the PATH
        """
        available = self.path is not None
        return available

    def run(self, volume_dir: str, pre: bool = False) -> IndexCheckRun:
        """
        run the check in the given volume directory

        Args:
            volume_dir: the directory holding the index.html to check
            pre: if True run the chair check also where the team check would be chosen

        Returns:
            IndexCheckRun: whether the check ran, the rule ids it reported and its output
        """
        args = [self.path, "pre"] if pre else [self.path]
        run = IndexCheckRun()
        try:
            completed = subprocess.run(
                args, cwd=volume_dir, capture_output=True, text=True, timeout=self.timeout, check=False
            )
            run.output = completed.stdout + completed.stderr
            run.ran = self.banner_pattern.search(run.output) is not None
            run.errors = set(self.error_pattern.findall(run.output)) - self.ignore
        except (OSError, subprocess.TimeoutExpired) as error:
            run.output = str(error)
        return run

    def errors(self, volume_dir: str) -> Optional[Set[str]]:
        """
        get the rule ids the team check and the chair check report in the given volume directory

        Args:
            volume_dir: the directory holding the index.html to check

        Returns:
            Optional[Set[str]]: the rule ids, None if the check did not run
        """
        errors = None
        runs = [self.run(volume_dir), self.run(volume_dir, pre=True)]
        if all(run.ran for run in runs):
            errors = runs[0].errors | runs[1].errors
        self.last_output = "\n".join(run.output for run in runs)
        return errors
