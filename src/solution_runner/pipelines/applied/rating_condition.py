"""Align the one audited prose weight with its explicit four-criterion formula."""

import re

from bs4 import BeautifulSoup

from ..probability.common import UnsupportedCondition


def repaired(html):
    soup = BeautifulSoup(html, "html.parser")
    count = 0
    for node in list(soup.find_all(string=True)):
        value, n = re.subn(
            r"\bв\u00ad*т\u00ad*р\u00ad*о\u00ad*е\b", "вчетверо", str(node)
        )
        if n:
            node.replace_with(value)
            count += n
    if count != 1:
        raise UnsupportedCondition(
            "exactly one audited objective-weight word must be repairable"
        )
    return str(soup)
