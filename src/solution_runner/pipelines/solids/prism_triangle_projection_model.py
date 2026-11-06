"""Orthogonal projections from isosceles and right triangular prism bases."""

import re
from dataclasses import replace

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .pyramid_model import root
from .spatial_metric_model import model

MODES = {
    "triangle_prism_line_projection_angle",
    "triangle_prism_split_edge_projection_angle",
}
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
SPLIT_HEADER = r"[ВB] основании прямой треугольной призмы ABCA_1B_1C_1 лежит равнобедренный треугольник ABC с равными сторонами AB и BC\. "
SPLIT_REQUEST = (
    r"Докажите, что (прямая KM перпендикулярна прямой AC|KM\s*=\s*KB)\. "
    r"Найдите угол между прямой KM и плоскостью ABB_1, если AB\s*=\s*(.+?), AC\s*=\s*(.+?) и AA_1\s*=\s*(.+?)\."
)
SPLIT_QUARTER = (
    SPLIT_HEADER
    + r"Точка K — середина ребра A_1B_1, а точка M делит ребро AC в отношении AM\s*:\s*MC\s*=\s*(.+?)\s*:\s*(.+?)\. "
    + SPLIT_REQUEST
)
SPLIT_HALF = (
    SPLIT_HEADER
    + r"Точки K и M — середины ребер A_1B_1 и AC соответственно\. "
    + SPLIT_REQUEST
)


def _split(groups, quarter):
    fraction = sp.Rational(1, 2)
    if quarter:
        p, q = map(positive, groups[:2])
        fraction = sp.simplify(p / (p + q))
        groups = groups[2:]
    claim, raw_a, raw_b, raw_h = groups
    perpendicular = claim.startswith("прямая")
    if perpendicular != quarter or quarter and fraction != sp.Rational(1, 4):
        raise ContentPlanError(
            "the midpoint and edge ratio do not imply the stated claim"
        )
    a, b, h = map(positive, (raw_a, raw_b, raw_h))
    altitude = root(a * a - b * b / 4)
    km = sp.sqrt(b * b * (fraction - sp.Rational(1, 4)) ** 2 + altitude**2 / 4 + h * h)
    mh = fraction * b * altitude / a
    return model(
        "triangle_prism_split_edge_projection_angle",
        (("a", a), ("b", b), ("height", h), ("fraction", fraction)),
        {
            "a": a,
            "b": b,
            "height": h,
            "fraction": fraction,
            "base_height": altitude,
            "KM": km,
            "MH": mh,
            "sine": mh / km,
            "CE": b * altitude / a,
            "base_dot": a * a - b * b / 2,
            "normal_norm": a,
            "normal_dot": fraction * b * altitude,
            "foot": b * b / (2 * a * a),
        },
        ("quarter" if quarter else "half",),
        sp.asin(mh / km),
    ), {"claim": "perpendicular" if quarter else "equal_lengths"}


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
    for pattern, solve in (
        (ISOSCELES, _isosceles),
        (RIGHT, _right),
        (SPLIT_QUARTER, lambda g: _split(g, True)),
        (SPLIT_HALF, lambda g: _split(g, False)),
    ):
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
