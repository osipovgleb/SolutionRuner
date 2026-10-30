"""Repair only the audited half-life exponent broken by source conversion."""

import re

from bs4 import BeautifulSoup

from ..probability.common import UnsupportedCondition
from .log_questions import BROKEN_DECAY_LAW, DECAY_LAW


def repaired(html):
    soup = BeautifulSoup(html, "html.parser")
    matches = [
        tag
        for tag in soup.select("[data-inline-latex]")
        if re.sub(r"\s+", "", tag["data-inline-latex"]) == "m(t)=" + BROKEN_DECAY_LAW
    ]
    if len(matches) != 1:
        raise UnsupportedCondition(
            "exactly one malformed half-life formula must be repairable"
        )
    matches[0]["data-inline-latex"] = "m(t)=" + DECAY_LAW
    return str(soup)
