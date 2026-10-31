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
        match = re.match(r"\s*" + marker + r"\s*", str(first))
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
    declaration(soup)
    math_wrappers(soup)
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


def declaration(soup):
    nodes = [
        n for n in soup.contents if not isinstance(n, NavigableString) or n.strip()
    ]
    if (
        len(nodes) != 2
        or getattr(nodes[0], "name", None) != "p"
        or nodes[0].attrs
        or getattr(nodes[1], "name", None) != "ol"
    ):
        return
    paragraph, ordered = nodes
    text = " ".join(paragraph.get_text(" ", strip=True).replace("\xad", "").split())
    if not text.startswith("Дано уравнение"):
        return
    rows = ordered.find_all("li", recursive=False)
    if not rows:
        return
    rows[0].insert(0, " ")
    for node in reversed(list(paragraph.contents)):
        rows[0].insert(0, node.extract())
    paragraph.extract()


def math_wrappers(soup):
    for node in reversed(soup.find_all(("span", "p", "center"))):
        if node.attrs or not node.find_parent("li"):
            continue
        children = [c for c in node.contents if not isinstance(c, NavigableString)]
        if (
            len(children) == 1
            and children[0].name == "span"
            and set(children[0].attrs) == {"data-inline-latex"}
            and all(
                not str(c).strip(" .\n\t")
                for c in node.contents
                if isinstance(c, NavigableString)
            )
        ):
            node.unwrap()
