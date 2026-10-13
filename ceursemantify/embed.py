"""
Created on 2026-10-13

@author: wf
"""

import re

from ceursemantify.pages import Fence, PageState


class Embedder:
    """
    embed the JSON-LD into the volume page of the proceedings chair: the
    state comment before the html element, the alternate link and the fence
    in the head; the markup of the chair is otherwise untouched
    """

    alternate_link = '<link rel="alternate" type="application/ld+json" href="index.jsonld">'
    state_pattern = re.compile(r"<!-- CEURSTATE=[^\n]*? -->\n?")
    fence_pattern = re.compile(rf"<!--\n{Fence.fence}json-ld\n.*?\n{Fence.fence}\n-->\n?", re.DOTALL)
    link_pattern = re.compile(re.escape(alternate_link) + r"\n?")
    # the state comment goes after the doctype, before the html element otherwise
    doctype_pattern = re.compile(r"<!DOCTYPE[^>]*>\n?", re.IGNORECASE)
    html_pattern = re.compile(r"<html[\s>]", re.IGNORECASE)
    head_pattern = re.compile(r"<head[^>]*>\n?", re.IGNORECASE)

    def __init__(self, state: PageState):
        """
        constructor

        Args:
            state: the state the page announces
        """
        self.state = state

    def strip(self, html_text: str) -> str:
        """
        remove the embedded parts from the given page

        Args:
            html_text: the html of a volume page

        Returns:
            str: the html without state comment, alternate link and fence
        """
        stripped = self.state_pattern.sub("", html_text)
        stripped = self.fence_pattern.sub("", stripped)
        stripped = self.link_pattern.sub("", stripped)
        return stripped

    def embed(self, html_text: str, jsonld_text: str, source: str) -> str:
        """
        embed the given JSON-LD into the given page, replacing an earlier embedding

        Args:
            html_text: the html of a volume page
            jsonld_text: the pretty printed JSON-LD
            source: what the JSON-LD was derived from e.g. the url of the volume

        Returns:
            str: the html with the JSON-LD embedded

        Raises:
            ValueError: if the page has no html or no head element
        """
        stripped = self.strip(html_text)
        html_match = self.html_pattern.search(stripped)
        head_match = self.head_pattern.search(stripped)
        if html_match is None or head_match is None:
            raise ValueError("no html or head element to embed into")
        doctype_match = self.doctype_pattern.match(stripped)
        state_at = doctype_match.end() if doctype_match else html_match.start()
        state_comment = self.state.as_html(source, state="embedded")
        inserted = f"{self.alternate_link}\n{Fence.as_html(jsonld_text)}\n"
        embedded = (
            stripped[:state_at]
            + state_comment
            + "\n"
            + stripped[state_at : head_match.end()]
            + inserted
            + stripped[head_match.end() :]
        )
        return embedded
