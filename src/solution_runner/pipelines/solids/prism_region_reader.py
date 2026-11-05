"""Read full vertex-list volume questions with explicit regular-prism dimensions."""

import re

from ..core.errors import ContentPlanError
from .prism_region import solve
from .regular_prism_geometry import VERTEX


def read(raw):
    match = re.fullmatch(
        r"Найдите объем многогранника, вершинами которого являются точки\s*((?:"
        + VERTEX
        + r"\s*,?\s*)+)правильной (треугольной|шестиугольной) призмы\s+(ABCA_1B_1C_1|ABCDEFA_1B_1C_1D_1E_1F_1)\s*,?\s*площадь основания которой равна\s+(.+?)\s*, а боковое ребро равно\s+(.+?)\.",
        raw,
    )
    if not match:
        return None
    body = "triangle" if match[2] == "треугольной" else "hexagon"
    if (
        match[3]
        != {"triangle": "ABCA_1B_1C_1", "hexagon": "ABCDEFA_1B_1C_1D_1E_1F_1"}[body]
    ):
        raise ContentPlanError("the named prism and base shape differ")
    names = tuple(re.findall(VERTEX, match[1]))
    return solve(body, names, (match[4], match[5]))
