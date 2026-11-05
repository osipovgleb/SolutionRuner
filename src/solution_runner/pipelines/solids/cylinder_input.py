"""Read whole cylinder HTML while preserving explicit volume-unit exponents."""

import re

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..triangles.right.altitude_input import _text
from ..triangles.right.altitude_solver import AltitudeSolveError


def text(html, source=None):
    if not isinstance(html, str):
        raise ContentPlanError("complete cylinder condition HTML is required")
    soup = BeautifulSoup(html, "html.parser")
    for sup in soup.find_all("sup"):
        previous = sup.previous_sibling
        if (
            sup.attrs
            or sup.find(True)
            or sup.get_text() != "3"
            or not isinstance(previous, str)
            or not re.search(r"\b(?:см|м)\s*$", previous)
        ):
            raise ContentPlanError("only a complete cubic unit exponent is supported")
        sup.replace_with("^3")
    try:
        raw = _text(str(soup), source, labels="VrhHCd").replace("ё", "е")
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
    return re.sub(r"\b(см|м)\s*\^3", r"\1^3", raw)
