"""Repair the two audited broken renderings of kilonewton metres per second."""

import re

from bs4 import BeautifulSoup

from ..probability.common import UnsupportedCondition

UNIT = r"\frac{\text{кН}\cdot\text{м}}{\text{с}}"
TRUNCATED = r"\left(\frac{\mathrm{kH}\cdot\mathrm{M}}{\mathrm{C}}\right)\cdot"
BROKEN = r"\frac{K_HH\cdotM}{C}"


def needs_repair(tail):
    compact = re.sub(r"\s+", "", tail)
    if compact not in [UNIT + ").", BROKEN + ").", TRUNCATED]:
        raise UnsupportedCondition(
            "the power unit must be kilonewton metres per second"
        )
    return compact != UNIT + ")."


def repaired(html):
    soup = BeautifulSoup(html, "html.parser")
    matches = [
        tag
        for tag in soup.select("[data-inline-latex]")
        if re.sub(r"\s+", "", tag["data-inline-latex"]) in [BROKEN, TRUNCATED]
    ]
    if len(matches) != 1:
        raise UnsupportedCondition(
            "exactly one audited malformed power unit is required"
        )
    tag = matches[0]
    if re.sub(r"\s+", "", tag["data-inline-latex"]) == TRUNCATED:
        tag.insert_after(").")
    tag["data-inline-latex"] = UNIT
    return str(soup)
