"""
Created on 2026-10-01

@author: wf
"""

import glob
import sys
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from typing import List, Optional

from basemkit.base_cmd import BaseCmd

import ceursemantify
from ceursemantify.generator import PageGenerator, Volume


@dataclass
class Version:
    """
    Version information for pyCEURsemantify
    """

    name: str = "pyCEURsemantify"
    version: str = ceursemantify.__version__
    date: str = "2026-10-01"
    updated: str = "2026-10-01"
    description: str = "Semantification of the CEUR-WS publication workflow"
    authors: str = "Wolfgang Fahl"
    doc_url: str = "https://github.com/ceurws/semantify"
    chat_url: str = "https://github.com/ceurws/semantify/discussions"
    cm_url: str = "https://github.com/ceurws/semantify"


class CeurSemantifyCmd(BaseCmd):
    """
    command line interface to generate CEUR-WS year and volume pages from JSON-LD
    """

    def __init__(self):
        """
        constructor
        """
        super().__init__(Version())

    def add_arguments(self, parser: ArgumentParser) -> None:
        """
        add the arguments of the generator to the given parser

        Args:
            parser: the argument parser
        """
        super().add_arguments(parser)
        parser.add_argument("files", nargs="*", help="JSON-LD files of volumes or glob patterns")
        parser.add_argument(
            "-o",
            "--output",
            default=".",
            help="directory to write the year directories to (default: current directory)",
        )
        parser.add_argument(
            "--base-url",
            default="https://ceur-ws.wikidata.dbis.rwth-aachen.de",
            help="url the generated pages are served from (default: %(default)s)",
        )

    def expand_files(self, patterns: List[str]) -> List[str]:
        """
        expand the given file names and glob patterns

        Args:
            patterns: file names or glob patterns

        Returns:
            List[str]: the sorted list of matching files
        """
        files = set()
        for pattern in patterns:
            files.update(glob.glob(pattern, recursive=True))
        expanded = sorted(files)
        return expanded

    def handle_args(self, args: Namespace) -> bool:
        """
        handle the parsed arguments

        Args:
            args: the parsed arguments

        Returns:
            bool: True if the arguments were handled
        """
        handled = super().handle_args(args)
        if not handled and args.files:
            volumes = [Volume.of_file(path) for path in self.expand_files(args.files)]
            generator = PageGenerator(base_url=args.base_url)
            report = generator.generate(volumes, args.output)
            if not args.quiet:
                for path in report.files:
                    print(path)
                for skipped in report.skipped:
                    print(f"skipped, no event start date: {skipped}", file=sys.stderr)
            handled = True
        return handled


def main(argv: Optional[List[str]] = None) -> int:
    """
    command line entry point

    Args:
        argv: the command line arguments

    Returns:
        int: the exit code
    """
    cmd = CeurSemantifyCmd()
    exit_code = cmd.run(argv)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
