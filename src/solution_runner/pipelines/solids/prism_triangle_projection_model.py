"""Orthogonal projections from isosceles and right triangular prism bases."""

import re
from dataclasses import replace

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .pyramid_model import root
from .spatial_metric_model import model

MODES = {"triangle_prism_line_projection_angle"}
HEADER = r"Основанием прямой призмы ABCA_1B_1C_1 является "
ISOSCELES = (
    HEADER
    + r"равнобедренный треугольник ABC, AB\s*=\s*AC\s*=\s*(.+?),+ BC\s*=\s*(.+?)\. Высота призмы равна (.+?)\. "
    r"(Точка M — середина ребра B_1C_1\. Докажите, что плоскость BA_1M перпендикулярна плоскости BCC_1|Докажите, что сечение призмы плоскостью, содержащей ребро AA_1 и перпендикулярной плоскости BCC_1, является квадратом)\. "
    r"Найдите угол между прямой A_1B и плоскостью BCC_1\."
)
RIGHT = (
    HEADER
    + r"прямоугольный треугольник ABC, с гипотенузой AB\s*=\s*(.+?), и катетом BC\s*=\s*(.+?)\. "
    r"Высота призмы равна (.+?)\. C_1H [−—–-] высота треугольника A_1B_1C_1\. "
    r"Докажите, что BH является проекцией прямой C_1B на плоскость ABB_1\. Найдите угол между прямой C_1B и плоскостью ABB_1\."
)


def _isosceles(groups):
    a, b, h = map(positive, groups[:3])
    altitude = root(a * a - b * b / 4)
    square = groups[3].startswith("Докажите, что сечение")
    if square and sp.simplify(altitude - h) != 0:
        raise ContentPlanError(
            "the specified perpendicular prism section is not square"
        )
    projection = sp.sqrt(h * h + b * b / 4)
    tangent = sp.simplify(altitude / projection)
    return model(
        "triangle_prism_line_projection_angle",
        (("a", a), ("b", b), ("height", h)),
        {
            "a": a,
            "b": b,
            "height": h,
            "half_base": b / 2,
            "base_height": altitude,
            "projection": projection,
            "tan": tangent,
        },
        (),
        sp.atan(tangent),
    ), {"base": "isosceles", "claim": "square" if square else "perpendicular_planes"}


def _right(groups):
    hyp, leg, h = map(positive, groups)
    other = root(hyp * hyp - leg * leg)
    altitude = other * leg / hyp
    diagonal = sp.sqrt(h * h + leg * leg)
    return model(
        "triangle_prism_line_projection_angle",
        (("hyp", hyp), ("leg", leg), ("height", h)),
        {
            "hyp": hyp,
            "leg": leg,
            "height": h,
            "other": other,
            "altitude": altitude,
            "diagonal": diagonal,
            "sine": altitude / diagonal,
        },
        (),
        sp.asin(altitude / diagonal),
    ), {"base": "right", "claim": "projection"}


def read(raw):
    for pattern, solve in ((ISOSCELES, _isosceles), (RIGHT, _right)):
        match = re.fullmatch(pattern, raw)
        if match:
            try:
                result, symbols = solve(match.groups())
                return replace(result, symbols=symbols)
            except UnsupportedCondition as exc:
                raise ContentPlanError(
                    "complete positive triangular-prism dimensions are required"
                ) from exc
    return None
