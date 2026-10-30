"""Prepare a minimal wording repair when no enlarged lens image is possible."""

import re

from bs4 import BeautifulSoup

from ..probability.common import UnsupportedCondition


def real_image_wording(html):
    soup = BeautifulSoup(html, "html.parser")
    pattern = r"\b" + "\u00ad*".join("увеличенного") + r"\b"
    count = 0
    for node in list(soup.find_all(string=True)):
        corrected, replacements = re.subn(pattern, "действительного", str(node))
        if replacements:
            node.replace_with(corrected)
            count += replacements
    if count != 1:
        raise UnsupportedCondition(
            "exactly one enlarged-image qualifier must be repairable"
        )
    return str(soup)
