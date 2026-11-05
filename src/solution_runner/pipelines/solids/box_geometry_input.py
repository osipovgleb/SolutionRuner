"""Fold explicit vertex subscripts and read complete geometric box HTML safely."""

import re

from bs4 import BeautifulSoup, Tag

from ..core.errors import ContentPlanError
from ..equations.power_arithmetic import ScalarParser
from ..probability.common import UnsupportedCondition
from ..triangles.right.altitude_input import _text
from ..triangles.right.altitude_solver import AltitudeSolveError
from .box_coordinates import IDENTIFIERS, SEGMENT

LETTERS = str.maketrans({"А": "A", "В": "B", "С": "C", "Д": "D"})


def text(html, source=None):
    if not isinstance(html, str):
        raise ContentPlanError("complete geometric box HTML is required")
    soup = BeautifulSoup(html, "html.parser")
    if soup.find("img") is not None and (not isinstance(source, str) or not source):
        raise ContentPlanError("a reviewed box figure identity is required")
    for sub in list(soup.find_all("sub")):
        previous = sub.previous_sibling
        while isinstance(previous, str) and not previous.strip():
            previous = previous.previous_sibling
        if (
            sub.attrs
            or sub.find(True) is not None
            or sub.get_text() != "1"
            or not isinstance(previous, Tag)
        ):
            raise ContentPlanError(
                "only an explicit adjacent vertex subscript one is supported"
            )
        label = previous.get_text().translate(LETTERS)
        valid = (
            previous.name == "var"
            and previous.attrs == {"data-math-identifier": previous.get_text()}
        ) or (previous.name in {"i", "em"} and not previous.attrs)
        if (
            not valid
            or previous.find(True) is not None
            or label + "_1" not in IDENTIFIERS
        ):
            raise ContentPlanError(
                "the subscript must belong to a canonical vertex identifier"
            )
        replacement = soup.new_tag("span")
        replacement["data-inline-latex"] = label + "_1"
        previous.replace_with(replacement)
        sub.decompose()
    for span in soup.select("span[data-inline-latex]"):
        span["data-inline-latex"] = span["data-inline-latex"].replace(r"\quad", " ")
    try:
        return (
            _text(str(soup), source, labels="ABCD", extra_identifiers=IDENTIFIERS)
            .replace("ё", "е")
            .replace("_{1}", "_1")
        )
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc


def assignments(raw):
    matches = list(re.finditer(rf"({SEGMENT})\s*=", raw))
    if len(matches) != 3 or raw[: matches[0].start()].strip():
        raise ContentPlanError("exactly three complete box assignments are required")
    given = []
    for i, match in enumerate(matches):
        value = raw[
            match.end() : matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        ].strip()
        if i + 1 < len(matches):
            separator = re.search(r"\s*[,;]\s*$", value)
            if separator is None:
                raise ContentPlanError("box assignments must be separated explicitly")
            value = value[: separator.start()]
        try:
            given.append((match[1], ScalarParser(value).parse()))
        except UnsupportedCondition as exc:
            raise ContentPlanError(str(exc)) from exc
    return tuple(given)
