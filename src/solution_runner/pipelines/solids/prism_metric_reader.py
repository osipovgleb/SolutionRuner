"""Read complete metric prism questions without replacing child vertices by the parent's."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from . import regular_prism_geometry as g
from .measurements import positive
from .prism_metric_model import solve

HEADERS = {
    "hexagon": ("шестиугольной", "ABCDEFA_1B_1C_1D_1E_1F_1"),
    "triangle": ("треугольной", "ABCA_1B_1C_1"),
    "square": ("четырехугольной", "ABCDA_1B_1C_1D_1"),
}
SEGMENT = rf"(?:{g.VERTEX}){{2}}"


def _question(raw, body, edge, height=sp.S.One):
    for kind, pattern, count in (
        (
            "metric_distance",
            rf"Найдите расстояние между точками\s+({g.VERTEX})\s+и\s+({g.VERTEX})\.",
            2,
        ),
        (
            "metric_vertex_angle",
            rf"Найдите угол\s+((?:{g.VERTEX}){{3}})\. Ответ дайте в градусах\.",
            3,
        ),
        ("metric_tangent", rf"Найдите тангенс угла\s+((?:{g.VERTEX}){{3}})\.", 3),
        (
            "metric_line_angle",
            rf"[Нн]айдите угол между (?:прямыми|диагоналями)\s+({SEGMENT})\s+и\s+({SEGMENT})\. Ответ дайте в градусах\.",
            0,
        ),
    ):
        match = re.fullmatch(pattern, raw)
        if match:
            requested = match.groups() if count in (0, 2) else g.names(match[1], count)
            return solve(kind, body, edge, requested, height)
    return None


def read(raw):
    for body, (adjective, header) in HEADERS.items():
        pattern = rf"[ВB] правильной {adjective} призме {header}(?: все ребра равны\s+(.+?)\.|, все ребра которой равны\s+(.+?),)\s*(.+)"
        match = re.fullmatch(pattern, raw)
        if match:
            return _question(match[3], body, positive(match[1] or match[2]))
    match = re.fullmatch(r"[ВB] кубе ABCDA_1B_1C_1D_1\s+(.+)", raw)
    if match:
        return _question(match[1], "cube", sp.S.One)
    match = re.fullmatch(
        rf"[ВB] правильной четырехугольной призме ABCDA_1B_1C_1D_1 известно, что\s+({SEGMENT})\s*=\s*2\s*({SEGMENT})\.\s*(.+)",
        raw,
    )
    if match:
        points = g.frame("square")
        diagonal = g.names(match[1], 2)
        edge = g.names(match[2], 2)
        if (
            diagonal[0][0] == diagonal[1][0]
            or diagonal[0].endswith("_1") == diagonal[1].endswith("_1")
            or g.squared(points, match[1]) != 3
            or edge[0].endswith("_1") != edge[1].endswith("_1")
            or g.squared(points, match[2]) != 1
        ):
            raise ContentPlanError(
                "one space diagonal and one horizontal square-base edge are required"
            )
        return _question(match[3], "square", sp.S.One, sp.sqrt(2))
    return None
