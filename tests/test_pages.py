"""
Created on 2026-10-01

@author: wf
"""

import os
import tempfile

from basemkit.basetest import Basetest

from ceursemantify.pages import Header
from ceursemantify.site import SiteConfig


class TestPages(Basetest):
    """
    test the parts of the pages that are not covered by the generator tests
    """

    def setUp(self, debug: bool = False, profile: bool = True) -> None:
        Basetest.setUp(self, debug=debug, profile=profile)

    def get_config(self, snippet: str, output_dir: str) -> SiteConfig:
        """
        get a site configuration with the given header snippet

        Args:
            snippet: the content of the header snippet
            output_dir: the directory to write the snippet to

        Returns:
            SiteConfig: the default configuration with the snippet as header
        """
        config = SiteConfig.of_yaml()
        config.header = os.path.join(output_dir, "header.html")
        with open(config.header, "w", encoding="utf-8") as header_file:
            header_file.write(snippet)
        return config

    def test_default_header(self) -> None:
        """
        test that the packaged header snippet is found and completely filled
        """
        config = SiteConfig.of_yaml()
        self.assertTrue(os.path.isfile(config.header))
        header = Header(config).as_html("Proceedings of events in 2024")
        if self.debug:
            print(header)
        self.assertNotIn("{{", header)
        self.assertIn("""<h1 style="color: #363636">Proceedings of events in 2024</h1>""", header)
        self.assertIn(f"""<a href="{config.original_url}/issn-{config.series_issn}.html">""", header)
        self.assertIn(f"""src="{config.base_url}/OpenAccesslogo_200x313.png\"""", header)
        self.assertIn(f"{config.series_title} (CEUR-WS.org) is a", header)

    def test_header_values(self) -> None:
        """
        test that values are escaped and that a value can neither break the
        replacement nor introduce a placeholder
        """
        cases = [
            ("R&D <b>", "<p>R&amp;D &lt;b&gt;</p>"),
            ('say "hi"', "<p>say &quot;hi&quot;</p>"),
            ("back\\1slash \\g<0>", "<p>back&#92;1slash &#92;g&lt;0&gt;</p>"),
            ("{{ base_url }}", "<p>&#123;&#123; base_url }}</p>"),
        ]
        with tempfile.TemporaryDirectory() as output_dir:
            config = self.get_config("<p>{{title}}</p>\n", output_dir)
            header = Header(config)
            for title, expected in cases:
                with self.subTest(title=title):
                    self.assertEqual(expected, header.as_html(title))

    def test_unknown_variable(self) -> None:
        """
        test that a snippet with a variable that is not available is refused
        """
        with tempfile.TemporaryDirectory() as output_dir:
            config = self.get_config("<p>{{ title }} {{ publisher }} {{ editor }}</p>", output_dir)
            with self.assertRaises(ValueError) as context:
                Header(config).as_html("title")
            self.assertIn("unknown variables: editor, publisher", str(context.exception))

    def test_no_header(self) -> None:
        """
        test that without a snippet the header is the title as plain heading
        """
        config = SiteConfig.of_yaml()
        config.header = ""
        header = Header(config).as_html("Proceedings of events in 2024")
        self.assertEqual("  <h1>Proceedings of events in 2024</h1>", header)

    def test_relative_header(self) -> None:
        """
        test that a relative header path is resolved against the directory of the configuration
        """
        with tempfile.TemporaryDirectory() as output_dir:
            config = self.get_config("<p>{{ title }}</p>", output_dir)
            config.header = "header.html"
            config_path = os.path.join(output_dir, "site.yaml")
            config.save_to_yaml_file(config_path)
            loaded_config = SiteConfig.of_yaml(config_path)
            self.assertEqual(
                os.path.join(os.path.realpath(output_dir), "header.html"), os.path.realpath(loaded_config.header)
            )
            self.assertEqual("<p>title</p>", Header(loaded_config).as_html("title"))
