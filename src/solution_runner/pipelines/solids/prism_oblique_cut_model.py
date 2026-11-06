"""Triangle-prism midpoint and perpendicular-face sections, direct and inverse."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {
    "triangle_prism_oblique_height",
    "triangle_prism_perpendicular_area",
    "triangle_prism_perpendicular_height",
    "triangle_prism_endpoint_plane_angle",
}
MIDPOINT = (
    r"[ВB] правильной треугольной призме сторона AB основания равна (.+?), точка M [—–-] середина ребра CC_1\. "
    r"Докажите, что сечение A_1MB [—–-] равнобедренный треугольник\. Найдите высоту призмы, если площадь сечения равна (.+?)\."
)
MIDPOINT_NAMED = (
    r"[ВB] правильной треугольной призме ABCA_1B_1C_1 известно, что AB\s*=\s*(.+?)\. Плоскость α проходит через вершины A_1 и B и середину M ребра CC_1\. "
    r"Докажите, что сечение призмы ABCA_1B_1C_1 плоскостью α является равнобедренным треугольником\. Найдите высоту призмы, если площадь сечения плоскостью α равна (.+?)\."
)
NORMAL = (
    r"[ВB] правильной треугольной призме ABCA_1B_1C_1 отметили точки M и K на ребрах AA_1 и A_1B_1 соответственно\. Известно, что (AM|A_1M)\s*=\s*(.+?)\s*(MA_1|AM), A_1K\s*=\s*KB_1\. "
    r"Через точки M и K провели плоскость α перпендикулярно плоскости ABB_1(?:A_1)?\. Докажите, что плоскость α проходит через вершину C_1\. "
    r"Найдите площадь сечения призмы ABCA_1B_1C_1 плоскостью α, если все ребра призмы равны (.+?)\."
)
REVERSE = (
    r"[ВB] правильной треугольной призме ABCA_1B_1C_1 все ребра которой равны, на ребре AA_1 отмечена точка M\. Известно, что AM\s*=\s*(.+?)\s*MA_1\. "
    r"Через точки M и C_1 перпендикулярно грани ABB_1A_1 проведена плоскость α\. Докажите, что плоскость α делит ребро A_1B_1 пополам\. "
    r"Найдите высоту призмы, если площадь сечения призмы ABCA_1B_1C_1 плоскостью α равна (.+?)\."
)
ENDPOINT = (
    r"Дана правильная треугольная призма ABCA_1B_1C_1, все ребра которой равны (.+?)\. "
    r"Через точки A, C_1 и середину T ребра A_1B_1 проведена плоскость\. "
    r"Докажите, что сечение призмы указанной плоскостью является прямоугольным треугольником\. "
    r"Найдите угол между плоскостью сечения и плоскостью ABC\."
)


def section_dimensions(a, r):
    return {
        "a": a,
        "r": r,
        "top": 1 - r,
        "AM": r * a,
        "A1M": (1 - r) * a,
        "A1K": a / 2,
        "MK": a * sp.sqrt((1 - r) ** 2 + sp.Rational(1, 4)),
        "KC1": a * sp.sqrt(3) / 2,
        "area": a * a * sp.sqrt(3) / 4 * sp.sqrt((1 - r) ** 2 + sp.Rational(1, 4)),
    }


def _endpoint(raw):
    a = positive(raw)
    q = section_dimensions(a, sp.S.Zero)
    q.update(height=a, A1T=q["A1K"], AT=q["MK"], TC1=q["KC1"], AC1=a * sp.sqrt(2))
    q["tan"] = q["height"] / q["A1T"]
    return model(
        "triangle_prism_endpoint_plane_angle", (("a", a),), q, (), sp.atan(q["tan"])
    )


def _midpoint(groups):
    a, area = map(positive, groups)
    if area <= a * a * sp.sqrt(3) / 4:
        raise ContentPlanError("the section area requires a positive prism height")
    height = sp.sqrt(16 * area * area / (3 * a * a) - a * a)
    return model(
        "triangle_prism_oblique_height",
        (("a", a), ("area", area)),
        {
            "a": a,
            "area": area,
            "height": height,
            "x": height / 2,
            "base": sp.sqrt(height * height + a * a),
            "half_base": sp.sqrt(height * height + a * a) / 2,
            "side": sp.sqrt(a * a + height * height / 4),
            "altitude": a * sp.sqrt(3) / 2,
        },
        (),
        height,
    )


def _normal(groups, reverse):
    if reverse:
        coefficient, area = map(positive, groups)
        r = coefficient / (coefficient + 1)
        a = sp.sqrt(4 * area / (sp.sqrt(3) * sp.sqrt((1 - r) ** 2 + sp.Rational(1, 4))))
        first = "AM"
        given = (("coefficient", coefficient), ("area", area))
    else:
        first, coefficient, last, a = groups
        if (first, last) not in {("AM", "MA_1"), ("A_1M", "AM")}:
            raise ContentPlanError(
                "the ratio must compare the two complementary edge parts"
            )
        coefficient, a = positive(coefficient), positive(a)
        r = coefficient / (coefficient + 1) if first == "AM" else 1 / (coefficient + 1)
        area = a * a * sp.sqrt(3) / 4 * sp.sqrt((1 - r) ** 2 + sp.Rational(1, 4))
        given = (("coefficient", coefficient), ("a", a))
    return model(
        "triangle_prism_perpendicular_" + ("height" if reverse else "area"),
        given,
        section_dimensions(a, r) | {"area": area},
        ("midpoint" if reverse else "vertex", first),
        a if reverse else area,
    )


def read(raw):
    raw = raw.replace(r"\alpha", "α")
    endpoint = re.fullmatch(ENDPOINT, raw)
    if endpoint:
        try:
            return _endpoint(endpoint[1])
        except UnsupportedCondition as exc:
            raise ContentPlanError(
                "a complete positive prism edge is required"
            ) from exc
    for pattern, kind in (
        (MIDPOINT, "midpoint"),
        (MIDPOINT_NAMED, "midpoint"),
        (NORMAL, "normal"),
        (REVERSE, "reverse"),
    ):
        match = re.fullmatch(pattern, raw)
        if match:
            try:
                return (
                    _midpoint(match.groups())
                    if kind == "midpoint"
                    else _normal(match.groups(), kind == "reverse")
                )
            except UnsupportedCondition as exc:
                raise ContentPlanError(
                    "complete numeric prism measurements are required"
                ) from exc
    return None
