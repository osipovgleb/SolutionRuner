"""Read ordered exam subparts, including the source's explicit paragraph markers."""

import re

from bs4 import NavigableString

from ..word_problems.common import UnsupportedCondition


def paragraphs(soup):
    nodes = [
        n for n in soup.contents if not isinstance(n, NavigableString) or n.strip()
    ]
    if len(nodes) != 2 or any(
        getattr(n, "name", None) != "p" or n.attrs for n in nodes
    ):
        return
    matches = []
    for node, marker in zip(nodes, (r"[аa]\)", r"[бb6]\)")):
        first = node.contents[0] if node.contents else None
        if not isinstance(first, NavigableString):
            return
        match = re.match(r"\s*" + marker + r"\s+", str(first))
        if not match:
            return
        matches.append(match.end())
    ordered = soup.new_tag("ol", attrs={"data-layout": "source-subparts", "type": "a"})
    soup.insert(0, ordered)
    for node, end, marker in zip(nodes, matches, ("а)", "б)")):
        first = node.contents[0]
        first.replace_with(str(first)[end:])
        node.name = "li"
        node.attrs = {"data-list-marker": marker}
        ordered.append(node.extract())


def subparts(soup):
    if not soup.find("ol"):
        paragraphs(soup)
    lists = soup.find_all("ol")
    if len(lists) != 1 or lists[0].attrs != {
        "data-layout": "source-subparts",
        "type": "a",
    }:
        raise UnsupportedCondition(
            "exactly one canonical two-part exam list is required"
        )
    ordered = lists[0]
    if any(
        (isinstance(node, NavigableString) and node.strip())
        or (getattr(node, "name", None) and node.name != "li")
        for node in ordered.children
    ):
        raise UnsupportedCondition(
            "instructions outside the two subparts are not discarded"
        )
    rows = ordered.find_all("li", recursive=False)
    if len(rows) != 2 or any(
        row.attrs not in ({"data-list-marker": marker}, {"data-list-marker": alias})
        for row, marker, alias in zip(rows, ("а)", "б)"), ("a)", "b)"))
    ):
        raise UnsupportedCondition("the two exam markers must be a and b in order")
    return ordered, rows
