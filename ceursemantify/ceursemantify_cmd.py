"""
Created on 2026-10-01

@author: wf
"""

import sys
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from typing import List, Optional

from basemkit.base_cmd import BaseCmd

import ceursemantify
from ceursemantify.endpoint import SptEndpoint
from ceursemantify.generator import Generator
from ceursemantify.site import SiteConfig, SiteReport, VolumeRanges


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
    command line interface of pyCEURsemantify:
    generate volume pages, rebuild year pages, serve the endpoint
    """

    def __init__(self):
        """
        constructor
        """
        super().__init__(Version())

    def add_arguments(self, parser: ArgumentParser) -> None:
        """
        add the arguments to the given parser

        Args:
            parser: the argument parser
        """
        super().add_arguments(parser)
        parser.add_argument(
            "volumes",
            nargs="*",
            help="volume numbers and ranges to generate, e.g. 3889 3887-3912",
        )
        parser.add_argument(
            "-y",
            "--year",
            type=int,
            action="append",
            dest="years",
            help="rebuild the page of the given year from the volumes present (can be given several times)",
        )
        parser.add_argument(
            "--regenerate",
            action="store_true",
            help="with --year: fetch and write the volumes present for the year again before rebuilding its page",
        )
        parser.add_argument("--progress", action="store_true", help="show a progress bar while generating volumes")
        parser.add_argument(
            "--serve",
            action="store_true",
            help="load all JSON-LD files into memory and serve them as SPARQL endpoint",
        )
        parser.add_argument("--host", default="127.0.0.1", help="host of the endpoint (default: %(default)s)")
        parser.add_argument("--port", type=int, default=9987, help="port of the endpoint (default: %(default)s)")
        parser.add_argument(
            "-o",
            "--output",
            default=".",
            help="directory that holds the year directories (default: current directory)",
        )
        parser.add_argument("--config", help="site configuration yaml file (default: the packaged site.yaml)")

    def show_report(self, title: str, report: SiteReport, args: Namespace) -> None:
        """
        show the given report: problems always, written files if verbose

        Args:
            title: what the report is about
            report: the report
            args: the parsed arguments
        """
        for problem in report.problems:
            print(problem, file=sys.stderr)
        if args.verbose:
            for path in report.written:
                print(path)
        if not args.quiet:
            print(f"{title}: {len(report.written)} files, {len(report.problems)} problems, {report.seconds:.1f} s")

    def handle_args(self, args: Namespace) -> bool:
        """
        handle the parsed arguments

        Args:
            args: the parsed arguments

        Returns:
            bool: True if the arguments were handled
        """
        handled = super().handle_args(args)
        if not handled:
            config = SiteConfig.of_yaml(args.config)
            generator = Generator.of_output(args.output, config)
            if args.volumes:
                numbers = VolumeRanges.numbers(args.volumes)
                report = generator.generate_volumes(numbers, progress=args.progress)
                self.show_report(f"{len(numbers)} volumes", report, args)
                handled = True
            for year in args.years or []:
                if args.regenerate:
                    report = generator.regenerate_year(year, progress=args.progress)
                else:
                    report = generator.rebuild_year(year)
                self.show_report(f"year {year}", report, args)
                handled = True
            if args.serve:
                endpoint = SptEndpoint(generator.site)
                load_report = endpoint.load()
                if not args.quiet:
                    print(
                        f"endpoint: {load_report.files} files, {load_report.triples} triples, "
                        f"{load_report.seconds:.1f} s, http://{args.host}:{args.port}/npq/{endpoint.name}"
                    )
                endpoint.serve(host=args.host, port=args.port)
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
